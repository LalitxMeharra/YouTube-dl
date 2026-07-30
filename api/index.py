from flask import Flask, request, jsonify, Response
import yt_dlp
import requests

app = Flask(__name__)

@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.get_json() or {}
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'URL enter karein!'}), 400

    # YouTube Bot Protection Bypass Configuration
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        # iOS / Android app client simulate karne ke liye:
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            title = info.get('title', 'Media_File')
            duration = info.get('duration_string', '00:00')

            video_formats = []
            audio_formats = []
            seen_resolutions = set()

            preview_url = info.get('url', '')

            for f in info.get('formats', []):
                # Video Streams
                if f.get('vcodec') != 'none':
                    height = f.get('height')
                    if height and height not in seen_resolutions:
                        seen_resolutions.add(height)
                        raw_url = f.get('url')
                        quality_label = f"{height}p"
                        filename = f"{title} ({quality_label}).mp4"
                        
                        video_formats.append({
                            'ext': 'mp4',
                            'quality': quality_label,
                            'download_url': f"/api/download?url={requests.utils.quote(raw_url)}&filename={requests.utils.quote(filename)}"
                        })

                # Audio Streams
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if f.get('abr'):
                        raw_url = f.get('url')
                        bitrate = f"{round(f.get('abr'))} kbps"
                        filename = f"{title} ({bitrate}).mp3"

                        audio_formats.append({
                            'ext': 'mp3',
                            'quality': bitrate,
                            'download_url': f"/api/download?url={requests.utils.quote(raw_url)}&filename={requests.utils.quote(filename)}"
                        })

            # High to Low Sorting
            video_formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
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
                    height = f.get('height')
                    if height and height not in seen_resolutions:
                        seen_resolutions.add(height)
                        # Constructing direct download link via server proxy endpoint
                        raw_url = f.get('url')
                        quality_label = f"{height}p"
                        filename = f"{title} ({quality_label}).mp4"
                        
                        video_formats.append({
                            'ext': 'mp4',
                            'quality': quality_label,
                            'download_url': f"/api/download?url={requests.utils.quote(raw_url)}&filename={requests.utils.quote(filename)}"
                        })

                # Audio Streams Extraction
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if f.get('abr'):
                        raw_url = f.get('url')
                        bitrate = f"{round(f.get('abr'))} kbps"
                        filename = f"{title} ({bitrate}).mp3"

                        audio_formats.append({
                            'ext': 'mp3',
                            'quality': bitrate,
                            'download_url': f"/api/download?url={requests.utils.quote(raw_url)}&filename={requests.utils.quote(filename)}"
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
                      
