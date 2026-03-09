import os
from flask import Flask
import boto3
from config import config_by_name
from models import (
    UserModel, FlightModel, HotelModel, TrainModel,
    BusModel, BookingModel, NotificationModel,
)
from routes import register_blueprints


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "production")

    if config_name not in config_by_name:
        config_name = "production"

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    region = app.config["AWS_REGION"]
    prefix = app.config["DYNAMO_TABLE_PREFIX"]
    dynamodb = boto3.resource("dynamodb", region_name=region)
    sns = boto3.client("sns", region_name=region)

    app.extensions["dynamodb"] = dynamodb
    app.extensions["sns"] = sns

    app.extensions["models"] = {
        "users": UserModel(dynamodb.Table(f"{prefix}-users")),
        "flights": FlightModel(dynamodb.Table(f"{prefix}-flights")),
        "hotels": HotelModel(dynamodb.Table(f"{prefix}-hotels")),
        "trains": TrainModel(dynamodb.Table(f"{prefix}-trains")),
        "buses": BusModel(dynamodb.Table(f"{prefix}-buses")),
        "bookings": BookingModel(dynamodb.Table(f"{prefix}-bookings")),
        "notifications": NotificationModel(dynamodb.Table(f"{prefix}-notifications")),
    }

    register_blueprints(app)

    @app.context_processor
    def inject_globals():
        from flask import session as s
        unread = 0
        if "user_id" in s:
            unread = app.extensions["models"]["notifications"].unread_count(
                s["user_id"]
            )
        return dict(unread_count=unread)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
