import os
import random
import string
import hashlib
import hmac
import logging
import math
import re
import secrets
from datetime import timezone
from datetime import datetime, date, timedelta
from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect

try:
    from dotenv import load_dotenv
    local_mode = os.environ.get('APP_ENV', 'development').lower() != 'production'
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=local_mode)
except ImportError:
    pass

from database import get_db, init_db
from email_service import send_email

app = Flask(__name__)
APP_ENV = os.environ.get('APP_ENV', 'development').lower()
IS_PRODUCTION = APP_ENV == 'production'
if IS_PRODUCTION:
    required_settings = ['SECRET_KEY', 'RESEND_API_KEY', 'MAIL_FROM', 'PUBLIC_BASE_URL']
    missing_settings = [name for name in required_settings if not os.environ.get(name)]
    if missing_settings:
        raise RuntimeError('Missing required production settings: ' + ', '.join(missing_settings))
    if len(os.environ['SECRET_KEY']) < 32 or os.environ['SECRET_KEY'] == 'generate-a-long-random-value-and-store-it-as-a-secret':
        raise RuntimeError('SECRET_KEY must be a unique random value with at least 32 characters.')
    if os.environ['RESEND_API_KEY'] == 're_your_resend_api_key':
        raise RuntimeError('Set a real Resend API key before starting production.')
    if 'your-verified-domain.example' in os.environ['MAIL_FROM']:
        raise RuntimeError('Set MAIL_FROM to an address on a domain verified in Resend.')
    if not os.environ['PUBLIC_BASE_URL'].startswith('https://') or 'your-domain.example' in os.environ['PUBLIC_BASE_URL']:
        raise RuntimeError('PUBLIC_BASE_URL must use HTTPS in production.')

app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    WTF_CSRF_TIME_LIMIT=7200,
)
csrf = CSRFProtect(app)
logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    proxy_hops = int(os.environ.get('TRUSTED_PROXY_HOPS', '1'))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops, x_host=proxy_hops)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'no-referrer')
    if request.is_secure:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_vehicle_image(url_field, file_field, fallback=''):
    """Return a submitted vehicle image URL or save its uploaded image locally."""
    uploaded = request.files.get(file_field)
    if uploaded and uploaded.filename:
        if not allowed_file(uploaded.filename):
            raise ValueError('Choose a PNG, JPG, JPEG, WEBP, or GIF image for each view.')
        safe_name = secure_filename(uploaded.filename)
        if not safe_name:
            raise ValueError('One of the selected image filenames is invalid.')
        filename = f"vehicle_{secrets.token_hex(8)}_{safe_name}"
        uploaded.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return f"/static/uploads/{filename}"
    return request.form.get(url_field, '').strip() or fallback or ''

def validate_vehicle_image_uploads(file_fields):
    """Reject unsupported gallery uploads before saving any of the selected files."""
    for field_name in file_fields:
        uploaded = request.files.get(field_name)
        if uploaded and uploaded.filename and not allowed_file(uploaded.filename):
            return 'Choose PNG, JPG, JPEG, WEBP, or GIF files for vehicle photos.'
    return None

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------
# Context Processors & Middleware
# ---------------------------------------------------------
@app.before_request
def load_logged_in_user():
    g.db = get_db()
    
    # User session
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = g.db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    # Admin session
    admin_id = session.get('admin_id')
    if admin_id is None:
        g.admin = None
    else:
        g.admin = g.db.execute("SELECT * FROM admins WHERE id = ?", (admin_id,)).fetchone()

    # Site settings
    settings_rows = g.db.execute("SELECT key, value FROM site_settings").fetchall()
    g.settings = {row['key']: row['value'] for row in settings_rows}

@app.route('/healthz')
def health_check():
    get_db().execute('SELECT 1').fetchone()
    return jsonify(status='ok')

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_global_vars():
    brands = []
    if hasattr(g, 'db'):
        brands = g.db.execute("SELECT * FROM brands ORDER BY name ASC").fetchall()
    return {
        'current_user': getattr(g, 'user', None),
        'current_admin': getattr(g, 'admin', None),
        'site_settings': getattr(g, 'settings', {}),
        'all_brands': brands,
        'current_year': datetime.now().year,
        'today': date.today().isoformat(),
        'demo_mode': not IS_PRODUCTION,
    }

# ---------------------------------------------------------
# Decorators
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.admin is None:
            flash("Administrator login required.", "danger")
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_safe_redirect_target(target):
    if not target or not target.startswith('/') or target.startswith('//'):
        return False
    parsed = urlsplit(target)
    return not parsed.netloc and parsed.scheme == ''

def is_valid_email(address):
    return bool(address and len(address) <= 254 and re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', address))

def create_email_code():
    return f'{secrets.randbelow(1_000_000):06d}'

def hash_email_code(purpose, email, code):
    message = f'{purpose}:{email.strip().lower()}:{code}'.encode('utf-8')
    key = app.secret_key.encode('utf-8') if isinstance(app.secret_key, str) else app.secret_key
    return hmac.new(key, message, hashlib.sha256).hexdigest()

def auth_rate_limited(scope, identity, max_attempts=8, window_seconds=900):
    now = int(datetime.now(timezone.utc).timestamp())
    identity_hash = hashlib.sha256(
        f'{request.remote_addr or "unknown"}:{identity.lower()}'.encode('utf-8')
    ).hexdigest()
    db = get_db()
    count = db.execute(
        'SELECT COUNT(*) FROM auth_attempts WHERE scope = ? AND identity_hash = ? AND attempted_at > ?',
        (scope, identity_hash, now - window_seconds),
    ).fetchone()[0]
    db.execute(
        'INSERT INTO auth_attempts (scope, identity_hash, attempted_at) VALUES (?, ?, ?)',
        (scope, identity_hash, now),
    )
    db.execute('DELETE FROM auth_attempts WHERE attempted_at < ?', (now - 86400,))
    db.commit()
    return count >= max_attempts

def send_templated_email(recipient, subject, heading, message, action_url=None, action_label=None, *, auth_only=False):
    from html import escape

    safe_heading = escape(heading)
    safe_message = escape(message).replace('\n', '<br>')
    action_html = ''
    if action_url and action_label:
        safe_url = escape(action_url, quote=True)
        action_html = f'<p><a href="{safe_url}">{escape(action_label)}</a></p>'
    html = f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto"><h2>{safe_heading}</h2><p>{safe_message}</p>{action_html}<p>FAST CARS</p></div>'
    text = f'{heading}\n\n{message}' + (f'\n\n{action_label}: {action_url}' if action_url and action_label else '')
    return send_email(recipient, subject, html, text, auth_only=auth_only)

@app.cli.command('create-admin')
def create_admin_command():
    """Interactively create the first production administrator."""
    import click

    username = click.prompt('Admin username').strip()
    email = click.prompt('Admin email').strip().lower()
    full_name = click.prompt('Admin full name').strip()
    password = click.prompt('Admin password', hide_input=True, confirmation_prompt=True)
    if len(password) < 12:
        raise click.ClickException('Admin passwords must be at least 12 characters.')
    db = get_db()
    try:
        db.execute(
            'INSERT INTO admins (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)',
            (username, email, generate_password_hash(password), full_name),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise click.ClickException('Could not create the administrator; check for duplicate username or email.') from exc
    click.echo(f'Administrator {username} created.')

# ---------------------------------------------------------
# Public & Guest User Routes
# ---------------------------------------------------------
@app.route('/')
def index():
    db = get_db()
    # 4 featured vehicles for "OUR CARS" section
    our_cars = db.execute("""
        SELECT v.*, b.name as brand_name 
        FROM vehicles v 
        JOIN brands b ON v.brand_id = b.id 
        WHERE v.status = 'Available'
        ORDER BY v.id ASC 
        LIMIT 4
    """).fetchall()

    # Category rates and photos are derived from live fleet records.
    small_info = db.execute("""
        SELECT MIN(price_per_day) as min_rate, image_url 
        FROM vehicles WHERE category = 'Small' AND status = 'Available'
    """).fetchone()

    premium_info = db.execute("""
        SELECT MIN(price_per_day) as min_rate, image_url 
        FROM vehicles WHERE category = 'Premium' AND status = 'Available'
    """).fetchone()

    large_info = db.execute("""
        SELECT MIN(price_per_day) as min_rate, image_url 
        FROM vehicles WHERE category = 'Large' AND status = 'Available'
    """).fetchone()

    # Use a local neutral image when a category has no fleet photo yet.
    fallback_image = url_for('static', filename='images/car-placeholder.svg')
    small_img = (small_info and small_info['image_url']) or fallback_image
    premium_img = (premium_info and premium_info['image_url']) or fallback_image
    large_img = (large_info and large_info['image_url']) or fallback_image

    small_rate = small_info and small_info['min_rate']
    premium_rate = premium_info and premium_info['min_rate']
    large_rate = large_info and large_info['min_rate']

    # Show only reviews that an administrator has approved.
    featured_testimonial = db.execute("""
        SELECT t.*, u.full_name as user_name, v.title as car_title
        FROM testimonials t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN bookings b ON b.user_id = u.id
        LEFT JOIN vehicles v ON b.vehicle_id = v.id
        WHERE t.status = 1
        ORDER BY t.id DESC
        LIMIT 1
    """).fetchone()

    return render_template('index.html', 
                           our_cars=our_cars,
                           small_img=small_img,
                           small_rate=small_rate,
                           premium_img=premium_img,
                           premium_rate=premium_rate,
                           large_img=large_img,
                           large_rate=large_rate,
                           featured_testimonial=featured_testimonial)

@app.route('/cars')
def cars():
    db = get_db()
    brand_id = request.args.get('brand', type=int)
    category = request.args.get('category') or request.args.get('car_type')
    fuel_type = request.args.get('fuel', type=str)
    transmission = request.args.get('transmission', type=str)
    max_price = request.args.get('max_price', type=float)
    search_q = request.args.get('q', type=str, default='').strip()
    sort_by = request.args.get('sort', default='newest')
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    query = """
        SELECT v.*, b.name as brand_name 
        FROM vehicles v 
        JOIN brands b ON v.brand_id = b.id 
        WHERE v.status = 'Available'
    """
    params = []

    if brand_id:
        query += " AND v.brand_id = ?"
        params.append(brand_id)
    if category and category.lower() != 'any':
        query += " AND LOWER(v.category) = LOWER(?)"
        params.append(category)
    if fuel_type:
        query += " AND v.fuel_type = ?"
        params.append(fuel_type)
    if transmission:
        query += " AND v.transmission = ?"
        params.append(transmission)
    if max_price:
        query += " AND v.price_per_day <= ?"
        params.append(max_price)
    if search_q:
        query += " AND (v.title LIKE ? OR b.name LIKE ? OR v.overview LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term, term])
    if from_date or to_date:
        try:
            search_start = date.fromisoformat(from_date)
            search_end = date.fromisoformat(to_date)
            if search_start < date.today() or search_end < search_start:
                raise ValueError
            query += """ AND NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.vehicle_id = v.id
                  AND b.status IN ('Pending', 'Confirmed')
                  AND b.from_date < ? AND b.to_date > ?
            )"""
            params.extend([search_end.isoformat(), search_start.isoformat()])
        except ValueError:
            flash('Enter a valid future pick-up and return date to check availability.', 'warning')
            from_date = ''
            to_date = ''

    if sort_by == 'price_low':
        query += " ORDER BY v.price_per_day ASC"
    elif sort_by == 'price_high':
        query += " ORDER BY v.price_per_day DESC"
    elif sort_by == 'year':
        query += " ORDER BY v.model_year DESC"
    else:
        query += " ORDER BY v.id DESC"

    car_list = db.execute(query, params).fetchall()
    brands = db.execute("SELECT * FROM brands ORDER BY name ASC").fetchall()

    return render_template('cars.html', 
                           cars=car_list, 
                           brands=brands,
                           selected_brand=brand_id,
                           selected_category=category,
                           selected_fuel=fuel_type,
                           selected_transmission=transmission,
                           selected_max_price=max_price,
                           search_q=search_q,
                           sort_by=sort_by,
                           selected_from_date=from_date,
                           selected_to_date=to_date)

    return render_template('cars.html', 
                           cars=car_list, 
                           brands=brands,
                           selected_brand=brand_id,
                           selected_fuel=fuel_type,
                           selected_transmission=transmission,
                           selected_max_price=max_price,
                           search_q=search_q,
                           sort_by=sort_by)

@app.route('/cars/<int:vehicle_id>')
def car_details(vehicle_id):
    db = get_db()
    car = db.execute("""
        SELECT v.*, b.name as brand_name 
        FROM vehicles v 
        JOIN brands b ON v.brand_id = b.id 
        WHERE v.id = ?
    """, (vehicle_id,)).fetchone()

    if not car:
        flash("Vehicle not found.", "warning")
        return redirect(url_for('cars'))

    # Keep each gallery view attached to this vehicle and omit missing or repeated photos.
    gallery = []
    seen_images = set()
    for label, image_key in (
        ('Front', 'image_url'),
        ('Side', 'image_side'),
        ('Rear', 'image_rear'),
        ('Interior', 'image_interior'),
    ):
        image = car[image_key]
        if image and image not in seen_images:
            gallery.append({'label': label, 'src': image, 'alt': f"{car['title']} — {label} view"})
            seen_images.add(image)

    # Related cars from same brand or similar
    similar_cars = db.execute("""
        SELECT v.*, b.name as brand_name 
        FROM vehicles v 
        JOIN brands b ON v.brand_id = b.id 
        WHERE v.id != ? AND (v.brand_id = ? OR v.fuel_type = ?)
        LIMIT 3
    """, (vehicle_id, car['brand_id'], car['fuel_type'])).fetchall()

    return render_template('car_details.html', car=car, gallery=gallery, similar_cars=similar_cars)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not is_valid_email(email) or not message:
            flash("Please fill in your name, email, and message.", "danger")
        else:
            db = get_db()
            db.execute("""
                INSERT INTO contact_queries (name, email, phone, subject, message)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, phone, subject, message))
            db.commit()
            support_email = g.settings.get('company_email', '').strip()
            if support_email:
                try:
                    send_templated_email(
                        support_email, f"Website inquiry: {subject or 'General question'}",
                        'A new website inquiry was received',
                        f'From: {name} ({email})\nPhone: {phone or "not provided"}\n\n{message}',
                    )
                except Exception:
                    logger.exception('Could not send notification for contact inquiry')
            try:
                send_templated_email(
                    email, 'We received your FAST CARS inquiry', 'Thanks for contacting FAST CARS',
                    'Your message has been received. Our team will follow up as soon as possible.',
                )
            except Exception:
                logger.exception('Could not send contact acknowledgement')
            flash("Thank you! Your message has been received. Our team will contact you shortly.", "success")
            return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip().lower()
    if not is_valid_email(email):
        flash("Please provide a valid email address.", "warning")
    else:
        db = get_db()
        existing = db.execute("SELECT id FROM subscribers WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("You are already subscribed to our newsletter!", "info")
        else:
            db.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
            db.commit()
            flash("Thank you for subscribing! You will receive exclusive car rental offers.", "success")
    return redirect(request.referrer or url_for('index'))

# ---------------------------------------------------------
# User Authentication & Password Recovery
# ---------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        country = request.form.get('country', '').strip()
        security_question = ''
        security_answer = ''

        if not all([full_name, email, password, confirm_password]) or request.form.get('terms_accepted') != 'yes':
            flash("Please complete all required fields.", "danger")
        elif not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            db = get_db()
            existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing_user:
                flash("An account with this email address already exists. Please log in.", "warning")
                return redirect(url_for('login'))

            hashed_pw = generate_password_hash(password)
            db.execute("""
                INSERT INTO users (full_name, email, password_hash, phone, address, city, country,
                                   security_question, security_answer, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (full_name, email, hashed_pw, phone, address, city, country, security_question, security_answer))
            db.commit()
            new_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            code = create_email_code()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.execute('DELETE FROM email_verification_codes WHERE user_id = ?', (new_user['id'],))
            db.execute('INSERT INTO email_verification_codes (user_id, code_hash, expires_at) VALUES (?, ?, ?)',
                       (new_user['id'], hash_email_code('verify-email', email, code), expires_at))
            db.commit()
            try:
                send_templated_email(email, 'Verify your FAST CARS email', 'Confirm your email address',
                                     f'Your verification code is {code}. It expires in 10 minutes.', auth_only=True)
            except Exception:
                logger.exception('Could not send registration email to user %s', new_user['id'])
                flash('Your account was created, but the verification email could not be sent. You can request another code below.', 'warning')
            else:
                flash('We sent a six-digit verification code to your email address.', 'success')
            return redirect(url_for('verify_email', email=email))

    return render_template('register.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = (request.values.get('email') or '').strip().lower()
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone() if is_valid_email(email) else None
    if request.method == 'POST':
        if not user:
            flash('That verification request is invalid. Please register again.', 'warning')
            return redirect(url_for('register'))
        if user['email_verified']:
            flash('This email address is already verified. Please sign in.', 'info')
            return redirect(url_for('login'))
        action = request.form.get('action', 'verify')
        if action == 'resend':
            if auth_rate_limited('email-verification-send', email, max_attempts=3, window_seconds=900):
                flash('Please wait before requesting another verification code.', 'warning')
                return redirect(url_for('verify_email', email=email))
            code = create_email_code()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.execute('DELETE FROM email_verification_codes WHERE user_id = ?', (user['id'],))
            db.execute('INSERT INTO email_verification_codes (user_id, code_hash, expires_at) VALUES (?, ?, ?)',
                       (user['id'], hash_email_code('verify-email', email, code), expires_at))
            db.commit()
            try:
                send_templated_email(email, 'Verify your FAST CARS email', 'Confirm your email address',
                                     f'Your verification code is {code}. It expires in 10 minutes.', auth_only=True)
                flash('A new verification code has been sent.', 'success')
            except Exception:
                logger.exception('Could not resend email verification code for user %s', user['id'])
                flash('The verification email could not be sent. Check the local email settings and try again.', 'danger')
            return redirect(url_for('verify_email', email=email))

        code = request.form.get('code', '').strip()
        if auth_rate_limited('email-verification-check', email, max_attempts=8):
            flash('Too many verification attempts. Request a new code later.', 'danger')
            return render_template('verify_email.html', email=email)
        pending = db.execute('SELECT * FROM email_verification_codes WHERE user_id = ?', (user['id'],)).fetchone()
        code_matches = pending and hmac.compare_digest(
            pending['code_hash'], hash_email_code('verify-email', email, code))
        code_valid = False
        if code_matches:
            try:
                code_valid = datetime.fromisoformat(pending['expires_at']) > datetime.now(timezone.utc)
            except ValueError:
                code_valid = False
        if not code_valid:
            flash('That code is invalid or expired. Request a new code and try again.', 'danger')
            return render_template('verify_email.html', email=email)
        db.execute('UPDATE users SET email_verified = 1 WHERE id = ?', (user['id'],))
        db.execute('DELETE FROM email_verification_codes WHERE user_id = ?', (user['id'],))
        db.commit()
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['user_email'] = user['email']
        try:
            send_templated_email(email, 'Welcome to FAST CARS', 'Your account is ready',
                                 f'Hello {user["full_name"]}, your FAST CARS email has been verified.')
        except Exception:
            logger.exception('Could not send welcome email to user %s', user['id'])
        flash('Email verified. Your account is ready.', 'success')
        return redirect(url_for('index'))
    if not user:
        flash('Enter the email address used during registration.', 'info')
        return redirect(url_for('register'))
    return render_template('verify_email.html', email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('profile'))

    next_url = request.args.get('next')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if auth_rate_limited('user-login', email):
            flash('Too many sign-in attempts. Please wait and try again.', 'danger')
            return render_template('login.html', next_url=next_url)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            if not user['email_verified']:
                flash('Verify your email before signing in.', 'warning')
                return redirect(url_for('verify_email', email=user['email']))
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            flash(f"Welcome back, {user['full_name']}!", "success")
            if is_safe_redirect_target(next_url):
                return redirect(next_url)
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html', next_url=next_url)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    db = get_db()
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if auth_rate_limited('password-reset-request', email, max_attempts=5):
            flash('If an account matches that email address, a password reset link has been sent.', 'info')
            return redirect(url_for('forgot_password'))
        user = db.execute('SELECT id, email FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            code = create_email_code()
            token_hash = hash_email_code('password-reset', email, code)
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.execute('DELETE FROM password_reset_tokens WHERE user_id = ?', (user['id'],))
            db.execute(
                'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)',
                (user['id'], token_hash, expires_at),
            )
            db.commit()
            try:
                send_templated_email(
                    user['email'], 'Your FAST CARS password reset code', 'Password reset requested',
                    f'Your password reset code is {code}. It expires in 10 minutes. If you did not request this, ignore this email.',
                    auth_only=True,
                )
            except Exception:
                logger.exception('Could not send password reset email to user %s', user['id'])
                db.execute('DELETE FROM password_reset_tokens WHERE user_id = ?', (user['id'],))
                db.commit()
        flash('If an account matches that email address, a password reset code has been sent.', 'info')
        return redirect(url_for('reset_password', email=email))
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = (request.values.get('email') or '').strip().lower()
    db = get_db()
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not is_valid_email(email):
            flash('Enter the email address where you received the code.', 'danger')
            return render_template('reset_password.html', email=email)
        if auth_rate_limited('password-reset-submit', email, max_attempts=8):
            flash('Too many reset attempts. Request a new code later.', 'danger')
            return render_template('reset_password.html', email=email)
        code_hash = hash_email_code('password-reset', email, code)
        reset = db.execute('SELECT * FROM password_reset_tokens WHERE token_hash = ?', (code_hash,)).fetchone()
        valid = False
        if reset:
            try:
                valid = datetime.fromisoformat(reset['expires_at']) > datetime.now(timezone.utc)
            except ValueError:
                valid = False
        if not valid:
            flash('That code is invalid or expired. Request a new reset code.', 'danger')
            return render_template('reset_password.html', email=email)
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        if len(new_password) < 8:
            flash('New password must be at least 8 characters.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            db.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                       (generate_password_hash(new_password), reset['user_id']))
            db.execute('DELETE FROM password_reset_tokens WHERE user_id = ?', (reset['user_id'],))
            db.commit()
            flash('Your password has been successfully reset. You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('reset_password.html', email=email)

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for('index'))

# ---------------------------------------------------------
# User Profile & Bookings
# ---------------------------------------------------------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()
            city = request.form.get('city', '').strip()
            country = request.form.get('country', '').strip()

            if not full_name:
                flash("Full name cannot be empty.", "danger")
            else:
                db.execute("""
                    UPDATE users 
                    SET full_name = ?, phone = ?, address = ?, city = ?, country = ?
                    WHERE id = ?
                """, (full_name, phone, address, city, country, g.user['id']))
                db.commit()
                session['user_name'] = full_name
                flash("Your profile details have been successfully updated.", "success")
                return redirect(url_for('profile'))

        elif action == 'request_password_change_code':
            old_password = request.form.get('old_password', '')
            if not check_password_hash(g.user['password_hash'], old_password):
                flash('Current password entered is incorrect.', 'danger')
                return redirect(url_for('profile', tab='security'))
            if auth_rate_limited('password-change-code', g.user['email'], max_attempts=3, window_seconds=900):
                flash('Please wait before requesting another password-change code.', 'danger')
                return redirect(url_for('profile', tab='security'))
            code = create_email_code()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.execute('DELETE FROM email_verification_codes WHERE user_id = ?', (g.user['id'],))
            db.execute('INSERT INTO email_verification_codes (user_id, code_hash, expires_at) VALUES (?, ?, ?)',
                       (g.user['id'], hash_email_code('change-password', g.user['email'], code), expires_at))
            db.commit()
            try:
                send_templated_email(g.user['email'], 'FAST CARS password change code',
                                     'Confirm your password change',
                                     f'Your password change code is {code}. It expires in 10 minutes.',
                                     auth_only=True)
                flash('A password-change code has been sent to your email.', 'success')
            except Exception:
                logger.exception('Could not send password change code for user %s', g.user['id'])
                flash('The code could not be sent. Check your email settings and try again.', 'danger')
            return redirect(url_for('profile', tab='security'))

        elif action == 'change_password':
            code = request.form.get('code', '').strip()
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            if auth_rate_limited('password-change-code-check', g.user['email'], max_attempts=8):
                flash('Too many code attempts. Request a new password-change code later.', 'danger')
                return redirect(url_for('profile', tab='security'))
            pending = db.execute('SELECT * FROM email_verification_codes WHERE user_id = ?',
                                 (g.user['id'],)).fetchone()
            matches = pending and hmac.compare_digest(
                pending['code_hash'], hash_email_code('change-password', g.user['email'], code))
            valid = False
            if matches:
                try:
                    valid = datetime.fromisoformat(pending['expires_at']) > datetime.now(timezone.utc)
                except ValueError:
                    valid = False
            if not valid:
                flash('The password-change code is invalid or expired. Request a new code.', 'danger')
                return redirect(url_for('profile', tab='security'))
            if not pending or not valid:
                return redirect(url_for('profile', tab='security'))
            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "danger")
            elif new_password != confirm_password:
                flash("New passwords do not match.", "danger")
            else:
                new_hash = generate_password_hash(new_password)
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, g.user['id']))
                db.execute('DELETE FROM email_verification_codes WHERE user_id = ?', (g.user['id'],))
                db.commit()
                flash("Password changed successfully!", "success")
                return redirect(url_for('profile', tab='security'))

    user_bookings_count = db.execute("SELECT COUNT(*) FROM bookings WHERE user_id = ?", (g.user['id'],)).fetchone()[0]
    user_testimonials_count = db.execute("SELECT COUNT(*) FROM testimonials WHERE user_id = ?", (g.user['id'],)).fetchone()[0]

    return render_template('profile.html', 
                           bookings_count=user_bookings_count,
                           testimonials_count=user_testimonials_count)

@app.route('/cars/<int:vehicle_id>/book', methods=['POST'])
@login_required
def book_car(vehicle_id):
    db = get_db()
    car = db.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
    if not car:
        flash("Vehicle not found.", "danger")
        return redirect(url_for('cars'))
    if car['status'] != 'Available':
        flash("This vehicle is not currently available for booking.", "warning")
        return redirect(url_for('car_details', vehicle_id=vehicle_id))

    from_date_str = request.form.get('from_date')
    to_date_str = request.form.get('to_date')
    pickup_location = request.form.get('pickup_location', '').strip()
    dropoff_location = request.form.get('dropoff_location', '').strip() or pickup_location
    driver_needed = 1 if request.form.get('driver_needed') else 0
    message = request.form.get('message', '').strip()

    if not from_date_str or not to_date_str or not pickup_location:
        flash("Please select pick-up date, return date, and location.", "danger")
        return redirect(url_for('car_details', vehicle_id=vehicle_id))

    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        today = date.today()

        if from_date < today:
            flash("Pick-up date cannot be in the past.", "danger")
            return redirect(url_for('car_details', vehicle_id=vehicle_id))
        if to_date < from_date:
            flash("Return date cannot be earlier than pick-up date.", "danger")
            return redirect(url_for('car_details', vehicle_id=vehicle_id))

        total_days = (to_date - from_date).days
        if total_days == 0:
            total_days = 1  # Minimum 1 day rental

        db.execute('BEGIN IMMEDIATE')
        conflict = db.execute("""
            SELECT id FROM bookings
            WHERE vehicle_id = ?
              AND status IN ('Pending', 'Confirmed')
              AND from_date < ? AND to_date > ?
            LIMIT 1
        """, (vehicle_id, to_date.isoformat(), from_date.isoformat())).fetchone()
        if conflict:
            db.rollback()
            flash("This vehicle is already reserved for some of those dates. Please choose different dates.", "warning")
            return redirect(url_for('car_details', vehicle_id=vehicle_id))

        # Base price calculation + optional driver fee ($35/day)
        daily_rate = car['price_per_day']
        driver_fee = 35.00 * total_days if driver_needed else 0.0
        total_price = (daily_rate * total_days) + driver_fee

        # Generate unique booking number
        rand_suffix = ''.join(random.choices(string.digits, k=4))
        booking_number = f"FC-{today.year}-{rand_suffix}"

        db.execute("""
            INSERT INTO bookings (
                booking_number, user_id, vehicle_id, from_date, to_date, total_days,
                total_price, pickup_location, dropoff_location, driver_needed, message, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            booking_number, g.user['id'], vehicle_id, from_date.isoformat(),
            to_date.isoformat(), total_days, total_price, pickup_location,
            dropoff_location, driver_needed, message
        ))
        db.commit()

        try:
            send_templated_email(
                g.user['email'], f"Reservation request {booking_number} received",
                "We received your reservation request",
                f"Your request for {car['title']} from {from_date.isoformat()} to {to_date.isoformat()} is pending confirmation. No online payment was taken.",
            )
        except Exception:
            logger.exception('Could not send booking email for booking %s', booking_number)
        support_email = g.settings.get('company_email', '').strip()
        if support_email:
            try:
                base_url = os.environ.get('PUBLIC_BASE_URL', request.url_root.rstrip('/'))
                send_templated_email(
                    support_email, f"New reservation request {booking_number}",
                    'A reservation request needs review',
                    f"Customer: {g.user['full_name']} ({g.user['email']})\nVehicle: {car['title']}\nDates: {from_date.isoformat()} through {to_date.isoformat()}\nTotal estimate: {total_price:.2f}",
                    f"{base_url.rstrip('/')}{url_for('admin_bookings')}", 'Review bookings',
                )
            except Exception:
                logger.exception('Could not notify staff for booking %s', booking_number)
        flash(f"Booking submitted successfully! Your reservation reference is #{booking_number}.", "success")
        return redirect(url_for('my_bookings'))

    except ValueError:
        flash("Invalid date format provided.", "danger")
        return redirect(url_for('car_details', vehicle_id=vehicle_id))

@app.route('/my-bookings')
@login_required
def my_bookings():
    db = get_db()
    bookings = db.execute("""
        SELECT b.*, v.title as car_title, v.image_url, v.fuel_type, v.model_year, br.name as brand_name
        FROM bookings b
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN brands br ON v.brand_id = br.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    """, (g.user['id'],)).fetchall()

    return render_template('my_bookings.html', bookings=bookings)

@app.route('/my-bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, g.user['id'])).fetchone()
    if not booking:
        flash("Booking record not found.", "danger")
        return redirect(url_for('my_bookings'))

    if booking['status'] == 'Cancelled':
        flash("This booking is already cancelled.", "info")
    elif booking['status'] == 'Confirmed':
        flash("Confirmed bookings cannot be cancelled online. Please contact customer service at " + g.settings.get('company_phone', 'our support line') + ".", "warning")
    else:
        db.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
        db.commit()
        flash("Your booking has been cancelled.", "info")

    return redirect(url_for('my_bookings'))

# ---------------------------------------------------------
# Testimonials (Public & User)
# ---------------------------------------------------------
@app.route('/testimonials', methods=['GET', 'POST'])
def testimonials():
    db = get_db()
    if request.method == 'POST':
        if not g.user:
            flash("Please log in to submit a testimonial.", "warning")
            return redirect(url_for('login', next=url_for('testimonials')))

        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        rating = request.form.get('rating', type=int)

        if not rating or not 1 <= rating <= 5:
            flash("Choose a rating from 1 to 5.", "danger")
        elif not content or len(content) > 2000 or len(title) > 120:
            flash("Enter feedback up to 2,000 characters and a title up to 120 characters.", "danger")
        else:
            db.execute("""
                INSERT INTO testimonials (user_id, rating, title, content, status)
                VALUES (?, ?, ?, ?, 0)
            """, (g.user['id'], rating, title, content))
            db.commit()
            flash("Thank you for sharing your experience! Your testimonial has been submitted for admin review.", "success")
            return redirect(url_for('testimonials'))

    # Public approved testimonials
    approved_list = db.execute("""
        SELECT t.*, u.full_name as user_name, u.city as user_city
        FROM testimonials t
        JOIN users u ON t.user_id = u.id
        WHERE t.status = 1
        ORDER BY t.created_at DESC
    """).fetchall()

    # User's own testimonials if logged in
    my_testimonials = []
    if g.user:
        my_testimonials = db.execute("""
            SELECT * FROM testimonials WHERE user_id = ? ORDER BY created_at DESC
        """, (g.user['id'],)).fetchall()

    return render_template('testimonials.html', 
                           approved_testimonials=approved_list, 
                           my_testimonials=my_testimonials)

# ---------------------------------------------------------
# Admin Portal Routes
# ---------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if g.admin:
        return redirect(url_for('admin_dashboard'))

    next_url = request.args.get('next')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if auth_rate_limited('admin-login', username.lower()):
            flash('Too many sign-in attempts. Please wait and try again.', 'danger')
            return render_template('admin/login.html', next_url=next_url)

        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE username = ? OR email = ?", (username, username)).fetchone()

        if admin and check_password_hash(admin['password_hash'], password):
            session.clear()
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash(f"Welcome to FAST CARS Admin Portal, {admin['full_name']}!", "success")
            if is_safe_redirect_target(next_url) and next_url.startswith('/admin'):
                return redirect(next_url)
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid administrator credentials.", "danger")

    return render_template('admin/login.html', next_url=next_url)

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if auth_rate_limited('admin-password-reset-request', email, max_attempts=5):
            flash('If an administrator account matches that email, a reset code has been sent.', 'info')
            return redirect(url_for('admin_reset_password', email=email))
        db = get_db()
        admin = db.execute('SELECT id, email FROM admins WHERE LOWER(email) = ?', (email,)).fetchone()
        if admin:
            code = create_email_code()
            expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
            db.execute('DELETE FROM admin_password_reset_codes WHERE admin_id = ?', (admin['id'],))
            db.execute('INSERT INTO admin_password_reset_codes (admin_id, code_hash, expires_at) VALUES (?, ?, ?)',
                       (admin['id'], hash_email_code('admin-password-reset', email, code), expires_at))
            db.commit()
            try:
                send_templated_email(admin['email'], 'FAST CARS administrator password reset code',
                                     'Administrator password reset',
                                     f'Your admin password reset code is {code}. It expires in 10 minutes.',
                                     auth_only=True)
            except Exception:
                logger.exception('Could not send admin password reset code for admin %s', admin['id'])
                db.execute('DELETE FROM admin_password_reset_codes WHERE admin_id = ?', (admin['id'],))
                db.commit()
        flash('If an administrator account matches that email, a reset code has been sent.', 'info')
        return redirect(url_for('admin_reset_password', email=email))
    return render_template('admin/forgot_password.html')

@app.route('/admin/reset-password', methods=['GET', 'POST'])
def admin_reset_password():
    email = (request.values.get('email') or '').strip().lower()
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        if not is_valid_email(email):
            flash('Enter the admin email that received the code.', 'danger')
            return render_template('admin/reset_password.html', email=email)
        if auth_rate_limited('admin-password-reset-submit', email, max_attempts=8):
            flash('Too many reset attempts. Request a new code later.', 'danger')
            return render_template('admin/reset_password.html', email=email)
        db = get_db()
        reset = db.execute('''
            SELECT r.*, a.email FROM admin_password_reset_codes r
            JOIN admins a ON a.id = r.admin_id
            WHERE LOWER(a.email) = ? AND r.code_hash = ?
        ''', (email, hash_email_code('admin-password-reset', email, code))).fetchone()
        valid = False
        if reset:
            try:
                valid = datetime.fromisoformat(reset['expires_at']) > datetime.now(timezone.utc)
            except ValueError:
                valid = False
        if not valid:
            flash('That code is invalid or expired. Request a new admin reset code.', 'danger')
        elif len(new_password) < 12:
            flash('Administrator passwords must be at least 12 characters.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            db.execute('UPDATE admins SET password_hash = ? WHERE id = ?',
                       (generate_password_hash(new_password), reset['admin_id']))
            db.execute('DELETE FROM admin_password_reset_codes WHERE admin_id = ?', (reset['admin_id'],))
            db.commit()
            flash('Administrator password reset successfully. Sign in with your new password.', 'success')
            return redirect(url_for('admin_login'))
    return render_template('admin/reset_password.html', email=email)

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    flash("Administrator logged out successfully.", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db()

    counts = {
        'users': db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'vehicles': db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
        'brands': db.execute("SELECT COUNT(*) FROM brands").fetchone()[0],
        'bookings': db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        'confirmed_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Confirmed'").fetchone()[0],
        'pending_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'").fetchone()[0],
        'cancelled_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Cancelled'").fetchone()[0],
        'queries': db.execute("SELECT COUNT(*) FROM contact_queries").fetchone()[0],
        'unread_queries': db.execute("SELECT COUNT(*) FROM contact_queries WHERE status = 'New'").fetchone()[0],
        'subscribers': db.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0],
        'testimonials': db.execute("SELECT COUNT(*) FROM testimonials").fetchone()[0],
        'pending_testimonials': db.execute("SELECT COUNT(*) FROM testimonials WHERE status = 0").fetchone()[0]
    }

    recent_bookings = db.execute("""
        SELECT b.*, u.full_name as user_name, u.email as user_email, v.title as vehicle_title
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN vehicles v ON b.vehicle_id = v.id
        ORDER BY b.created_at DESC
        LIMIT 6
    """).fetchall()

    recent_queries = db.execute("""
        SELECT * FROM contact_queries ORDER BY created_at DESC LIMIT 5
    """).fetchall()

    return render_template('admin/dashboard.html', counts=counts, recent_bookings=recent_bookings, recent_queries=recent_queries)

@app.route('/admin/dashboard/snapshot')
@admin_required
def admin_dashboard_snapshot():
    """Small authenticated snapshot used to refresh the dashboard when records change."""
    db = get_db()
    counts = {
        'users': db.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'vehicles': db.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0],
        'brands': db.execute('SELECT COUNT(*) FROM brands').fetchone()[0],
        'bookings': db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0],
        'pending_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Pending'").fetchone()[0],
        'confirmed_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Confirmed'").fetchone()[0],
        'cancelled_bookings': db.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Cancelled'").fetchone()[0],
        'queries': db.execute('SELECT COUNT(*) FROM contact_queries').fetchone()[0],
        'unread_queries': db.execute("SELECT COUNT(*) FROM contact_queries WHERE status = 'New'").fetchone()[0],
        'subscribers': db.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0],
        'testimonials': db.execute('SELECT COUNT(*) FROM testimonials').fetchone()[0],
        'pending_testimonials': db.execute('SELECT COUNT(*) FROM testimonials WHERE status = 0').fetchone()[0],
    }
    return jsonify(counts)

# Admin Brand Management
@app.route('/admin/brands', methods=['GET', 'POST'])
@admin_required
def admin_brands():
    db = get_db()
    if request.method == 'POST':
        brand_name = request.form.get('name', '').strip()
        if not brand_name:
            flash("Brand name cannot be blank.", "danger")
        else:
            existing = db.execute("SELECT id FROM brands WHERE LOWER(name) = LOWER(?)", (brand_name,)).fetchone()
            if existing:
                flash("A brand with this name already exists.", "warning")
            else:
                db.execute("INSERT INTO brands (name) VALUES (?)", (brand_name,))
                db.commit()
                flash(f"Brand '{brand_name}' created successfully.", "success")
                return redirect(url_for('admin_brands'))

    brands_list = db.execute("""
        SELECT b.*, COUNT(v.id) as vehicle_count 
        FROM brands b 
        LEFT JOIN vehicles v ON b.id = v.brand_id 
        GROUP BY b.id 
        ORDER BY b.name ASC
    """).fetchall()
    return render_template('admin/brands.html', brands=brands_list)

@app.route('/admin/brands/<int:brand_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_brand_edit(brand_id):
    db = get_db()
    brand = db.execute("SELECT * FROM brands WHERE id = ?", (brand_id,)).fetchone()
    if not brand:
        flash("Brand not found.", "danger")
        return redirect(url_for('admin_brands'))

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if not new_name:
            flash("Brand name cannot be empty.", "danger")
        else:
            duplicate = db.execute(
                "SELECT id FROM brands WHERE LOWER(name) = LOWER(?) AND id != ?",
                (new_name, brand_id),
            ).fetchone()
            if duplicate:
                flash("A brand with this name already exists.", "warning")
            else:
                db.execute("UPDATE brands SET name = ? WHERE id = ?", (new_name, brand_id))
                db.commit()
                flash("Brand updated successfully.", "success")
                return redirect(url_for('admin_brands'))

    return render_template('admin/brand_edit.html', brand=brand)

@app.route('/admin/brands/<int:brand_id>/delete', methods=['POST'])
@admin_required
def admin_brand_delete(brand_id):
    db = get_db()
    attached_cars = db.execute("SELECT COUNT(*) FROM vehicles WHERE brand_id = ?", (brand_id,)).fetchone()[0]
    if attached_cars > 0:
        flash(f"Cannot delete brand: {attached_cars} vehicle(s) are currently associated with it. Please reassign or delete those vehicles first.", "danger")
    else:
        db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
        db.commit()
        flash("Brand deleted successfully.", "success")
    return redirect(url_for('admin_brands'))

# Admin Vehicle Management
@app.route('/admin/vehicles')
@admin_required
def admin_vehicles():
    db = get_db()
    vehicles = db.execute("""
        SELECT v.*, b.name as brand_name 
        FROM vehicles v 
        JOIN brands b ON v.brand_id = b.id 
        ORDER BY v.id DESC
    """).fetchall()
    return render_template('admin/vehicles.html', vehicles=vehicles)

@app.route('/admin/vehicles/add', methods=['GET', 'POST'])
@admin_required
def admin_vehicle_add():
    db = get_db()
    brands = db.execute("SELECT * FROM brands ORDER BY name ASC").fetchall()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        brand_id = request.form.get('brand_id', type=int)
        overview = request.form.get('overview', '').strip()
        price_per_day = request.form.get('price_per_day', type=float)
        fuel_type = request.form.get('fuel_type')
        model_year = request.form.get('model_year', type=int)
        seating_capacity = request.form.get('seating_capacity', type=int)
        transmission = request.form.get('transmission')
        status = request.form.get('status', 'Available')
        category = request.form.get('category', 'Premium')

        brand_exists = brand_id and db.execute('SELECT 1 FROM brands WHERE id = ?', (brand_id,)).fetchone()
        valid_price = price_per_day is not None and math.isfinite(price_per_day) and price_per_day > 0
        if (not title or not brand_exists or not valid_price or fuel_type not in {'Petrol', 'Diesel', 'Electric', 'Hybrid'}
                or not model_year or not 1886 <= model_year <= date.today().year + 2
                or not seating_capacity or not 1 <= seating_capacity <= 100
                or transmission not in {'Automatic', 'Manual'}
                or category not in {'Small', 'Premium', 'Large'}
                or status not in {'Available', 'Booked', 'Maintenance'}):
            flash('Enter a valid vehicle title, brand, positive daily rate, year, seat count, transmission, category, and status.', 'danger')
            return render_template('admin/vehicle_add.html', brands=brands)

        # Features
        air_conditioner = 1 if request.form.get('air_conditioner') else 0
        power_door_locks = 1 if request.form.get('power_door_locks') else 0
        antilock_braking_system = 1 if request.form.get('antilock_braking_system') else 0
        brake_assist = 1 if request.form.get('brake_assist') else 0
        power_steering = 1 if request.form.get('power_steering') else 0
        driver_airbag = 1 if request.form.get('driver_airbag') else 0
        passenger_airbag = 1 if request.form.get('passenger_airbag') else 0
        power_windows = 1 if request.form.get('power_windows') else 0
        cd_player = 1 if request.form.get('cd_player') else 0
        central_locking = 1 if request.form.get('central_locking') else 0
        crash_sensor = 1 if request.form.get('crash_sensor') else 0
        leather_seats = 1 if request.form.get('leather_seats') else 0
        bluetooth = 1 if request.form.get('bluetooth') else 0
        child_seat = 1 if request.form.get('child_seat') else 0
        gps_navigation = 1 if request.form.get('gps_navigation') else 0

        # Require an actual photo for every angle so the gallery never repeats a placeholder.
        image_pairs = (
            ('image_url', 'image_file'),
            ('image_side', 'image_side_file'),
            ('image_rear', 'image_rear_file'),
            ('image_interior', 'image_interior_file'),
        )
        if not all(request.form.get(url_field, '').strip() or
                   (request.files.get(file_field) and request.files[file_field].filename)
                   for url_field, file_field in image_pairs):
            flash('Add a front, side, rear, and interior photo for this vehicle using a file or image URL.', 'danger')
            return render_template('admin/vehicle_add.html', brands=brands)
        upload_error = validate_vehicle_image_uploads(file_field for _, file_field in image_pairs)
        if upload_error:
            flash(upload_error, 'danger')
            return render_template('admin/vehicle_add.html', brands=brands)
        try:
            image_url = save_vehicle_image('image_url', 'image_file')
            image_side = save_vehicle_image('image_side', 'image_side_file')
            image_rear = save_vehicle_image('image_rear', 'image_rear_file')
            image_interior = save_vehicle_image('image_interior', 'image_interior_file')
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('admin/vehicle_add.html', brands=brands)

        db.execute("""
                INSERT INTO vehicles (
                    title, brand_id, overview, price_per_day, fuel_type, model_year,
                    seating_capacity, transmission, category, image_url, image_side, image_rear, image_interior, status,
                    air_conditioner, power_door_locks, antilock_braking_system, brake_assist,
                    power_steering, driver_airbag, passenger_airbag, power_windows,
                    cd_player, central_locking, crash_sensor, leather_seats, bluetooth,
                    child_seat, gps_navigation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
                title, brand_id, overview, price_per_day, fuel_type, model_year,
                seating_capacity, transmission, category, image_url, image_side, image_rear, image_interior, status,
                air_conditioner, power_door_locks, antilock_braking_system, brake_assist,
                power_steering, driver_airbag, passenger_airbag, power_windows,
                cd_player, central_locking, crash_sensor, leather_seats, bluetooth,
                child_seat, gps_navigation
        ))
        db.commit()
        flash(f"Vehicle '{title}' posted successfully!", "success")
        return redirect(url_for('admin_vehicles'))

    return render_template('admin/vehicle_add.html', brands=brands)

@app.route('/admin/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_vehicle_edit(vehicle_id):
    db = get_db()
    vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
    if not vehicle:
        flash("Vehicle not found.", "danger")
        return redirect(url_for('admin_vehicles'))

    brands = db.execute("SELECT * FROM brands ORDER BY name ASC").fetchall()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        brand_id = request.form.get('brand_id', type=int)
        overview = request.form.get('overview', '').strip()
        price_per_day = request.form.get('price_per_day', type=float)
        fuel_type = request.form.get('fuel_type')
        model_year = request.form.get('model_year', type=int)
        seating_capacity = request.form.get('seating_capacity', type=int)
        transmission = request.form.get('transmission')
        status = request.form.get('status', 'Available')
        category = request.form.get('category', vehicle['category'] or 'Premium')

        brand_exists = brand_id and db.execute('SELECT 1 FROM brands WHERE id = ?', (brand_id,)).fetchone()
        valid_price = price_per_day is not None and math.isfinite(price_per_day) and price_per_day > 0
        if (not title or not brand_exists or not valid_price or fuel_type not in {'Petrol', 'Diesel', 'Electric', 'Hybrid'}
                or not model_year or not 1886 <= model_year <= date.today().year + 2
                or not seating_capacity or not 1 <= seating_capacity <= 100
                or transmission not in {'Automatic', 'Manual'}
                or category not in {'Small', 'Premium', 'Large'}
                or status not in {'Available', 'Booked', 'Maintenance'}):
            flash('Enter a valid vehicle title, brand, positive daily rate, year, seat count, transmission, category, and status.', 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, brands=brands)

        air_conditioner = 1 if request.form.get('air_conditioner') else 0
        power_door_locks = 1 if request.form.get('power_door_locks') else 0
        antilock_braking_system = 1 if request.form.get('antilock_braking_system') else 0
        brake_assist = 1 if request.form.get('brake_assist') else 0
        power_steering = 1 if request.form.get('power_steering') else 0
        driver_airbag = 1 if request.form.get('driver_airbag') else 0
        passenger_airbag = 1 if request.form.get('passenger_airbag') else 0
        power_windows = 1 if request.form.get('power_windows') else 0
        cd_player = 1 if request.form.get('cd_player') else 0
        central_locking = 1 if request.form.get('central_locking') else 0
        crash_sensor = 1 if request.form.get('crash_sensor') else 0
        leather_seats = 1 if request.form.get('leather_seats') else 0
        bluetooth = 1 if request.form.get('bluetooth') else 0
        child_seat = 1 if request.form.get('child_seat') else 0
        gps_navigation = 1 if request.form.get('gps_navigation') else 0

        upload_error = validate_vehicle_image_uploads(
            ('image_file', 'image_side_file', 'image_rear_file', 'image_interior_file')
        )
        if upload_error:
            flash(upload_error, 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, brands=brands)

        try:
            image_url = save_vehicle_image('image_url', 'image_file', vehicle['image_url'])
            image_side = save_vehicle_image('image_side', 'image_side_file', vehicle['image_side'])
            image_rear = save_vehicle_image('image_rear', 'image_rear_file', vehicle['image_rear'])
            image_interior = save_vehicle_image('image_interior', 'image_interior_file', vehicle['image_interior'])
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, brands=brands)

        if not all((image_url, image_side, image_rear, image_interior)):
            flash('This vehicle needs a front, side, rear, and interior photo. Provide each missing view using a file or image URL.', 'danger')
            return render_template('admin/vehicle_edit.html', vehicle=vehicle, brands=brands)

        db.execute("""
            UPDATE vehicles SET
                title = ?, brand_id = ?, overview = ?, price_per_day = ?,
                fuel_type = ?, model_year = ?, seating_capacity = ?, transmission = ?, category = ?,
                image_url = ?, image_side = ?, image_rear = ?, image_interior = ?, status = ?,
                air_conditioner = ?, power_door_locks = ?, antilock_braking_system = ?, brake_assist = ?,
                power_steering = ?, driver_airbag = ?, passenger_airbag = ?, power_windows = ?,
                cd_player = ?, central_locking = ?, crash_sensor = ?, leather_seats = ?, bluetooth = ?,
                child_seat = ?, gps_navigation = ?
            WHERE id = ?
        """, (
            title, brand_id, overview, price_per_day, fuel_type, model_year,
            seating_capacity, transmission, category,
            image_url, image_side, image_rear, image_interior, status,
            air_conditioner, power_door_locks, antilock_braking_system, brake_assist,
            power_steering, driver_airbag, passenger_airbag, power_windows,
            cd_player, central_locking, crash_sensor, leather_seats, bluetooth,
            child_seat, gps_navigation, vehicle_id
        ))
        db.commit()
        flash("Vehicle updated successfully.", "success")
        return redirect(url_for('admin_vehicles'))

    return render_template('admin/vehicle_edit.html', vehicle=vehicle, brands=brands)

@app.route('/admin/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@admin_required
def admin_vehicle_delete(vehicle_id):
    db = get_db()
    db.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
    db.commit()
    flash("Vehicle deleted successfully.", "success")
    return redirect(url_for('admin_vehicles'))

# Admin Booking Management
@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    db = get_db()
    status_filter = request.args.get('status', 'all')
    
    query = """
        SELECT b.*, u.full_name as user_name, u.email as user_email, u.phone as user_phone,
               v.title as vehicle_title, br.name as brand_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN vehicles v ON b.vehicle_id = v.id
        JOIN brands br ON v.brand_id = br.id
    """
    params = []
    if status_filter != 'all':
        query += " WHERE b.status = ?"
        params.append(status_filter.capitalize())

    query += " ORDER BY b.created_at DESC"
    bookings = db.execute(query, params).fetchall()

    return render_template('admin/bookings.html', bookings=bookings, current_filter=status_filter)

@app.route('/admin/bookings/<int:booking_id>/status', methods=['POST'])
@admin_required
def admin_booking_status(booking_id):
    new_status = request.form.get('status')
    admin_remark = request.form.get('admin_remark', '').strip()

    if new_status in ['Pending', 'Confirmed', 'Cancelled']:
        db = get_db()
        booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
        if not booking:
            flash("Booking record not found.", "warning")
            return redirect(url_for('admin_bookings'))
        if new_status == 'Confirmed':
            overlap = db.execute("""
                SELECT id FROM bookings
                WHERE vehicle_id = ? AND id != ?
                  AND status IN ('Pending', 'Confirmed')
                  AND from_date < ? AND to_date > ?
                LIMIT 1
            """, (booking['vehicle_id'], booking_id, booking['to_date'], booking['from_date'])).fetchone()
            if overlap:
                flash("This vehicle has another active reservation during those dates. Resolve it before confirming this booking.", "danger")
                return redirect(url_for('admin_bookings'))
        db.execute("""
            UPDATE bookings 
            SET status = ?, admin_remark = ?
            WHERE id = ?
        """, (new_status, admin_remark, booking_id))
        db.commit()
        user = db.execute("""
            SELECT u.email, b.booking_number FROM bookings b
            JOIN users u ON u.id = b.user_id WHERE b.id = ?
        """, (booking_id,)).fetchone()
        if user:
            try:
                send_templated_email(
                    user['email'], f"Booking {user['booking_number']} update",
                    f"Your booking is {new_status.lower()}",
                    admin_remark or f"Your reservation status is now {new_status}.",
                )
            except Exception:
                logger.exception('Could not send status email for booking %s', booking_id)
        flash(f"Booking status updated to '{new_status}'.", "success")
    return redirect(url_for('admin_bookings'))

# Admin Testimonials Management
@app.route('/admin/testimonials')
@admin_required
def admin_testimonials():
    db = get_db()
    testimonials = db.execute("""
        SELECT t.*, u.full_name as user_name, u.email as user_email
        FROM testimonials t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """).fetchall()
    return render_template('admin/testimonials.html', testimonials=testimonials)

@app.route('/admin/testimonials/<int:testimonial_id>/toggle', methods=['POST'])
@admin_required
def admin_testimonial_toggle(testimonial_id):
    db = get_db()
    t = db.execute("SELECT status FROM testimonials WHERE id = ?", (testimonial_id,)).fetchone()
    if t:
        new_status = 0 if t['status'] == 1 else 1
        db.execute("UPDATE testimonials SET status = ? WHERE id = ?", (new_status, testimonial_id))
        db.commit()
        status_label = "Active (Published)" if new_status == 1 else "Inactive (Hidden)"
        flash(f"Testimonial marked as {status_label}.", "success")
    return redirect(url_for('admin_testimonials'))

@app.route('/admin/testimonials/<int:testimonial_id>/delete', methods=['POST'])
@admin_required
def admin_testimonial_delete(testimonial_id):
    db = get_db()
    db.execute("DELETE FROM testimonials WHERE id = ?", (testimonial_id,))
    db.commit()
    flash("Testimonial deleted successfully.", "success")
    return redirect(url_for('admin_testimonials'))

# Admin Contact Queries Management
@app.route('/admin/contacts')
@admin_required
def admin_contacts():
    db = get_db()
    queries = db.execute("SELECT * FROM contact_queries ORDER BY created_at DESC").fetchall()
    return render_template('admin/contacts.html', queries=queries)

@app.route('/admin/contacts/<int:query_id>/status', methods=['POST'])
@admin_required
def admin_contact_status(query_id):
    status = request.form.get('status', 'Read')
    admin_note = request.form.get('admin_note', '').strip()
    reply_message = request.form.get('reply_message', '').strip()
    db = get_db()
    query = db.execute('SELECT * FROM contact_queries WHERE id = ?', (query_id,)).fetchone()
    if not query:
        flash('Inquiry not found.', 'warning')
        return redirect(url_for('admin_contacts'))
    if status not in {'New', 'Read', 'Replied'}:
        flash('Choose a valid inquiry status.', 'danger')
        return redirect(url_for('admin_contacts'))
    if status == 'Replied':
        if not reply_message:
            flash('Enter a reply message before marking the inquiry as replied.', 'danger')
            return redirect(url_for('admin_contacts'))
        try:
            send_templated_email(
                query['email'],
                f"Response to your FAST CARS inquiry: {query['subject'] or 'General question'}",
                'A response from FAST CARS',
                reply_message,
            )
        except Exception:
            logger.exception('Could not send reply for contact inquiry %s', query_id)
            flash('The reply could not be sent. The inquiry was not marked as replied.', 'danger')
            return redirect(url_for('admin_contacts'))
    db.execute("UPDATE contact_queries SET status = ?, admin_note = ? WHERE id = ?", (status, admin_note, query_id))
    db.commit()
    flash('Reply sent and inquiry marked as replied.' if status == 'Replied' else f"Inquiry marked as '{status}'.", 'success')
    return redirect(url_for('admin_contacts'))

@app.route('/admin/contacts/<int:query_id>/delete', methods=['POST'])
@admin_required
def admin_contact_delete(query_id):
    db = get_db()
    db.execute("DELETE FROM contact_queries WHERE id = ?", (query_id,))
    db.commit()
    flash("Inquiry deleted successfully.", "success")
    return redirect(url_for('admin_contacts'))

# Admin Registered Users Management
@app.route('/admin/users')
@admin_required
def admin_users():
    db = get_db()
    users = db.execute("""
        SELECT u.*, COUNT(b.id) as booking_count
        FROM users u
        LEFT JOIN bookings b ON u.id = b.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_user_delete(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("User account deleted successfully.", "success")
    return redirect(url_for('admin_users'))

# Admin Newsletter Subscribers
@app.route('/admin/subscribers')
@admin_required
def admin_subscribers():
    db = get_db()
    subscribers = db.execute("SELECT * FROM subscribers ORDER BY subscribed_at DESC").fetchall()
    return render_template('admin/subscribers.html', subscribers=subscribers)

@app.route('/admin/subscribers/<int:sub_id>/delete', methods=['POST'])
@admin_required
def admin_subscriber_delete(sub_id):
    db = get_db()
    db.execute("DELETE FROM subscribers WHERE id = ?", (sub_id,))
    db.commit()
    flash("Subscriber removed.", "success")
    return redirect(url_for('admin_subscribers'))

# Admin Page Content & Settings Management
@app.route('/admin/pages', methods=['GET', 'POST'])
@admin_required
def admin_pages():
    db = get_db()
    if request.method == 'POST':
        for key in ['company_name', 'company_phone', 'company_email', 'company_address', 'working_hours', 'about_us', 'terms_conditions', 'privacy_policy']:
            if key in request.form:
                val = request.form.get(key, '').strip()
                db.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (key, val))
        db.commit()
        flash("Website settings and page content updated successfully.", "success")
        return redirect(url_for('admin_pages'))

    settings_rows = db.execute("SELECT key, value FROM site_settings").fetchall()
    settings_dict = {row['key']: row['value'] for row in settings_rows}
    return render_template('admin/pages.html', settings=settings_dict)

# Admin Change Password
@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE id = ?", (g.admin['id'],)).fetchone()

        if not check_password_hash(admin['password_hash'], current_password):
            flash("Current administrator password is incorrect.", "danger")
        elif len(new_password) < 12:
            flash("New administrator passwords must be at least 12 characters long.", "danger")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        else:
            new_hash = generate_password_hash(new_password)
            db.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (new_hash, admin['id']))
            db.commit()
            flash("Administrator password updated successfully.", "success")
            return redirect(url_for('admin_dashboard'))

    return render_template('admin/change_password.html')

# ---------------------------------------------------------
# Run entrypoint
# ---------------------------------------------------------
if __name__ == '__main__':
    init_db()
    print("FAST CARS Rental Booking System is starting on http://127.0.0.1:5000")
    app.run(debug=not IS_PRODUCTION, port=int(os.environ.get('PORT', '5000')))
