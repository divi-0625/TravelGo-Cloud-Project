from flask import (
    Blueprint, redirect, url_for, session, flash,
    current_app, jsonify,
)
from functools import wraps

notif_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _get_models():
    return current_app.extensions["models"]


@notif_bp.route("/mark-read/<notif_id>", methods=["POST"])
@login_required
def mark_read(notif_id):
    models = _get_models()
    models["notifications"].mark_read(notif_id)
    return redirect(url_for("main.dashboard"))


@notif_bp.route("/count")
@login_required
def unread_count():
    models = _get_models()
    count = models["notifications"].unread_count(session["user_id"])
    return jsonify({"unread": count})
