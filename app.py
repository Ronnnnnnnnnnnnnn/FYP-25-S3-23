from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db_config import DatabaseConnection
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
import uuid
import os
import stripe

app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ANIMATIONS_FOLDER'] = 'static/animations'
app.config['PROFILE_PICTURES_FOLDER'] = 'static/uploads/profile_pictures'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Price IDs - Set these in Railway environment variables
# You'll get these from Stripe Dashboard after creating products
PRICE_IDS = {
    'monthly': os.getenv('STRIPE_PRICE_ID_MONTHLY', ''),  # $9.99/month
    'yearly': os.getenv('STRIPE_PRICE_ID_YEARLY', '')     # $99.99/year
}

# Frontend URL for redirects
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5000')


# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANIMATIONS_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROFILE_PICTURES_FOLDER'], exist_ok=True)

# Create subdirectories for different tools
os.makedirs(os.path.join(app.config['ANIMATIONS_FOLDER'], 'faceswap'), exist_ok=True)
os.makedirs(os.path.join(app.config['ANIMATIONS_FOLDER'], 'fomd'), exist_ok=True)
os.makedirs(os.path.join(app.config['ANIMATIONS_FOLDER'], 'makeittalk'), exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
ALLOWED_PROFILE_PICTURE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_db():
    return DatabaseConnection().get_connection()


def validate_card(card_number, expiry_date, cvv, card_name):
    """
    Validate credit card details without processing payment.
    Returns (is_valid, error_message)
    """
    # Remove spaces from card number
    card_number = card_number.replace(' ', '').replace('-', '')
    
    # Validate card number format (must be 13-19 digits)
    if not card_number.isdigit():
        return False, 'Card number must contain only digits'
    
    if len(card_number) < 13 or len(card_number) > 19:
        return False, 'Card number must be between 13 and 19 digits'
    
    # Luhn algorithm validation
    def luhn_check(card_num):
        def digits_of(n):
            return [int(d) for d in str(n)]
        digits = digits_of(card_num)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0
    
    if not luhn_check(card_number):
        return False, 'Invalid card number (failed Luhn algorithm check)'
    
    # Validate expiry date format (MM/YY)
    if not expiry_date or '/' not in expiry_date:
        return False, 'Invalid expiry date format. Use MM/YY'
    
    try:
        month, year = expiry_date.split('/')
        month = int(month)
        year = int(year)
        
        if month < 1 or month > 12:
            return False, 'Invalid expiry month. Must be between 01 and 12'
        
        # Convert YY to full year (assuming 20YY)
        current_year = datetime.now().year
        current_month = datetime.now().month
        full_year = 2000 + year
        
        # Check if card is expired
        if full_year < current_year or (full_year == current_year and month < current_month):
            return False, 'Card has expired'
        
    except ValueError:
        return False, 'Invalid expiry date format. Use MM/YY'
    
    # Validate CVV (3-4 digits)
    if not cvv or not cvv.isdigit():
        return False, 'CVV must be 3-4 digits'
    
    if len(cvv) < 3 or len(cvv) > 4:
        return False, 'CVV must be 3-4 digits'
    
    # Validate cardholder name
    if not card_name or len(card_name.strip()) < 2:
        return False, 'Cardholder name is required'
    
    return True, None


def check_account_status():
    """Check if the logged-in user's account is suspended"""
    if 'user_id' not in session:
        return None
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT subscription_status FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if user and user.get('subscription_status') == 'suspended':
            session.clear()  # Clear session if suspended
            return 'suspended'
        return 'active' if user else None
    except Exception as e:
        print(f"Error checking account status: {e}")
        return None
    finally:
        cursor.close()
        db.close()

def check_user_subscriber_access():
    """Check if user is a subscriber or admin by querying database (not just session)"""
    if 'user_id' not in session:
        return False, None, None
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT role, subscription_status FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return False, None, None
        
        current_role = user.get('role', 'user')
        current_status = user.get('subscription_status', 'inactive')
        
        # Update session if it's stale
        if current_role != session.get('role'):
            session['role'] = current_role
        if current_status != session.get('subscription_status'):
            session['subscription_status'] = current_status
        
        # Check if user has subscriber access (must be subscriber/admin AND status active)
        has_access = (current_role in ['subscriber', 'admin']) and (current_status == 'active')
        return has_access, current_role, current_status
    except Exception as e:
        print(f"Error checking subscriber access: {e}")
        # Fallback to session check
        return session.get('role') in ['subscriber', 'admin'], session.get('role'), session.get('subscription_status')

def create_talking_animation(image_path, audio_path, output_path, api_url=None):
    """
    Stub function for MakeItTalk animation creation.
    Replace this with your actual MakeItTalk implementation.
    """
    try:
        # TODO: Implement actual MakeItTalk animation logic here
        # For now, return a placeholder response
        return {
            'status': 'error',
            'message': 'MakeItTalk animation feature not yet implemented. Please implement the create_talking_animation function.'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Animation creation failed: {str(e)}'
        }

# ============================================
# MAIN ROUTES (HTML Pages)
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/verify-account')
def verify_account_page():
    return render_template('verify_account.html')

@app.route('/user')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    
    # Fetch user's current role and info from database (to handle role changes)
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT fullname, role, subscription_status FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return redirect(url_for('login_page'))
        
        # Update session with current role from database
        current_role = user.get('role', 'user')
        if current_role != session.get('role'):
            session['role'] = current_role
        
        # If user is now a subscriber or admin, redirect to subscriber dashboard
        if current_role in ['subscriber', 'admin']:
            return redirect(url_for('subscriber_dashboard'))
        
        # Only show user dashboard for users with role 'user'
        if current_role != 'user':
            return redirect(url_for('login_page'))
        
        fullname = user.get('fullname', 'User')
        subscription_status = user.get('subscription_status', 'inactive')
        
    except Exception as e:
        print(f"Error fetching user info: {e}")
        fullname = 'User'
        subscription_status = 'inactive'
    
    return render_template('user.html', user_fullname=fullname, subscription_status=subscription_status)

@app.route('/subscriber')
def subscriber_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    if session.get('role') not in ['subscriber', 'admin']:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    
    # Fetch user's fullname and subscription info from database
    subscription_info = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get user info
        cursor.execute("SELECT fullname, subscription_plan FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if user:
            fullname = user.get('fullname', 'Subscriber')
            
            # Get subscription details (most recent active subscription)
            cursor.execute(
                """SELECT plan_type, start_date, end_date, payment_status, amount 
                   FROM subscriptions 
                   WHERE user_id = %s AND payment_status = 'completed'
                   ORDER BY created_at DESC 
                   LIMIT 1""",
                (session['user_id'],)
            )
            subscription = cursor.fetchone()
            
            if subscription:
                subscription_info = {
                    'plan_type': subscription.get('plan_type', 'monthly'),
                    'start_date': subscription.get('start_date'),
                    'end_date': subscription.get('end_date'),
                    'amount': float(subscription.get('amount', 0)),
                    'payment_status': subscription.get('payment_status', 'completed')
                }
            elif user.get('subscription_plan'):
                # Fallback to user table if no subscription record found
                plan_type = user.get('subscription_plan', 'monthly')
                subscription_info = {
                    'plan_type': plan_type,
                    'start_date': None,
                    'end_date': None,
                    'amount': 9.99 if plan_type == 'monthly' else 99.99,
                    'payment_status': 'completed'
                }
        else:
            fullname = 'Subscriber'
        
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error fetching subscriber info: {e}")
        import traceback
        traceback.print_exc()
        fullname = 'Subscriber'
        subscription_info = None
    
    return render_template('subscriber.html', user_fullname=fullname, subscription_info=subscription_info)

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    
    # Fetch user's fullname from database
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT fullname FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        fullname = user.get('fullname', 'Admin') if user else 'Admin'
    except Exception as e:
        print(f"Error fetching user fullname: {e}")
        fullname = 'Admin'
    
    return render_template('admin.html', user_fullname=fullname)

@app.route('/payment')
def payment_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    # If user is already a subscriber, redirect to subscriber dashboard
    if session.get('role') in ['subscriber', 'admin']:
        return redirect(url_for('subscriber_dashboard'))
    return render_template('payment.html', stripe_publishable_key=STRIPE_PUBLISHABLE_KEY)


@app.route('/payment-success')
def payment_success():
    """Payment success page"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    session_id = request.args.get('session_id')
    return render_template('payment_success.html', session_id=session_id)

@app.route('/makeittalk')
def makeittalk_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    
    # Check user role from database (not just session - session might be stale)
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT role, subscription_status FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return redirect(url_for('login_page'))
        
        # Update session with current role
        current_role = user.get('role', 'user')
        current_status = user.get('subscription_status', 'inactive')
        
        if current_role != session.get('role'):
            session['role'] = current_role
        if current_status != session.get('subscription_status'):
            session['subscription_status'] = current_status
        
        # Check if user is a subscriber or admin
        if current_role not in ['subscriber', 'admin'] or current_status != 'active':
            return redirect(url_for('payment_page'))
        
        return render_template('makeittalk.html', user_role=current_role)
    except Exception as e:
        print(f"Error checking user role for makeittalk: {e}")
        # Fallback to session check
        if session.get('role') not in ['subscriber', 'admin']:
            return redirect(url_for('payment_page'))
        return render_template('makeittalk.html', user_role=session.get('role'))

@app.route('/fomd')
def fomd_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    
    # Check user role from database (not just session - session might be stale)
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT role, subscription_status FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return redirect(url_for('login_page'))
        
        # Update session with current role
        current_role = user.get('role', 'user')
        current_status = user.get('subscription_status', 'inactive')
        
        if current_role != session.get('role'):
            session['role'] = current_role
        if current_status != session.get('subscription_status'):
            session['subscription_status'] = current_status
        
        # Check if user is a subscriber or admin
        if current_role not in ['subscriber', 'admin'] or current_status != 'active':
            return redirect(url_for('payment_page'))
        
        return render_template('fomd.html', user_role=current_role)
    except Exception as e:
        print(f"Error checking user role for fomd: {e}")
        # Fallback to session check
        if session.get('role') not in ['subscriber', 'admin']:
            return redirect(url_for('payment_page'))
        return render_template('fomd.html', user_role=session.get('role'))

@app.route('/faceswap')
def faceswap_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    # Check if user is a regular user or subscriber (not admin)
    if session.get('role') not in ['user', 'subscriber']:
        return redirect(url_for('login_page'))
    return render_template('faceswap.html', user_role=session.get('role'))

# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/signup', methods=['POST'])
def api_signup():
    db = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
            
        fullname = data.get('fullname')
        email = data.get('email')
        password = data.get('password')
        
        if not all([fullname, email, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
        
        # Get database connection with proper error handling
        try:
            db = get_db()
            if not db:
                print("ERROR: get_db() returned None")
                return jsonify({'success': False, 'message': 'Database connection failed. Please try again.'}), 500
            if not db.is_connected():
                print("ERROR: Database connection is not active")
                return jsonify({'success': False, 'message': 'Database connection is not active. Please try again.'}), 500
            print("Database connection successful")
        except MySQLError as db_error:
            print(f"Database connection error (MySQL Error): {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Database connection error: {str(db_error)}'}), 500
        except Exception as db_error:
            print(f"Database connection error (General): {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Database connection error: {str(db_error)}'}), 500
        
        cursor = db.cursor(dictionary=True)
        
        # Check if email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Insert new user (no email verification needed)
        hashed_password = generate_password_hash(password)
        cursor.execute(
            """INSERT INTO users (fullname, email, password, role, subscription_status) 
               VALUES (%s, %s, %s, %s, %s)""",
            (fullname, email, hashed_password, 'user', 'inactive')
        )
        db.commit()
        
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True, 
            'message': 'Account created successfully! You can now login.'
        })
    
    except Exception as e:
        print(f"Signup error: {e}")
        import traceback
        traceback.print_exc()
        # Ensure we close connections even on error
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if db:
            try:
                db.close()
            except:
                pass
        return jsonify({'success': False, 'message': f'Signup failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        db.close()
        
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Check if account is suspended
        if user.get('subscription_status') == 'suspended':
            return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
        
        # Create session
        session['user_id'] = user['user_id']
        session['email'] = user['email']
        session['fullname'] = user['fullname']
        session['role'] = user['role']
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'role': user['role'],
            'redirect': url_for(f'{user["role"]}_dashboard') if user['role'] != 'user' else url_for('user_dashboard')
        })
    
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/account/delete', methods=['POST'])
def api_delete_account():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = None
    cursor = None
    try:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        
        # Delete user's profile picture if exists
        cursor.execute("SELECT profile_picture FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user and user[0]:
            profile_pic_path = os.path.join('static', user[0])
            if os.path.exists(profile_pic_path):
                try:
                    os.remove(profile_pic_path)
                    print(f"Deleted profile picture: {profile_pic_path}")
                except Exception as e:
                    print(f"Error deleting profile picture: {e}")
        
        # Delete user's animations (if table exists)
        try:
            cursor.execute("SELECT animation_path FROM animations WHERE user_id = %s", (user_id,))
            animations = cursor.fetchall()
            
            for anim in animations:
                if anim[0]:
                    anim_path = os.path.join('static', anim[0])
                    if os.path.exists(anim_path):
                        try:
                            os.remove(anim_path)
                            print(f"Deleted animation: {anim_path}")
                        except Exception as e:
                            print(f"Error deleting animation: {e}")
        except Exception as e:
            print(f"Animations table may not exist or error accessing it: {e}")
        
        # Delete user's avatars (if table exists)
        try:
            cursor.execute("SELECT avatar_path FROM avatars WHERE user_id = %s", (user_id,))
            avatars = cursor.fetchall()
            
            for avatar in avatars:
                if avatar[0]:
                    avatar_path = os.path.join('static', avatar[0])
                    if os.path.exists(avatar_path):
                        try:
                            os.remove(avatar_path)
                            print(f"Deleted avatar: {avatar_path}")
                        except Exception as e:
                            print(f"Error deleting avatar: {e}")
        except Exception as e:
            print(f"Avatars table may not exist or error accessing it: {e}")
        
        # Delete user from database
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        db.commit()
        
        # Clear session
        session.clear()
        
        return jsonify({'success': True, 'message': 'Account deleted successfully'})
    
    except Exception as e:
        print(f"Delete account error: {e}")
        import traceback
        traceback.print_exc()
        if db:
            db.rollback()
        return jsonify({'success': False, 'message': f'Failed to delete account: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if email exists
        cursor.execute("SELECT user_id, fullname FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        db.close()
        
        # Always return success message for security (don't reveal if email exists)
        # In production, you would send an email with reset link here
        return jsonify({
            'success': True,
            'message': 'If an account with that email exists, password reset instructions have been sent.'
        })
    
    except Exception as e:
        print(f"Forgot password error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'}), 500

@app.route('/api/change-password', methods=['POST'])
def api_change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Verify current password
        cursor.execute("SELECT password FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password'], current_password):
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
        
        # Update password
        hashed_password = generate_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password = %s WHERE user_id = %s",
            (hashed_password, session['user_id'])
        )
        db.commit()
        
        cursor.close()
        db.close()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    
    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'}), 500

@app.route('/api/profile', methods=['GET', 'PUT'])
def api_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        if request.method == 'GET':
            cursor.execute("SELECT user_id, fullname, email, role, subscription_status, profile_picture FROM users WHERE user_id = %s", 
                         (session['user_id'],))
            user = cursor.fetchone()
            profile_pic = user.get('profile_picture') if user else None
            print(f"📥 Profile GET - User ID: {session['user_id']}, Role: {user.get('role') if user else 'None'}, Profile Picture: {profile_pic}")
            if profile_pic:
                full_path = os.path.join('static', profile_pic)
                file_exists = os.path.exists(full_path)
                print(f"   → Profile picture file exists: {file_exists} at {full_path}")
            return jsonify({'success': True, 'user': user})
        
        elif request.method == 'PUT':
            data = request.get_json()
            fullname = data.get('fullname')
            email = data.get('email')
            
            cursor.execute(
                "UPDATE users SET fullname = %s, email = %s WHERE user_id = %s",
                (fullname, email, session['user_id'])
            )
            db.commit()
            
            session['fullname'] = fullname
            session['email'] = email
            
            return jsonify({'success': True, 'message': 'Profile updated'})
    
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/profile-picture', methods=['POST'])
def api_upload_profile_picture():
    """Upload profile picture"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename, ALLOWED_PROFILE_PICTURE_EXTENSIONS):
        return jsonify({'success': False, 'message': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
    
    try:
        # Generate unique filename: user_id_timestamp.extension
        user_id = session['user_id']
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{user_id}_{int(datetime.now().timestamp())}.{file_ext}"
        filepath = os.path.join(app.config['PROFILE_PICTURES_FOLDER'], filename)
        
        # Save file
        file.save(filepath)
        
        # Get relative path for database storage
        relative_path = f"uploads/profile_pictures/{filename}"
        
        # Update database
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get old profile picture path to delete it
        cursor.execute("SELECT profile_picture FROM users WHERE user_id = %s", (user_id,))
        old_user = cursor.fetchone()
        old_picture_path = old_user.get('profile_picture') if old_user else None
        
        # Update user's profile picture
        print(f"📸 Updating profile picture for user_id {user_id} with path: {relative_path}")
        cursor.execute(
            "UPDATE users SET profile_picture = %s WHERE user_id = %s",
            (relative_path, user_id)
        )
        db.commit()
        print(f"✓ Database UPDATE executed and committed")
        
        # Verify the update
        cursor.execute("SELECT profile_picture FROM users WHERE user_id = %s", (user_id,))
        updated_user = cursor.fetchone()
        saved_path = updated_user.get('profile_picture') if updated_user else None
        print(f"✓ Profile picture saved to database: {saved_path}")
        print(f"✓ File exists check: {os.path.exists(filepath)}")
        
        cursor.close()
        db.close()
        
        # Delete old profile picture if it exists
        if old_picture_path and old_picture_path.startswith('uploads/'):
            old_full_path = os.path.join('static', old_picture_path)
            if os.path.exists(old_full_path):
                try:
                    os.remove(old_full_path)
                except Exception as e:
                    print(f"Error deleting old profile picture: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'Profile picture updated successfully',
            'profile_picture': relative_path
        })
    
    except Exception as e:
        print(f"Profile picture upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stripe/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    data = request.get_json()
    plan_type = data.get('plan', 'monthly')  # 'monthly' or 'yearly'
    
    if plan_type not in ['monthly', 'yearly']:
        return jsonify({'success': False, 'message': 'Invalid plan type'}), 400
    
    price_id = PRICE_IDS.get(plan_type)
    if not price_id:
        return jsonify({'success': False, 'message': 'Price ID not configured. Please set STRIPE_PRICE_ID_MONTHLY and STRIPE_PRICE_ID_YEARLY in environment variables.'}), 500
    
    db = None
    cursor = None
    try:
        # Get user info
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT email, fullname, stripe_customer_id FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Create or get Stripe customer
        if user['stripe_customer_id']:
            customer_id = user['stripe_customer_id']
        else:
            customer = stripe.Customer.create(
                email=user['email'],
                name=user['fullname'],
                metadata={'user_id': str(session['user_id'])}
            )
            customer_id = customer.id
            
            # Save customer ID to database
            cursor.execute(
                "UPDATE users SET stripe_customer_id = %s WHERE user_id = %s",
                (customer_id, session['user_id'])
            )
            db.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{FRONTEND_URL}/payment',
            metadata={
                'user_id': str(session['user_id']),
                'plan_type': plan_type
            }
        )
        
        return jsonify({
            'success': True,
            'sessionId': checkout_session.id,
            'publishableKey': STRIPE_PUBLISHABLE_KEY
        })
    
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return jsonify({'success': False, 'message': f'Stripe error: {str(e)}'}), 500
    except Exception as e:
        print(f"Create checkout session error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


@app.route('/api/stripe/verify-session/<session_id>', methods=['GET'])
def verify_session(session_id):
    """Verify payment session and update user subscription immediately"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = None
    cursor = None
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            user_id = session['user_id']
            plan_type = checkout_session.metadata.get('plan_type', 'monthly') if checkout_session.metadata else 'monthly'
            
            # Update user subscription in database IMMEDIATELY (don't wait for webhook)
            db = get_db()
            cursor = db.cursor(dictionary=True)
            
            # Calculate end date
            start_date = datetime.now().date()
            if plan_type == 'monthly':
                end_date = start_date + timedelta(days=30)
                amount = 9.99
            else:
                end_date = start_date + timedelta(days=365)
                amount = 99.99
            
            # Update user to subscriber
            cursor.execute(
                """UPDATE users 
                   SET role = 'subscriber', 
                       subscription_status = 'active',
                       stripe_subscription_id = %s,
                       subscription_plan = %s,
                       subscription_end_date = %s
                   WHERE user_id = %s""",
                (checkout_session.subscription, plan_type, end_date, user_id)
            )
            
            # Check if subscription record exists, if not create it
            cursor.execute(
                "SELECT subscription_id FROM subscriptions WHERE user_id = %s AND stripe_subscription_id = %s",
                (user_id, checkout_session.subscription)
            )
            existing_sub = cursor.fetchone()
            
            if not existing_sub:
                # Create subscription record if it doesn't exist
                cursor.execute(
                    """INSERT INTO subscriptions 
                       (user_id, plan_type, start_date, end_date, payment_status, amount, stripe_subscription_id)
                       VALUES (%s, %s, %s, %s, 'completed', %s, %s)""",
                    (user_id, plan_type, start_date, end_date, amount, checkout_session.subscription)
                )
            
            db.commit()
            print(f'✅ Subscription activated immediately for user {user_id} (plan: {plan_type})')
            
            # Refresh session with updated role
            cursor.execute("SELECT role, subscription_status, subscription_plan FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if user:
                session['role'] = user.get('role', 'user')
                session['subscription_status'] = user.get('subscription_status', 'inactive')
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'status': checkout_session.payment_status,
                'subscription_id': checkout_session.subscription,
                'customer_id': checkout_session.customer,
                'role': user.get('role', 'user') if user else 'user',
                'subscription_status': user.get('subscription_status', 'inactive') if user else 'inactive',
                'plan_type': plan_type,
                'message': 'Subscription activated successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'status': checkout_session.payment_status,
                'message': 'Payment not yet processed'
            })
    except stripe.error.StripeError as e:
        print(f"Stripe error in verify-session: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        print(f"Error in verify-session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


@app.route('/api/user/refresh-session', methods=['POST'])
def refresh_user_session():
    """Refresh user session from database (useful after subscription changes)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT role, subscription_status, subscription_plan, fullname, email FROM users WHERE user_id = %s",
            (session['user_id'],)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Update session with current database values
        session['role'] = user.get('role', 'user')
        session['subscription_status'] = user.get('subscription_status', 'inactive')
        session['fullname'] = user.get('fullname', 'User')
        session['email'] = user.get('email', '')
        
        return jsonify({
            'success': True,
            'role': user.get('role', 'user'),
            'subscription_status': user.get('subscription_status', 'inactive'),
            'subscription_plan': user.get('subscription_plan'),
            'message': 'Session refreshed successfully'
        })
    except Exception as e:
        print(f"Error refreshing session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        print('Invalid payload')
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        print('Invalid signature')
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    db = None
    cursor = None
    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = int(session['metadata'].get('user_id', 0))
            plan_type = session['metadata'].get('plan_type', 'monthly')
            
            # Update user subscription
            db = get_db()
            cursor = db.cursor(dictionary=True)
            
            # Calculate end date
            start_date = datetime.now().date()
            if plan_type == 'monthly':
                end_date = start_date + timedelta(days=30)
                amount = 9.99
            else:
                end_date = start_date + timedelta(days=365)
                amount = 99.99
            
            # Update user
            cursor.execute(
                """UPDATE users 
                   SET role = 'subscriber', 
                       subscription_status = 'active',
                       stripe_subscription_id = %s,
                       subscription_plan = %s,
                       subscription_end_date = %s
                   WHERE user_id = %s""",
                (session['subscription'], plan_type, end_date, user_id)
            )
            
            # Create subscription record
            cursor.execute(
                """INSERT INTO subscriptions 
                   (user_id, plan_type, start_date, end_date, payment_status, amount, stripe_subscription_id)
                   VALUES (%s, %s, %s, %s, 'completed', %s, %s)""",
                (user_id, plan_type, start_date, end_date, amount, session['subscription'])
            )
            
            db.commit()
            print(f'Subscription activated for user {user_id}')
        
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            subscription_id = subscription['id']
            
            db = get_db()
            cursor = db.cursor(dictionary=True)
            
            # Find user by subscription ID
            cursor.execute(
                "SELECT user_id FROM users WHERE stripe_subscription_id = %s",
                (subscription_id,)
            )
            user = cursor.fetchone()
            
            if user:
                if subscription['status'] == 'active':
                    # Update subscription end date
                    end_date = datetime.fromtimestamp(subscription['current_period_end']).date()
                    cursor.execute(
                        "UPDATE users SET subscription_status = 'active', subscription_end_date = %s WHERE user_id = %s",
                        (end_date, user['user_id'])
                    )
                    db.commit()
                    print(f'Subscription updated for user {user["user_id"]}')
        
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription['id']
            
            db = get_db()
            cursor = db.cursor()
            
            # Find user by subscription ID
            cursor.execute(
                "SELECT user_id FROM users WHERE stripe_subscription_id = %s",
                (subscription_id,)
            )
            user = cursor.fetchone()
            
            if user:
                # Revoke subscription
                cursor.execute(
                    "UPDATE users SET role = 'user', subscription_status = 'inactive', subscription_plan = NULL, subscription_end_date = NULL WHERE user_id = %s",
                    (user[0],)
                )
                cursor.execute(
                    "UPDATE subscriptions SET payment_status = 'canceled' WHERE stripe_subscription_id = %s",
                    (subscription_id,)
                )
                db.commit()
                print(f'Subscription canceled for user {user[0]}')
        
        return jsonify({'received': True})
    
    except Exception as e:
        print(f'Webhook error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


@app.route('/api/stripe/cancel-subscription', methods=['POST'])
def cancel_subscription():
    """Cancel user subscription"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT stripe_subscription_id FROM users WHERE user_id = %s",
            (session['user_id'],)
        )
        user = cursor.fetchone()
        
        if not user or not user['stripe_subscription_id']:
            return jsonify({'success': False, 'message': 'No active subscription found'}), 404
        
        # Cancel subscription at period end
        subscription = stripe.Subscription.modify(
            user['stripe_subscription_id'],
            cancel_at_period_end=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Subscription will be canceled at the end of the current period'
        })
    
    except stripe.error.StripeError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        print(f'Cancel subscription error: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT user_id, fullname, email, role, subscription_status, created_at FROM users")
        users = cursor.fetchall()
        return jsonify({'success': True, 'users': users})
    
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        db.close()

@app.route('/api/admin/user/<int:user_id>', methods=['PUT', 'DELETE'])
def admin_manage_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        if request.method == 'PUT':
            data = request.get_json()
            action = data.get('action')
            
            if action == 'suspend':
                cursor.execute("UPDATE users SET subscription_status = %s WHERE user_id = %s", 
                             ('suspended', user_id))
                db.commit()
                return jsonify({'success': True, 'message': 'User suspended'})
            
            elif action == 'activate':
                cursor.execute("UPDATE users SET subscription_status = %s WHERE user_id = %s", 
                             ('active', user_id))
                db.commit()
                return jsonify({'success': True, 'message': 'User activated'})
            
            elif action == 'edit':
                fullname = data.get('fullname')
                email = data.get('email')
                
                if not fullname or not email:
                    return jsonify({'success': False, 'message': 'Fullname and email are required'}), 400
                
                # Check if email is already taken by another user
                cursor.execute("SELECT user_id FROM users WHERE email = %s AND user_id != %s", (email, user_id))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Email already exists'}), 400
                
                cursor.execute(
                    "UPDATE users SET fullname = %s, email = %s WHERE user_id = %s",
                    (fullname, email, user_id)
                )
                db.commit()
                return jsonify({'success': True, 'message': 'User updated successfully'})
            
            else:
                return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        elif request.method == 'DELETE':
            # Prevent admin from deleting themselves
            if user_id == session['user_id']:
                return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
            
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            db.commit()
            return jsonify({'success': True, 'message': 'User deleted successfully'})
    
    except Exception as e:
        print(f"Manage user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        db.close()

# ============================================
# MAKEITTALK API ENDPOINTS
# ============================================
@app.route('/api/makeittalk/animate', methods=['POST'])
def makeittalk_animate():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    # Check if user is a subscriber or admin (check database, not just session)
    has_access, role, sub_status = check_user_subscriber_access()
    if not has_access:
        return jsonify({'success': False, 'message': 'Subscription required. Please upgrade to access this feature.'}), 403
    
    if 'image' not in request.files or 'audio' not in request.files:
        return jsonify({'success': False, 'message': 'Image and audio required'}), 400
    
    image_file = request.files['image']
    audio_file = request.files['audio']
    
    if image_file.filename == '' or audio_file.filename == '':
        return jsonify({'success': False, 'message': 'No files selected'}), 400
    
    try:
        # Save uploaded files
        image_filename = secure_filename(f"{uuid.uuid4()}_{image_file.filename}")
        audio_filename = secure_filename(f"{uuid.uuid4()}_{audio_file.filename}")
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        
        image_file.save(image_path)
        audio_file.save(audio_path)
        
        # Generate output filename
        output_filename = f"makeittalk_{uuid.uuid4()}.mp4"
        output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'makeittalk', output_filename)
        
        # Get ngrok URL from environment variable or use default
        api_url = os.environ.get('MAKEITTALK_API_URL', None)
        
        # Process with MakeItTalk
        result = create_talking_animation(
            image_path=image_path,
            audio_path=audio_path,
            output_path=output_path,
            api_url=api_url
        )
        
        if result['status'] == 'success':
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'makeittalk', f'animations/makeittalk/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'Animation created successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/makeittalk/{output_filename}'
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Animation generation failed')
            }), 500
    
    except Exception as e:
        print(f"MakeItTalk error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================
# FACESWAP API ENDPOINTS
# ============================================
@app.route('/api/faceswap/save', methods=['POST'])
def faceswap_save():
    """Save face swap result to database and server"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    # Check if user is a regular user or subscriber (not admin)
    if session.get('role') not in ['user', 'subscriber']:
        return jsonify({'success': False, 'message': 'Access denied. Only users and subscribers can use face swap.'}), 403
    
    try:
        # Get image data from request
        if 'image' not in request.files:
            # Try to get base64 data from JSON
            data = request.get_json()
            if not data or 'image_data' not in data:
                return jsonify({'success': False, 'message': 'No image provided'}), 400
            
            import base64
            import io
            
            # Decode base64 image
            image_data = data['image_data']
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            
            # Generate filename
            output_filename = f"faceswap_{uuid.uuid4()}.png"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'faceswap', output_filename)
            
            # Save image directly (base64 decoded bytes)
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'faceswap', f'animations/faceswap/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'Face swap saved successfully',
                'animation_id': animation_id,
                'image_url': f'/static/animations/faceswap/{output_filename}'
            })
        else:
            # Handle file upload
            file = request.files['image']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Generate filename
            output_filename = f"faceswap_{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'faceswap', output_filename)
            
            # Save file
            file.save(output_path)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'faceswap', f'animations/faceswap/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'Face swap saved successfully',
                'animation_id': animation_id,
                'image_url': f'/static/animations/faceswap/{output_filename}'
            })
    
    except Exception as e:
        print(f"Face swap save error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/makeittalk/save', methods=['POST'])
def makeittalk_save():
    """Save MakeItTalk animation result to database and server"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    # Check if user is a subscriber or admin (check database, not just session)
    has_access, role, sub_status = check_user_subscriber_access()
    if not has_access:
        return jsonify({'success': False, 'message': 'Subscription required. Please upgrade to access this feature.'}), 403
    
    try:
        # Get video data from request
        if 'video' not in request.files:
            # Try to get base64 data from JSON
            data = request.get_json()
            if not data or 'video_data' not in data:
                return jsonify({'success': False, 'message': 'No video provided'}), 400
            
            import base64
            
            # Decode base64 video
            video_data = data['video_data']
            if video_data.startswith('data:video'):
                video_data = video_data.split(',')[1]
            
            video_bytes = base64.b64decode(video_data)
            
            # Generate filename
            output_filename = f"makeittalk_{uuid.uuid4()}.mp4"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'makeittalk', output_filename)
            
            # Save video
            with open(output_path, 'wb') as f:
                f.write(video_bytes)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'makeittalk', f'animations/makeittalk/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'MakeItTalk animation saved successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/makeittalk/{output_filename}'
            })
        else:
            # Handle file upload
            file = request.files['video']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Generate filename
            output_filename = f"makeittalk_{uuid.uuid4()}.mp4"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'makeittalk', output_filename)
            
            # Save file
            file.save(output_path)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'makeittalk', f'animations/makeittalk/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'MakeItTalk animation saved successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/makeittalk/{output_filename}'
            })
    
    except Exception as e:
        print(f"MakeItTalk save error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/animation/delete/<int:animation_id>', methods=['DELETE'])
def delete_animation(animation_id):
    """Delete an animation/faceswap by ID"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Verify the animation belongs to the current user
        cursor.execute(
            "SELECT animation_id, tool_type, animation_path FROM animations WHERE animation_id = %s AND user_id = %s",
            (animation_id, session['user_id'])
        )
        
        animation = cursor.fetchone()
        
        if not animation:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Animation not found or access denied'}), 404
        
        # Delete the file from server
        # animation_path in DB is like 'animations/faceswap/filename.png'
        # Full path is 'static/animations/faceswap/filename.png'
        file_path = os.path.join('static', animation['animation_path'])
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        except Exception as file_error:
            print(f"Error deleting file {file_path}: {file_error}")
            # Continue with database deletion even if file deletion fails
        
        # Delete from database
        cursor.execute("DELETE FROM animations WHERE animation_id = %s AND user_id = %s", 
                      (animation_id, session['user_id']))
        db.commit()
        
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Animation deleted successfully'
        })
    
    except Exception as e:
        print(f"Delete animation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================
# FOMD API ENDPOINTS
# ============================================
@app.route('/api/fomd/save', methods=['POST'])
def fomd_save():
    """Save FOMD animation result to database and server"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    # Check if user is a subscriber or admin (check database, not just session)
    has_access, role, sub_status = check_user_subscriber_access()
    if not has_access:
        return jsonify({'success': False, 'message': 'Subscription required. Please upgrade to access this feature.'}), 403
    
    try:
        # Get video data from request
        if 'video' not in request.files:
            # Try to get base64 data from JSON
            data = request.get_json()
            if not data or 'video_data' not in data:
                return jsonify({'success': False, 'message': 'No video provided'}), 400
            
            import base64
            import io
            
            # Decode base64 video
            video_data = data['video_data']
            if video_data.startswith('data:video'):
                video_data = video_data.split(',')[1]
            
            video_bytes = base64.b64decode(video_data)
            
            # Generate filename
            output_filename = f"fomd_{uuid.uuid4()}.mp4"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'fomd', output_filename)
            
            # Save video
            with open(output_path, 'wb') as f:
                f.write(video_bytes)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'fomd', f'animations/fomd/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'FOMD animation saved successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/fomd/{output_filename}'
            })
        else:
            # Handle file upload
            file = request.files['video']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Generate filename
            output_filename = f"fomd_{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}"
            output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], 'fomd', output_filename)
            
            # Save file
            file.save(output_path)
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute(
                "INSERT INTO animations (user_id, tool_type, animation_path, status) VALUES (%s, %s, %s, %s)",
                (session['user_id'], 'fomd', f'animations/fomd/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'FOMD animation saved successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/fomd/{output_filename}'
            })
    
    except Exception as e:
        print(f"FOMD save error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================
# GET USER GENERATED ITEMS
# ============================================
@app.route('/api/user/generated-items', methods=['GET'])
def get_user_generated_items():
    """Get all generated items (animations/photos) for the current user"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get user role to filter by allowed tools
        user_role = session.get('role', 'user')
        
        # Build query based on user role
        if user_role == 'user':
            # Users can only see faceswap
            cursor.execute(
                """SELECT animation_id, tool_type, animation_path, status, created_at 
                   FROM animations 
                   WHERE user_id = %s AND tool_type = 'faceswap'
                   ORDER BY created_at DESC""",
                (session['user_id'],)
            )
        else:
            # Subscribers and admins can see all
            cursor.execute(
                """SELECT animation_id, tool_type, animation_path, status, created_at 
                   FROM animations 
                   WHERE user_id = %s
                   ORDER BY created_at DESC""",
                (session['user_id'],)
            )
        
        items = cursor.fetchall()
        
        cursor.close()
        db.close()
        
        # Format items for frontend
        formatted_items = []
        for item in items:
            formatted_items.append({
                'id': item['animation_id'],
                'tool_type': item['tool_type'],
                'file_path': item['animation_path'],
                'file_url': f"/static/{item['animation_path']}",
                'status': item['status'],
                'created_at': item['created_at'].isoformat() if item['created_at'] else None
            })
        
        return jsonify({
            'success': True,
            'items': formatted_items
        })
    
    except Exception as e:
        print(f"Get generated items error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions and return JSON for API routes"""
    print(f"Unhandled exception: {e}")
    import traceback
    traceback.print_exc()
    # If it's an API request, return JSON
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
    # Otherwise render an error page (not JSON)
    try:
        return render_template('error.html', error=str(e)), 500
    except:
        # Fallback if error.html doesn't exist
        return f'<h1>An error occurred</h1><p>{str(e)}</p>', 500

# Database connection will be tested on first request

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Face Animation Platform Starting...")
    print("="*60)
    print(f"Server running at: http://localhost:5000")
    print(f"Static folder: {app.static_folder}")
    print(f"Template folder: {app.template_folder}")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')