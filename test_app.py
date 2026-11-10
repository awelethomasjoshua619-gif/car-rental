"""
Automated Comprehensive Test Suite for FAST CARS Car Rental Booking System
Validates every endpoint, authentication, booking logic, admin operations, and database integrity.
"""

import unittest
import atexit
import json
import os
import tempfile
import uuid
from datetime import date, timedelta
from urllib.parse import urlsplit
from unittest.mock import MagicMock, patch
import database

_test_db_handle, _test_db_path = tempfile.mkstemp(prefix='fastcars-tests-', suffix='.db')
os.close(_test_db_handle)
database.DB_PATH = _test_db_path
atexit.register(lambda: os.path.exists(_test_db_path) and os.unlink(_test_db_path))

from app import app
from database import init_db, get_db

class FastCarsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM users WHERE email = 'testuser@example.com'")
            db.commit()

    def test_01_public_pages(self):
        """Test all public guest endpoints return 200 OK."""
        endpoints = ['/', '/cars', '/about', '/contact', '/faq', '/terms', '/privacy', '/testimonials', '/login', '/register', '/forgot-password']
        for ep in endpoints:
            response = self.client.get(ep)
            self.assertEqual(response.status_code, 200, f"Failed on endpoint {ep}")

    def test_02_car_details_page(self):
        """Test car details endpoint for car ID 1."""
        response = self.client.get('/cars/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'BMW M4', response.data)

    def test_03_user_registration_and_login(self):
        """New accounts must verify the emailed code before sign-in."""
        # 1. Register new user
        reg_data = {
            'full_name': 'Test User',
            'email': 'testuser@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'phone': '+1 555-0199',
            'address': '456 Test Way',
            'city': 'San Francisco',
            'country': 'USA',
            'terms_accepted': 'yes'
        }
        with patch('app.send_templated_email') as send_email:
            res = self.client.post('/register', data=reg_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Verify your email', res.data)
        import re
        code_match = re.search(r'verification code is (\d{6})', send_email.call_args.args[3])
        self.assertIsNotNone(code_match)
        code = code_match.group(1)

        # An unverified account is not allowed to sign in.
        res = self.client.post('/login', data={'email': reg_data['email'], 'password': reg_data['password']}, follow_redirects=True)
        self.assertIn(b'Verify your email', res.data)
        with patch('app.send_templated_email'):
            res = self.client.post('/verify-email', data={'email': reg_data['email'], 'code': code, 'action': 'verify'}, follow_redirects=True)
        self.assertIn(b'Email verified', res.data)
        self.client.post('/logout', follow_redirects=True)

        # 3. Login with registered user
        login_data = {
            'email': 'testuser@example.com',
            'password': 'password123'
        }
        res = self.client.post('/login', data=login_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Test User', res.data)

    def test_04_forgot_password_recovery(self):
        """Test one-time emailed password reset codes."""
        with patch('app.send_templated_email') as send_email:
            res = self.client.post('/forgot-password', data={'email': 'john@example.com'})
        self.assertEqual(res.status_code, 302)
        self.assertTrue(send_email.called)
        import re
        code_match = re.search(r'reset code is (\d{6})', send_email.call_args.args[3])
        self.assertIsNotNone(code_match)
        res = self.client.post('/reset-password', data={
            'email': 'john@example.com',
            'code': code_match.group(1),
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'successfully reset', res.data)

        # Verify login with new password works
        res = self.client.post('/login', data={'email': 'john@example.com', 'password': 'newpassword123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'John Doe', res.data)

    def test_05_car_booking_flow(self):
        """Test logged-in user can book a car and view booking history."""
        # Login as demo user
        with self.client:
            self.client.post('/login', data={'email': 'john@example.com', 'password': 'newpassword123'})
            
            # Book car ID 1
            from_date = date.today() + timedelta(days=30)
            to_date = from_date + timedelta(days=3)
            booking_data = {
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'pickup_location': 'FAST CARS Downtown Headquarters',
                'dropoff_location': 'Los Angeles International Airport (LAX)',
                'driver_needed': '1',
                'message': 'Please have water bottles ready.'
            }
            res = self.client.post('/cars/1/book', data=booking_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Booking submitted successfully', res.data)

            # View booking history
            res = self.client.get('/my-bookings')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'BMW M4', res.data)

    def test_06_admin_portal_flow(self):
        """Test admin login, dashboard metrics, brand CRUD, and vehicle management."""
        with self.client:
            # 1. Admin Login
            res = self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'FAST CARS Admin Portal', res.data)

            # 2. View Dashboard
            res = self.client.get('/admin/dashboard')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Operational Overview', res.data)

            # 3. Add Brand
            res = self.client.post('/admin/brands', data={'name': 'Lamborghini'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Lamborghini', res.data)

            # 4. View Vehicles
            res = self.client.get('/admin/vehicles')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Fleet Catalog', res.data)

            # 5. View Bookings & confirm booking
            res = self.client.get('/admin/bookings')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Manage Customer Bookings', res.data)

            res = self.client.post('/admin/bookings/1/status', data={'status': 'Confirmed', 'admin_remark': 'Key ready at desk'}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Confirmed', res.data)

            # 6. View Testimonials
            res = self.client.get('/admin/testimonials')
            self.assertEqual(res.status_code, 200)

            # 7. View Registered Users
            res = self.client.get('/admin/users')
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Registered Customer Accounts', res.data)

            # 8. View Contacts
            res = self.client.get('/admin/contacts')
            self.assertEqual(res.status_code, 200)

            # 9. View Subscribers
            res = self.client.get('/admin/subscribers')
            self.assertEqual(res.status_code, 200)

            # 10. Update CMS page settings
            res = self.client.post('/admin/pages', data={
                'company_name': 'FAST CARS Rentals Worldwide',
                'company_phone': '+1 (800) 555-3278',
                'company_email': 'support@fastcars.com',
                'company_address': '742 Evergreen Terrace, LA',
                'working_hours': '24/7 Service',
                'about_us': 'Updated about us text test.',
                'terms_conditions': 'Updated terms.',
                'privacy_policy': 'Updated privacy policy.'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'updated successfully', res.data)

    def test_07_csrf_rejects_cross_site_posts(self):
        """Every state-changing form must require its session CSRF token."""
        app.config['WTF_CSRF_ENABLED'] = True
        client = app.test_client()
        try:
            response = client.post('/contact', data={
                'name': 'Test', 'email': 'test@example.com', 'message': 'Missing token'
            })
            self.assertEqual(response.status_code, 400)
            page = client.get('/contact')
            import re
            match = re.search(rb'name=\"csrf_token\" value=\"([^\"]+)\"', page.data)
            self.assertIsNotNone(match)
            with patch('app.send_templated_email'):
                response = client.post('/contact', data={
                    'csrf_token': match.group(1).decode(),
                    'name': 'Test', 'email': 'test@example.com', 'message': 'Valid token'
                })
            self.assertEqual(response.status_code, 302)
        finally:
            app.config['WTF_CSRF_ENABLED'] = False

    def test_08_conflicting_dates_are_rejected(self):
        """A second active reservation cannot take dates already held by another booking."""
        with app.app_context():
            db = get_db()
            booking = db.execute("""
                SELECT vehicle_id, from_date, to_date FROM bookings
                WHERE status IN ('Pending', 'Confirmed') ORDER BY id LIMIT 1
            """).fetchone()
            if not booking:
                self.skipTest('No seeded active booking is available for the collision check.')
        register_data = {
            'full_name': 'Collision Test',
            'email': 'collision-test@example.com',
            'password': 'samplepassword123',
            'confirm_password': 'samplepassword123',
            'terms_accepted': 'yes',
        }
        with patch('app.send_templated_email') as send_email:
            self.client.post('/register', data=register_data)
        import re
        verification_code = re.search(r'verification code is (\d{6})', send_email.call_args.args[3]).group(1)
        self.client.post('/verify-email', data={
            'email': register_data['email'], 'code': verification_code, 'action': 'verify'
        })
        with app.app_context():
            before = get_db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
        response = self.client.post(f"/cars/{booking['vehicle_id']}/book", data={
            'from_date': booking['from_date'],
            'to_date': booking['to_date'],
            'pickup_location': 'Test location',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already reserved', response.data)
        with app.app_context():
            after = get_db().execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
        self.assertEqual(before, after)

    def test_09_resend_email_request(self):
        """Transactional email uses the Resend endpoint and bearer authorization."""
        from email_service import send_email
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{\"id\":\"email-test\"}'
        with patch.dict(os.environ, {
            'MAIL_PROVIDER': 'resend',
            'RESEND_API_KEY': 're_test_key',
            'MAIL_FROM': 'FAST CARS <mail@example.test>',
        }), patch('email_service.urlopen', return_value=response) as urlopen:
            result = send_email('customer@example.test', 'Test subject', '<p>hello</p>', 'hello')
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(result['id'], 'email-test')
        self.assertEqual(request.full_url, 'https://api.resend.com/emails')
        self.assertEqual(request.get_header('Authorization'), 'Bearer re_test_key')
        self.assertIn('FAST-CARS', request.get_header('User-agent'))
        self.assertEqual(payload['to'], ['customer@example.test'])

    def test_10_gmail_smtp_is_limited_to_authentication_mail(self):
        """Gmail SMTP sends auth codes only and uses authenticated TLS."""
        from email_service import send_email
        smtp_context = MagicMock()
        smtp = smtp_context.__enter__.return_value
        with patch.dict(os.environ, {
            'MAIL_PROVIDER': 'gmail',
            'SMTP_USERNAME': 'admin@gmail.com',
            'SMTP_PASSWORD': 'abcd efgh ijkl mnop',
            'MAIL_FROM': 'FAST CARS <admin@gmail.com>',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'APP_ENV': 'development',
        }), patch('email_service.smtplib.SMTP', return_value=smtp_context) as smtp_factory:
            result = send_email('customer@example.test', 'Verification code', '<p>123456</p>', '123456', auth_only=True)
            ordinary = send_email('customer@example.test', 'Booking update', '<p>booking</p>', 'booking')
        smtp_factory.assert_called_once_with('smtp.gmail.com', 587, timeout=20)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with('admin@gmail.com', 'abcdefghijklmnop')
        smtp.send_message.assert_called_once()
        self.assertTrue(result['accepted'])
        self.assertIsNone(ordinary)

    def test_11_fleet_date_search_hides_unavailable_vehicles(self):
        """The landing-page date search filters cars with active overlapping bookings."""
        with app.app_context():
            db = get_db()
            booking = db.execute("""
                SELECT b.vehicle_id, b.from_date, b.to_date, v.title
                FROM bookings b JOIN vehicles v ON v.id = b.vehicle_id
                WHERE b.status IN ('Pending', 'Confirmed') ORDER BY b.id LIMIT 1
            """).fetchone()
            if not booking:
                self.skipTest('No active booking is available for the date search check.')
            title = booking['title'].encode()
            dates = {'from_date': booking['from_date'], 'to_date': booking['to_date']}
        response = self.client.get('/cars', query_string=dates)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(title, response.data)

    def test_12_admin_vehicle_creation_and_validation(self):
        """The admin can create a valid vehicle and invalid prices are rejected."""
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        vehicle_data = {
            'title': 'Validation Test Vehicle',
            'brand_id': '1',
            'price_per_day': '125',
            'fuel_type': 'Petrol',
            'model_year': '2025',
            'seating_capacity': '5',
            'transmission': 'Automatic',
            'category': 'Premium',
            'status': 'Available',
            'image_url': 'https://example.test/validation-front.jpg',
            'image_side': 'https://example.test/validation-side.jpg',
            'image_rear': 'https://example.test/validation-rear.jpg',
            'image_interior': 'https://example.test/validation-interior.jpg',
        }
        response = self.client.post('/admin/vehicles/add', data=vehicle_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            db = get_db()
            vehicle = db.execute(
                "SELECT image_url, image_side, image_rear, image_interior FROM vehicles WHERE title = 'Validation Test Vehicle'"
            ).fetchone()
        self.assertIsNotNone(vehicle)
        self.assertEqual(vehicle['image_url'], 'https://example.test/validation-front.jpg')
        self.assertEqual(vehicle['image_side'], 'https://example.test/validation-side.jpg')
        self.assertEqual(vehicle['image_rear'], 'https://example.test/validation-rear.jpg')
        self.assertEqual(vehicle['image_interior'], 'https://example.test/validation-interior.jpg')

        vehicle_data.update(title='Invalid Price Vehicle', price_per_day='-5')
        response = self.client.post('/admin/vehicles/add', data=vehicle_data)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            count = get_db().execute(
                "SELECT COUNT(*) FROM vehicles WHERE title = 'Invalid Price Vehicle'"
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_13_admin_replies_to_contact_inquiry(self):
        """Marking an inquiry Replied sends the typed customer response."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("""
                INSERT INTO contact_queries (name, email, subject, message)
                VALUES ('Local Test', 'local-test@example.test', 'Test question', 'Question body')
            """)
            query_id = cursor.lastrowid
            db.commit()
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        with patch('app.send_templated_email') as send_email:
            response = self.client.post(f'/admin/contacts/{query_id}/status', data={
                'status': 'Replied',
                'reply_message': 'Here is the requested answer.',
                'admin_note': 'Answered for local demo.',
            }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reply sent', response.data)
        self.assertEqual(send_email.call_args.args[0], 'local-test@example.test')
        self.assertEqual(send_email.call_args.args[3], 'Here is the requested answer.')
        with app.app_context():
            saved = get_db().execute('SELECT status, admin_note FROM contact_queries WHERE id = ?', (query_id,)).fetchone()
        self.assertEqual(saved['status'], 'Replied')
        self.assertEqual(saved['admin_note'], 'Answered for local demo.')

    def test_14_admin_cannot_confirm_overlapping_pending_booking(self):
        """A pending overlapping request must be resolved before confirmation."""
        with app.app_context():
            db = get_db()
            user_id = db.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()['id']
            vehicle_id = db.execute('SELECT id FROM vehicles ORDER BY id LIMIT 1').fetchone()['id']
            from_date = (date.today() + timedelta(days=60)).isoformat()
            to_date = (date.today() + timedelta(days=65)).isoformat()
            first_ref = f"TEST-A-{uuid.uuid4().hex[:10]}"
            second_ref = f"TEST-B-{uuid.uuid4().hex[:10]}"
            ids = []
            for ref in (first_ref, second_ref):
                cursor = db.execute("""
                    INSERT INTO bookings (
                        booking_number, user_id, vehicle_id, from_date, to_date,
                        total_days, total_price, pickup_location, dropoff_location, status
                    ) VALUES (?, ?, ?, ?, ?, 5, 500, 'Test pickup', 'Test return', 'Pending')
                """, (ref, user_id, vehicle_id, from_date, to_date))
                ids.append(cursor.lastrowid)
            db.commit()
        self.client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        response = self.client.post(f'/admin/bookings/{ids[1]}/status', data={
            'status': 'Confirmed', 'admin_remark': 'Approval conflict check'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'another active reservation', response.data)
        with app.app_context():
            status = get_db().execute('SELECT status FROM bookings WHERE id = ?', (ids[1],)).fetchone()['status']
        self.assertEqual(status, 'Pending')

    def test_15_admin_dashboard_snapshot_tracks_new_users_and_bookings(self):
        """The authenticated dashboard data endpoint reflects database changes immediately."""
        response = self.client.get('/admin/dashboard/snapshot')
        self.assertIn(response.status_code, (302, 401))
        dashboard_client = app.test_client()
        dashboard_client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        before = dashboard_client.get('/admin/dashboard/snapshot').get_json()
        self.client.post('/register', data={
            'full_name': 'Dashboard Live Test',
            'email': f'dashboard-{uuid.uuid4().hex[:8]}@example.test',
            'password': 'livepassword123',
            'confirm_password': 'livepassword123',
            'terms_accepted': 'yes',
        })
        after_registration = dashboard_client.get('/admin/dashboard/snapshot').get_json()
        self.assertEqual(after_registration['users'], before['users'] + 1)
        with app.app_context():
            db = get_db()
            user_id = db.execute('SELECT id FROM users ORDER BY id DESC LIMIT 1').fetchone()['id']
            vehicle_id = db.execute('SELECT id FROM vehicles ORDER BY id LIMIT 1').fetchone()['id']
            today = date.today()
            from_date = (today + timedelta(days=90)).isoformat()
            to_date = (today + timedelta(days=92)).isoformat()
            db.execute("""
                INSERT INTO bookings (
                    booking_number, user_id, vehicle_id, from_date, to_date,
                    total_days, total_price, pickup_location, dropoff_location, status
                ) VALUES (?, ?, ?, ?, ?, 2, 300, 'Test pickup', 'Test return', 'Pending')
            """, (f"DASH-{uuid.uuid4().hex[:12]}", user_id, vehicle_id, from_date, to_date))
            db.commit()
        after_booking = dashboard_client.get('/admin/dashboard/snapshot').get_json()
        self.assertEqual(after_booking['bookings'], before['bookings'] + 1)
        self.assertEqual(after_booking['pending_bookings'], before['pending_bookings'] + 1)

    def test_16_password_change_requires_email_code(self):
        """Customer password changes require a code sent to the registered email."""
        self.client.post('/login', data={'email': 'john@example.com', 'password': 'newpassword123'})
        with patch('app.send_templated_email') as send_email:
            response = self.client.post('/profile', data={
                'action': 'request_password_change_code', 'old_password': 'newpassword123'
            }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        import re
        match = re.search(r'password change code is (\d{6})', send_email.call_args.args[3])
        self.assertIsNotNone(match)
        response = self.client.post('/profile', data={
            'action': 'change_password', 'code': match.group(1),
            'new_password': 'changedpass123', 'confirm_password': 'changedpass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password changed successfully', response.data)
        self.client.post('/logout')
        response = self.client.post('/login', data={
            'email': 'john@example.com', 'password': 'changedpass123'
        }, follow_redirects=True)
        self.assertIn(b'John Doe', response.data)

    def test_17_admin_password_recovery_uses_admin_email(self):
        """Admin reset code is sent to the email assigned to the admin account."""
        admin_email = 'awelethomasjoshua619@gmail.com'
        with patch('app.send_templated_email') as send_email:
            response = self.client.post('/admin/forgot-password', data={'email': admin_email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send_email.call_args.args[0], admin_email)
        import re
        code = re.search(r'admin password reset code is (\d{6})', send_email.call_args.args[3]).group(1)
        response = self.client.post('/admin/reset-password', data={
            'email': admin_email,
            'code': code,
            'new_password': 'AdminNewPassword123',
            'confirm_password': 'AdminNewPassword123',
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Administrator password reset successfully', response.data)
        response = self.client.post('/admin/login', data={
            'username': admin_email, 'password': 'AdminNewPassword123'
        }, follow_redirects=True)
        self.assertIn(b'Operational Overview', response.data)

if __name__ == '__main__':
    unittest.main()
