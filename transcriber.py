"""
transcriber.py

Transcription pipeline: isolate vocals from music/noise with demucs,
then transcribe the vocal track with mlx-whisper (Apple Silicon).
Returns timestamped segments and an SRT rendering.
"""

import shutil
import subprocess
import sys
from pathlib import Path
import mlx_whisper
from constants import WHISPER_MODEL, DEMUCS_MODEL, ABS_SEPARATED_PATH, DEMUCS_TIMEOUT_SECONDS


def separate_vocals(audio_path: Path) -> Path:
    """
    Runs demucs two-stem separation to isolate vocals from the mix.

    Args:
        audio_path (Path): Path to the source audio file.

    Returns:
        Path: Path to the produced vocals.wav file.

    Raises:
        RuntimeError: If demucs fails or times out.
        FileNotFoundError: If the expected vocals file is not produced.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, '-m', 'demucs',
                '--two-stems=vocals',
                '-o', ABS_SEPARATED_PATH,
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=DEMUCS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"demucs timed out after {DEMUCS_TIMEOUT_SECONDS}s")
    if result.returncode != 0:
        raise RuntimeError(f"demucs failed: {result.stderr.strip()}")

    vocals_path = Path(ABS_SEPARATED_PATH) / DEMUCS_MODEL / audio_path.stem / 'vocals.wav'
    if not vocals_path.is_file():
        raise FileNotFoundError(f"Vocals file not produced: {vocals_path}")
    return vocals_path


def transcribe_audio(audio_path: Path, language: str) -> dict:
    """
    Isolates vocals then transcribes them with mlx-whisper.

    Args:
        audio_path (Path): Path to the source audio file.
        language (str): Whisper language code (e.g. "tr", "en").

    Returns:
        dict: {"segments": [{start, end, text}], "srt": str}
    """
    vocals_path = separate_vocals(audio_path)
    try:
        result = mlx_whisper.transcribe(
            str(vocals_path),
            path_or_hf_repo=WHISPER_MODEL,
            language=language,
        )
    finally:
        # Remove the per-file demucs output (vocals.wav + no_vocals.wav).
        shutil.rmtree(vocals_path.parent, ignore_errors=True)

    segments = [
        {
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip(),
        }
        for segment in result['segments']
    ]
    return {'segments': segments, 'srt': _build_srt(segments)}


def _format_srt_timestamp(seconds: float) -> str:
    """
    Formats a timestamp in seconds as SRT time (HH:MM:SS,mmm).

    Args:
        seconds (float): Timestamp in seconds.

    Returns:
        str: SRT-formatted timestamp.
    """
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _build_srt(segments: list) -> str:
    """
    Renders transcription segments as an SRT document.

    Args:
        segments (list): List of {start, end, text} dicts.

    Returns:
        str: SRT-formatted subtitle text.
    """
    blocks = []
    for index, segment in enumerate(segments, start=1):
        start = _format_srt_timestamp(segment['start'])
        end = _format_srt_timestamp(segment['end'])
        blocks.append(f"{index}\n{start} --> {end}\n{segment['text']}")
    return "\n\n".join(blocks) + "\n"
