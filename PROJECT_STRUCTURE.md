# AI Vision - Project Structure

## Overview
AI Vision is a Flask-based web application that processes videos using AI to detect objects, estimate distances, generate natural language narrations, and produce synchronized audio-visual outputs.

## Directory Structure

```
AIVISION/
│
├── app_unified.py              # Main Flask application with routes and API endpoints
├── backend_processing.py       # AI processing pipeline (YOLO, GPT, TTS, video merging)
├── models.py                   # SQLAlchemy database models (User, Video)
├── requirements.txt            # Python package dependencies
├── run.bat                     # Windows batch script to launch the application
├── .env                        # Environment variables (API keys, secrets)
├── .env.example               # Template for environment variables
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html              # Base template with global styles and animations
│   ├── signup.html            # User registration page
│   ├── login.html             # User login page
│   ├── dashboard.html         # Main dashboard shell with navigation
│   ├── home.html              # Dashboard home content
│   ├── features.html          # Features showcase page
│   └── upload.html            # Video upload and processing interface
│
├── static/                     # Static assets (CSS, JavaScript)
│   ├── css/
│   │   ├── dashboard.css      # Dashboard-specific styles
│   │   └── styles.css         # Upload page and global styles
│   └── js/
│       ├── app.js             # Global JavaScript utilities and functions
│       ├── dashboard.js       # Dashboard interactions and animations
│       └── upload.js          # Video upload, processing, and results display
│
├── uploads/                    # Temporary storage for uploaded videos
│   └── [user_uploaded_videos]
│
├── processed_videos/           # Output directory for AI-processed videos
│   └── [ai_vision_*.mp4]
│
└── instance/                   # Flask instance folder
    └── users.db               # SQLite database file
```

## Core Components

### 1. Flask Application (`app_unified.py`)
- **Authentication Routes**: `/signup`, `/login`, `/logout`
- **Dashboard Routes**: `/dashboard`, `/dashboard/home`, `/dashboard/features`, `/dashboard/upload`
- **API Endpoints**:
  - `POST /api/upload-video` - Upload and process video
  - `GET /api/download/<video_id>` - Download processed video
  - `GET /api/videos` - List user's videos
  - `GET /api/session-check` - Check authentication status
- **Features**:
  - Session-based authentication
  - CORS support for cross-origin requests
  - File upload handling with size limits (500MB)
  - Database integration with SQLAlchemy

### 2. Backend Processing (`backend_processing.py`)
- **Object Detection**:
  - YOLOv8s (COCO dataset) for general objects
  - Custom YOLOv8 model for traffic-specific objects
  - Configurable confidence and IOU thresholds
- **Distance Estimation**:
  - Focal length calculation from camera FOV
  - Real-world dimension mapping for known objects
  - Ground-plane geometry for zebra crossings
  - EMA smoothing for stable readings
- **Narration Generation**:
  - GPT-3.5-turbo integration for natural language
  - Fallback rule-based narration
  - Scene summarization from detection data
- **Text-to-Speech**:
  - Facebook MMS-TTS model
  - Audio generation with speed adjustment
  - WAV format output
- **Video Merging**:
  - MoviePy for video/audio synchronization
  - Bounding box and label annotation
  - Speed adjustment to match narration duration

### 3. Database Models (`models.py`)
- **User Model**:
  - Fields: id, username, email, password (hashed), created_at
  - Relationship: One-to-many with Video
- **Video Model**:
  - Fields: id, filename, uploaded_at, processed, processed_path, narration, transcript, user_id
  - Relationship: Many-to-one with User

### 4. Frontend Templates

#### `base.html`
- Global layout with TailwindCSS
- Custom animations (gradient, fade-in, zoom-in, spinner)
- Flash message display
- Loads global JavaScript (`app.js`)

#### `dashboard.html`
- Navigation sidebar with sections
- Content area for dynamic page loading
- Animated background elements (blobs, glass shapes)

#### `upload.html`
- File upload interface with drag-and-drop
- Processing state with spinner and progress bar
- Results display with video player
- Error handling with retry button

### 5. Frontend JavaScript

#### `upload.js`
- File selection and validation
- Drag-and-drop functionality
- Video upload via Fetch API
- Processing state management
- Results display with video player
- Error handling and retry logic

#### `dashboard.js`
- CTA button interactions
- Drag-and-drop setup
- Reduced motion support
- Accessibility features (keyboard navigation, ARIA)

#### `app.js`
- Global utility functions
- Tab switching logic
- File upload handling
- Camera recording setup (legacy, not currently used)
- Processing and results display

## Data Flow

### Video Processing Flow
1. **User uploads video** → `upload.html` → `upload.js`
2. **POST to `/api/upload-video`** → `app_unified.py`
3. **Save to uploads/** → Create Video record in database
4. **Call `process_video_backend()`** → `backend_processing.py`
5. **AI Processing**:
   - Load YOLO models
   - Detect objects frame-by-frame
   - Estimate distances
   - Generate narration with GPT
   - Create TTS audio
   - Merge video and audio
6. **Save to processed_videos/** → Update Video record
7. **Return video URL** → `/api/download/<video_id>`
8. **Display results** → `upload.js` shows video player

### Authentication Flow
1. **User signs up** → `signup.html` → `POST /signup`
2. **Hash password** → Store in database
3. **User logs in** → `login.html` → `POST /login`
4. **Verify credentials** → Create session
5. **Access protected routes** → `@login_required` decorator checks session

## Configuration

### Environment Variables (`.env`)
```
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-your-openai-key-here
```

### Backend Configuration (`backend_processing.py`)
```python
# Model paths
CUSTOM_MODEL_PATH = "/path/to/custom/yolo/model.pt"
COCO_MODEL_PATH = "yolov8s.pt"

# Processing settings
TARGET_WIDTH, TARGET_HEIGHT = 960, 540
FRAME_SKIP = 1

# Detection thresholds
CONF_COCO, IOU_COCO = 0.35, 0.70
CONF_CUSTOM, IOU_CUSTOM = 0.30, 0.70

# Camera parameters
VFOV_DEG = 49.0
CAMERA_HEIGHT_M = 1.50

# Output directory
OUTPUT_DIR = "/content/AIVISION/processed_videos"
```

## Key Technologies

- **Backend**: Flask, SQLAlchemy, Flask-CORS
- **AI/ML**: YOLOv8 (Ultralytics), OpenAI GPT-3.5, Transformers (MMS-TTS)
- **Video Processing**: OpenCV, MoviePy
- **Frontend**: TailwindCSS, Vanilla JavaScript
- **Database**: SQLite
- **Authentication**: Werkzeug password hashing, Flask sessions

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- CSRF protection via Flask sessions
- File upload validation (type, size)
- Login required decorators for protected routes
- Secure file naming with `secure_filename()`

## Performance Optimizations

- Frame skipping for faster processing
- EMA smoothing for stable distance readings
- Model caching to avoid reloading
- Temporary file cleanup after processing
- Configurable video resolution
- GPU acceleration support (CUDA)

## Future Enhancements

- Real-time video streaming processing
- Multi-language TTS support
- Custom object training interface
- Video history and analytics dashboard
- Export options (JSON, CSV for detections)
- Mobile app integration
- Cloud storage integration (AWS S3, Google Cloud)
