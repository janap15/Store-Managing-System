import os

database = os.environ["DATABASE_URL"]

class Configuration():
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:root@{database}/applications"
    JWT_SECRET_KEY = "JWT_SECRET_KEY"
    REDIS_HOST = "redis"
    REDIS_PRODUCT_LIST = "products"
