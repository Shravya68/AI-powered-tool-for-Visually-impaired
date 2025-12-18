# AI Vision - Intelligent Video Processing System

A complete Flask-based web application for AI-powered video processing with object detection, distance estimation, natural language narration, and text-to-speech audio generation.

## Features

- 🔐 User authentication (signup/login/logout) with secure password hashing
- 📁 Video file upload support (up to 500MB)
- 🤖 AI-powered object detection using YOLOv8 (COCO + Custom models)
- 📏 Real-time distance estimation for detected objects
- 🗣️ GPT-powered natural language narration generation
- 🔊 Text-to-speech audio narration with video synchronization
- 🎬 Processed video output with bounding boxes and audio narration
- 💾 SQLite database for user and video management
- 🎨 Modern UI with TailwindCSS and animated backgrounds
- ⚡ Real-time processing feedback with progress indicators

## Project Structure

```
.
├── app_unified.py          # Main Flask application with API routes
├── backend_processing.py   # AI video processing backend (YOLO, GPT, TTS)
├── models.py              # Database models (User, Video)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── run.bat               # Windows batch script to run the app
├── templates/            # Jinja2 templates
│   ├── base.html        # Base template with animations
│   ├── signup.html      # User registration
│   ├── login.html       # User login
│   ├── dashboard.html   # Main dashboard shell
│   ├── home.html        # Dashboard home content
│   ├── features.html    # Features page
│   └── upload.html      # Video upload interface
├── static/              # Static assets
│   ├── css/
│   │   ├── dashboard.css  # Dashboard styles
│   │   └── styles.css     # Global styles
│   └── js/
│       ├── app.js         # Global JavaScript utilities
│       ├── dashboard.js   # Dashboard interactions
│       └── upload.js      # Video upload and processing logic
├── uploads/             # Uploaded video files
├── processed_videos/    # AI-processed output videos
└── instance/            # SQLite database files
    └── users.db
```

## Installation

### 1. Clone or download this project

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```
SECRET_KEY=your-random-secret-key-here
BACKEND_API_URL=http://localhost:5001/process-video
SQLITE_CLOUD_URL=  # Optional: leave empty for local SQLite
```

### 4. Run the application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## AI Processing Pipeline

The backend processing (`backend_processing.py`) performs the following steps:

### 1. Object Detection
- Uses YOLOv8s (COCO dataset) for general objects (cars, people, bicycles, etc.)
- Uses custom-trained YOLOv8 model for traffic-specific objects (traffic lights, signs, zebra crossings)
- Processes video frames with configurable frame skip for performance

### 2. Distance Estimation
- Calculates focal length from camera field of view
- Estimates distance using object pixel size and known real-world dimensions
- Applies EMA smoothing for stable distance readings
- Uses ground-plane geometry for zebra crossings

### 3. Narration Generation
- Collects detection data from all frames
- Sends scene summary to GPT-3.5-turbo for natural language narration
- Generates first-person plural narrative describing the scene
- Falls back to rule-based narration if GPT is unavailable

### 4. Text-to-Speech
- Uses Facebook MMS-TTS model for high-quality speech synthesis
- Generates audio narration from GPT text
- Applies speed adjustment for natural pacing

### 5. Video Merging
- Annotates original video with bounding boxes and distance labels
- Synchronizes video speed with audio narration duration
- Outputs final MP4 with embedded audio

### API Response Format

**Success:**
```json
{
  "status": "ok",
  "video_url": "/api/download/1",
  "narration": "We are at a busy intersection...",
  "transcript": "Full detection summary...",
  "video_id": 1
}
```

**Error:**
```json
{
  "status": "error",
  "message": "Error description"
}
```

## Database Configuration

### Local SQLite (Default)

By default, the app uses a local SQLite database file `users.db` in the project directory.

### SQLite Cloud (Optional)

To use SQLite Cloud:

1. Sign up for SQLite Cloud
2. Get your connection URL
3. Add it to `.env`:

```
SQLITE_CLOUD_URL=sqlitecloud://user:pass@host.sqlite.cloud:8860/dbname
```

The app will automatically use SQLite Cloud if this variable is set.

## Usage

### 1. Sign Up
- Navigate to `/signup`
- Fill in: First name, Last name, Email, Password (min 8 chars)
- Confirm password

### 2. Login
- Navigate to `/login`
- Enter email and password

### 3. Dashboard
After login, you'll see the dashboard with:
- **Home**: Overview and quick actions
- **Features**: Description of capabilities
- **Upload Video**: Main processing interface

### 4. Process Videos

1. Click "Upload Video" from the dashboard
2. Select a video file (MP4, WebM, AVI, MOV, MKV - max 500MB)
3. Click "🚀 Process Video with AI"
4. Wait for processing (typically 2-5 minutes depending on video length)

### 5. View Results
- Watch the processed video with:
  - Bounding boxes around detected objects
  - Distance labels for each object
  - AI-generated audio narration
- Download the complete processed video
- Process another video

## Customization

### AI Model Configuration
Edit `backend_processing.py` to customize:

```python
# Detection thresholds
CONF_COCO = 0.35  # COCO model confidence threshold
CONF_CUSTOM = 0.30  # Custom model confidence threshold

# Video processing
TARGET_WIDTH, TARGET_HEIGHT = 960, 540  # Output resolution
FRAME_SKIP = 1  # Process every Nth frame

# Camera parameters
VFOV_DEG = 49.0  # Vertical field of view
CAMERA_HEIGHT_M = 1.50  # Camera height in meters

# TTS settings
EXTRA_SLOW_FACTOR = 1.3  # Speech speed adjustment
```

### Styling (TailwindCSS)
The app uses TailwindCSS via CDN. To customize:
- Edit `templates/base.html` for global styles
- Modify `static/css/dashboard.css` for dashboard-specific styles
- Modify `static/css/styles.css` for upload page styles

### OpenAI API Key
Add to `.env` for GPT narration:
```
OPENAI_API_KEY=sk-your-api-key-here
```

Without this key, the system uses fallback rule-based narration.

## Security Notes

- Always use a strong `SECRET_KEY` in production
- Use HTTPS in production
- Keep `.env` file secure and never commit it
- Passwords are hashed using Werkzeug's `generate_password_hash`
- Session-based authentication with secure cookies

## Troubleshooting

### Video not displaying after processing
- Hard refresh browser (Ctrl+Shift+R)
- Check browser console for errors
- Verify processed video file exists in `processed_videos/` folder

### Processing takes too long
- Reduce video resolution or length
- Increase `FRAME_SKIP` in `backend_processing.py`
- Use GPU acceleration if available (CUDA)

### YOLO model not found
- Ensure model paths are correct in `backend_processing.py`
- Download YOLOv8s: automatically downloaded on first run
- Custom model: update `CUSTOM_MODEL_PATH` to your model location

### GPT narration not working
- Add valid `OPENAI_API_KEY` to `.env`
- System will use fallback narration if key is missing

### Database errors
- Delete `instance/users.db` and restart to recreate tables
- Check file permissions on `instance/` folder

## License

MIT License - feel free to use and modify as needed.
