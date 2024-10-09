import os
import sys
import socket
from flask import Flask, render_template_string, request, send_file, jsonify
from pytube import YouTube
from moviepy.editor import AudioFileClip
import requests
import tempfile

app = Flask(__name__)

@app.route("/")
def index():
    version = sys.version_info
    env = os.getenv('ENV', 'Development')
    hostname = socket.gethostname()
    
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Downloader</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .neumorphic {
                background: #e0e0e0;
                box-shadow: 20px 20px 60px #bebebe, -20px -20px 60px #ffffff;
            }
            .dark .neumorphic {
                background: #2d3748;
                box-shadow: 20px 20px 60px #1a202c, -20px -20px 60px #4a5568;
            }
        </style>
    </head>
    <body class="bg-gray-100 dark:bg-gray-800 transition-colors duration-300">
        <div class="container mx-auto px-4 py-8">
            <div class="neumorphic rounded-lg p-8 mb-8">
                <h1 class="text-3xl font-bold mb-4 text-gray-800 dark:text-white">YouTube Downloader</h1>
                <h2 class="text-xl mb-2 text-gray-700 dark:text-gray-300">Environment: {{ env }}</h2>
                <p class="text-gray-600 dark:text-gray-400">Running Python: {{ python_version }}</p>
                <p class="text-gray-600 dark:text-gray-400">Hostname: {{ hostname }}</p>
            </div>
            
            <div class="neumorphic rounded-lg p-8">
                <form id="downloadForm" class="mb-4">
                    <input type="text" id="youtubeUrl" placeholder="Enter YouTube URL" class="w-full p-2 mb-4 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-white">
                    <button type="submit" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded">
                        Get Download Options
                    </button>
                </form>
                
                <div id="videoInfo" class="hidden mb-4">
                    <img id="thumbnail" src="" alt="Video Thumbnail" class="w-full h-48 object-cover mb-2 rounded">
                    <h3 id="videoTitle" class="text-xl font-bold mb-2 text-gray-800 dark:text-white"></h3>
                </div>
                
                <div id="downloadOptions" class="hidden">
                    <h4 class="text-lg font-bold mb-2 text-gray-800 dark:text-white">Download Options:</h4>
                    <div id="optionsList"></div>
                </div>
            </div>
        </div>
        
        <script>
        document.getElementById('downloadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('youtubeUrl').value;
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            const data = await response.json();
            
            document.getElementById('thumbnail').src = data.thumbnail_url;
            document.getElementById('videoTitle').textContent = data.title;
            document.getElementById('videoInfo').classList.remove('hidden');
            
            const optionsList = document.getElementById('optionsList');
            optionsList.innerHTML = '';
            data.streams.forEach(stream => {
                const button = document.createElement('button');
                button.textContent = `${stream.resolution} (${stream.file_size} MB)`;
                button.className = 'bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded mr-2 mb-2';
                button.onclick = () => downloadVideo(url, stream.itag, stream.is_audio);
                optionsList.appendChild(button);
            });
            document.getElementById('downloadOptions').classList.remove('hidden');
        });

        async function downloadVideo(url, itag, isAudio) {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url, itag: itag, is_audio: isAudio})
            });
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = isAudio ? 'audio.mp3' : 'video.mp4';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
        }
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html, env=env, python_version=f"{version.major}.{version.minor}.{version.micro}", hostname=hostname)

@app.route("/get_video_info", methods=['POST'])
def get_video_info():
    url = request.json['url']
    try:
        yt = YouTube(url)
        streams = []
        for stream in yt.streams.filter(progressive=True):
            streams.append({
                'itag': stream.itag,
                'resolution': stream.resolution,
                'file_size': round(stream.filesize / (1024 * 1024), 2),
                'is_audio': False
            })
        
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            streams.append({
                'itag': audio_stream.itag,
                'resolution': '320kbps MP3',
                'file_size': round(audio_stream.filesize / (1024 * 1024), 2),
                'is_audio': True
            })
        
        return jsonify({
            'title': yt.title,
            'thumbnail_url': yt.thumbnail_url,
            'streams': streams
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/download", methods=['POST'])
def download():
    url = request.json['url']
    itag = request.json['itag']
    is_audio = request.json['is_audio']
    
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            stream.download(filename=temp_file.name)
            
            if is_audio:
                audio = AudioFileClip(temp_file.name)
                audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                audio.write_audiofile(audio_file.name, codec='libmp3lame', bitrate='320k')
                os.unlink(temp_file.name)
                return send_file(audio_file.name, as_attachment=True, download_name=f"{yt.title}.mp3")
            else:
                return send_file(temp_file.name, as_attachment=True, download_name=f"{yt.title}.mp4")
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
