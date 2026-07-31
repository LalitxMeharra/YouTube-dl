import re
from flask import Flask, request, jsonify, Response
import yt_dlp
import requests

app = Flask(__name__)

# ---------------------------------------------------------------------------
# yt-dlp setup — no cookies needed, plain extraction works fine
# ---------------------------------------------------------------------------
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
}


def clean_name(text):
    """Sanitize a string for safe use as a filename."""
    text = re.sub(r'[\\/:*?"<>|]', '', text or 'media')
    text = text.strip()
    return text[:80] if len(text) > 80 else text


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

    raw_title = info.get('title', 'YouTube Media')
    title = clean_name(raw_title)
    duration = info.get('duration_string') or ''
    thumbnail = info.get('thumbnail', '')

    video_formats = []
    audio_formats = []
    seen_video_res = set()
    seen_audio_abr = set()
    best_preview_url = ''
    best_height = -1

    for f in info.get('formats', []):
        dl_url = f.get('url')
        if not dl_url:
            continue

        has_video = f.get('vcodec') not in (None, 'none')
        has_audio = f.get('acodec') not in (None, 'none')

        if has_video and has_audio:
            height = f.get('height') or 0
            quality = f"{height}p" if height else (f.get('format_note') or 'SD')
            if quality in seen_video_res:
                continue
            seen_video_res.add(quality)

            filename = f"{title} ({quality}).mp4"
            video_formats.append({
                'quality': quality,
                'height': height,
                'filename': filename,
                'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
            })

            # Highest-res progressive stream = live preview source
            if height > best_height:
                best_height = height
                best_preview_url = dl_url

        elif has_audio and not has_video:
            abr = f.get('abr') or 0
            label = f"{int(abr)}kbps" if abr else 'Audio'
            if label in seen_audio_abr:
                continue
            seen_audio_abr.add(label)

            filename = f"{title} ({label}).mp3"
            audio_formats.append({
                'quality': label,
                'abr': abr,
                'filename': filename,
                'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
            })

    video_formats.sort(key=lambda x: x['height'], reverse=True)
    audio_formats.sort(key=lambda x: x['abr'], reverse=True)

    return jsonify({
        'title': raw_title,
        'duration': duration,
        'thumbnail': thumbnail,
        'preview_url': best_preview_url,
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
            # attachment = browser saves the file directly, never opens
            # a tab / built-in viewer for it.
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/octet-stream",
        }
        content_length = req.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length
        return Response(req.iter_content(chunk_size=1024 * 1024), headers=headers)
    except Exception as e:
        return str(e), 500


def handler(request, response):
    return app(request, response)
