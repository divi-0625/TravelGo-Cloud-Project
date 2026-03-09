class Config:
    SECRET_KEY = "teamnameuniquetechwithteamleaderandteammembers"
    AWS_REGION = "ap-south-1"
    SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:336449003024:TravelGoNotifications"
    DYNAMO_TABLE_PREFIX = "travelgo"
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600
    RESULTS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
