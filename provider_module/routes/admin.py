"""Basic admin review page for testing (Vidya's full module replaces this)."""
from flask import Blueprint, abort, redirect, render_template, url_for

from db import get_db
from security import login_required

bp = Blueprint("admin", __name__)


@bp.route("/admin")
@login_required("admin")
def admin():
    db = get_db()
    orgs = db.execute("SELECT * FROM organizations WHERE role='organization' "
                      "ORDER BY created_at DESC").fetchall()
    opps = db.execute("SELECT o.*, g.name AS org_name FROM opportunities o "
                      "JOIN organizations g ON g.id=o.org_id "
                      "ORDER BY o.created_at DESC").fetchall()
    return render_template("admin.html", orgs=orgs, opps=opps)


@bp.route("/admin/<kind>/<int:item_id>/<action>", methods=["POST"])
@login_required("admin")
def admin_action(kind, item_id, action):
    if kind not in ("org", "opp") or action not in ("approve", "reject"):
        abort(404)
    table = "organizations" if kind == "org" else "opportunities"
    status = "approved" if action == "approve" else "rejected"
    db = get_db()
    # Table name comes from a fixed whitelist above, values are parameterized
    db.execute(f"UPDATE {table} SET status=? WHERE id=?", (status, item_id))
    db.commit()
    return redirect(url_for("admin.admin"))