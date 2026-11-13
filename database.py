import os
import sqlite3
from datetime import datetime, date, timedelta
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(__file__), 'fastcars.db')
)
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db():
    """Returns a database connection with dictionary-like row access."""
    try:
        from flask import has_app_context, g
        if has_app_context():
            if 'db' not in g:
                os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
                conn = sqlite3.connect(DB_PATH, timeout=30)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA busy_timeout = 30000")
                g.db = conn
            return g.db
    except ImportError:
        pass

    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def init_db():
    """Initializes the database using schema.sql and populates initial seed data."""
    conn = get_db()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    user_columns = {col[1] for col in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'email_verified' not in user_columns:
        conn.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1')
        conn.commit()
    # Ensure any new columns exist in vehicles table
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(vehicles)")
    columns = [col[1] for col in cur.fetchall()]
    for col_name in ['category', 'image_side', 'image_rear', 'image_interior']:
        if col_name not in columns:
            cur.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} TEXT")
    # Recovery now uses short-lived email links, so legacy security answers are obsolete.
    conn.execute("UPDATE users SET security_question = '', security_answer = ''")
    # Customer feedback is published on submission and cannot be hidden by admin moderation.
    conn.execute("UPDATE testimonials SET status = 1 WHERE status != 1")
    # These seed files are exterior shots, not interiors. Do not present them as
    # cabin photos; the vehicle page will say when a verified interior is unavailable.
    for vehicle_id in (2, 5, 8):
        conn.execute(
            "UPDATE vehicles SET image_interior = NULL "
            "WHERE id = ? AND image_interior = ?",
            (vehicle_id, f'/static/images/cars/car_{vehicle_id}_interior.jpg'),
        )
    # The current front/side/rear source set is catalogued as a 992 Carrera S,
    # photographed in 2021, rather than the seeded 2024 Carrera GTS.
    conn.execute(
        "UPDATE vehicles SET title = 'Porsche 911 Carrera S (992)', model_year = 2021 "
        "WHERE id = 5 AND title = 'Porsche 911 Carrera GTS' "
        "AND image_url = '/static/images/cars/car_5_front.jpg'"
    )
    # Remove fictional business contact details and sample reviews from the
    # public site on existing development databases as well as fresh installs.
    conn.execute("UPDATE site_settings SET value = '' WHERE key = 'company_phone' AND value LIKE '%555-FAST%'")
    conn.execute("UPDATE site_settings SET value = '' WHERE key = 'company_phone' AND value = '+1 (800) 555-3278'")
    conn.execute("UPDATE site_settings SET value = '' WHERE key = 'company_email' AND value = 'support@fastcars.com'")
    conn.execute("UPDATE site_settings SET value = '' WHERE key = 'company_address' AND value LIKE '%Evergreen Terrace%'")
    conn.execute("UPDATE site_settings SET value = '' WHERE key = 'working_hours' AND value LIKE '%8:00 AM - 8:00 PM%'")
    conn.execute("UPDATE site_settings SET value = ? WHERE key = 'about_us' AND value LIKE '%premier car rental partner%'",
                 ('Browse the available vehicles and send a reservation request for staff review.',))
    conn.execute("UPDATE site_settings SET value = ? WHERE key = 'terms_conditions' AND value LIKE '%200 miles/day%'",
                 ('A reservation is a request and is not confirmed until FAST CARS staff approve it. Before pickup, confirm the rental price, driver requirements, deposit, cancellation terms, fuel, mileage, and insurance directly with staff.',))
    conn.execute("UPDATE site_settings SET value = ? WHERE key = 'privacy_policy' AND value LIKE '%cryptographically secured%'",
                 ('Privacy policy is being prepared. Review and publish it before collecting customer information.',))
    conn.execute("UPDATE testimonials SET status = 0 WHERE content IN (?, ?, ?)", (
        'Rented the BMW M4 for a weekend trip to Napa Valley. The car was spotless, pick-up took less than 3 minutes, and customer support was exceptional. Highly recommended!',
        'FAST CARS lived up to its name. The Mercedes S-Class was like gliding on a cloud. Outstanding service from start to finish.',
        'Booked the Tesla Model S Plaid for a business convention. Supercharging network was easy and the car performance was out of this world.',
    ))
    demo_admin_email = os.environ.get('DEMO_ADMIN_EMAIL', '').strip().lower()
    if '@' in demo_admin_email and '.' in demo_admin_email.rsplit('@', 1)[-1]:
        conn.execute(
            "UPDATE admins SET email = ? WHERE username = 'admin' AND email = 'awelethomasjoshua619@gmail.com'",
            (demo_admin_email,),
        )
    conn.commit()
    if os.environ.get('APP_ENV', 'development').lower() != 'production':
        seed_data(conn)
    else:
        default_admin = conn.execute(
            "SELECT password_hash FROM admins WHERE username = 'admin' OR email = 'awelethomasjoshua619@gmail.com' LIMIT 1"
        ).fetchone()
        default_user = conn.execute(
            "SELECT password_hash FROM users WHERE email = 'john@example.com' LIMIT 1"
        ).fetchone()
        has_demo_password = (
            (default_admin and check_password_hash(default_admin['password_hash'], 'admin123'))
            or (default_user and check_password_hash(default_user['password_hash'], 'user123'))
        )
        if has_demo_password:
            conn.close()
            raise RuntimeError(
                'Production database contains a demo password. Use a fresh database and create a production admin.'
            )
    office_defaults = {
        'company_address': 'mush surulere 666',
        'company_phone': '08134018568',
        'company_email': 'awelethomasjoshua619@gmail.com',
    }
    for key, value in office_defaults.items():
        conn.execute(
            """INSERT INTO site_settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value
               WHERE TRIM(site_settings.value) = ''""",
            (key, value),
        )
    conn.commit()
    conn.close()

def seed_data(conn):
    """Inserts initial demo data if tables are empty."""
    cursor = conn.cursor()

    # 1. Admin Seed
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        configured_admin_email = os.environ.get('DEMO_ADMIN_EMAIL', '').strip().lower()
        if '@' not in configured_admin_email or '.' not in configured_admin_email.rsplit('@', 1)[-1]:
            configured_admin_email = 'awelethomasjoshua619@gmail.com'
        cursor.execute(
            """INSERT INTO admins (username, email, password_hash, full_name)
               VALUES (?, ?, ?, ?)""",
            ('admin', configured_admin_email, generate_password_hash('admin123'), 'FAST CARS Administrator')
        )

    # 2. Site Settings Seed
    cursor.execute("SELECT COUNT(*) FROM site_settings")
    if cursor.fetchone()[0] == 0:
        default_settings = {
            'company_name': 'FAST CARS Rental & Luxury Fleet',
            'company_phone': '08134018568',
            'company_email': 'awelethomasjoshua619@gmail.com',
            'company_address': 'mush surulere 666',
            'working_hours': '',
            'currency_code': '',
            'chauffeur_fee_per_day': '',
            'about_us': 'Browse the available vehicles and send a reservation request for staff review.',
            'terms_conditions': 'A reservation is a request and is not confirmed until FAST CARS staff approve it. Before pickup, confirm the rental price, driver requirements, deposit, cancellation terms, fuel, mileage, and insurance directly with staff.',
            'privacy_policy': 'Privacy policy is being prepared. Review and publish it before collecting customer information.',
        }
        for k, v in default_settings.items():
            cursor.execute("INSERT OR REPLACE INTO site_settings (key, value) VALUES (?, ?)", (k, v))

    # 3. Brands Seed
    cursor.execute("SELECT COUNT(*) FROM brands")
    if cursor.fetchone()[0] == 0:
        brands = [
            'BMW',
            'Mercedes-Benz',
            'Audi',
            'Tesla',
            'Porsche',
            'Toyota',
            'Ford',
            'Hyundai'
        ]
        for b in brands:
            cursor.execute("INSERT INTO brands (name) VALUES (?)", (b,))

    # 4. Vehicles Seed
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    if cursor.fetchone()[0] == 0:
        # Fetch brand IDs
        brand_map = {}
        for row in cursor.execute("SELECT id, name FROM brands").fetchall():
            brand_map[row['name']] = row['id']

        vehicles = [
            {
                'title': 'BMW M4 Competition Coupe',
                'brand_id': brand_map.get('BMW', 1),
                'overview': 'The BMW M4 Competition Coupe delivers exhilarating performance with a 503-hp twin-turbo inline-six, race-inspired bucket seats, and aggressive aerodynamic styling.',
                'price_per_day': 185.00,
                'fuel_type': 'Petrol',
                'model_year': 2024,
                'seating_capacity': 4,
                'transmission': 'Automatic',
                'category': 'Small',
                'image_url': '/static/images/cars/car_1_front.jpg',
                'image_side': '/static/images/cars/car_1_side.jpg',
                'image_rear': '/static/images/cars/car_1_rear.jpg',
                'image_interior': '/static/images/cars/car_1_interior.jpg',
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Mercedes-Benz S-Class AMG Line',
                'brand_id': brand_map.get('Mercedes-Benz', 2),
                'overview': 'The pinnacle of automotive luxury. Whisper-quiet cabin, massaging executive leather seats, high-end Burmester audio, and effortless twin-turbo V8 propulsion.',
                'price_per_day': 220.00,
                'fuel_type': 'Hybrid',
                'model_year': 2024,
                'seating_capacity': 5,
                'transmission': 'Automatic',
                'category': 'Premium',
                'image_url': '/static/images/cars/car_2_front.jpg',
                'image_side': '/static/images/cars/car_2_side.jpg',
                'image_rear': '/static/images/cars/car_2_rear.jpg',
                'image_interior': None,
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Tesla Model 3 Performance',
                'brand_id': brand_map.get('Tesla', 4),
                'overview': 'Mind-bending 0-60 in 3.1s dual-motor electric performance. Featuring full glass panoramic roof, minimalist touchscreen cockpit, autopilot assistance, and over 315 miles range.',
                'price_per_day': 170.00,
                'fuel_type': 'Electric',
                'model_year': 2024,
                'seating_capacity': 5,
                'transmission': 'Automatic',
                'category': 'Small',
                'image_url': '/static/images/cars/car_3_front.jpg',
                'image_side': '/static/images/cars/car_3_side.jpg',
                'image_rear': '/static/images/cars/car_3_rear.jpg',
                'image_interior': '/static/images/cars/car_3_interior.jpg',
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Audi RS6 Avant Quattro',
                'brand_id': brand_map.get('Audi', 3),
                'overview': 'Supercar speed packed into the world’s most versatile luxury wagon. Twin-turbo V8, quattro all-wheel drive, and cavernous trunk space for travel gear.',
                'price_per_day': 195.00,
                'fuel_type': 'Petrol',
                'model_year': 2023,
                'seating_capacity': 5,
                'transmission': 'Automatic',
                'category': 'Large',
                'image_url': '/static/images/cars/car_4_front.jpg',
                'image_side': '/static/images/cars/car_4_side.jpg',
                'image_rear': '/static/images/cars/car_4_rear.jpg',
                'image_interior': '/static/images/cars/car_4_interior.jpg',
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Porsche 911 Carrera S (992)',
                'brand_id': brand_map.get('Porsche', 5),
                'overview': 'Timeless silhouette and precision German engineering. Twin-turbo flat-six, sports exhaust, responsive paddle shifters, and unforgettable handling on winding roads.',
                'price_per_day': 260.00,
                'fuel_type': 'Petrol',
                'model_year': 2021,
                'seating_capacity': 4,
                'transmission': 'Automatic',
                'category': 'Premium',
                'image_url': '/static/images/cars/car_5_front.jpg',
                'image_side': '/static/images/cars/car_5_side.jpg',
                'image_rear': '/static/images/cars/car_5_rear.jpg',
                'image_interior': None,
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Toyota RAV4 Hybrid Limited',
                'brand_id': brand_map.get('Toyota', 6),
                'overview': 'Reliable, fuel-efficient SUV loaded with smart tech, spacious seating, all-wheel drive, and generous cargo capacity for family trips.',
                'price_per_day': 75.00,
                'fuel_type': 'Hybrid',
                'model_year': 2023,
                'seating_capacity': 5,
                'transmission': 'Automatic',
                'category': 'Large',
                'image_url': '/static/images/cars/car_6_front.jpg',
                'image_side': '/static/images/cars/car_6_side.jpg',
                'image_rear': '/static/images/cars/car_6_rear.jpg',
                'image_interior': '/static/images/cars/car_6_interior.jpg',
                'leather_seats': 0, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Ford Mustang GT 5.0 V8',
                'brand_id': brand_map.get('Ford', 7),
                'overview': 'American muscle at its finest. Roaring 5.0L Coyote V8 engine producing 480 horsepower, Brembo brakes, and iconic road presence.',
                'price_per_day': 110.00,
                'fuel_type': 'Petrol',
                'model_year': 2023,
                'seating_capacity': 4,
                'transmission': 'Automatic',
                'category': 'Premium',
                'image_url': '/static/images/cars/car_7_front.jpg',
                'image_side': '/static/images/cars/car_7_side.jpg',
                'image_rear': '/static/images/cars/car_7_rear.jpg',
                'image_interior': '/static/images/cars/car_7_interior.jpg',
                'leather_seats': 1, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            },
            {
                'title': 'Hyundai Ioniq 5 Electric Crossover',
                'brand_id': brand_map.get('Hyundai', 8),
                'overview': 'Futuristic styling, ultra-fast 800V charging, lounge-style relaxing cabin, and ultra-smooth silent electric drive.',
                'price_per_day': 85.00,
                'fuel_type': 'Electric',
                'model_year': 2024,
                'seating_capacity': 5,
                'transmission': 'Automatic',
                'category': 'Small',
                'image_url': '/static/images/cars/car_8_front.jpg',
                'image_side': '/static/images/cars/car_8_side.jpg',
                'image_rear': '/static/images/cars/car_8_rear.jpg',
                'image_interior': None,
                'leather_seats': 0, 'gps_navigation': 1, 'bluetooth': 1, 'air_conditioner': 1, 'driver_airbag': 1, 'passenger_airbag': 1, 'antilock_braking_system': 1
            }
        ]

        for v in vehicles:
            cursor.execute("""
                INSERT INTO vehicles (
                    title, brand_id, overview, price_per_day, fuel_type, model_year,
                    seating_capacity, transmission, category, image_url, image_side,
                    image_rear, image_interior, leather_seats, gps_navigation,
                    bluetooth, air_conditioner, driver_airbag, passenger_airbag, antilock_braking_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                v['title'], v['brand_id'], v['overview'], v['price_per_day'], v['fuel_type'],
                v['model_year'], v['seating_capacity'], v['transmission'], v.get('category', 'Premium'),
                v['image_url'], v.get('image_side'), v.get('image_rear'), v.get('image_interior'),
                v.get('leather_seats', 1), v.get('gps_navigation', 1), v.get('bluetooth', 1),
                v.get('air_conditioner', 1), v.get('driver_airbag', 1), v.get('passenger_airbag', 1),
                v.get('antilock_braking_system', 1)
            ))

    # 5. Sample Contact Query Seed
    cursor.execute("SELECT COUNT(*) FROM contact_queries")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO contact_queries (name, email, phone, subject, message, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            'Sarah Jenkins',
            'sarah.j@example.com',
            '+1 (555) 987-6543',
            'Corporate Fleet Rental Inquiry',
            'Hello FAST CARS team, we are planning a 3-day executive conference next month and need 4 executive sedans with dedicated drivers. Could you provide a customized corporate package quotation?',
            'New'
        ))

    # 6. Sample Newsletter Subscriber Seed
    cursor.execute("SELECT COUNT(*) FROM subscribers")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO subscribers (email) VALUES (?)", ('vip.driver@example.com',))

    conn.commit()

if __name__ == '__main__':
    print("Initializing FAST CARS database...")
    init_db()
    print("Database fastcars.db initialized and seeded successfully.")
