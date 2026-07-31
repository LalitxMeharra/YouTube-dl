from flask import Flask, render_template_string, request, jsonify
import yt_dlp

app = Flask(__name__)

HTML_CODE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YT Media Downloader</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 600px; 
            margin: 20px auto; 
            padding: 20px; 
            background-color: #121212; 
            color: #fff; 
        }
        .input-group { 
            display: flex; 
            gap: 10px; 
            margin-bottom: 20px; 
        }
        input[type="text"] { 
            flex: 1; 
            padding: 12px; 
            border-radius: 5px; 
            border: 1px solid #333; 
            background: #222; 
            color: #fff; 
            font-size: 14px;
        }
        button { 
            padding: 12px 20px; 
            border: none; 
            background: #ff0000; 
            color: #fff; 
            font-weight: bold; 
            border-radius: 5px; 
            cursor: pointer; 
        }
        .card { 
            background: #1e1e1e; 
            padding: 15px; 
            border-radius: 8px; 
            margin-top: 20px; 
            display: none; 
        }
        .card img { 
            width: 100%; 
            border-radius: 6px; 
        }
        .section-title {
            margin-top: 15px;
            font-size: 16px;
            color: #ff4757;
            border-bottom: 1px solid #333;
            padding-bottom: 5px;
        }
        .format-btn { 
            display: block; 
            background: #0088cc; 
            color: #fff; 
            padding: 10px; 
            text-decoration: none; 
            border-radius: 4px; 
            margin: 8px 0; 
            font-size: 14px; 
            text-align: center;
        }
        .audio-btn {
            background: #2ed573;
        }
    </style>
</head>
<body>

    <h2>YouTube Downloader</h2>
    
    <div class="input-group">
        <input type="text" id="videoUrl" placeholder="YouTube URL yahan paste karein...">
        <button onclick="fetchMediaInfo()">Fetch</button>
    </div>

    <div id="resultCard" class="card">
        <img id="thumb" src="" alt="Thumbnail">
        <h3 id="videoTitle"></h3>
        <p>Duration: <span id="duration"></span></p>
        <hr>
        
        <div id="formatsList"></div>
    </div>

    <script>
        async function fetchMediaInfo() {
            const url = document.getElementById('videoUrl').value;
            const resultCard = document.getElementById('resultCard');
            const formatsList = document.getElementById('formatsList');
            
            if(!url) return alert("Pehle URL enter karein!");

            formatsList.innerHTML = "Loading available qualities...";
            resultCard.style.display = "block";

            try {
                const response = await fetch('/get-info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();

                if(data.error) {
                    alert("Error: " + data.error);
                    resultCard.style.display = "none";
                    return;
                }

                document.getElementById('thumb').src = data.thumbnail;
                document.getElementById('videoTitle').innerText = data.title;
                document.getElementById('duration').innerText = data.duration;

                formatsList.innerHTML = '';

                // Video Formats Section
                if(data.video_formats.length > 0) {
                    const vTitle = document.createElement('h4');
                    vTitle.className = 'section-title';
                    vTitle.innerText = "Video Quality (HD & Standard):";
                    formatsList.appendChild(vTitle);

                    data.video_formats.forEach(f => {
                        const btn = document.createElement('a');
                        btn.className = 'format-btn';
                        btn.href = f.url;
                        btn.target = '_blank';
                        btn.innerText = `Download Video (${f.quality} - ${f.ext.toUpperCase()})`;
                        formatsList.appendChild(btn);
                    });
                }

                // Audio Formats Section
                if(data.audio_formats.length > 0) {
                    const aTitle = document.createElement('h4');
                    aTitle.className = 'section-title';
                    aTitle.innerText = "Audio Formats:";
                    formatsList.appendChild(aTitle);

                    data.audio_formats.forEach(f => {
                        const btn = document.createElement('a');
                        btn.className = 'format-btn audio-btn';
                        btn.href = f.url;
                        btn.target = '_blank';
                        btn.innerText = `Download Audio (${f.quality} - ${f.ext.toUpperCase()})`;
                        formatsList.appendChild(btn);
                    });
                }

            } catch (err) {
                alert("Server Error ya Invalid URL!");
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_CODE)

@app.route('/get-info', methods=['POST'])
def get_info():
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'URL enter karein!'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            title = info.get('title', 'Video')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration_string', '')

            video_formats = []
            audio_formats = []
            seen_resolutions = set()

            for f in info.get('formats', []):
                # Video Formats (Extracting 1080p, 720p, 480p, 360p, etc.)
                if f.get('vcodec') != 'none':
                    height = f.get('height')
                    if height and height not in seen_resolutions:
                        seen_resolutions.add(height)
                        video_formats.append({
                            'ext': f.get('ext', 'mp4'),
                            'quality': f"{height}p",
                            'url': f.get('url')
                        })

                # Audio Formats
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    if f.get('abr'):
                        audio_formats.append({
                            'ext': f.get('ext', 'm4a'),
                            'quality': f"{round(f.get('abr'))} kbps",
                            'url': f.get('url')
                        })

            # High to Low resolution sorting
            video_formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)

            return jsonify({
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'video_formats': video_formats,
                'audio_formats': audio_formats[:4] # Top 4 audio qualities
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
