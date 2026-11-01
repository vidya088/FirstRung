"""Public home page (basic list; Pragathi's search/filter page replaces this)."""
from datetime import date

from flask import Blueprint, render_template

from db import get_db

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    """Only approved, non-expired listings are visible."""
    rows = get_db().execute(
        "SELECT o.*, g.name AS org_name FROM opportunities o "
        "JOIN organizations g ON g.id = o.org_id "
        "WHERE o.status='approved' AND o.deadline >= ? ORDER BY o.created_at DESC",
        (date.today().isoformat(),)).fetchall()
    return render_template("home.html", items=rows)