# FAST CARS - Car Rental Booking System
> **Aptech eProject Deliverable (Python & Web Engineering)**  
> Developed for **FAST CARS Inc.**

---

## 📌 Executive Summary

**FAST CARS** is a Flask and SQLite car-rental reservation application with a public fleet, customer accounts, reservation requests, and an administration portal. It includes a Docker production image and a persistent-volume deployment setup. A real launch still requires verified company details, a configured domain, and Resend credentials.

The application is built using **Python (Flask)**, **SQLite3**, **HTML5**, **CSS3**, and **JavaScript**, adhering strictly to modern security best practices (cryptographic password hashing with PBKDF2/SHA-256, SQL injection prevention via parameterized queries, and role-based access control).

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
* **Car Reservation:** Reservation requests with date conflict checks, custom pick-up/drop-off locations, and optional chauffeur service ($35/day). Online payments are not enabled.
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
| **Administrator** | `admin` or `awelethomasjoshua619@gmail.com` | `admin123` *(unless changed)* | [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login) |
| **Registered User** | `john@example.com` | `user123` | [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) |

The administrator email above is assigned to the admin account; the email alone does not grant admin access. Use the admin password, or choose **Forgot admin password?** to receive a one-time reset code at that address. Public admin registration is disabled. These demo credentials apply only to the development database. Production startup does not seed sample accounts or sample bookings.

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

The local app uses a development database seeded with sample fleet and demo accounts. Gmail SMTP can deliver registration verification, password reset, and password-change codes directly from the admin Gmail account. Enable Google 2-Step Verification and create an App Password in the Google Account; use that 16-character App Password in `.env`, not the normal Gmail password. The app deliberately keeps booking, contact, and newsletter messages out of Gmail. If the SMTP settings are incomplete, development email is logged in the terminal. Restart `python run.py` after saving `.env`. Reservation requests are stored and managed by staff; online card payments are not enabled.

## Optional Production Deployment with Docker

1. Copy .env.example to .env and set a strong SECRET_KEY. Generate one with python -c "import secrets; print(secrets.token_urlsafe(48))".
2. Set PUBLIC_BASE_URL to the final HTTPS website address.
3. Add a Resend API key and a sender address on a domain verified in Resend. The app checks these settings and refuses to start in production when they are missing.
4. Start the service with docker compose up --build -d. Docker Compose stores the SQLite database in a named persistent volume and uploaded car images in static/uploads.
5. Create the first administrator interactively with docker compose exec web flask --app app create-admin.
6. Sign in, add the real fleet and company details, and confirm the contact, terms, and privacy pages before launch.

The deployment exposes /healthz for platform health checks. For a managed host, deploy the Docker image with persistent storage mounted at /data, preserve the environment variables from .env.example, and use the host-provided HTTPS URL in PUBLIC_BASE_URL.

For local real-email delivery, use the Resend settings above. Public production hosting additionally requires HTTPS and production settings.

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
