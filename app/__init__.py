# app/__init__.py
import os
import logging
from flask import Flask
from dotenv import load_dotenv
from .config import config
from .extensions import csrf, limiter
from .database.schema import init_db

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


def create_app(config_name: str = None) -> Flask:
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        static_folder=os.path.join(ROOT_DIR, 'static'),
        static_url_path='/static'
    )

    # Load config
    app.config.from_object(config.get(config_name, config['default']))

    # Init extensions
    csrf.init_app(app)
    limiter.init_app(app)

    # Init database
    with app.app_context():
        init_db()

    # Register blueprints
    from .routes.auth    import auth_bp
    from .routes.main    import main_bp
    from .routes.profile import profile_bp
    from .routes.blood   import blood_bp
    from .routes.bmi     import bmi_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(blood_bp)
    app.register_blueprint(bmi_bp)

    return app
