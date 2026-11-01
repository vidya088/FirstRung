"""Security helpers: CSRF token, login checks and input validation."""
import re
import secrets
from datetime import date
from functools import wraps

from flask import abort, flash, redirect, request, session, url_for

import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def csrf_protect():
    if request.method == "POST":
        token = session.get("csrf")
        if not token or token != request.form.get("csrf"):
            abort(400, "Invalid form token. Go back and try again.")


def inject_globals():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return {"csrf": session["csrf"], "user_name": session.get("name"),
            "user_role": session.get("role")}


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "org_id" not in session:
                flash("Please log in first.", "error")
                return redirect(url_for("auth.login"))
            if role and session.get("role") != role:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def clean(field, maxlen=200):
    return request.form.get(field, "").strip()[:maxlen]


def validate_registration(f):
    errors = []
    for key, label in [("name", "Organization name"), ("city", "City"),
                       ("contact_person", "Contact person")]:
        if not f[key]:
            errors.append(f"{label} is required.")
    if f["org_type"] not in config.ORG_TYPES:
        errors.append("Choose a valid organization type.")
    if not EMAIL_RE.match(f["email"]):
        errors.append("Enter a valid email address.")
    if not re.fullmatch(r"\d{10}", f["phone"]):
        errors.append("Phone number must be 10 digits.")
    if f["website"] and not f["website"].startswith(("http://", "https://")):
        errors.append("Website must start with http:// or https://")
    pw = f["password"]
    if len(pw) < 8 or not re.search(r"\d", pw) or not re.search(r"[A-Za-z]", pw):
        errors.append("Password needs 8+ characters with letters and numbers.")
    if pw != f["confirm"]:
        errors.append("Passwords do not match.")
    return errors


def validate_opportunity(f):
    errors = []
    for key, label in [("title", "Title"), ("description", "Description"),
                       ("skills", "Required skills"), ("duration", "Duration"),
                       ("location", "Location"), ("apply_info", "How to apply")]:
        if not f[key]:
            errors.append(f"{label} is required.")
    if f["opp_type"] not in config.OPP_TYPES:
        errors.append("Choose a valid opportunity type.")
    if f["mode"] not in config.MODES:
        errors.append("Choose a valid mode.")
    try:
        if date.fromisoformat(f["deadline"]) < date.today():
            errors.append("Deadline cannot be in the past.")
    except ValueError:
        errors.append("Enter a valid deadline date.")
    return errors