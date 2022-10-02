import os 
import redis

class Config(object):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    API_KEY = os.getenv("API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_TYPE = 'redis'
    SESSION_USE_SIGNER = True
    SESSION_PERMANENT = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql:///news-tracker7'
    SESSION_REDIS = redis.from_url('redis://localhost:6379')

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SESSION_REDIS = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379')) #2nd argument for local db is necessary for some reason because the production version keeps getting called in development.

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql:///newstracker-test'
    SQLALCHEMY_ECHO = False
    DEBUG_TB_HOSTS= ['dont-show-debug-toolbar']
    WTF_CSRF_ENABLED = False
