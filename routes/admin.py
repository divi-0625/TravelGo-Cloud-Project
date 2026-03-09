from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app,
)
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


def _get_models():
    return current_app.extensions["models"]


@admin_bp.route("/")
@admin_required
def dashboard():
    models = _get_models()
    stats = {
        "users": models["users"].count(),
        "flights": models["flights"].count(),
        "hotels": models["hotels"].count(),
        "trains": models["trains"].count(),
        "buses": models["buses"].count(),
        "bookings": models["bookings"].count(),
        "bookings_by_type": models["bookings"].count_by_type(),
    }
    return render_template("admin.html", stats=stats, section="dashboard")


@admin_bp.route("/users")
@admin_required
def users():
    models = _get_models()
    all_users = models["users"].get_all_users()
    return render_template("admin.html", users=all_users, section="users")


@admin_bp.route("/bookings")
@admin_required
def bookings():
    models = _get_models()
    all_bookings = models["bookings"].get_all()
    return render_template("admin.html", bookings=all_bookings, section="bookings")


TRANSPORT_FIELDS = {
    "flights": ["name", "airline", "source", "destination", "date",
                 "departure", "arrival", "duration", "price", "availability"],
    "hotels": ["name", "destination", "checkin", "checkout", "price",
                "rating", "rooms", "amenities", "availability"],
    "trains": ["name", "operator", "source", "destination", "date",
                "departure", "arrival", "duration", "price", "availability"],
    "buses": ["name", "operator", "source", "destination", "date",
               "departure", "arrival", "duration", "price", "availability"],
}


def _collect_form_data(transport_type):
    data = {}
    for field in TRANSPORT_FIELDS.get(transport_type, []):
        val = request.form.get(field, "").strip()
        if val:
            data[field] = val
    return data


@admin_bp.route("/<transport_type>")
@admin_required
def list_items(transport_type):
    if transport_type not in TRANSPORT_FIELDS:
        flash("Invalid type.", "danger")
        return redirect(url_for("admin.dashboard"))
    models = _get_models()
    items = models[transport_type].get_all()
    fields = TRANSPORT_FIELDS[transport_type]
    return render_template(
        "admin.html",
        section="list",
        transport_type=transport_type,
        items=items,
        fields=fields,
    )


@admin_bp.route("/<transport_type>/add", methods=["GET", "POST"])
@admin_required
def add_item(transport_type):
    if transport_type not in TRANSPORT_FIELDS:
        flash("Invalid type.", "danger")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        data = _collect_form_data(transport_type)
        models = _get_models()
        models[transport_type].add(data)
        flash(f"{transport_type.title()[:-1]} added!", "success")
        return redirect(url_for("admin.list_items", transport_type=transport_type))

    fields = TRANSPORT_FIELDS[transport_type]
    return render_template(
        "admin.html",
        section="add",
        transport_type=transport_type,
        fields=fields,
    )


@admin_bp.route("/<transport_type>/edit/<item_id>", methods=["GET", "POST"])
@admin_required
def edit_item(transport_type, item_id):
    if transport_type not in TRANSPORT_FIELDS:
        flash("Invalid type.", "danger")
        return redirect(url_for("admin.dashboard"))

    models = _get_models()
    item = models[transport_type].find_by_id(item_id)
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for("admin.list_items", transport_type=transport_type))

    if request.method == "POST":
        data = _collect_form_data(transport_type)
        models[transport_type].update(item_id, data)
        flash("Updated!", "success")
        return redirect(url_for("admin.list_items", transport_type=transport_type))

    fields = TRANSPORT_FIELDS[transport_type]
    return render_template(
        "admin.html",
        section="edit",
        transport_type=transport_type,
        item=item,
        fields=fields,
    )


@admin_bp.route("/<transport_type>/delete/<item_id>", methods=["POST"])
@admin_required
def delete_item(transport_type, item_id):
    if transport_type not in TRANSPORT_FIELDS:
        flash("Invalid type.", "danger")
        return redirect(url_for("admin.dashboard"))
    models = _get_models()
    models[transport_type].delete(item_id)
    flash("Deleted.", "info")
    return redirect(url_for("admin.list_items", transport_type=transport_type))
