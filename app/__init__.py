import os
from flask import Flask
from dotenv import load_dotenv
from .db import init_db

def create_app():
    load_dotenv()
    app = Flask(__name__)

    # Ensure database tables exist on startup
    try:
        init_db()
    except Exception as e:
        # Surface clearly in logs; page will show a friendly message later
        print(f"Database init failed: {e}")

    from .routes import main_routes
    app.register_blueprint(main_routes)

    return app
