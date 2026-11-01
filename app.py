from functools import wraps
import os

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)

from database import get_db_connection, init_db

app = Flask(__name__)

# Development-only fallback. Set SECRET_KEY in your environment
# before deploying or sharing the app publicly.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "change-this-development-key-before-deployment"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    with get_db_connection() as db:
        user = db.execute("""
            SELECT id, name, email, role
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

    return dict(user) if user else None


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not get_current_user():
            flash("Please log in first.")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


def student_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = get_current_user()

        if not user:
            flash("Please log in first.")
            return redirect(url_for("login"))

        if user["role"] != "student":
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view


# ---------------- HOME PAGE ----------------

@app.route("/")
def index():
    with get_db_connection() as db:
        opportunities = db.execute("""
            SELECT *
            FROM opportunities
            WHERE status = 'approved'
              AND (
                  deadline = ''
                  OR deadline IS NULL
                  OR deadline >= date('now', 'localtime')
              )
            ORDER BY id DESC
            LIMIT 3
        """).fetchall()

    return render_template(
        "index.html",
        opportunities=opportunities
    )


# ---------------- REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or "@" not in email:
            flash("Enter your name and a valid email address.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        try:
            with get_db_connection() as db:
                cursor = db.execute("""
                    INSERT INTO users (
                        name, email, password_hash, role
                    )
                    VALUES (?, ?, ?, 'student')
                """, (name, email, password_hash))

                db.execute("""
                    INSERT INTO profiles (user_id)
                    VALUES (?)
                """, (cursor.lastrowid,))

            flash("Account created. You can now log in.")
            return redirect(url_for("login"))

        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                flash("That email address is already registered.")
            else:
                app.logger.exception("Registration failed")
                flash("Could not create the account. Please try again.")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db_connection() as db:
            user = db.execute("""
                SELECT *
                FROM users
                WHERE email = ?
            """, (email,)).fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["id"]

            flash("You are logged in.")
            return redirect(url_for("profile"))

        flash("Incorrect email or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


# ---------------- STUDENT PROFILE ----------------

@app.route("/profile", methods=["GET", "POST"])
@student_required
def profile():
    user = get_current_user()

    with get_db_connection() as db:
        if request.method == "POST":
            education = request.form.get(
                "education", ""
            ).strip()[:200]

            skills = request.form.get(
                "skills", ""
            ).strip()[:1000]

            interests = request.form.get(
                "interests", ""
            ).strip()[:1000]

            location = request.form.get(
                "location", ""
            ).strip()[:200]

            db.execute("""
                INSERT INTO profiles (
                    user_id, education, skills, interests, location
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(user_id) DO UPDATE SET
                    education = excluded.education,
                    skills = excluded.skills,
                    interests = excluded.interests,
                    location = excluded.location
            """, (
                user["id"], education, skills, interests, location
            ))

            flash("Your profile has been saved.")
            return redirect(url_for("profile"))

        row = db.execute("""
            SELECT *
            FROM profiles
            WHERE user_id = ?
        """, (user["id"],)).fetchone()

    return render_template(
        "profile.html",
        profile=dict(row) if row else {}
    )


# ---------------- SEARCH AND FILTERS ----------------

@app.route("/search")
def search():
    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    skill = request.args.get("skill", "").strip()
    eligibility = request.args.get("eligibility", "").strip()
    duration = request.args.get("duration", "").strip()

    filters = [
        "status = 'approved'",
        """(
            deadline = ''
            OR deadline IS NULL
            OR deadline >= date('now', 'localtime')
        )"""
    ]
    params = []

    if keyword:
        filters.append("""
            (title LIKE ? OR organization LIKE ? OR description LIKE ?)
        """)
        params.extend([f"%{keyword}%"] * 3)

    if category:
        filters.append("category = ?")
        params.append(category)

    if location:
        filters.append("location LIKE ?")
        params.append(f"%{location}%")

    if skill:
        filters.append("skills LIKE ?")
        params.append(f"%{skill}%")

    if eligibility:
        filters.append("eligibility LIKE ?")
        params.append(f"%{eligibility}%")

    if duration:
        filters.append("duration LIKE ?")
        params.append(f"%{duration}%")

    sql = """
        SELECT *
        FROM opportunities
        WHERE
    """ + " AND ".join(filters) + " ORDER BY id DESC"

    with get_db_connection() as db:
        opportunities = db.execute(sql, params).fetchall()

    return render_template(
        "search.html",
        opportunities=opportunities,
        filters={
            "keyword": keyword,
            "category": category,
            "location": location,
            "skill": skill,
            "eligibility": eligibility,
            "duration": duration
        },
        categories=[
            "Internship",
            "Apprenticeship",
            "Workshop",
            "Certification Course",
            "Skill Training"
        ]
    )


# ---------------- RECOMMENDATION LOGIC ----------------

def recommendation_score(profile_data, opportunity):
    """
    Simple rule-based score out of 100.
    It is not an AI prediction and cannot guarantee selection.
    """
    if not profile_data:
        return 0

    def split_values(value):
        return {
            item.strip().lower()
            for item in (value or "").replace(";", ",").split(",")
            if item.strip()
        }

    user_skills = split_values(profile_data.get("skills", ""))
    user_interests = split_values(
        profile_data.get("interests", "")
    )
    opportunity_skills = split_values(opportunity["skills"])

    score = 0

    # Skills match: up to 60 points.
    if opportunity_skills:
        matches = user_skills.intersection(opportunity_skills)
        score += round(
            60 * len(matches) / len(opportunity_skills)
        )

    # Interest match: up to 20 points.
    searchable_text = (
        opportunity["title"] + " " +
        opportunity["category"] + " " +
        opportunity["description"]
    ).lower()

    if user_interests:
        matching_interests = sum(
            1 for interest in user_interests
            if interest in searchable_text
        )
        score += min(20, matching_interests * 10)

    # Location match: 20 points.
    user_location = (
        profile_data.get("location") or ""
    ).strip().lower()

    opportunity_location = (
        opportunity["location"] or ""
    ).strip().lower()

    if user_location and (
        user_location in opportunity_location
        or opportunity_location in ("online", "remote")
    ):
        score += 20

    return min(score, 100)


@app.route("/recommendations")
@student_required
def recommendations():
    user = get_current_user()

    with get_db_connection() as db:
        profile_row = db.execute("""
            SELECT *
            FROM profiles
            WHERE user_id = ?
        """, (user["id"],)).fetchone()

        profile_data = dict(profile_row) if profile_row else {}

        opportunities = db.execute("""
            SELECT *
            FROM opportunities
            WHERE status = 'approved'
              AND (
                  deadline = ''
                  OR deadline IS NULL
                  OR deadline >= date('now', 'localtime')
              )
        """).fetchall()

    matches = [
        (
            recommendation_score(profile_data, dict(opportunity)),
            dict(opportunity)
        )
        for opportunity in opportunities
    ]

    matches.sort(key=lambda item: item[0], reverse=True)

    has_profile = any(
        profile_data.get(field)
        for field in ("education", "skills", "interests", "location")
    )

    return render_template(
        "recommendations.html",
        matches=matches,
        has_profile=has_profile
    )


@app.errorhandler(403)
def forbidden(_error):
    return "You do not have permission to view this page.", 403


if __name__ == "__main__":
    init_db()
    app.run(debug=True)