# =====================================================================
# app_unified.py - FIXED VERSION WITH CORS SUPPORT
# =====================================================================

import os
import sys
import base64
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # ADD THIS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# =====================================================================
# CONFIGURATION
# =====================================================================

PROJECT_DIR = "/content/AIVISION"
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

# Initialize Flask
app = Flask(__name__,
            template_folder=os.path.join(PROJECT_DIR, 'templates'),
            static_folder=os.path.join(PROJECT_DIR, 'static'))

# ADD CORS SUPPORT
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = 'ai-vision-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aivision.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(PROJECT_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# =====================================================================
# DATABASE MODELS
# =====================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    videos = db.relationship('Video', backref='user', lazy=True, cascade='all, delete-orphan')

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    processed_path = db.Column(db.String(500), nullable=True)
    narration = db.Column(db.Text, nullable=True)
    transcript = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# =====================================================================
# BACKEND IMPORT
# =====================================================================

try:
    from backend_processing import process_video_backend
    BACKEND_AVAILABLE = True
    print("✅ Backend processing available")
except ImportError as e:
    print(f"⚠️ Backend not available: {e}")
    BACKEND_AVAILABLE = False

    def process_video_backend(input_path):
        return {
            "success": False,
            "error": "Backend not configured"
        }

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def allowed_file(filename):
    ALLOWED = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =====================================================================
# AUTHENTICATION ROUTES
# =====================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        print(f"📝 Signup attempt: {first_name} {last_name} <{email}>")

        # Validation
        errors = []
        if not first_name: errors.append('First name required')
        if not last_name: errors.append('Last name required')
        if not email: errors.append('Email required')
        if not password: errors.append('Password required')
        elif len(password) < 8: errors.append('Password must be 8+ characters')
        if password != confirm_password: errors.append('Passwords do not match')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('signup.html')

        # Check existing
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('signup.html')

        # Create username
        username = f"{first_name}_{last_name}".lower()
        if User.query.filter_by(username=username).first():
            import random
            username = f"{username}{random.randint(100, 999)}"

        # Create user
        try:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            print(f"✅ User created: {username}")
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Signup error: {e}")
            flash(f'Error: {str(e)}', 'error')
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_name'] = user.username
            print(f"✅ Login successful: {user.username}")
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            print(f"❌ Login failed for: {email}")
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

# =====================================================================
# DASHBOARD ROUTES
# =====================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard/home')
@login_required
def dashboard_home():
    return render_template('home.html')

@app.route('/dashboard/features')
@login_required
def dashboard_features():
    return render_template('features.html')

@app.route('/dashboard/upload')
@login_required
def dashboard_upload():
    return render_template('upload.html')

# =====================================================================
# VIDEO PROCESSING API
# =====================================================================

@app.route('/api/upload-video', methods=['POST'])
@login_required
def upload_and_process_video():
    """Complete endpoint that handles upload AND processing"""
    try:
        print("\n" + "="*70)
        print("🎬 VIDEO UPLOAD & PROCESSING REQUEST")
        print("="*70)

        # Check file
        if 'video' not in request.files:
            print("❌ No video in request")
            return jsonify({
                'status': 'error',
                'message': 'No video file provided'
            }), 400

        file = request.files['video']

        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': 'Invalid file type. Use MP4, AVI, MOV, MKV, or WebM'
            }), 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        print(f"💾 Saving: {unique_filename}")
        file.save(filepath)

        # Save to database
        user_id = session.get('user_id')
        new_video = Video(filename=unique_filename, user_id=user_id)
        db.session.add(new_video)
        db.session.commit()

        print(f"✅ Saved to DB, video_id: {new_video.id}")

        # Check backend
        if not BACKEND_AVAILABLE:
            return jsonify({
                'status': 'error',
                'message': 'Backend processing not available'
            }), 503

        # Process video
        print(f"🔄 Starting AI processing...")
        result = process_video_backend(filepath)

        if not result.get('success'):
            print(f"❌ Processing failed: {result.get('error')}")
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Processing failed')
            }), 500

        # Update database
        new_video.processed = True
        new_video.processed_path = result.get('video_path')
        new_video.narration = result.get('narration')
        new_video.transcript = result.get('transcript')
        db.session.commit()

        print(f"✅ Processing complete!")

        # Use download URL
        video_url = f"/api/download/{new_video.id}"
        print(f"📹 Video available at: {video_url}")
        print("="*70 + "\n")

        # Return success response
        return jsonify({
            'status': 'ok',
            'message': 'Processing complete!',
            'video_url': video_url,
            'transcript': result.get('transcript', result.get('narration', '')),
            'narration': result.get('narration', ''),
            'video_id': new_video.id
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ERROR:\n{error_trace}")
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/download/<int:video_id>')
@login_required
def download_video(video_id):
    """Download processed video"""
    try:
        video = Video.query.get(video_id)

        if not video or video.user_id != session.get('user_id'):
            return jsonify({'error': 'Not found'}), 404

        if not video.processed or not video.processed_path:
            return jsonify({'error': 'Video not processed'}), 400

        if not os.path.exists(video.processed_path):
            return jsonify({'error': 'File not found'}), 404

        return send_file(
            video.processed_path,
            as_attachment=False,  # Changed to False for inline viewing
            download_name=f"ai_vision_{video.filename}",
            mimetype='video/mp4'
        )
    except Exception as e:
        print(f"❌ Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos')
@login_required
def get_videos():
    """Get user's videos"""
    user_id = session.get('user_id')
    videos = Video.query.filter_by(user_id=user_id).order_by(Video.uploaded_at.desc()).all()

    return jsonify({
        'videos': [{
            'id': v.id,
            'filename': v.filename,
            'uploaded_at': v.uploaded_at.isoformat(),
            'processed': v.processed,
            'narration': v.narration,
            'can_download': v.processed and v.processed_path and os.path.exists(v.processed_path)
        } for v in videos]
    })

@app.route('/api/session-check')
def session_check():
    """Check session status"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session.get('user_id'),
            'username': session.get('username')
        })
    return jsonify({'logged_in': False}), 401

# =====================================================================
# ERROR HANDLERS
# =====================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# =====================================================================
# DATABASE INITIALIZATION
# =====================================================================

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database initialized")

# =====================================================================
# MAIN
# =====================================================================

if __name__ == '__main__':
    init_db()

    print("\n" + "="*80)
    print("🚀 AI VISION - Ready to Launch")
    print("="*80)
    print(f"📁 Project: {PROJECT_DIR}")
    print(f"📁 Uploads: {app.config['UPLOAD_FOLDER']}")
    print(f"🔧 Backend: {'✅ Available' if BACKEND_AVAILABLE else '❌ Not Available'}")
    print("="*80 + "\n")