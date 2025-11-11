from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db_config import DatabaseConnection
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
import uuid
import os
import random
import string

app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ANIMATIONS_FOLDER'] = 'static/animations'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')

mail = Mail(app)

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANIMATIONS_FOLDER'], exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_db():
    return DatabaseConnection().get_connection()

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, otp, fullname):
    """Send OTP verification email"""
    try:
        # Check if email is configured
        mail_username = app.config.get('MAIL_USERNAME', '')
        mail_password = app.config.get('MAIL_PASSWORD', '')
        
        if not mail_username or not mail_password:
            print(f"ERROR: Email not configured. MAIL_USERNAME: {bool(mail_username)}, MAIL_PASSWORD: {bool(mail_password)}")
            return False
        
        print(f"Attempting to send email to {email} from {mail_username}")
        
        msg = Message(
            subject='Verify Your Email - FirstMod-AI',
            recipients=[email],
            html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #667eea;">Welcome to FirstMod-AI, {fullname}!</h2>
                <p>Thank you for signing up. Please verify your email address by entering the OTP code below:</p>
                <div style="background-color: #f0f0f0; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px;">
                    <h1 style="color: #667eea; font-size: 32px; letter-spacing: 5px; margin: 0;">{otp}</h1>
                </div>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't create an account, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">© 2025 FirstMod-AI. All rights reserved.</p>
            </body>
            </html>
            """
        )
        mail.send(msg)
        print(f"Email sent successfully to {email}")
        return True
    except Exception as e:
        print(f"ERROR sending email to {email}: {e}")
        import traceback
        traceback.print_exc()
        return False

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

@app.route('/user')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    if session.get('role') not in ['user', 'subscriber', 'admin']:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    return render_template('user.html')

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
    return render_template('subscriber.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    return render_template('admin.html')

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
    return render_template('payment.html')

@app.route('/makeittalk')
def makeittalk_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return redirect(url_for('login_page'))
    # Check if user is a subscriber or admin
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
    # Check if user is a subscriber or admin
    if session.get('role') not in ['subscriber', 'admin']:
        return redirect(url_for('payment_page'))
    return render_template('fomd.html', user_role=session.get('role'))

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
        
        # Check if email exists and is verified
        cursor.execute("SELECT user_id, email_verified FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            if existing_user.get('email_verified', False):  # email_verified is True
                cursor.close()
                db.close()
                return jsonify({'success': False, 'message': 'Email already exists'}), 400
            else:
                # Email exists but not verified, delete old record and create new one
                cursor.execute("DELETE FROM users WHERE email = %s", (email,))
                db.commit()
        
        # Generate OTP and expiration time (10 minutes from now)
        otp = generate_otp()
        expires_at = datetime.now() + timedelta(minutes=10)
        
        # Insert new user with unverified status
        hashed_password = generate_password_hash(password)
        cursor.execute(
            """INSERT INTO users (fullname, email, password, role, subscription_status, email_verified, verification_code, verification_code_expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (fullname, email, hashed_password, 'user', 'inactive', False, otp, expires_at)
        )
        db.commit()
        
        # Close cursor and connection before sending email
        if cursor:
            cursor.close()
        if db:
            db.close()
        
        # Send verification email
        email_sent = False
        try:
            print(f"Preparing to send OTP email to {email} with OTP: {otp}")
            email_sent = send_verification_email(email, otp, fullname)
            print(f"Email sending result: {email_sent}")
        except Exception as email_error:
            print(f"Email sending exception: {email_error}")
            import traceback
            traceback.print_exc()
            # User is created, but email failed - still return success but warn user
            return jsonify({
                'success': True, 
                'message': 'Account created but failed to send verification email. Please contact support or try resending OTP.',
                'requires_verification': True,
                'email_error': True
            }), 200
        
        if email_sent:
            return jsonify({
                'success': True, 
                'message': 'Account created! Please check your email for verification code.',
                'requires_verification': True
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Account created but failed to send verification email. Please contact support or try resending OTP.',
                'requires_verification': True,
                'email_error': True
            }), 200
    
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

@app.route('/api/verify-email', methods=['POST'])
def api_verify_email():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not all([email, otp]):
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user exists with this email and OTP
        cursor.execute(
            """SELECT user_id, verification_code, verification_code_expires_at, email_verified 
               FROM users WHERE email = %s""",
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Invalid email or OTP'}), 400
        
        # Check if already verified
        if user['email_verified']:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Email already verified'}), 400
        
        # Check if OTP matches
        if user['verification_code'] != otp:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Invalid OTP code'}), 400
        
        # Check if OTP expired
        if user['verification_code_expires_at'] and datetime.now() > user['verification_code_expires_at']:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'OTP code has expired. Please request a new one.'}), 400
        
        # Verify the email
        cursor.execute(
            """UPDATE users SET email_verified = TRUE, verification_code = NULL, 
               verification_code_expires_at = NULL, subscription_status = 'active' 
               WHERE user_id = %s""",
            (user['user_id'],)
        )
        db.commit()
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True, 
            'message': 'Email verified successfully! You can now login.'
        })
    
    except Exception as e:
        print(f"Verify email error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/get-otp', methods=['POST'])
def api_get_otp():
    """Get OTP for testing purposes (only for unverified users)"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Get OTP for unverified user
        cursor.execute(
            "SELECT verification_code, email_verified, created_at FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        
        cursor.close()
        db.close()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if user['email_verified']:
            return jsonify({'success': False, 'message': 'Email already verified'}), 400
        
        if not user['verification_code']:
            return jsonify({'success': False, 'message': 'No verification code found'}), 404
        
        return jsonify({
            'success': True,
            'otp': user['verification_code'],
            'message': 'OTP retrieved (for testing only)'
        })
    
    except Exception as e:
        print(f"Get OTP error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/resend-otp', methods=['POST'])
def api_resend_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if user exists and is not verified
        cursor.execute(
            "SELECT user_id, fullname, email_verified FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Email not found'}), 400
        
        if user['email_verified']:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Email already verified'}), 400
        
        # Generate new OTP
        otp = generate_otp()
        expires_at = datetime.now() + timedelta(minutes=10)
        
        # Update verification code
        cursor.execute(
            "UPDATE users SET verification_code = %s, verification_code_expires_at = %s WHERE user_id = %s",
            (otp, expires_at, user['user_id'])
        )
        db.commit()
        cursor.close()
        db.close()
        
        # Send new OTP email
        if send_verification_email(email, otp, user['fullname']):
            return jsonify({
                'success': True, 
                'message': 'New verification code sent to your email.'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to send verification email. Please try again.'
            }), 500
    
    except Exception as e:
        print(f"Resend OTP error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # Check if email is verified
        # Allow existing users (created before email verification) to login
        # If verification_code is NULL, it means it's an old user created before email verification feature
        email_verified = user.get('email_verified', False)
        verification_code = user.get('verification_code')
        
        # If user has verification_code but not verified, require verification
        if verification_code is not None and not email_verified:
            return jsonify({
                'success': False, 
                'message': 'Please verify your email before logging in. Check your inbox for the verification code.',
                'requires_verification': True
            }), 403
        
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
            cursor.execute("SELECT user_id, fullname, email, role, subscription_status FROM users WHERE user_id = %s", 
                         (session['user_id'],))
            user = cursor.fetchone()
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


@app.route('/api/subscription/update', methods=['POST'])
def update_subscription():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    # Check if account is suspended
    status = check_account_status()
    if status == 'suspended':
        return jsonify({'success': False, 'message': 'Your account has been suspended. Please contact an administrator.'}), 403
    
    data = request.get_json()
    plan = data.get('plan')
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(
            "UPDATE users SET role = %s, subscription_status = %s WHERE user_id = %s",
            ('subscriber', 'active', session['user_id'])
        )
        db.commit()
        
        session['role'] = 'subscriber'
        
        return jsonify({'success': True, 'message': 'Subscription updated'})
    
    except Exception as e:
        print(f"Update subscription error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
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
    # Check if user is a subscriber or admin
    if session.get('role') not in ['subscriber', 'admin']:
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
        output_path = os.path.join(app.config['ANIMATIONS_FOLDER'], output_filename)
        
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
                "INSERT INTO animations (user_id, animation_path, status) VALUES (%s, %s, %s)",
                (session['user_id'], f'animations/{output_filename}', 'completed')
            )
            db.commit()
            
            animation_id = cursor.lastrowid
            
            cursor.close()
            db.close()
            
            return jsonify({
                'success': True,
                'message': 'Animation created successfully',
                'animation_id': animation_id,
                'video_url': f'/static/animations/{output_filename}'
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Animation generation failed')
            }), 500
    
    except Exception as e:
        print(f"MakeItTalk error: {e}")
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
    # Otherwise return the default error page
    return jsonify({'success': False, 'message': 'An error occurred'}), 500

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