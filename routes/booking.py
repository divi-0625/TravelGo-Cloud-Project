from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app, make_response,
)
from functools import wraps
from datetime import datetime, timezone
from io import BytesIO
from xhtml2pdf import pisa
import qrcode
import base64

booking_bp = Blueprint("booking", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to book.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _get_models():
    return current_app.extensions["models"]


def _generate_qr_base64(data_str):
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#4338ca", back_color="#ffffff")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")



@booking_bp.route("/book/<item_type>/<item_id>", methods=["GET", "POST"])
@login_required
def book(item_type, item_id):
    models = _get_models()

    model_map = {
        "flights": models["flights"],
        "hotels": models["hotels"],
        "trains": models["trains"],
        "buses": models["buses"],
    }
    model = model_map.get(item_type)
    if not model:
        flash("Invalid booking type.", "danger")
        return redirect(url_for("main.home"))

    item = model.find_by_id(item_id)
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for("main.home"))

    if request.method == "POST":
        date = request.form.get("date", "")
        passengers = int(request.form.get("passengers", 1))
        seat_pref = request.form.get("seat_preference", "")

        if models["bookings"].is_duplicate(
            session["user_id"], item_type, item_id, date
        ):
            flash("You already have a booking for this on the same date.", "warning")
            return redirect(url_for("booking.book", item_type=item_type, item_id=item_id))

        if item.get("availability", 0) < passengers:
            flash("Not enough availability.", "danger")
            return redirect(url_for("booking.book", item_type=item_type, item_id=item_id))

        total_price = item["price"] * passengers

        session["pending_booking"] = {
            "item_type": item_type,
            "item_id": str(item["_id"]),
            "item_name": item.get("name", item.get("airline", item.get("operator", "N/A"))),
            "source": item.get("source", ""),
            "destination": item.get("destination", ""),
            "date": date,
            "passengers": passengers,
            "seat_preference": seat_pref,
            "price_per_unit": item["price"],
            "total_price": total_price,
        }

        return redirect(url_for("booking.payment"))

    return render_template("booking.html", item=item, item_type=item_type)



@booking_bp.route("/payment", methods=["GET", "POST"])
@login_required
def payment():
    models = _get_models()
    pending = session.get("pending_booking")

    if not pending:
        flash("No pending booking found. Please start a new booking.", "warning")
        return redirect(url_for("search.search_page"))

    if request.method == "POST":
        payment_method = request.form.get("payment_method", "card")
        card_number = request.form.get("card_number", "")
        card_expiry = request.form.get("card_expiry", "")
        card_cvv = request.form.get("card_cvv", "")
        card_name = request.form.get("card_name", "")
        upi_id = request.form.get("upi_id", "")

        if payment_method == "card":
            if not card_number or not card_expiry or not card_cvv or not card_name:
                flash("Please fill in all card details.", "danger")
                return redirect(url_for("booking.payment"))
            clean_card = card_number.replace(" ", "").replace("-", "")
            if len(clean_card) < 13 or len(clean_card) > 19 or not clean_card.isdigit():
                flash("Invalid card number.", "danger")
                return redirect(url_for("booking.payment"))
        elif payment_method == "upi":
            if not upi_id or "@" not in upi_id:
                flash("Please enter a valid UPI ID.", "danger")
                return redirect(url_for("booking.payment"))

        item_type = pending["item_type"]
        item_id = pending["item_id"]

        model_map = {
            "flights": models["flights"],
            "hotels": models["hotels"],
            "trains": models["trains"],
            "buses": models["buses"],
        }
        model = model_map.get(item_type)
        item = model.find_by_id(item_id) if model else None
        if not item:
            flash("Item no longer available.", "danger")
            session.pop("pending_booking", None)
            return redirect(url_for("search.search_page"))

        if item.get("availability", 0) < pending["passengers"]:
            flash("Seats/rooms no longer available.", "danger")
            session.pop("pending_booking", None)
            return redirect(url_for("search.search_page"))

        payment_info = {
            "method": payment_method,
            "status": "success",
            "paid_at": datetime.now(timezone.utc),
        }
        if payment_method == "card":
            payment_info["card_last4"] = card_number.replace(" ", "")[-4:]
            payment_info["card_name"] = card_name
        elif payment_method == "upi":
            payment_info["upi_id"] = upi_id
        elif payment_method == "netbanking":
            payment_info["bank"] = request.form.get("bank_name", "N/A")

        booking_data = {
            "user_id": session["user_id"],
            "username": session["username"],
            "item_type": item_type,
            "item_id": str(item["_id"]),
            "item_name": pending["item_name"],
            "source": pending["source"],
            "destination": pending["destination"],
            "date": pending["date"],
            "passengers": pending["passengers"],
            "seat_preference": pending["seat_preference"],
            "price": pending["total_price"],
            "payment": payment_info,
            "status": "confirmed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = models["bookings"].create(booking_data)
        model.decrement_availability(item_id, pending["passengers"])

        models["notifications"].create(
            session["user_id"],
            f"Payment of ₹{pending['total_price']:,.2f} successful via {payment_method.upper()}!",
            "success",
        )

        models["notifications"].create(
            session["user_id"],
            f"Booking confirmed! {item_type.title()} to {pending.get('destination', 'N/A')} on {pending['date']}. Total: ₹{pending['total_price']:,.2f}",
            "success",
        )

        models["notifications"].create(
            session["user_id"],
            f"Reminder: Your trip to {pending.get('destination', 'N/A')} is on {pending['date']}. Don't forget to pack!",
            "reminder",
        )

        sns_arn = current_app.config.get("SNS_TOPIC_ARN")
        if sns_arn:
            try:
                sns = current_app.extensions["sns"]
                sns.publish(
                    TopicArn=sns_arn,
                    Subject="TravelGo Booking Confirmed",
                    Message=(
                        f"Booking ID: {result.inserted_id}\n"
                        f"Type: {item_type.title()}\n"
                        f"Item: {pending['item_name']}\n"
                        f"Route: {pending.get('source', '')} → {pending.get('destination', 'N/A')}\n"
                        f"Date: {pending['date']}\n"
                        f"Passengers: {pending['passengers']}\n"
                        f"Total Paid: Rs. {pending['total_price']:,.2f}\n"
                        f"Payment: {payment_method.upper()}"
                    ),
                )
            except Exception:
                pass

        session.pop("pending_booking", None)

        flash("Payment successful! Booking confirmed!", "success")
        return redirect(url_for("booking.confirmation", booking_id=str(result.inserted_id)))

    return render_template("payment.html", booking=pending)



@booking_bp.route("/booking/confirmation/<booking_id>")
@login_required
def confirmation(booking_id):
    models = _get_models()
    booking = models["bookings"].find_by_id(booking_id)
    if not booking or booking["user_id"] != session["user_id"]:
        flash("Booking not found.", "danger")
        return redirect(url_for("main.dashboard"))
    return render_template("confirmation.html", booking=booking)



@booking_bp.route("/booking/cancel/<booking_id>", methods=["POST"])
@login_required
def cancel(booking_id):
    models = _get_models()
    booking = models["bookings"].find_by_id(booking_id)
    if not booking or booking["user_id"] != session["user_id"]:
        flash("Booking not found.", "danger")
        return redirect(url_for("main.dashboard"))

    models["bookings"].cancel(booking_id)

    models["notifications"].create(
        session["user_id"],
        f"Your booking for {booking.get('item_name', 'N/A')} on {booking.get('date', '')} has been cancelled.",
        "info",
    )

    payment = booking.get("payment", {})
    refund_method = payment.get("method", "original payment method").upper()
    models["notifications"].create(
        session["user_id"],
        f"Refund of ₹{booking.get('price', 0):,.2f} initiated to your {refund_method}. It may take 5-7 business days.",
        "info",
    )

    sns_arn = current_app.config.get("SNS_TOPIC_ARN")
    if sns_arn:
        try:
            sns = current_app.extensions["sns"]
            sns.publish(
                TopicArn=sns_arn,
                Subject="TravelGo Booking Cancelled",
                Message=(
                    f"Booking ID: {booking_id}\n"
                    f"Item: {booking.get('item_name', 'N/A')}\n"
                    f"Date: {booking.get('date', '')}\n"
                    f"Refund: Rs. {booking.get('price', 0):,.2f} to {refund_method}"
                ),
            )
        except Exception:
            pass

    flash("Booking cancelled. Refund has been initiated.", "info")
    return redirect(url_for("main.dashboard"))



@booking_bp.route("/booking/download/<booking_id>")
@login_required
def download(booking_id):
    models = _get_models()
    booking = models["bookings"].find_by_id(booking_id)
    if not booking or booking["user_id"] != session["user_id"]:
        flash("Booking not found.", "danger")
        return redirect(url_for("main.dashboard"))

    type_labels = {
        "flights": "Flight", "hotels": "Hotel",
        "trains": "Train", "buses": "Bus",
    }
    type_icons = {
        "flights": "&#9992;", "hotels": "&#127976;",
        "trains": "&#128646;", "buses": "&#128652;",
    }
    btype = type_labels.get(booking.get("item_type", ""), "Travel")
    bicon = type_icons.get(booking.get("item_type", ""), "&#9992;")

    route = ""
    if booking.get("source"):
        route = f'{booking["source"]} &rarr; {booking["destination"]}'
    elif booking.get("destination"):
        route = booking["destination"]

    payment = booking.get("payment", {})
    pay_method = ""
    if payment.get("method") == "card":
        pay_method = f'Card ending ****{payment.get("card_last4", "")}'
    elif payment.get("method") == "upi":
        pay_method = f'UPI ({payment.get("upi_id", "")})'
    elif payment.get("method") == "netbanking":
        pay_method = f'Net Banking ({payment.get("bank", "N/A")})'

    created = ""
    if booking.get("created_at"):
        try:
            dt = datetime.fromisoformat(booking["created_at"])
            created = dt.strftime("%b %d, %Y %I:%M %p")
        except (ValueError, TypeError):
            created = str(booking["created_at"])

    bid = str(booking["_id"])
    qr_data = f"TravelGo Booking | ID: {bid} | {btype}: {booking.get('item_name','N/A')} | {route} | Date: {booking.get('date','')} | Rs. {booking.get('price',0):,.2f}"
    qr_b64 = _generate_qr_base64(qr_data)

    status = booking.get("status", "confirmed")
    status_color = "#059669" if status == "confirmed" else "#dc2626"
    status_bg = "#ecfdf5" if status == "confirmed" else "#fef2f2"

    optional_rows = ""
    if route:
        optional_rows += f'<tr><td class="label">Route</td><td class="value">{route}</td></tr>'
    if booking.get("seat_preference") and booking.get("seat_preference") != "any":
        optional_rows += f'<tr><td class="label">Seat Preference</td><td class="value">{booking["seat_preference"].title()}</td></tr>'
    if pay_method:
        optional_rows += f'<tr><td class="label">Payment Method</td><td class="value">{pay_method}</td></tr>'
    if created:
        optional_rows += f'<tr><td class="label">Booked On</td><td class="value">{created}</td></tr>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>TravelGo Receipt - {bid}</title>
<style>
@page {{ size: A4; margin: 1.5cm; }}
* {{ margin: 0; padding: 0; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #1e293b; background: #fff; }}
.receipt {{ width: 100%; max-width: 560px; margin: 0 auto; }}
.header-bar {{ background-color: #4338ca; padding: 20px 24px; color: #ffffff; }}
.header-bar h1 {{ font-size: 20px; letter-spacing: 1px; margin-bottom: 2px; }}
.header-bar p {{ font-size: 11px; color: #c7d2fe; }}
.sub-header {{ background-color: #4f46e5; padding: 14px 24px; }}
.sub-header table {{ width: 100%; }}
.sub-header td {{ color: #e0e7ff; font-size: 11px; vertical-align: top; }}
.sub-header .bid {{ font-size: 10px; color: #a5b4fc; }}
.sub-header .bid strong {{ color: #ffffff; font-size: 11px; }}
.sub-header .status {{ text-align: right; }}
.status-badge {{ display: inline-block; padding: 3px 12px; border-radius: 10px; font-size: 11px; font-weight: 700; background-color: {status_bg}; color: {status_color}; }}
.trip-banner {{ padding: 18px 24px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
.trip-banner table {{ width: 100%; }}
.trip-banner .icon-cell {{ width: 40px; font-size: 24px; vertical-align: middle; text-align: center; }}
.trip-banner .trip-info {{ vertical-align: middle; }}
.trip-banner .trip-type {{ font-size: 10px; color: #6366f1; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }}
.trip-banner .trip-name {{ font-size: 15px; font-weight: 700; color: #1e293b; margin-top: 2px; }}
.body {{ padding: 20px 24px; }}
table.details {{ width: 100%; border-collapse: collapse; }}
table.details tr {{ border-bottom: 1px solid #f1f5f9; }}
table.details td {{ padding: 9px 4px; font-size: 11px; }}
table.details td.label {{ color: #64748b; width: 42%; }}
table.details td.value {{ font-weight: 600; text-align: right; color: #1e293b; }}
.total-bar {{ background-color: #4338ca; padding: 14px 24px; }}
.total-bar table {{ width: 100%; }}
.total-bar td {{ font-size: 14px; color: #ffffff; }}
.total-bar td.amount {{ text-align: right; font-size: 18px; font-weight: 700; }}
.qr-section {{ padding: 18px 24px; text-align: center; border-top: 1px dashed #cbd5e1; }}
.qr-section img {{ width: 110px; height: 110px; }}
.qr-section p {{ font-size: 9px; color: #94a3b8; margin-top: 6px; }}
.footer {{ padding: 12px 24px; text-align: center; background-color: #f8fafc; border-top: 1px solid #e2e8f0; }}
.footer p {{ font-size: 9px; color: #94a3b8; }}
.footer .brand {{ font-weight: 700; color: #4338ca; }}
</style></head><body>
<div class="receipt">

 <div class="header-bar">
  <h1>TravelGo</h1>
  <p>Booking Confirmation &amp; Receipt</p>
 </div>

 <div class="sub-header">
  <table><tr>
   <td class="bid">Booking ID<br/><strong>{bid}</strong></td>
   <td class="status"><span class="status-badge">{status.upper()}</span></td>
  </tr></table>
 </div>

 <div class="trip-banner">
  <table><tr>
   <td class="icon-cell">{bicon}</td>
   <td class="trip-info">
    <div class="trip-type">{btype} Booking</div>
    <div class="trip-name">{booking.get('item_name', 'N/A')}</div>
   </td>
  </tr></table>
 </div>

 <div class="body">
  <table class="details">
   <tr><td class="label">Travel Date</td><td class="value">{booking.get('date', '')}</td></tr>
   <tr><td class="label">Passengers / Rooms</td><td class="value">{booking.get('passengers', 1)}</td></tr>
   {optional_rows}
   <tr><td class="label">Payment Status</td><td class="value" style="color:{status_color}">{payment.get('status', 'success').upper()}</td></tr>
  </table>
 </div>

 <div class="total-bar">
  <table><tr>
   <td>Total Amount</td>
   <td class="amount">Rs. {booking.get('price', 0):,.2f}</td>
  </tr></table>
 </div>

 <div class="qr-section">
  <img src="data:image/png;base64,{qr_b64}" />
  <p>Scan this QR code at the counter for quick verification</p>
 </div>

 <div class="footer">
  <p><span class="brand">TravelGo</span> &mdash; Your journey, our commitment. Thank you for booking with us!</p>
  <p>This is a computer-generated receipt and does not require a signature.</p>
 </div>

</div>
</body></html>"""

    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    if pisa_status.err:
        response = make_response(html)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="TravelGo_Booking_{bid}.html"'
        return response

    pdf_buffer.seek(0)
    pdf_response = make_response(pdf_buffer.read())
    pdf_response.headers["Content-Type"] = "application/pdf"
    pdf_response.headers["Content-Disposition"] = f'attachment; filename="TravelGo_Booking_{bid}.pdf"'
    return pdf_response
