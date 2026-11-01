"""Settings and fixed lists used across the project."""
import os
import secrets

# Keep the secret key out of GitHub: set it as an environment variable.
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
DB_FILE = "app.db"

ORG_TYPES = ["Company", "NGO", "Training institute"]
OPP_TYPES = ["Internship", "Apprenticeship", "Workshop", "Course"]
MODES = ["Online", "Offline", "Hybrid"]

# Test admin (Vidya's module will replace this). Change via environment variables.
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe@123")