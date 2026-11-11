# FAST CARS - Car Rental Booking System
> **Aptech eProject Deliverable (Python & Web Engineering)**  
> Academic school project demonstrating a car-rental booking website.

---

## 📌 Executive Summary

**FAST CARS** is a school project: a Flask and SQLite car-rental reservation application with a sample public fleet, customer accounts, reservation requests, and an administration portal. It includes an optional Docker image and persistent-volume setup. It is a demonstration system rather than a verified rental business; set presentation contact details, currency, and policies to the values you intend to show.

The stack is **Python 3**, **Flask**, **SQLite 3**, **HTML5**, **CSS3**, and **JavaScript**, with Flask-WTF for forms and CSRF protection, Werkzeug for password hashing, python-dotenv for local configuration, and Gmail SMTP or Resend for email.

---

## 🚀 Key Features & Modules

### 1. Guest Users (Public Visitors)
* **Fleet Catalog & Showcase:** Explore vehicles with high-resolution imagery, technical specs (Fuel Type, Model Year, Transmission, Seating Capacity), and daily rental rates.
* **Smart Search & Filters:** Search by keyword, brand, fuel type (Petrol, Electric, Hybrid, Diesel), transmission, and daily budget limits.
* **Interactive Booking Calculator:** Select pick-up/return dates to calculate rental days, daily rate, and optional chauffeur service fee in real-time.
* **Contact & Inquiries:** Save corporate and general rental inquiries for administration and send acknowledgement emails.
* **Company Information:** Learn about FAST CARS through dynamic About Us, FAQ, Rental Terms, and Privacy Policy sections.
* **Newsletter Subscription:** Collect email addresses for future promotions in the admin portal.

### 2. Registered Users (Customer Portal)
* **User Registration & Security:** Create accounts with full profile details and secure password hashing.
* **Email Verification:** New customer accounts receive a six-digit email code and cannot sign in until the address is verified.
* **Password Recovery:** Single-use, time-limited six-digit reset codes are sent to the account email.
* **Car Reservation:** Reservation requests with date conflict checks, custom pick-up/drop-off locations, and an optional chauffeur fee configured by an administrator. Online payments are not enabled.
* **Booking History & Status Tracking:** Monitor reservation status (`Pending`, `Confirmed`, `Cancelled`).
* **Booking Summary:** View and print reservation details and the estimated rental total.
* **Profile Management:** Update personal contact details and change account passwords.
* **Feedback & Reviews:** Submit star ratings (1–5) and reviews for admin moderation.

### 3. Administrator Portal (Super User)
* **Executive Analytics Dashboard:** Real-time KPI counters (Total Users, Fleet Size, Brands, Total Bookings, Confirmed/Pending/Cancelled breakdown, Inquiries, Active Testimonials, Subscribers).
* **Vehicle Brand Management:** Create, edit, and delete vehicle brands (with relational integrity protection).
* **Vehicle Fleet Management (CRUD):** Post vehicles with specifications, operational status, and 15 feature checkboxes. Each vehicle has its own front, side, rear, and interior photos, uploaded locally or provided by image URL.
* **Booking Management:** Review incoming bookings, confirm reservations, cancel with remarks, and manage pickup schedules.
* **Testimonials Moderation:** Approve (Activate) or Hide (Deactivate) customer reviews with one click.
* **Contact Queries Management:** Read customer inquiries, append internal follow-up notes, and track reply status.
* **User Accounts Oversight:** View registered customer accounts, joined dates, and lifetime booking frequency.
* **Newsletter Subscribers:** View and manage email subscriber lists.
* **Content Management System (CMS):** Update company phone, email, street address, business hours, and full legal page narratives.
* **Security & Credentials:** Sign in using the provisioned administrator username or email, change the admin password, and recover it with a one-time code sent to the administrator email.

---

## Demo Accounts (Local Development Only)

| Role | Username / Email | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` or the address set in `DEMO_ADMIN_EMAIL` | `admin123` *(unless changed)* | [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login) |
| **Registered User** | `john@example.com` | `user123` | [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) |

The administrator email is assigned to the admin account; the email alone does not grant admin access. Set `DEMO_ADMIN_EMAIL` in `.env` to an inbox you can access so **Forgot admin password?** delivers its one-time code there. Public admin registration is disabled. These demo credentials apply only to the development database and are not shown on login pages. Production startup does not seed sample accounts or sample bookings.

---

## 🛠️ Installation & Running the Application

### Prerequisites
* **Python 3.8+** (Tested on Python 3.13)
* Web browser (Chrome, Edge, Firefox, Safari)

### Quick Start (Windows / Mac / Linux)

1. Open PowerShell or Command Prompt in the project directory:
   ```bash
   cd "c:\Users\tjayt\Desktop\car website"
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the local application (no hosting account, domain, API key, or payment setup is needed):
   ```bash
   python run.py
   ```

4. Open your browser and navigate to:
   * **Public Website:** `http://127.0.0.1:5000/`
   * **Admin Management Portal:** `http://127.0.0.1:5000/admin/login`

---

## 🧪 Automated Testing

A local automated test suite is included in `test_app.py`, covering public routes, user registration and login, email password-reset flow, reservation checks, Resend request format, CSRF, and selected admin actions:

```bash
python test_app.py
```

---

### Local demonstration scope

The local app uses a development database seeded with sample fleet and demo accounts. Configure a working mail provider for verification codes, password recovery, booking notices, contact inquiries and replies, profile changes, reviews, and newsletter confirmations. Gmail SMTP requires Google 2-Step Verification and a 16-character App Password in `.env`; the host must also allow outbound SMTP connections. The app reports when an email cannot be delivered. If a support reply cannot be delivered, the inquiry is not marked as replied. Reservation requests are stored and managed by staff; online card payments are not enabled. Set the rental currency and any chauffeur fee in Admin → Website Content before publishing the catalog.

## Optional Production Deployment with Docker

1. Copy .env.example to .env and set a strong SECRET_KEY. Generate one with python -c "import secrets; print(secrets.token_urlsafe(48))".
2. Set PUBLIC_BASE_URL to the final HTTPS website address.
3. Configure the production email provider. Resend requires an API key and verified sender address; Gmail SMTP requires an app password and reachable SMTP host. Production startup validates required settings.
4. Start the service with docker compose up --build -d. Docker Compose stores the SQLite database in a named persistent volume and uploaded car images in static/uploads.
5. Create the first administrator interactively with docker compose exec web flask --app app create-admin.
6. Sign in, add the real fleet and company details, and confirm the contact, terms, and privacy pages before launch.

The deployment exposes /healthz for platform health checks. For a managed host, deploy the Docker image with persistent storage mounted at /data, preserve the environment variables from .env.example, and use the host-provided HTTPS URL in PUBLIC_BASE_URL.

For live email delivery, configure either Gmail SMTP or Resend in `.env`. Public production hosting additionally requires HTTPS and production settings.

## 📁 Project Directory Structure

```text
car website/
├── app.py                     # Main application routes & controller logic
├── database.py                # Database connection manager, schema execution & seed data
├── models.py                  # Database helpers & queries
├── run.py                     # Project runner script
├── requirements.txt           # Python package requirements
├── schema.sql                 # Complete relational database DDL script
├── fastcars.db                # SQLite database (auto-generated with seed data)
├── fastcars_backup.sql        # Database backup SQL dump
├── test_app.py                # Automated unit test suite
├── PROJECT_REPORT.md          # Comprehensive Aptech eProject Documentation Report
├── README.md                  # System overview & instructions
├── static/
│   ├── css/
│   │   ├── style.css          # Public responsive frontend stylesheet
│   │   └── admin.css          # Admin dashboard stylesheet
│   ├── js/
│   │   └── main.js            # Real-time price calculation, star picker, invoice print
│   └── uploads/               # Vehicle photo upload storage
└── templates/
    ├── base.html              # Base public layout with navigation & footer
    ├── index.html             # Homepage with hero, filters, featured fleet & reviews
    ├── cars.html              # Full fleet catalog with multi-parameter filtering
    ├── car_details.html       # Vehicle details, specifications & booking form
    ├── about.html             # Company story, mission & core values
    ├── contact.html           # Contact Us inquiry form & corporate info
    ├── faq.html               # Frequently asked questions
    ├── terms.html             # Rental terms & conditions
    ├── privacy.html           # Privacy policy
    ├── login.html             # User authentication
    ├── register.html          # User registration
    ├── forgot_password.html   # Request a six-digit email reset code
    ├── reset_password.html    # Use a one-time password reset code
    ├── verify_email.html      # Verify a new account by email code
    ├── profile.html           # Profile update & password change
    ├── my_bookings.html       # Booking history, cancellation & invoice receipt
    ├── testimonials.html      # Public reviews & review submission
    └── admin/
        ├── base_admin.html    # Admin portal sidebar layout
        ├── login.html         # Admin login
        ├── dashboard.html     # Real-time analytics & KPIs
        ├── brands.html        # Brand management & creation
        ├── brand_edit.html    # Edit vehicle brand
        ├── vehicles.html      # Fleet inventory table
        ├── vehicle_add.html   # Post vehicle form (specs & 15 features)
        ├── vehicle_edit.html  # Edit vehicle details
        ├── bookings.html      # Manage bookings (Confirm / Cancel / Remark)
        ├── testimonials.html  # Moderate reviews (Active / Inactive)
        ├── contacts.html      # Manage contact inquiries & notes
        ├── users.html         # Manage registered users
        ├── subscribers.html   # Manage newsletter subscribers
        ├── pages.html         # CMS for pages & company contact info
        └── change_password.html # Admin credential updater
```
