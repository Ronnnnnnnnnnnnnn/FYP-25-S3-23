from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from werkzeug.utils import secure_filename
from db_config import DatabaseConnection
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
import uuid
import os
import secrets

app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')

app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ANIMATIONS_FOLDER'] = 'static/animations'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration - Using Mailgun API (works with Railway, no domain verification needed)
# Get your API key from: https://app.mailgun.com/app/api-keys
# Set these environment variables in Railway:
# MAILGUN_API_KEY=your_mailgun_api_key_here
# MAILGUN_DOMAIN=your_mailgun_domain (e.g., sandbox12345.mailgun.org for testing)
# MAILGUN_FROM_EMAIL=noreply@your_mailgun_domain
# 
# Mailgun free tier: 5,000 emails/month, can send to any email address
# No domain verification needed for sandbox domain (testing)
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY', '')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN', '')
MAILGUN_FROM_EMAIL = os.getenv('MAILGUN_FROM_EMAIL', '')

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANIMATIONS_FOLDER'], exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_db():
    return DatabaseConnection().get_connection()

def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def send_verification_email(email, token, fullname):
    """Send verification link email using Mailgun API"""
    try:
        # Check if Mailgun is configured
        if not MAILGUN_API_KEY or not MAILGUN_DOMAIN or not MAILGUN_FROM_EMAIL:
            print(f"ERROR: Mailgun not configured. Set MAILGUN_API_KEY, MAILGUN_DOMAIN, and MAILGUN_FROM_EMAIL environment variables.")
            return False
        
        # Generate verification URL
        verification_url = url_for('verify_email_link', token=token, _external=True)
        
        print(f"Attempting to send verification email to {email} via Mailgun API")
        print(f"Verification URL: {verification_url}")
        
        # Mailgun API endpoint
        url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
        
        # Mailgun uses Basic Auth with api key
        auth = ("api", MAILGUN_API_KEY)
        
        data = {
            "from": MAILGUN_FROM_EMAIL,
            "to": email,
            "subject": "Verify Your Email - FirstMod-AI",
            "html": f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #667eea;">Welcome to FirstMod-AI, {fullname}!</h2>
                <p>Thank you for signing up. Please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background-color: #667eea; color: white; padding: 15px 30px; text-decoration: none; 
                              border-radius: 5px; display: inline-block; font-size: 16px; font-weight: bold;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #667eea; word-break: break-all; font-size: 12px;">{verification_url}</p>
                <p style="color: #666; font-size: 14px;">This link will expire in 24 hours.</p>
                <p style="color: #666; font-size: 14px;">If you didn't create an account, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">© 2025 FirstMod-AI. All rights reserved.</p>
            </body>
            </html>
            """
        }
        
        # Send email via Mailgun API
        response = requests.post(url, auth=auth, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ Verification email sent successfully to {email} via Mailgun")
            return True
        else:
            print(f"✗ ERROR: Mailgun API returned status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ ERROR: Email sending timed out")
        return False
    except Exception as e:
        print(f"✗ ERROR sending email to {email}: {e}")
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

@app.route('/verify-account')
def verify_account_page():
    return render_template('verify_account.html')

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
        
        # Generate verification token and expiration time (24 hours from now)
        verification_token = generate_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        # Insert new user with unverified status
        hashed_password = generate_password_hash(password)
        cursor.execute(
            """INSERT INTO users (fullname, email, password, role, subscription_status, email_verified, verification_token, verification_token_expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (fullname, email, hashed_password, 'user', 'inactive', False, verification_token, expires_at)
        )
        db.commit()
        
        # Close cursor and connection before sending email
        if cursor:
            cursor.close()
        if db:
            db.close()
        
        # Send verification email
        # Try to send email synchronously first to catch errors immediately
        print(f"Preparing to send verification email to {email} with token: {verification_token[:20]}...")
        email_sent = False
        email_error_msg = None
        
        try:
            email_sent = send_verification_email(email, verification_token, fullname)
            if email_sent:
                print(f"✓ Verification email sent successfully to {email}")
            else:
                print(f"✗ Verification email failed to send to {email}")
                email_error_msg = "Email sending returned False"
        except Exception as email_error:
            print(f"✗ Exception during email sending: {email_error}")
            import traceback
            traceback.print_exc()
            email_error_msg = str(email_error)
        
        # Return response based on email sending result
        if email_sent:
            return jsonify({
                'success': True, 
                'message': 'Account created! Please check your email and click the verification link to activate your account.',
                'requires_verification': True
            })
        else:
            # Email failed, but account is created - user can request resend
            return jsonify({
                'success': True, 
                'message': f'Account created but verification email failed to send. Error: {email_error_msg}. Please use "Resend Verification" or contact support.',
                'requires_verification': True,
                'email_error': True,
                'verification_token': verification_token  # Include token for manual verification if needed
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

@app.route('/verify-email/<token>')
def verify_email_link(token):
    """Verify email using verification token from link"""
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Find user with this verification token
        cursor.execute(
            """SELECT user_id, verification_token, verification_token_expires_at, email_verified, email 
               FROM users WHERE verification_token = %s""",
            (token,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            db.close()
            return render_template('verify_result.html', 
                                 success=False, 
                                 message='Invalid verification link.')
        
        # Check if already verified
        if user['email_verified']:
            cursor.close()
            db.close()
            return render_template('verify_result.html', 
                                 success=True, 
                                 message='Email already verified! You can now login.')
        
        # Check if token expired
        if user['verification_token_expires_at'] and datetime.now() > user['verification_token_expires_at']:
            cursor.close()
            db.close()
            return render_template('verify_result.html', 
                                 success=False, 
                                 message='Verification link has expired. Please request a new one.')
        
        # Verify the email
        cursor.execute(
            """UPDATE users SET email_verified = TRUE, verification_token = NULL, 
               verification_token_expires_at = NULL, subscription_status = 'active' 
               WHERE user_id = %s""",
            (user['user_id'],)
        )
        db.commit()
        cursor.close()
        db.close()
        
        return render_template('verify_result.html', 
                             success=True, 
                             message='Email verified successfully! You can now login.')
    
    except Exception as e:
        print(f"Verify email error: {e}")
        import traceback
        traceback.print_exc()
        return render_template('verify_result.html', 
                             success=False, 
                             message='An error occurred during verification. Please try again.')

@app.route('/api/resend-verification', methods=['POST'])
def api_resend_verification():
    """Resend verification email"""
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
        
        # Generate new verification token
        verification_token = generate_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        # Update verification token
        cursor.execute(
            "UPDATE users SET verification_token = %s, verification_token_expires_at = %s WHERE user_id = %s",
            (verification_token, expires_at, user['user_id'])
        )
        db.commit()
        cursor.close()
        db.close()
        
        # Send new verification email
        import threading
        def send_email_async():
            try:
                send_verification_email(email, verification_token, user['fullname'])
            except Exception as e:
                print(f"Background email sending failed: {e}")
        
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Verification email sent! Please check your inbox.'
        })
    
    except Exception as e:
        print(f"Resend verification error: {e}")
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
        # If verification_token is NULL, it means it's an old user created before email verification feature
        email_verified = user.get('email_verified', False)
        verification_token = user.get('verification_token')
        
        # If user has verification_token but not verified, require verification
        if verification_token is not None and not email_verified:
            return jsonify({
                'success': False, 
                'message': 'Please verify your email before logging in. Check your inbox for the verification link.',
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