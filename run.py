#!/usr/bin/env python
"""
FAST CARS - Car Rental Booking System
Aptech eProject Implementation
Run script: python run.py
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)

from app import app
from database import init_db

if __name__ == '__main__':
    if app.config.get('SESSION_COOKIE_SECURE'):
        raise RuntimeError('Use the production WSGI server (gunicorn wsgi:app) in production.')
    # Ensure database tables and initial seed data exist
    init_db()
    print("FAST CARS development server: http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=int(__import__('os').environ.get('PORT', '5000')), debug=True)
