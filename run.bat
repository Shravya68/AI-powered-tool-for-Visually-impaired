@echo off
echo Starting Video Processing Web App...
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env file with your configuration before running again!
    pause
    exit /b
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask application...
python app.py
