# app/config.py
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'CHANGE_THIS_IN_PRODUCTION_NOW')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    RATELIMIT_STORAGE_URI = 'memory://'


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    DEBUG = True
    SESSION_COOKIE_SECURE = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
