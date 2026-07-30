from flask import Flask, request, jsonify, Response
import requests

app = Flask(__name__)

# RapidAPI Credentials extracted from screenshot
RAPIDAPI_KEY = "cfbbce34b8msh41bce2b6fe55e64p10868cjsn75c3fee35761"
RAPIDAPI_HOST = "youtube-mp3-audio-video-downloader.p.rapidapi.com"

@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.get_json() or {}
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'URL enter karein!'}), 400

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:
        # Requesting Video Information from API
        response = requests.get(
            f"https://{RAPIDAPI_HOST}/get_video_information",
            params={"url": video_url},
            headers=headers
        )
        res_data = response.json()

        # Check for errors from API
        if response.status_code != 200 or res_data.get('error'):
            return jsonify({'error': res_data.get('message', 'Video info fetch nahi ho saki!')}), 400

        title = res_data.get('title', 'YouTube Media')
        duration = res_data.get('duration', 'Media Stream')

        video_formats = []
        audio_formats = []

        # Parse Videos
        for item in res_data.get('formats', []):
            dl_url = item.get('url')
            if not dl_url:
                continue

            quality = item.get('qualityLabel') or f"{item.get('height', '720')}p"
            is_audio_only = item.get('mimeType', '').startswith('audio/') or item.get('vcodec') == 'none'

            if not is_audio_only:
                filename = f"{title} ({quality}).mp4"
                video_formats.append({
                    'quality': quality,
                    'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
                })
            else:
                filename = f"{title} (Audio).mp3"
                audio_formats.append({
                    'quality': item.get('audioQuality', 'HQ Audio'),
                    'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(filename)}"
                })

        # Fallback if specific formats mapping is empty
        if not video_formats and res_data.get('downloadUrl'):
            dl_url = res_data.get('downloadUrl')
            video_formats.append({
                'quality': 'Best Quality MP4',
                'download_url': f"/api/download?url={requests.utils.quote(dl_url)}&filename={requests.utils.quote(title + '.mp4')}"
            })

        return jsonify({
            'title': title,
            'duration': duration,
            'preview_url': video_formats[0]['download_url'] if video_formats else '',
            'video_formats': video_formats,
            'audio_formats': audio_formats if audio_formats else [{'quality': 'High Quality MP3', 'download_url': f"/api/download?url={requests.utils.quote(res_data.get('downloadUrl', ''))}&filename={requests.utils.quote(title + '.mp3')}"}]
        })

    except Exception as e:
        return jsonify({'error': f"Server Error: {str(e)}"}), 500


@app.route('/api/download', methods=['GET'])
def force_download():
    media_url = request.args.get('url')
    filename = request.args.get('filename', 'download.mp4')

    if not media_url:
        return "Missing URL", 400

    try:
        req = requests.get(media_url, stream=True)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": req.headers.get("Content-Type", "application/octet-stream")
        }
        return Response(req.iter_content(chunk_size=1024*1024), headers=headers)
    except Exception as e:
        return str(e), 500

def handler(request, response):
    return app(request, response)
me)}"
                        })

            # Sort Video High to Low
            video_formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
            
            # Sort Audio High to Low
            audio_formats.sort(key=lambda x: int(x['quality'].split()[0]), reverse=True)

            return jsonify({
                'title': title,
                'duration': duration,
                'preview_url': preview_url,
                'video_formats': video_formats,
                'audio_formats': audio_formats[:5]
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Endpoint to force direct browser download instead of opening stream
@app.route('/api/download', methods=['GET'])
def force_download():
    media_url = request.args.get('url')
    filename = request.args.get('filename', 'download.mp4')

    if not media_url:
        return "Missing URL", 400

    try:
        # Stream response from source
        req = requests.get(media_url, stream=True)
        
        # Headers for forcing attachment download
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": req.headers.get("Content-Type", "application/octet-stream")
        }

        return Response(req.iter_content(chunk_size=1024*1024), headers=headers)
    except Exception as e:
        return str(e), 500

# Vercel entry point
def handler(request, response):
    return app(request, response)
                      
