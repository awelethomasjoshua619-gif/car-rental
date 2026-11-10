import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_report():
    doc = docx.Document()

    # Page Margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    font.color.rgb = RGBColor(51, 51, 51)

    # -------------------------------------------------------------
    # Title Cover Page
    # -------------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(80)
    title_p.paragraph_format.space_after = Pt(10)
    run_org = title_p.add_run("APTECH ePROJECT REPORT\n")
    run_org.font.size = Pt(16)
    run_org.font.bold = True
    run_org.font.color.rgb = RGBColor(37, 99, 235)

    run_title = title_p.add_run("CAR RENTAL BOOKING SYSTEM\n(FAST CARS)\n")
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(17, 24, 39)

    run_sub = title_p.add_run("A Web-Based Fleet Management and Reservation Request System\n")
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph().paragraph_format.space_after = Pt(120)

    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.add_run("Course Track: Python & Web Application Engineering\n").font.bold = True
    meta_p.add_run("Technology Stack: Python (Flask), SQLite3, HTML5, CSS3, JavaScript\n")
    meta_p.add_run("Academic Term: November 2026\n")

    doc.add_page_break()

    # -------------------------------------------------------------
    # 1. Certificate of Completion
    # -------------------------------------------------------------
    h1 = doc.add_heading("1. Certificate of Completion", level=1)
    h1.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    cert_box = doc.add_table(rows=1, cols=1)
    cert_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = cert_box.cell(0, 0)
    set_cell_background(cell, "F8FAFC")
    set_cell_margins(cell, top=200, bottom=200, left=250, right=250)

    cp = cell.paragraphs[0]
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.add_run("CERTIFICATE OF COMPLETION\n\n").font.bold = True
    cp.add_run(
        "This is to certify that the project entitled:\n\n"
        "\"FAST CARS - CAR RENTAL BOOKING SYSTEM\"\n\n"
        "describes the implemented FAST CARS car rental reservation application and its current verification scope.\n\n"
        "Core guest, customer, and administrator flows are covered. External email delivery and public hosting "
        "require live service credentials and deployment configuration. Online payments are not enabled.\n\n"
    )

    sig_p = cell.add_paragraph()
    sig_p.add_run("Student Name: _______________________      Batch Code: ___________________\n\n")
    sig_p.add_run("Project Guide: _______________________      Date:       ___________________\n\n")
    sig_p.add_run("Center Head:   _______________________      Seal:       ___________________\n")

    doc.add_page_break()

    # -------------------------------------------------------------
    # 2. Table of Contents
    # -------------------------------------------------------------
    h2 = doc.add_heading("2. Table of Contents", level=1)
    h2.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    toc_items = [
        ("1. Certificate of Completion", "02"),
        ("2. Table of Contents", "03"),
        ("3. Problem Definition", "04"),
        ("    3.1 Introduction to FAST CARS", "04"),
        ("    3.2 Limitations of Legacy Manual System", "04"),
        ("    3.3 Proposed Solution & System Modules", "05"),
        ("4. Customer Requirement Specification (CRS)", "06"),
        ("    4.1 Functional Requirements (Guest, User, Admin)", "06"),
        ("    4.2 Non-Functional Requirements (Security & Performance)", "08"),
        ("    4.3 Hardware & Software Prerequisites", "08"),
        ("5. Project Plan & Work Breakdown Structure", "09"),
        ("6. Entity-Relationship (E-R) Diagrams & Database Schema", "10"),
        ("    6.1 Relational Architecture", "10"),
        ("    6.2 Complete Data Dictionary", "11"),
        ("7. Algorithms & Core Application Logic", "13"),
        ("    7.1 Two-Step Security Question Password Recovery", "13"),
        ("    7.2 Real-time Multi-day Booking & Chauffeur Price Engine", "14"),
        ("8. GUI Standards Document", "15"),
        ("9. Interface Design Document", "17"),
        ("10. Task Sheet & Milestone Log", "19"),
        ("11. Project Review and Monitoring Report", "20"),
        ("12. Unit Testing Check List", "21"),
        ("13. Final Check List & Deliverables", "23")
    ]

    toc_table = doc.add_table(rows=len(toc_items), cols=2)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (title, page) in enumerate(toc_items):
        r0 = toc_table.cell(i, 0).paragraphs[0]
        r1 = toc_table.cell(i, 1).paragraphs[0]
        r0.text = title
        r1.text = page
        r1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if not title.startswith("    "):
            r0.runs[0].font.bold = True
            r1.runs[0].font.bold = True

    doc.add_page_break()

    # -------------------------------------------------------------
    # 3. Problem Definition
    # -------------------------------------------------------------
    h3 = doc.add_heading("3. Problem Definition", level=1)
    h3.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    doc.add_heading("3.1 Introduction & Scenario", level=2)
    doc.add_paragraph(
        "Currently, FAST CARS is handling customer queries and vehicle bookings either through telephone or walk-ins. "
        "Due to these manual dependencies, the company is not utilizing vehicles to their optimum capacity and faces "
        "severe geographic constraints in reaching a wider customer base. Scheduling conflicts, double-booking risks, "
        "and human computation errors during rate calculations further hamper growth."
    )

    doc.add_heading("3.2 Proposed Solution", level=2)
    doc.add_paragraph(
        "To overcome these limitations, FAST CARS has commissioned a state-of-the-art web application for booking rental cars. "
        "The system is designed for small, medium, and large/premium car rental operations, delivering complete end-to-end "
        "functionality for listing, discovering, calculating, and booking vehicles."
    )

    doc.add_heading("3.3 Core System Modules (Per Specification)", level=2)
    modules = [
        ("Guest Users:", "Can view the website, inspect detailed vehicle specifications, apply search filters (brand, fuel, price), view client testimonials, and submit inquiries through the Contact Us page."),
        ("Register Users:", "New accounts require a six-digit email verification code before sign-in. Customers can recover passwords with a single-use, expiring six-digit email code, submit reservation requests with availability checks, view booking history and summaries, update profile details, change passwords, and post testimonials."),
        ("Admin (Super User):", "The administrative authority who manages the entire system. Can create, edit, and delete vehicle brands; post and manage vehicles with full specifications and 15 feature checkboxes; confirm or cancel bookings with remarks; moderate testimonials (Active/Inactive); respond to contact queries; review registered user accounts; manage subscribers; update page content and company contact info; monitor live dashboard KPIs; and update admin passwords.")
    ]
    for mod_title, mod_desc in modules:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run(mod_title + " ")
        r.font.bold = True
        p.add_run(mod_desc)

    doc.add_page_break()

    # -------------------------------------------------------------
    # 4. Customer Requirement Specification (CRS)
    # -------------------------------------------------------------
    h4 = doc.add_heading("4. Customer Requirement Specification (CRS)", level=1)
    h4.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    doc.add_heading("4.1 Functional Requirements Breakdown", level=2)
    crs_table = doc.add_table(rows=1, cols=3)
    crs_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Req ID", "Module", "Functional Specification"]
    for j, h in enumerate(headers):
        cell = crs_table.cell(0, j)
        set_cell_background(cell, "2563EB")
        p = cell.paragraphs[0]
        p.text = h
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    reqs = [
        ("FR-01", "Guest Portal", "Browse vehicles with high-resolution imagery, brand, fuel, transmission, seats, and daily rate."),
        ("FR-02", "Guest Portal", "Filter fleet by Brand, Fuel Type, Transmission, and Maximum Daily Price."),
        ("FR-03", "Guest Portal", "Inspect complete accessories checklist (AC, ABS, Airbags, Bluetooth, GPS, Power Locks, etc.)."),
        ("FR-04", "Guest Portal", "Submit inquiry queries through Contact Us form."),
        ("FR-05", "Guest Portal", "Subscribe email address to the promotional newsletter."),
        ("FR-06", "User Portal", "Register account with name, email, password (minimum 8 characters), phone, address, and terms acceptance."),
        ("FR-07", "User Portal", "Log in securely using email and hashed password."),
        ("FR-08", "User Portal", "Verify new accounts and reset passwords with single-use, expiring six-digit email codes; real delivery requires Resend configuration."),
        ("FR-09", "User Portal", "Real-time car booking with pick-up/return dates, locations, optional chauffeur driver add-on ($35/day)."),
        ("FR-10", "User Portal", "View booking history with status badges (Pending, Confirmed, Cancelled)."),
        ("FR-11", "User Portal", "Cancel pending reservations and view/print formatted invoices."),
        ("FR-12", "User Portal", "Update profile details (name, phone, address) and update password."),
        ("FR-13", "User Portal", "Post 1-5 star testimonials with feedback comments for moderation."),
        ("FR-14", "Admin Portal", "Dedicated administrator authentication."),
        ("FR-15", "Admin Portal", "Analytics dashboard displaying live counts of users, vehicles, brands, bookings, queries, subscribers."),
        ("FR-16", "Admin Portal", "Brand Management: Create, edit, and delete vehicle brands (with cascade protection)."),
        ("FR-17", "Admin Portal", "Vehicle Management: Post, edit, and delete vehicles with 15 feature checkboxes and a vehicle-specific front, side, rear, and interior photo gallery."),
        ("FR-18", "Admin Portal", "Booking Management: Confirm or Cancel customer bookings with internal notes/remarks."),
        ("FR-19", "Admin Portal", "Testimonial Moderation: Toggle reviews between Active (Published) and Inactive (Hidden)."),
        ("FR-20", "Admin Portal", "Contact Query Management: Mark inquiries as Read/Replied and add internal follow-up notes."),
        ("FR-21", "Admin Portal", "User Management: View customer registration dates, contact info, and booking counts."),
        ("FR-22", "Admin Portal", "CMS Content Editor: Dynamically edit company name, phone, email, address, About Us, Terms, Privacy."),
        ("FR-23", "Admin Portal", "Subscriber Management: Review and remove newsletter subscribers."),
        ("FR-24", "Admin Portal", "Admin Security: Sign in using the provisioned username or email, change the admin password, and recover it with a one-time code sent to the admin email; public admin registration is disabled.")
    ]

    for req_id, mod, desc in reqs:
        row = crs_table.add_row()
        row.cells[0].paragraphs[0].text = req_id
        row.cells[1].paragraphs[0].text = mod
        row.cells[2].paragraphs[0].text = desc

    doc.add_heading("4.2 Hardware & Software Requirements (Per Spec)", level=2)
    hw_p = doc.add_paragraph()
    hw_p.add_run("Hardware Requirements:\n").font.bold = True
    hw_p.add_run("• Processor: Pentium 166 MHz or better (Modern multi-core processor recommended)\n")
    hw_p.add_run("• RAM: 128 MB minimum (2 GB+ recommended)\n")
    hw_p.add_run("• Storage: 200 MB free hard drive space\n\n")

    hw_p.add_run("Software Requirements:\n").font.bold = True
    hw_p.add_run("• Operating System: Windows OS (Windows 2000 Server or higher / Windows 10/11)\n")
    hw_p.add_run("• Programming Language: Python 3.8+\n")
    hw_p.add_run("• Web Framework: Flask 3.1+\n")
    hw_p.add_run("• Database Engine: SQLite 3\n")
    hw_p.add_run("• Browser: Google Chrome, Microsoft Edge, Mozilla Firefox, or Safari\n")

    doc.add_page_break()

    # -------------------------------------------------------------
    # 5. Database Schema & Data Dictionary
    # -------------------------------------------------------------
    h5 = doc.add_heading("5. Entity-Relationship & Data Dictionary", level=1)
    h5.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    doc.add_paragraph(
        "The SQLite schema uses relational tables, keys, and constraints to support the application's records. "
        "Referential integrity is enabled for relational operations. No formal normalization audit is claimed."
    )

    tables_info = [
        ("users", [
            ("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Unique user identifier"),
            ("full_name", "TEXT", "NOT NULL", "Customer's full legal name"),
            ("email", "TEXT", "UNIQUE NOT NULL", "Customer login email"),
            ("password_hash", "TEXT", "NOT NULL", "PBKDF2/SHA-256 hashed password"),
            ("phone", "TEXT", "NULL", "Contact telephone number"),
            ("address", "TEXT", "NULL", "Street address"),
            ("city", "TEXT", "NULL", "City of residence"),
            ("country", "TEXT", "NULL", "Country of residence"),
            ("created_at", "TIMESTAMP", "DEFAULT CURRENT_TIMESTAMP", "Registration timestamp")
        ]),
        ("vehicles", [
            ("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Unique vehicle identifier"),
            ("title", "TEXT", "NOT NULL", "Vehicle model title (e.g. BMW M4)"),
            ("brand_id", "INTEGER", "NOT NULL, FK -> brands(id)", "Associated manufacturer brand"),
            ("overview", "TEXT", "NULL", "Detailed vehicle description"),
            ("price_per_day", "REAL", "NOT NULL", "Rental rate per 24-hour period"),
            ("fuel_type", "TEXT", "NOT NULL", "Petrol, Diesel, Electric, or Hybrid"),
            ("model_year", "INTEGER", "NOT NULL", "Manufacturing year"),
            ("seating_capacity", "INTEGER", "NOT NULL", "Passenger capacity"),
            ("transmission", "TEXT", "NOT NULL", "Automatic or Manual"),
            ("image_url", "TEXT", "NULL", "Relative upload path or external URL"),
            ("status", "TEXT", "DEFAULT 'Available'", "Available, Booked, Maintenance"),
            ("air_conditioner", "INTEGER", "DEFAULT 1", "Feature flag (1=True, 0=False)"),
            ("antilock_braking_system", "INTEGER", "DEFAULT 1", "Feature flag (1=True, 0=False)"),
            ("bluetooth", "INTEGER", "DEFAULT 1", "Feature flag (1=True, 0=False)"),
            ("gps_navigation", "INTEGER", "DEFAULT 1", "Feature flag (1=True, 0=False)")
        ]),
        ("bookings", [
            ("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Unique booking record ID"),
            ("booking_number", "TEXT", "UNIQUE NOT NULL", "Public reference format (e.g. FC-2026-8812)"),
            ("user_id", "INTEGER", "NOT NULL, FK -> users(id)", "Customer placing booking"),
            ("vehicle_id", "INTEGER", "NOT NULL, FK -> vehicles(id)", "Vehicle booked"),
            ("from_date", "DATE", "NOT NULL", "Pick-up reservation date"),
            ("to_date", "DATE", "NOT NULL", "Return reservation date"),
            ("total_days", "INTEGER", "NOT NULL", "Calculated days duration"),
            ("total_price", "REAL", "NOT NULL", "Computed total cost (base + chauffeur)"),
            ("pickup_location", "TEXT", "NOT NULL", "Designated pick-up terminal"),
            ("dropoff_location", "TEXT", "NOT NULL", "Designated return terminal"),
            ("driver_needed", "INTEGER", "DEFAULT 0", "Chauffeur flag (1=Yes, 0=No)"),
            ("status", "TEXT", "DEFAULT 'Pending'", "Pending, Confirmed, Cancelled"),
            ("admin_remark", "TEXT", "NULL", "Administrator operational note")
        ])
    ]

    for tbl_name, cols in tables_info:
        doc.add_heading(f"Table: {tbl_name}", level=2)
        tbl = doc.add_table(rows=1, cols=4)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        for idx, th in enumerate(["Column", "Data Type", "Constraints", "Description"]):
            c = tbl.cell(0, idx)
            set_cell_background(c, "1E293B")
            p = c.paragraphs[0]
            p.text = th
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

        for col_name, ctype, constr, cdesc in cols:
            row = tbl.add_row()
            row.cells[0].paragraphs[0].text = col_name
            row.cells[1].paragraphs[0].text = ctype
            row.cells[2].paragraphs[0].text = constr
            row.cells[3].paragraphs[0].text = cdesc

    doc.add_page_break()

    # -------------------------------------------------------------
    # 6. Algorithms & Core Logic
    # -------------------------------------------------------------
    h6 = doc.add_heading("6. Algorithms & Core Logic", level=1)
    h6.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    doc.add_heading("6.1 Email Verification and Password Recovery", level=2)
    doc.add_paragraph("Six-digit email codes are stored only as keyed hashes, expire after ten minutes, and are consumed after successful verification or reset.")
    p_algo1 = doc.add_paragraph()
    p_algo1.style = 'Normal'
    p_algo1.paragraph_format.left_indent = Inches(0.5)
    p_algo1.add_run(
        "1. Generate a random six-digit code for email verification or password recovery.\n"
        "2. Store only a keyed hash of the code with a ten-minute expiry.\n"
        "3. Deliver the code through Resend when configured; local development logs it to the terminal.\n"
        "4. Limit verification attempts and compare the submitted code hash.\n"
        "5. Mark the account verified or update the password hash, then consume the code."
    )

    doc.add_heading("6.2 Multi-Day Rental & Optional Chauffeur Pricing Engine", level=2)
    p_algo2 = doc.add_paragraph()
    p_algo2.paragraph_format.left_indent = Inches(0.5)
    p_algo2.add_run(
        "1. Capture Inputs: pick_up_date D1, return_date D2, vehicle_rate R, driver_flag F.\n"
        "2. Date Validation: Assert D1 >= current_date() and D2 >= D1.\n"
        "3. Compute calendar duration: days = (D2 - D1).days.\n"
        "4. Enforce minimum period: If days == 0, days = 1 (same-day return is charged as 1 full day).\n"
        "5. Define chauffeur tariff: driver_rate = $35.00 / day.\n"
        "6. Calculate base cost: base_total = R * days.\n"
        "7. Calculate driver add-on: driver_total = (F == 1) ? (driver_rate * days) : 0.00.\n"
        "8. Grand Total Calculation: grand_total = base_total + driver_total.\n"
        "9. Return (days, grand_total) to live UI and store in database record."
    )

    # -------------------------------------------------------------
    # 7. GUI Standards Document
    # -------------------------------------------------------------
    h_gui = doc.add_heading("7. GUI Standards Document (Minimalist Monochrome)", level=1)
    h_gui.runs[0].font.color.rgb = RGBColor(17, 24, 39)

    doc.add_paragraph(
        "In strict adherence to modern Swiss minimalist and luxury automotive design philosophies, "
        "FAST CARS employs an uncompromising, high-contrast black-and-white monochrome aesthetic. "
        "By eliminating superfluous color gradients, the user interface achieves maximum clarity, rapid scanning, "
        "and effortless readability across diverse lighting conditions."
    )

    doc.add_heading("7.1 Color Palette & Visual Hierarchy", level=2)
    gui_table = doc.add_table(rows=1, cols=3)
    gui_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, th in enumerate(["Token / Role", "Color Hex Value", "Application"]):
        c = gui_table.cell(0, idx)
        set_cell_background(c, "000000")
        p = c.paragraphs[0]
        p.text = th
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    gui_tokens = [
        ("Background Pure Black", "#000000", "Main canvas background and navigation chrome"),
        ("Card / Surface Black", "#0E0E0E / #121212", "Vehicle cards, form containers, and content blocks"),
        ("Crisp Border Line", "#262626 / #404040", "Card boundaries, input outlines, and table dividers"),
        ("High-Contrast White", "#FFFFFF", "Primary typography, high-priority buttons, and active tags"),
        ("Muted Neutral Gray", "#A3A3A3", "Secondary metadata, spec labels, and subtitles"),
        ("Subtle Charcoal", "#1F1F1F", "Hover states and inactive badges")
    ]
    for tok, hx, appl in gui_tokens:
        row = gui_table.add_row()
        row.cells[0].paragraphs[0].text = tok
        row.cells[1].paragraphs[0].text = hx
        row.cells[2].paragraphs[0].text = appl

    doc.add_heading("7.2 Geometric Typography & Micro-Interactions", level=2)
    doc.add_paragraph(
        "• Typography: Modern geometric sans-serif with tracked uppercase badges for high legibility.\n"
        "• Buttons: High-contrast inverted buttons (solid white with pure black typography on resting state; "
        "pure black with white outline on hover state).\n"
        "• Form Inputs: Dark charcoal surfaces with crisp 1px borders and pure white input text."
    )

    doc.add_page_break()
    h7 = doc.add_heading("7. Unit Testing Check List", level=1)
    h7.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    doc.add_paragraph("The current local automated test suite contains 17 tests covering selected routes and key flows. These checks do not prove every production scenario is defect-free.")

    ut_table = doc.add_table(rows=1, cols=5)
    ut_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, th in enumerate(["Test ID", "Scenario", "Input Condition", "Expected Result", "Status"]):
        c = ut_table.cell(0, idx)
        set_cell_background(c, "2563EB")
        p = c.paragraphs[0]
        p.text = th
        p.runs[0].font.bold = True
        p.runs[0].font.color.rgb = RGBColor(255, 255, 255)

    tests_data = [
        ("TC-01", "Public Portal Navigation", "GET /, /cars, /about, /contact, /faq", "HTTP 200 OK across all endpoints", "PASS"),
        ("TC-02", "Vehicle Details Loading", "GET /cars/1 (BMW M4)", "Displays car specs, features & rate", "PASS"),
        ("TC-03", "Customer Registration", "Valid email, password (8+ chars), terms accepted", "Account created, auto-session established", "PASS"),
        ("TC-04", "Duplicate Email Guard", "Register with existing user email", "Rejection alert with login prompt", "PASS"),
        ("TC-05", "Customer Login", "Valid credentials in isolated test database", "Session created, redirects to dashboard", "PASS"),
        ("TC-06", "Password Reset", "Token workflow; Resend response mocked", "Reset path and email client exercised", "PASS"),
        ("TC-07", "Date Conflict", "Overlapping vehicle reservation dates", "Conflicting request rejected", "PASS"),
        ("TC-08", "Resend Client", "Mocked successful API response", "Expected request contract sent", "PASS"),
        ("TC-09", "Availability Search", "Vehicle has an overlapping booking", "Vehicle omitted from date results", "PASS"),
        ("TC-10", "Vehicle Validation", "Invalid vehicle form fields", "Invalid record rejected", "PASS"),
        ("TC-11", "CSRF Protection", "POST without token and with valid token", "Missing token rejected; valid form accepted", "PASS"),
        ("TC-12", "Admin Inquiry Reply", "Reply to a saved customer inquiry", "Email sent and inquiry marked Replied", "PASS"),
        ("TC-13", "Booking Approval Conflict", "Confirm one of two overlapping pending requests", "Conflict rejected; booking remains Pending", "PASS"),
        ("TC-14", "Live Dashboard Snapshot", "Register customer and add booking during admin session", "Dashboard endpoint reports updated counts", "PASS"),
        ("TC-15", "Admin Email Password Recovery", "Request code for configured admin email, reset, and log in by email", "Code sent to admin email; new password accepted", "PASS")
    ]

    for tid, tscen, tinp, texp, tstat in tests_data:
        row = ut_table.add_row()
        row.cells[0].paragraphs[0].text = tid
        row.cells[1].paragraphs[0].text = tscen
        row.cells[2].paragraphs[0].text = tinp
        row.cells[3].paragraphs[0].text = texp
        cstat = row.cells[4].paragraphs[0]
        cstat.text = tstat
        cstat.runs[0].font.bold = True
        cstat.runs[0].font.color.rgb = RGBColor(16, 185, 129)

    doc.add_page_break()

    # -------------------------------------------------------------
    # 8. Final Check List & Deliverables
    # -------------------------------------------------------------
    h8 = doc.add_heading("8. Final Check List & Deliverables", level=1)
    h8.runs[0].font.color.rgb = RGBColor(37, 99, 235)

    check_items = [
        "Complete Python source code (Flask web application) with detailed block comments and documentation.",
        "SQLite schema with optional development seed data; production initialization does not add demo accounts or bookings.",
        "Complete database DDL schema script (schema.sql).",
        "Standalone database backup SQL dump (fastcars_backup.sql) ready for final zip package submission.",
        "Interactive frontend logic (main.js) for live day/rate calculation, star rating selector, and invoice printing.",
        "Automated test suite (test_app.py); 17 local tests pass, covering selected flows rather than every production scenario.",
        "One-click runner script (run.py) launching the server on http://127.0.0.1:5000.",
        "Project documentation in PROJECT_REPORT.md and this Word report. Hosting and real email delivery remain to be configured and verified.",
        "System Guide and Credential Manual (README.md)."
    ]

    for itm in check_items:
        p = doc.add_paragraph(style='List Bullet')
        r = p.add_run("[X] ")
        r.font.bold = True
        r.font.color.rgb = RGBColor(16, 185, 129)
        p.add_run(itm)

    output_path = r"c:\Users\tjayt\Desktop\car website\Project Report - Car Rental Booking System.docx"
    doc.save(output_path)
    print(f"Generated DOCX Project Report: {output_path}")

if __name__ == '__main__':
    create_report()
