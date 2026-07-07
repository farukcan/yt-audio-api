"""
constants.py

Central configuration module for YouTube Audio Converter API.
Defines paths, token settings, and HTTP response codes.

Crafted with precision by Alperen Sümeroğlu — powering clean and configurable logic.
"""

import os
from pathlib import Path

# --- Directory Configurations ---
ROOT_DIRECTORY = Path(__file__).resolve().parent
DOWNLOADS_DIRECTORY = 'downloads'
ABS_DOWNLOADS_PATH = str(ROOT_DIRECTORY / DOWNLOADS_DIRECTORY)
SEPARATED_DIRECTORY = 'separated'
ABS_SEPARATED_PATH = str(ROOT_DIRECTORY / SEPARATED_DIRECTORY)

# --- HTTP Response Codes ---
REQUEST_TIMEOUT = 408       # Used when token is expired
UNAUTHORIZED = 401          # Used when token is invalid
NOT_FOUND = 404             # File not found on server
BAD_REQUEST = 400           # Missing parameters in request
INTERNAL_SERVER_ERROR = 500 # Fallback for unexpected server errors

# --- Token Settings ---
EXPIRY_TIME_MINUTES = 5     # Token expiration duration in minutes
TOKEN_LENGTH = 20           # Length of generated token (in characters)

# --- Transcription Settings ---
WHISPER_MODEL = 'mlx-community/whisper-large-v3-mlx'  # mlx-whisper model repo
DEMUCS_MODEL = 'htdemucs'                             # Demucs separation model
DEFAULT_LANGUAGE = 'tr'                               # Default transcription language
DEMUCS_TIMEOUT_SECONDS = 1800                         # Max wall time for vocal separation