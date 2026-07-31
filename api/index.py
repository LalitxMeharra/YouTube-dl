import os
from flask import Flask, request, jsonify, Response
import yt_dlp
import requests

import shutil

app = Flask(__name__)

BUNDLED_COOKIES = os.path.join(os.path.dirname(__file__), 'cookies.txt')
# Vercel's project directory is read-only at runtime (only /tmp is writable).
# yt-dlp needs to write back to the cookie jar after use, so we copy the
# bundled cookies file into /tmp on cold start and point yt-dlp there.
COOKIES_PATH = '/tmp/cookies.txt'

if os.path.exists(BUNDLED_COOKIES) and not os.path.exists(COOKIES_PATH):
    shutil.copy(BUNDLED_COOKIES, COOKIES_PATH)

# Logged-in cookies are what actually gets past YouTube's bot-check on
# datacenter IPs (Vercel). Note: android/ios client spoofing is NOT used
# here because yt-dlp skips those clients entirely when cookies are set
# ("does not support cookies"), which left us with zero usable formats.
# format='best' picks a single progressive stream so no ffmpeg merge step
# is needed (Vercel has no ffmpeg binary available).
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'format': 'best',
}

if os.path.exists(COOKIES_PATH):
    YDL_OPTS['cookiefile'] = COOKIES_PATH


@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.get_json() or {}
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'URL enter karein!'}), 400

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception as e:
        return jsonify({'error': f'Video info fetch nahi ho saki: {str(e)}'}), 400

    title = info.get('title', 'YouTube Media')
    duration = info.get('duration_string') or str(info.get('duration', ''))

    video_formats = []
    audio_formats = []
    seen_video_res = set()
    seen_audio_abr = set()

    for f in info.get('formats', []):
        dl_url = f.get('url')
        if not dl_url:
            continue

        has_video = f.get('vcodec') not in (None, 'none')
        has_audio = f.get('acodec') not in (None, 'none')

        # Progressive (video+audio together) formats only — these download
        # directly in-browser without needing server-side ffmpeg merging.
        if has_video and has_audio:
            quality = f.get('format_note') or f"{f.get('height', '?')}p"
            if quality in seen_video_res:
                continue
            seen_video_res.add(quality)
            filename = f"{title} ({quality}).mp4"
            video_formats.append({
                'quality': quality,
                'height': f.get('height') or 0,
                'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
            })
        elif has_audio and not has_video:
            abr = f.get('abr') or 0
            label = f"{int(abr)}kbps" if abr else 'Audio'
            if label in seen_audio_abr:
                continue
            seen_audio_abr.add(label)
            filename = f"{title} ({label}).m4a"
            audio_formats.append({
                'quality': label,
                'abr': abr,
                'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
            })

    video_formats.sort(key=lambda x: x['height'], reverse=True)
    audio_formats.sort(key=lambda x: x['abr'], reverse=True)

    return jsonify({
        'title': title,
        'duration': duration,
        'preview_url': video_formats[0]['download_url'] if video_formats else '',
        'video_formats': video_formats,
        'audio_formats': audio_formats[:5]
    })


@app.route('/api/download', methods=['GET'])
def force_download():
    media_url = request.args.get('url')
    filename = request.args.get('filename', 'download.mp4')

    if not media_url:
        return "Missing URL", 400

    try:
        req = requests.get(media_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": req.headers.get("Content-Type", "application/octet-stream")
        }
        return Response(req.iter_content(chunk_size=1024 * 1024), headers=headers)
    except Exception as e:
        return str(e), 500


def handler(request, response):
    return app(request, response)
