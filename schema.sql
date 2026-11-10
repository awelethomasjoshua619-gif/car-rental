-- FAST CARS - Car Rental Booking System Database Schema
-- Compatible with SQLite3

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 1,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    security_question TEXT NOT NULL DEFAULT '',
    security_answer TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    brand_id INTEGER NOT NULL,
    overview TEXT,
    price_per_day REAL NOT NULL,
    fuel_type TEXT NOT NULL,
    model_year INTEGER NOT NULL,
    seating_capacity INTEGER NOT NULL,
    transmission TEXT NOT NULL,
    category TEXT DEFAULT 'Premium',
    image_url TEXT,
    image_side TEXT,
    image_rear TEXT,
    image_interior TEXT,
    air_conditioner INTEGER DEFAULT 1,
    power_door_locks INTEGER DEFAULT 1,
    antilock_braking_system INTEGER DEFAULT 1,
    brake_assist INTEGER DEFAULT 1,
    power_steering INTEGER DEFAULT 1,
    driver_airbag INTEGER DEFAULT 1,
    passenger_airbag INTEGER DEFAULT 1,
    power_windows INTEGER DEFAULT 1,
    cd_player INTEGER DEFAULT 0,
    central_locking INTEGER DEFAULT 1,
    crash_sensor INTEGER DEFAULT 1,
    leather_seats INTEGER DEFAULT 0,
    bluetooth INTEGER DEFAULT 1,
    child_seat INTEGER DEFAULT 0,
    gps_navigation INTEGER DEFAULT 1,
    status TEXT DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_number TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    total_days INTEGER NOT NULL,
    total_price REAL NOT NULL,
    pickup_location TEXT NOT NULL,
    dropoff_location TEXT NOT NULL,
    driver_needed INTEGER DEFAULT 0,
    message TEXT,
    status TEXT DEFAULT 'Pending',
    admin_remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS testimonials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rating INTEGER DEFAULT 5,
    title TEXT,
    content TEXT NOT NULL,
    status INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contact_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    subject TEXT,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'New',
    admin_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_verification_codes_user_id
    ON email_verification_codes (user_id);

CREATE TABLE IF NOT EXISTS admin_password_reset_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    code_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_admin_password_reset_codes_admin_id
    ON admin_password_reset_codes (admin_id);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id
    ON password_reset_tokens (user_id);

CREATE TABLE IF NOT EXISTS auth_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    identity_hash TEXT NOT NULL,
    attempted_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_attempts_scope_identity_time
    ON auth_attempts (scope, identity_hash, attempted_at);
