import os
import shutil
from flask import Flask, request, jsonify, Response

import yt_dlp
import requests

app = Flask(__name__)

# ---------------------------------------------------------------------------
# yt-dlp setup
# ---------------------------------------------------------------------------
BUNDLED_COOKIES = os.path.join(os.path.dirname(__file__), 'cookies.txt')
# Vercel's project directory is read-only at runtime (only /tmp is writable).
# yt-dlp needs to write back to the cookie jar after use, so we copy the
# bundled cookies file into /tmp on cold start and point yt-dlp there.
COOKIES_PATH = '/tmp/cookies.txt'

if os.path.exists(BUNDLED_COOKIES) and not os.path.exists(COOKIES_PATH):
    shutil.copy(BUNDLED_COOKIES, COOKIES_PATH)

YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'format': 'best',
    # ios/tv/mweb are the clients most likely to still return a real,
    # direct file URL (many others got YouTube's SABR-only streaming lock
    # in 2026, which returns a link that only works through ffmpeg, not a
    # plain browser download).
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'tv', 'mweb'],
        }
    },
}

if os.path.exists(COOKIES_PATH):
    YDL_OPTS['cookiefile'] = COOKIES_PATH


# ---------------------------------------------------------------------------
# Frontend (single file — served directly by Flask, no /public folder)
# ---------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>StreamPulse | Ultimate Media Downloader</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #08090c;
            --card-bg: rgba(18, 20, 29, 0.75);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --text-main: #f1f5f9;
            --text-sub: #94a3b8;
            --radius-lg: 20px;
            --radius-md: 12px;
        }
        * {
            box-sizing: border-box; margin: 0; padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-user-select: none; user-select: none;
            -webkit-touch-callout: none;
        }
        body {
            background-color: var(--bg-color); color: var(--text-main);
            min-height: 100vh; display: flex; justify-content: center;
            align-items: center; padding: 20px; overflow-x: hidden; position: relative;
        }
        body::before {
            content: ''; position: absolute; top: -10%; left: 50%;
            transform: translateX(-50%); width: 400px; height: 400px;
            background: radial-gradient(circle, rgba(0,242,254,0.15) 0%, rgba(0,0,0,0) 70%);
            z-index: 0; pointer-events: none;
        }
        .container { width: 100%; max-width: 540px; z-index: 1; }
        .header { text-align: center; margin-bottom: 25px; }
        .header h1 {
            font-size: 28px; font-weight: 800;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .header p { color: var(--text-sub); font-size: 14px; margin-top: 4px; }
        .input-card {
            background: var(--card-bg); backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px); border: 1px solid var(--border-color);
            border-radius: var(--radius-lg); padding: 8px; display: flex;
            align-items: center; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            transition: border-color 0.3s ease;
        }
        .input-card:focus-within { border-color: var(--accent-cyan); box-shadow: 0 0 20px rgba(0, 242, 254, 0.2); }
        .input-card i { color: var(--text-sub); padding: 0 15px; font-size: 18px; }
        .input-card input {
            flex: 1; background: transparent; border: none; outline: none;
            color: #fff; font-size: 15px; -webkit-user-select: text; user-select: text;
        }
        .input-card input::placeholder { color: #475569; }
        .fetch-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            border: none; color: #000; font-weight: 700; padding: 12px 24px;
            border-radius: var(--radius-md); cursor: pointer;
            transition: transform 0.2s ease, filter 0.2s ease;
            display: flex; align-items: center; gap: 8px;
        }
        .fetch-btn:active { transform: scale(0.96); }
        .result-card {
            background: var(--card-bg); backdrop-filter: blur(16px);
            border: 1px solid var(--border-color); border-radius: var(--radius-lg);
            padding: 20px; margin-top: 20px; display: none; animation: fadeIn 0.4s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        .preview-container {
            width: 100%; border-radius: var(--radius-md); overflow: hidden;
            background: #000; border: 1px solid var(--border-color); position: relative;
        }
        .preview-container video { width: 100%; height: auto; max-height: 260px; display: block; object-fit: cover; }
        .video-title { font-size: 16px; font-weight: 700; margin: 15px 0 12px 0; line-height: 1.4; color: var(--text-main); }
        .tabs {
            display: flex; background: rgba(0, 0, 0, 0.4); padding: 4px;
            border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: 15px;
        }
        .tab-btn {
            flex: 1; padding: 10px; border: none; background: transparent;
            color: var(--text-sub); font-weight: 600; font-size: 14px; border-radius: 8px;
            cursor: pointer; transition: all 0.3s ease; display: flex;
            align-items: center; justify-content: center; gap: 8px;
        }
        .tab-btn.active { background: rgba(0, 242, 254, 0.15); color: var(--accent-cyan); border: 1px solid rgba(0, 242, 254, 0.3); }
        .format-list { display: none; flex-direction: column; gap: 10px; }
        .format-list.active { display: flex; }
        .format-item {
            background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color);
            padding: 12px 16px; border-radius: var(--radius-md); display: flex;
            justify-content: space-between; align-items: center; transition: background 0.2s ease;
        }
        .format-item:hover { background: rgba(255, 255, 255, 0.06); }
        .format-info { display: flex; flex-direction: column; }
        .format-quality { font-weight: 700; font-size: 14px; color: #fff; }
        .format-size { font-size: 12px; color: var(--text-sub); margin-top: 2px; }
        .dl-action-btn {
            background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 254, 0.3); padding: 8px 16px; border-radius: 8px;
            text-decoration: none; font-size: 13px; font-weight: 700;
            display: flex; align-items: center; gap: 6px; transition: all 0.2s ease;
        }
        .dl-action-btn:hover { background: var(--accent-cyan); color: #000; }
        .empty-msg { color: var(--text-sub); font-size: 13px; text-align: center; padding: 12px; }
        .loader { display: none; text-align: center; padding: 20px; color: var(--accent-cyan); }
        .loader i { font-size: 24px; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body oncontextmenu="return false;">
    <div class="container">
        <div class="header">
            <h1>STREAMPULSE</h1>
            <p>Fast High-Quality Media Downloader</p>
        </div>
        <div class="input-card">
            <i class="fa-solid fa-link"></i>
            <input type="text" id="videoUrl" placeholder="Paste YouTube Link here..." autocomplete="off">
            <button class="fetch-btn" onclick="processFetch()">
                <i class="fa-solid fa-bolt"></i> Fetch
            </button>
        </div>
        <div class="loader" id="loader">
            <i class="fa-solid fa-circle-notch"></i>
            <p style="margin-top: 8px; font-size: 13px;">Extracting formats...</p>
        </div>
        <div class="result-card" id="resultCard">
            <div class="preview-container">
                <video id="videoPreview" controls poster="" playsinline preload="metadata">
                    <source id="videoSource" src="" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            <h3 class="video-title" id="videoTitle">Sample Video Title</h3>
            <div class="tabs">
                <button class="tab-btn active" id="videoTabBtn" onclick="switchTab('video')">
                    <i class="fa-solid fa-video"></i> Video
                </button>
                <button class="tab-btn" id="audioTabBtn" onclick="switchTab('audio')">
                    <i class="fa-solid fa-music"></i> Audio
                </button>
            </div>
            <div class="format-list active" id="videoFormats"></div>
            <div class="format-list" id="audioFormats"></div>
        </div>
    </div>
    <script>
        document.addEventListener('contextmenu', event => event.preventDefault());

        function switchTab(type) {
            const vBtn = document.getElementById('videoTabBtn');
            const aBtn = document.getElementById('audioTabBtn');
            const vList = document.getElementById('videoFormats');
            const aList = document.getElementById('audioFormats');
            if (type === 'video') {
                vBtn.classList.add('active'); aBtn.classList.remove('active');
                vList.classList.add('active'); aList.classList.remove('active');
            } else {
                aBtn.classList.add('active'); vBtn.classList.remove('active');
                aList.classList.add('active'); vList.classList.remove('active');
            }
        }

        async function processFetch() {
            const urlInput = document.getElementById('videoUrl').value;
            if (!urlInput) return alert('Pehle YouTube URL enter karein!');

            const loader = document.getElementById('loader');
            const resultCard = document.getElementById('resultCard');
            loader.style.display = 'block';
            resultCard.style.display = 'none';

            try {
                const response = await fetch('/api/get-info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlInput })
                });
                const data = await response.json();

                if (data.error) {
                    alert("Error: " + data.error);
                    loader.style.display = 'none';
                    return;
                }

                loader.style.display = 'none';
                resultCard.style.display = 'block';
                document.getElementById('videoTitle').innerText = data.title;

                const videoPlayer = document.getElementById('videoPreview');
                const videoSrc = document.getElementById('videoSource');
                if (data.preview_url) {
                    videoSrc.src = data.preview_url;
                    videoPlayer.load();
                }

                const vContainer = document.getElementById('videoFormats');
                vContainer.innerHTML = '';
                if (data.video_formats.length === 0) {
                    vContainer.innerHTML = '<div class="empty-msg">Koi video format nahi mila.</div>';
                }
                data.video_formats.forEach(f => {
                    vContainer.innerHTML += `
                        <div class="format-item">
                            <div class="format-info">
                                <span class="format-quality">${f.quality}</span>
                                <span class="format-size">MP4 Video</span>
                            </div>
                            <a href="${f.download_url}" class="dl-action-btn">
                                <i class="fa-solid fa-download"></i> Download
                            </a>
                        </div>
                    `;
                });

                const aContainer = document.getElementById('audioFormats');
                aContainer.innerHTML = '';
                if (data.audio_formats.length === 0) {
                    aContainer.innerHTML = '<div class="empty-msg">Koi audio format nahi mila.</div>';
                }
                data.audio_formats.forEach(f => {
                    aContainer.innerHTML += `
                        <div class="format-item">
                            <div class="format-info">
                                <span class="format-quality">${f.quality}</span>
                                <span class="format-size">Audio</span>
                            </div>
                            <a href="${f.download_url}" class="dl-action-btn">
                                <i class="fa-solid fa-download"></i> Download
                            </a>
                        </div>
                    `;
                });
            } catch (err) {
                alert("Failed to fetch media details!");
                loader.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def home():
    return Response(INDEX_HTML, mimetype='text/html')


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
