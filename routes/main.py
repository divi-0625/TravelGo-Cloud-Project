from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app,
)
from functools import wraps

main_bp = Blueprint("main", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _get_models():
    return current_app.extensions["models"]


@main_bp.route("/")
def home():
    models = _get_models()
    listings = {
        "flights": models["flights"].get_all()[:6],
        "hotels":  models["hotels"].get_all()[:6],
        "trains":  models["trains"].get_all()[:6],
        "buses":   models["buses"].get_all()[:6],
    }
    return render_template("home.html", listings=listings)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    models = _get_models()
    user_id = session["user_id"]
    bookings = models["bookings"].find_by_user(user_id)
    notifications = models["notifications"].get_for_user(user_id, limit=5)
    unread = models["notifications"].unread_count(user_id)
    return render_template(
        "dashboard.html",
        bookings=bookings,
        notifications=notifications,
        unread_count=unread,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    models = _get_models()
    user = models["users"].find_by_id(session["user_id"])

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            models["users"].update_profile(session["user_id"], {
                "username": request.form.get("username", user["username"]),
                "phone": request.form.get("phone", ""),
                "address": request.form.get("address", ""),
            })
            session["username"] = request.form.get("username", user["username"])

            models["notifications"].create(
                session["user_id"],
                "Your profile has been updated successfully.",
                "info",
            )

            flash("Profile updated.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not models["users"].verify_password(user["password_hash"], current_pw):
                flash("Current password is incorrect.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            elif len(new_pw) < 6:
                flash("Password must be at least 6 characters.", "danger")
            else:
                models["users"].change_password(session["user_id"], new_pw)

                models["notifications"].create(
                    session["user_id"],
                    "Your password was changed successfully. If this wasn't you, contact support immediately.",
                    "warning",
                )

                flash("Password changed successfully.", "success")

        return redirect(url_for("main.profile"))

    bookings = models["bookings"].find_by_user(session["user_id"])
    return render_template("profile.html", user=user, bookings=bookings)
