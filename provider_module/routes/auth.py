"""Organization registration, login and logout (Sinchana)."""
import secrets

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import config
from db import get_db
from security import clean, validate_registration

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = {}
    if request.method == "POST":
        form = {k: clean(k) for k in ["name", "org_type", "email", "phone", "city",
                                      "website", "contact_person"]}
        form["email"] = form["email"].lower()
        form["password"] = request.form.get("password", "")
        form["confirm"] = request.form.get("confirm", "")
        errors = validate_registration(form)
        db = get_db()
        if not errors and db.execute("SELECT 1 FROM organizations WHERE email=?",
                                     (form["email"],)).fetchone():
            errors.append("This email is already registered.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db.execute(
                "INSERT INTO organizations (name, org_type, email, password_hash,"
                " phone, city, website, contact_person) VALUES (?,?,?,?,?,?,?,?)",
                (form["name"], form["org_type"], form["email"],
                 generate_password_hash(form["password"]), form["phone"],
                 form["city"], form["website"], form["contact_person"]))
            db.commit()
            flash("Registered. You can log in once the admin approves your account.",
                  "ok")
            return redirect(url_for("auth.login"))
    return render_template("register.html", f=form, org_types=config.ORG_TYPES)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = clean("email").lower()
        org = get_db().execute("SELECT * FROM organizations WHERE email=?",
                               (email,)).fetchone()
        # Same message for wrong email or password (does not reveal which one)
        if not org or not check_password_hash(org["password_hash"],
                                              request.form.get("password", "")):
            flash("Incorrect email or password.", "error")
        else:
            session.clear()
            session.update(org_id=org["id"], name=org["name"], role=org["role"],
                           csrf=secrets.token_hex(16))
            return redirect(url_for("admin.admin" if org["role"] == "admin"
                                    else "provider.dashboard"))
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("public.home"))