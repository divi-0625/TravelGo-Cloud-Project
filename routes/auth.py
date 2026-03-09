from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app,
)

auth_bp = Blueprint("auth", __name__)


def _get_models():
    return current_app.extensions["models"]


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("auth.register"))

        models = _get_models()
        if models["users"].find_by_email(email):
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        if models["users"].find_by_username(username):
            flash("Username already taken.", "danger")
            return redirect(url_for("auth.register"))

        user = models["users"].create_user(username, email, password)

        models["notifications"].create(
            str(user["_id"]),
            "Welcome to TravelGo! Start exploring travel options.",
            "success",
        )

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        models = _get_models()
        user = models["users"].find_by_email(email)

        if user and models["users"].verify_password(user["password_hash"], password):
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["role"] = user.get("role", "user")

            models["notifications"].create(
                str(user["_id"]),
                f"You logged in successfully. Welcome back, {user['username']}!",
                "info",
            )

            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))
