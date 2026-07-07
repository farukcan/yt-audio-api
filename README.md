# 🎧 YouTube Audio / Transcript Converter API
---

## 🍴 About This Fork

This is a fork of [alperensumeroglu/yt-audio-api](https://github.com/alperensumeroglu/yt-audio-api) that extends the original MP3 download API with a **speech-to-text pipeline** and a few fixes. What's different:

- **New: async transcription** — `/transcript` and `/transcript/status` endpoints isolate vocals with `demucs` and transcribe them with `mlx-whisper` (Apple Silicon), returning SRT + timestamped segments. See [Transcription](#-transcription-vocals--text).
- **New modules** — `transcriber.py` (demucs + whisper pipeline) and `job_manager.py` (thread-safe in-memory job registry for polling long-running jobs).
- **Fixed: double extension** — the yt-dlp output template produced `*.mp3.mp3` after FFmpeg post-processing; downloads are now named `<uuid>.mp3` correctly.
- **Fixed: Flask 3 compatibility** — `send_from_directory(..., filename=...)` was a Flask 1.x keyword; upgraded to the Flask 3 API with an explicit file-existence check.
- **Modernized dependencies** — `requirements.txt` moved from pinned Flask 1.1 (2020-era) to `Flask>=3.0`, adding `demucs`, `mlx-whisper`, and `torchcodec`.

Everything else — token-based MP3 download flow, expiry, cleanup — works as in the original.

---

## 📚 Table of Contents
1. [Features](#-features)
2. [Installation](#-installation)
3. [Example Usage](#-example-usage)
4. [API Endpoints](#-api-endpoints)
5. [Internals (How It Works)](#️-internals-how-it-works)
6. [Tech Stack](#-tech-stack)
7. [Ideal For](#-ideal-for)
8. [Author](#-author)
9. [Weekly Rewind](#-weekly-rewind-tech-ai--entrepreneurship)
10. [License](#-license)

---

## 🌟 Features
- 🔗 Accepts any public YouTube URL
- 🎵 Downloads best audio using `yt-dlp`
- ✨ Converts audio to high-quality `.mp3` via `FFmpeg`
- 🔐 Returns a one-time secure token to download the file
- ⏱️ Tokens expire automatically (default: 5 mins)
- 🧹 Expired files are auto-deleted (clean disk usage)
- 🚀 Built for fast local or cloud deployment

---

## 📦 Installation

### Requirements & Launch
Required packages are listed in [`requirements.txt`](./requirements.txt). To install all of them simply run:
```bash
pip install -r requirements.txt
```

Make sure FFmpeg is installed on your system:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

Clone and run the project:
```bash
git clone https://github.com/farukcan/yt-audio-api.git
cd yt-audio-api
python3 main.py
```

---

## 📗 Example Usage
### Step 1: Request Token
```
GET /?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
```
Response:
```json
{
  "token": "CGIroH6G-8JDL3DllsUhM6_CfYc"
}
```

### Step 2: Download Audio
```
GET /download?token=CGIroH6G-8JDL3DllsUhM6_CfYc
```
Result: `yourfile.mp3` will download automatically 🎶

---

## 📝 Transcription (Vocals → Text)

Beyond downloading, the API can transcribe a video's speech. It isolates
vocals from music and noise with **demucs**, then transcribes them with
**mlx-whisper** (`whisper-large-v3` on Apple Silicon). Because this takes
1–3 minutes, transcription runs as an **asynchronous job**: start it, then
poll for the result.

```mermaid
graph LR
    A[YouTube URL] --> B[yt-dlp: download mp3]
    B --> C[demucs: isolate vocals]
    C --> D[mlx-whisper: transcribe]
    D --> E[SRT + segment JSON]
```

### Step 1: Start a job
```
GET /transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&lang=tr
```
`lang` is optional (default: `tr`). Response:
```json
{ "job": "52ac9c65-6ed0-4a1c-ba9a-7607beef30d3" }
```

### Step 2: Poll for the result
```
GET /transcript/status?job=52ac9c65-6ed0-4a1c-ba9a-7607beef30d3
```
While running:
```json
{ "status": "processing" }
```
When ready:
```json
{
  "status": "done",
  "srt": "1\n00:00:00,000 --> 00:00:08,160\n...",
  "segments": [ { "start": 0.0, "end": 8.16, "text": "..." } ]
}
```
On failure, `status` is `"error"` with an `error` message (HTTP 500).

> ⚠️ Transcription requires **Apple Silicon** (mlx-whisper). The first run
> downloads the Whisper (~3 GB) and demucs (~300 MB) models.

---

## 🔄 API Endpoints
| Method | Route                 | Description                                                    |
|--------|-----------------------|----------------------------------------------------------------|
| GET    | `/`                   | Accepts `?url=<video_url>`, returns download token             |
| GET    | `/download`           | Accepts `?token=<token>`, returns audio file                   |
| GET    | `/transcript`         | Accepts `?url=<video_url>&lang=<code>`, starts a job, returns `job` id |
| GET    | `/transcript/status`  | Accepts `?job=<job_id>`, returns job status and result         |

---

## ⚖️ Internals (How It Works)
- Downloads audio using `yt-dlp`
- Converts it to `.mp3` using FFmpeg (192kbps)
- Stores audio in `/downloads` directory
- Generates expiring token for each file
- A background daemon removes expired tokens/files
- For transcription: isolates vocals with `demucs`, transcribes with `mlx-whisper`,
  and tracks each request as an in-memory async job

---

## 📊 Tech Stack
- Python 3.11+
- Flask 3.x
- yt-dlp
- FFmpeg
- demucs (vocal separation)
- mlx-whisper (Apple Silicon transcription)

---

## 🤝 Ideal For
- Developers building podcast/audio/subtitle tools
- Automation pipelines for archiving
- Students & hobbyists learning API development

---

MIT License — free for personal and commercial use.
