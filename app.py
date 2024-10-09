import os
import sys
import socket
from flask import Flask, render_template_string, request, send_file
from pytube import YouTube
from moviepy.editor import AudioFileClip
import requests
import io

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    version = sys.version_info
    env = os.getenv('ENV', 'Development')
    hostname = socket.gethostname()

    if request.method == 'POST':
        link = request.form.get('youtube_link')
        if 'youtube.com/watch' in link or 'youtu.be/' in link:
            try:
                yt = YouTube(link)
                video_title = yt.title
                thumbnail_url = yt.thumbnail_url
                resolutions = ['144p', '240p', '360p', '480p', '540p', '720p', '720p60', '920p', '1080p', '1080p60']
                download_options = []

                for res in resolutions:
                    stream = yt.streams.filter(res=res.replace('60', ''), fps=60 if '60' in res else None, file_extension='mp4').first()
                    if stream:
                        size = round(stream.filesize / (1024 * 1024), 2)
                        download_options.append({
                            'resolution': res,
                            'size': size,
                            'itag': stream.itag
                        })

                audio_stream = yt.streams.filter(only_audio=True).first()
                if audio_stream:
                    audio_size = round(audio_stream.filesize / (1024 * 1024), 2)
                    download_options.append({
                        'resolution': 'Audio (320kbps MP3)',
                        'size': audio_size,
                        'itag': audio_stream.itag
                    })

                return render_template_string(HTML_TEMPLATE, 
                    version=f"{version.major}.{version.minor}.{version.micro}",
                    env=env,
                    hostname=hostname,
                    video_title=video_title,
                    thumbnail_url=thumbnail_url,
                    download_options=download_options
                )
            except Exception as e:
                error_message = f"Error processing video. Please check the link and try again. Error: {str(e)}"
                return render_template_string(HTML_TEMPLATE, 
                    version=f"{version.major}.{version.minor}.{version.micro}",
                    env=env,
                    hostname=hostname,
                    error_message=error_message
                )
        else:
            error_message = "Invalid YouTube link. Please enter a valid YouTube video URL."
            return render_template_string(HTML_TEMPLATE, 
                version=f"{version.major}.{version.minor}.{version.micro}",
                env=env,
                hostname=hostname,
                error_message=error_message
            )

    return render_template_string(HTML_TEMPLATE, 
        version=f"{version.major}.{version.minor}.{version.micro}",
        env=env,
        hostname=hostname
    )

@app.route("/download", methods=['POST'])
def download():
    link = request.form.get('link')
    itag = request.form.get('itag')
    is_audio = request.form.get('is_audio') == 'true'

    try:
        yt = YouTube(link)
        stream = yt.streams.get_by_itag(itag)
        
        if is_audio:
            buffer = io.BytesIO()
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            
            audio = AudioFileClip(buffer)
            audio_buffer = io.BytesIO()
            audio.write_audiofile(audio_buffer, codec='libmp3lame', bitrate='320k')
            audio_buffer.seek(0)
            
            return send_file(
                audio_buffer,
                as_attachment=True,
                download_name=f"{yt.title}.mp3",
                mimetype="audio/mpeg"
            )
        else:
            buffer = io.BytesIO()
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=stream.default_filename,
                mimetype="video/mp4"
            )
    except Exception as e:
        return f"Error downloading: {str(e)}", 400

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        h1 {
            color: #e74c3c;
        }
        form {
            background-color: #fff;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        input[type="submit"] {
            background-color: #e74c3c;
            color: #fff;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 3px;
        }
        input[type="submit"]:hover {
            background-color: #c0392b;
        }
        .error {
            color: #e74c3c;
            font-weight: bold;
        }
        .video-info {
            background-color: #fff;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            margin-top: 20px;
        }
        .video-info img {
            max-width: 100%;
            height: auto;
            margin-bottom: 10px;
        }
        .download-options {
            list-style-type: none;
            padding: 0;
        }
        .download-options li {
            margin-bottom: 10px;
        }
        .download-button {
            background-color: #3498db;
            color: #fff;
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 3px;
            text-decoration: none;
            display: inline-block;
        }
        .download-button:hover {
            background-color: #2980b9;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            font-size: 0.9em;
            color: #777;
        }
    </style>
</head>
<body>
    <h1>YouTube Downloader</h1>
    <form method="post">
        <input type="text" name="youtube_link" placeholder="Enter YouTube video URL" required>
        <input type="submit" value="Get Download Options">
    </form>
    
    {% if error_message %}
    <p class="error">{{ error_message }}</p>
    {% endif %}
    
    {% if video_title %}
    <div class="video-info">
        <h2>{{ video_title }}</h2>
        <img src="{{ thumbnail_url }}" alt="Video Thumbnail">
        <h3>Download Options:</h3>
        <ul class="download-options">
            {% for option in download_options %}
            <li>
                <form action="/download" method="post">
                    <input type="hidden" name="link" value="{{ request.form.youtube_link }}">
                    <input type="hidden" name="itag" value="{{ option.itag }}">
                    <input type="hidden" name="is_audio" value="{{ 'true' if option.resolution == 'Audio (320kbps MP3)' else 'false' }}">
                    <button type="submit" class="download-button">
                        Download {{ option.resolution }} ({{ option.size }} MB)
                    </button>
                </form>
            </li>
            {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    <div class="footer">
        <p>Running Python: {{ version }}</p>
        <p>Environment: {{ env }}</p>
        <p>Hostname: {{ hostname }}</p>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
