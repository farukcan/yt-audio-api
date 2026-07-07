"""
job_manager.py

In-memory async job registry for the transcription pipeline.
Transcription (vocal separation + Whisper) is long-running, so requests
start a background job and poll its status by job id.
"""

import threading
from uuid import uuid4

# Job status values exposed to API clients
STATUS_PROCESSING = 'processing'
STATUS_DONE = 'done'
STATUS_ERROR = 'error'

# Maps job id -> {"status": str, "result": dict | None, "error": str | None}
_jobs = {}

# Guards concurrent access from the request thread and worker threads
_lock = threading.Lock()


def create_job() -> str:
    """
    Registers a new job in the processing state and returns its id.

    Returns:
        str: The generated job id.
    """
    job_id = str(uuid4())
    with _lock:
        _jobs[job_id] = {'status': STATUS_PROCESSING, 'result': None, 'error': None}
    return job_id


def set_result(job_id: str, result: dict) -> None:
    """
    Marks a job as done and stores its transcription result.

    Args:
        job_id (str): The job id.
        result (dict): The transcription result payload.
    """
    with _lock:
        _jobs[job_id] = {'status': STATUS_DONE, 'result': result, 'error': None}


def set_error(job_id: str, error: str) -> None:
    """
    Marks a job as failed and stores the error message.

    Args:
        job_id (str): The job id.
        error (str): Human-readable error description.
    """
    with _lock:
        _jobs[job_id] = {'status': STATUS_ERROR, 'result': None, 'error': error}


def get_job(job_id: str) -> dict:
    """
    Retrieves the current state of a job.

    Args:
        job_id (str): The job id.

    Returns:
        dict: The job state, or None if the id is unknown.
    """
    with _lock:
        return _jobs.get(job_id)


def remove_job(job_id: str) -> None:
    """
    Drops a job from the registry so finished results are not retained
    for the process lifetime (results are delivered once, then evicted).

    Args:
        job_id (str): The job id.
    """
    with _lock:
        _jobs.pop(job_id, None)
