# app/__init__.py
from flask import Flask
from .routes import bp as routes_bp
from .reset_password import reset_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = 'secret_key_here'  # Set your secret key here
    app.register_blueprint(routes_bp)
    app.register_blueprint(reset_bp) 
    return app




