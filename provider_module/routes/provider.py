"""Organization dashboard and opportunity posting (Sinchana)."""
from datetime import date

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

import config
from db import get_db
from security import clean, login_required, validate_opportunity

bp = Blueprint("provider", __name__)


@bp.route("/dashboard")
@login_required("organization")
def dashboard():
    db = get_db()
    org = db.execute("SELECT * FROM organizations WHERE id=?",
                     (session["org_id"],)).fetchone()
    # An organization only ever reads its OWN listings
    items = db.execute("SELECT * FROM opportunities WHERE org_id=? "
                       "ORDER BY created_at DESC", (session["org_id"],)).fetchall()
    return render_template("dashboard.html", org=org, items=items,
                           today=date.today().isoformat())


@bp.route("/post", methods=["GET", "POST"])
@login_required("organization")
def post():
    db = get_db()
    org = db.execute("SELECT status FROM organizations WHERE id=?",
                     (session["org_id"],)).fetchone()
    if org["status"] != "approved":
        flash("Your account must be approved by the admin before you can post.",
              "error")
        return redirect(url_for("provider.dashboard"))
    form = {}
    if request.method == "POST":
        form = {k: clean(k, 2000 if k == "description" else 200)
                for k in ["title", "opp_type", "description", "skills", "eligibility",
                          "duration", "location", "mode", "deadline", "apply_info"]}
        errors = validate_opportunity(form)
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db.execute(
                "INSERT INTO opportunities (org_id, title, opp_type, description,"
                " skills, eligibility, duration, location, mode, deadline, apply_info)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (session["org_id"], form["title"], form["opp_type"],
                 form["description"], form["skills"], form["eligibility"],
                 form["duration"], form["location"], form["mode"], form["deadline"],
                 form["apply_info"]))
            db.commit()
            flash("Submitted. It will go live after admin review.", "ok")
            return redirect(url_for("provider.dashboard"))
    return render_template("post.html", f=form, opp_types=config.OPP_TYPES,
                           modes=config.MODES)