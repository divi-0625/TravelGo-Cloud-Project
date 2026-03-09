def register_blueprints(app):
    from .auth import auth_bp
    from .main import main_bp
    from .search import search_bp
    from .booking import booking_bp
    from .admin import admin_bp
    from .notifications import notif_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notif_bp)
    app.register_blueprint(api_bp)
