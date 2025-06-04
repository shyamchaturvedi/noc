from flask import Flask, request, render_template_string, jsonify, send_file
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import re
import pandas as pd
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up file handler for logging
if not os.path.exists('logs'):
    os.makedirs('logs')
handler = RotatingFileHandler('logs/app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
logger.addHandler(handler)

# Create Flask app
app = Flask(__name__)

# Security configurations
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
)

class DataError(Exception):
    """Custom exception for data loading errors"""
    pass

def load_data(file_path):
    """Load and validate data from the specified file."""
    try:
        if not os.path.exists(file_path):
            raise DataError(f"Data file not found: {file_path}")
        
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) < 2:  # Need at least header + 1 data row
                raise DataError("Data file is empty or missing header")
            
            for line_num, line in enumerate(lines[1:], 2):  # skip header
                try:
                    parts = line.strip().split('\t')
                    if len(parts) < 6:
                        logger.warning(f"Invalid data format at line {line_num}")
                        continue
                    
                    record = {
                        "associate_name": parts[0].strip(),
                        "associate_id": parts[1].strip(),
                        "receiver_name": parts[2].strip(),
                        "form_status": parts[3].strip(),
                        "line_no": parts[4].strip(),
                        "set_no": parts[5].strip()
                    }
                    data.append(record)
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {str(e)}")
                    continue
        
        logger.info(f"Successfully loaded {len(data)} records")
        return data
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        raise DataError(f"Failed to load data: {str(e)}")

# Load data once when app starts
try:
    data = load_data('data.txt')
except DataError as e:
    logger.error(f"Critical error loading data: {str(e)}")
    data = []

# ... rest of your existing code ... 