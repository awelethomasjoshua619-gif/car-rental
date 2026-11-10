"""Production WSGI entry point; initialize schema before workers start."""

from app import app
from database import init_db

init_db()

