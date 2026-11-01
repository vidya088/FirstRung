import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "youthconnect.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db_connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
                CHECK (role IN ('student', 'provider', 'admin')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            education TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            location TEXT DEFAULT '',
            FOREIGN KEY (user_id)
                REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            skills TEXT DEFAULT '',
            eligibility TEXT DEFAULT '',
            duration TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'approved'
                CHECK (status IN (
                    'pending', 'approved', 'rejected', 'removed'
                )),
            is_demo INTEGER NOT NULL DEFAULT 1
        );
        """)

        count = db.execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()[0]

        if count == 0:
            demo_opportunities = [
                (
                    "Python Developer Intern",
                    "Demo Tech Labs",
                    "Internship",
                    "Bengaluru",
                    "Python, SQL, Git",
                    "Students pursuing CS/IT",
                    "8 weeks",
                    "2099-12-31",
                    "Demo listing for testing search and recommendations."
                ),
                (
                    "Web Development Basics",
                    "Demo Learning Hub",
                    "Skill Training",
                    "Online",
                    "HTML, CSS, JavaScript",
                    "Beginners",
                    "4 weeks",
                    "2099-12-31",
                    "Demo training listing, not a verified real course."
                ),
                (
                    "Digital Marketing Workshop",
                    "Demo Career Centre",
                    "Workshop",
                    "Mysuru",
                    "Marketing, social media, communication",
                    "Students",
                    "2 days",
                    "2099-12-31",
                    "Demo workshop listing for testing the app."
                ),
                (
                    "Data Analytics Certificate",
                    "Demo Learning Hub",
                    "Certification Course",
                    "Online",
                    "Python, Excel, SQL",
                    "Beginners with basic computer skills",
                    "10 weeks",
                    "2099-12-31",
                    "Demo certification listing for testing."
                ),
                (
                    "Electrical Technician Apprentice",
                    "Demo Skills Centre",
                    "Apprenticeship",
                    "Mysuru",
                    "Electrical basics, safety",
                    "ITI or relevant technical qualification",
                    "6 months",
                    "2099-12-31",
                    "Demo apprenticeship listing for testing."
                )
            ]

            db.executemany("""
                INSERT INTO opportunities (
                    title, organization, category, location,
                    skills, eligibility, duration, deadline,
                    description, status, is_demo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 1)
            """, demo_opportunities)