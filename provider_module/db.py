"""Database: tables, connection and first-time setup (SQLite)."""
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    org_type TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    phone TEXT NOT NULL,
    city TEXT NOT NULL,
    website TEXT,
    contact_person TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'organization',   -- organization | admin
    status TEXT NOT NULL DEFAULT 'pending',      -- pending | approved | rejected
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id INTEGER NOT NULL REFERENCES organizations(id),
    title TEXT NOT NULL,
    opp_type TEXT NOT NULL,
    description TEXT NOT NULL,
    skills TEXT NOT NULL,
    eligibility TEXT,
    duration TEXT NOT NULL,
    location TEXT NOT NULL,
    mode TEXT NOT NULL,
    deadline TEXT NOT NULL,
    apply_info TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',      -- pending | approved | rejected
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(config.DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(config.DB_FILE)
    db.executescript(SCHEMA)
    if not db.execute("SELECT 1 FROM organizations WHERE role='admin'").fetchone():
        db.execute(
            "INSERT INTO organizations (name, org_type, email, password_hash, phone,"
            " city, contact_person, role, status) VALUES (?,?,?,?,?,?,?,?,?)",
            ("Admin", "Company", config.ADMIN_EMAIL,
             generate_password_hash(config.ADMIN_PASSWORD),
             "0000000000", "-", "Admin", "admin", "approved"))
    db.commit()
    db.close()