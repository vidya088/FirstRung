"""
Youth Skill Development & Internship Finder
Module: Provider Registration & Posting (Sinchana Raghu)

Run:
    pip install flask
    python app.py
Open: http://127.0.0.1:5000
"""
import os

from flask import Flask

import config
from db import close_db, init_db
from routes import admin, auth, provider, public
from security import csrf_protect, inject_globals


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.teardown_appcontext(close_db)
    app.before_request(csrf_protect)
    app.context_processor(inject_globals)
    for module in (public, auth, provider, admin):
        app.register_blueprint(module.bp)
    return app


app = create_app()

if __name__ == "__main__":
    init_db()
    # Debug is OFF by default. To turn on auto-reload while coding (PowerShell):
    #   $env:DEBUG="1"; python app.py
    app.run(debug=os.environ.get("DEBUG") == "1")