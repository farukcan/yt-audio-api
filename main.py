"""
main.py
Developed by Alperen Sümeroğlu - YouTube Audio Converter API
Clean, modular Flask-based backend for downloading and serving YouTube audio tracks.
Utilizes yt-dlp and FFmpeg for conversion and token-based access management.
"""

import secrets
import threading
from flask import Flask, request, jsonify, send_from_directory
from uuid import uuid4
from pathlib import Path
import yt_dlp
import access_manager
import job_manager
import transcriber
from constants import *

# Initialize the Flask application
app = Flask(__name__)


@app.route("/", methods=["GET"])
def handle_audio_request():
    """
    Main endpoint to receive a YouTube video URL, download the audio in MP3 format,
    and return a unique token for accessing the file later.

    Query Parameters:
        - url (str): Full YouTube video URL.

    Returns:
        - JSON: {"token": <download_token>}
    """
    video_url = request.args.get("url")
    if not video_url:
        return jsonify(error="Missing 'url' parameter in request."), BAD_REQUEST

    try:
        filename = _download_audio(video_url)
    except Exception as e:
        return jsonify(error="Failed to download or convert audio.", detail=str(e)), INTERNAL_SERVER_ERROR

    return _generate_token_response(filename)


def _download_audio(video_url: str) -> str:
    """
    Downloads the best audio track of a YouTube URL and converts it to MP3.

    Args:
        video_url (str): Full YouTube video URL.

    Returns:
        str: The generated "<uuid>.mp3" filename inside the downloads directory.
    """
    # Use an extension-less output template so the FFmpegExtractAudio
    # postprocessor produces exactly "<uuid>.mp3" (avoids a ".mp3.mp3" name).
    file_id = uuid4()
    filename = f"{file_id}.mp3"
    output_template = str(Path(ABS_DOWNLOADS_PATH) / str(file_id))

    # yt-dlp configuration for downloading best audio and converting to mp3
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return filename


@app.route("/download", methods=["GET"])
def download_audio():
    """
    Endpoint to serve an audio file associated with a given token.
    If token is valid and not expired, returns the associated MP3 file.

    Query Parameters:
        - token (str): Unique access token

    Returns:
        - MP3 audio file as attachment or error JSON
    """
    token = request.args.get("token")
    if not token:
        return jsonify(error="Missing 'token' parameter in request."), BAD_REQUEST

    if not access_manager.has_access(token):
        return jsonify(error="Token is invalid or unknown."), UNAUTHORIZED

    if not access_manager.is_valid(token):
        return jsonify(error="Token has expired."), REQUEST_TIMEOUT

    filename = access_manager.get_audio_file(token)
    if not (Path(ABS_DOWNLOADS_PATH) / filename).is_file():
        return jsonify(error="Requested file could not be found on the server."), NOT_FOUND

    return send_from_directory(ABS_DOWNLOADS_PATH, filename, as_attachment=True)


@app.route("/transcript", methods=["GET"])
def start_transcript():
    """
    Starts an asynchronous transcription job for a YouTube URL.
    Downloads the audio, isolates vocals, and transcribes them in the
    background; returns a job id to poll for the result.

    Query Parameters:
        - url (str): Full YouTube video URL.
        - lang (str, optional): Whisper language code (default: DEFAULT_LANGUAGE).

    Returns:
        - JSON: {"job": <job_id>}
    """
    video_url = request.args.get("url")
    if not video_url:
        return jsonify(error="Missing 'url' parameter in request."), BAD_REQUEST

    language = request.args.get("lang") or DEFAULT_LANGUAGE
    job_id = job_manager.create_job()

    worker = threading.Thread(
        target=_run_transcript_job,
        args=(job_id, video_url, language),
        daemon=True
    )
    worker.start()

    return jsonify(job=job_id)


@app.route("/transcript/status", methods=["GET"])
def transcript_status():
    """
    Returns the status and, once ready, the result of a transcription job.

    Query Parameters:
        - job (str): Job id returned by /transcript.

    Returns:
        - JSON: {"status": "processing"}
                {"status": "done", "srt": <str>, "segments": [...]}
                {"status": "error", "error": <str>}

    A finished job (done or error) is delivered once and then evicted.
    """
    job_id = request.args.get("job")
    if not job_id:
        return jsonify(error="Missing 'job' parameter in request."), BAD_REQUEST

    job = job_manager.get_job(job_id)
    if job is None:
        return jsonify(error="Job is invalid or unknown."), NOT_FOUND

    if job['status'] == job_manager.STATUS_ERROR:
        job_manager.remove_job(job_id)
        return jsonify(status=job_manager.STATUS_ERROR, error=job['error']), INTERNAL_SERVER_ERROR

    if job['status'] == job_manager.STATUS_PROCESSING:
        return jsonify(status=job_manager.STATUS_PROCESSING)

    job_manager.remove_job(job_id)
    return jsonify(
        status=job_manager.STATUS_DONE,
        srt=job['result']['srt'],
        segments=job['result']['segments']
    )


def _run_transcript_job(job_id: str, video_url: str, language: str) -> None:
    """
    Background worker that downloads audio and transcribes it, recording
    the outcome in the job registry.

    Args:
        job_id (str): The job id to update.
        video_url (str): Full YouTube video URL.
        language (str): Whisper language code.
    """
    audio_path = None
    try:
        filename = _download_audio(video_url)
        audio_path = Path(ABS_DOWNLOADS_PATH) / filename
        result = transcriber.transcribe_audio(audio_path, language)
        job_manager.set_result(job_id, result)
    except Exception as e:
        job_manager.set_error(job_id, str(e))
    finally:
        # The transcript mp3 is transient (not token-managed), so remove it.
        if audio_path is not None:
            audio_path.unlink(missing_ok=True)


def _generate_token_response(filename: str):
    """
    Generates a secure download token for a given filename,
    registers it in the access manager, and returns the token as JSON.

    Args:
        filename (str): The name of the downloaded MP3 file

    Returns:
        JSON: {"token": <generated_token>}
    """
    token = secrets.token_urlsafe(TOKEN_LENGTH)
    access_manager.add_token(token, filename)
    return jsonify(token=token)


def main():
    """
    Starts the background thread for automatic token cleanup
    and launches the Flask development server.
    """
    token_cleaner_thread = threading.Thread(
        target=access_manager.manage_tokens,
        daemon=True
    )
    token_cleaner_thread.start()
    app.run(debug=True)


if __name__ == "__main__":
    main()
