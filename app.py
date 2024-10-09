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
        <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/2.3.0/alpine-ie11.min.js"></script>
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
    <body class="bg-gray-100 dark:bg-gray-800 transition-colors duration-300" x-data="{ darkMode: false }">
        <div class="container mx-auto px-4 py-8">
            <div class="neumorphic rounded-lg p-8 mb-8">
                <h1 class="text-4xl font-bold mb-4 text-gray-800 dark:text-white">YouTube Downloader</h1>
                <p class="text-gray-600 dark:text-gray-300 mb-4">Enter a YouTube URL to download video or audio</p>
                <div class="mb-4">
                    <input type="text" id="youtube-url" placeholder="https://www.youtube.com/watch?v=..." 
                           class="w-full p-2 rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white">
                </div>
                <button onclick="getVideoInfo()" 
                        class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded transition duration-300">
                    Get Video Info
                </button>
            </div>

            <div id="video-info" class="neumorphic rounded-lg p-8 mb-8 hidden">
                <img id="thumbnail" src="" alt="Video Thumbnail" class="w-full mb-4 rounded">
                <h2 id="video-title" class="text-2xl font-bold mb-4 text-gray-800 dark:text-white"></h2>
                <div id="download-options"></div>
            </div>

            <div class="neumorphic rounded-lg p-8">
                <h2 class="text-2xl font-bold mb-4 text-gray-800 dark:text-white">Server Info</h2>
                <p class="text-gray-600 dark:text-gray-300">Environment: {{ env }}</p>
                <p class="text-gray-600 dark:text-gray-300">Python Version: {{ version.major }}.{{ version.minor }}.{{ version.micro }}</p>
                <p class="text-gray-600 dark:text-gray-300">Hostname: {{ hostname }}</p>
            </div>
        </div>

        <button @click="darkMode = !darkMode" 
                class="fixed bottom-4 right-4 bg-gray-200 dark:bg-gray-600 p-2 rounded-full shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
        </button>

        <script>
            function getVideoInfo() {
                const url = document.getElementById('youtube-url').value;
                fetch(`/video_info?url=${encodeURIComponent(url)}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('video-info').classList.remove('hidden');
                        document.getElementById('thumbnail').src = data.thumbnail_url;
                        document.getElementById('video-title').textContent = data.title;
                        const downloadOptions = document.getElementById('download-options');
                        downloadOptions.innerHTML = '';
                        data.streams.forEach(stream => {
                            const button = document.createElement('button');
                            button.textContent = `${stream.resolution} (${stream.filesize} MB)`;
                            button.className = 'bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded m-2 transition duration-300';
                            button.onclick = () => downloadVideo(url, stream.itag);
                            downloadOptions.appendChild(button);
                        });
                        if (data.audio_stream) {
                            const audioButton = document.createElement('button');
                            audioButton.textContent = `Audio MP3 (${data.audio_stream.filesize} MB)`;
                            audioButton.className = 'bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded m-2 transition duration-300';
                            audioButton.onclick = () => downloadAudio(url, data.audio_stream.itag);
                            downloadOptions.appendChild(audioButton);
                        }
                    })
                    .catch(error => console.error('Error:', error));
            }

            function downloadVideo(url, itag) {
                window.location.href = `/download_video?url=${encodeURIComponent(url)}&itag=${itag}`;
            }

            function downloadAudio(url, itag) {
                window.location.href = `/download_audio?url=${encodeURIComponent(url)}&itag=${itag}`;
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, version=version, env=env, hostname=hostname)

@app.route("/video_info")
def video_info():
    url = request.args.get('url')
    try:
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        stream_data = [
            {
                'itag': stream.itag,
                'resolution': stream.resolution,
                'filesize': round(stream.filesize / (1024 * 1024), 2)
            }
            for stream in streams
        ]
        audio_stream = yt.streams.filter(only_audio=True).first()
        audio_data = None
        if audio_stream:
            audio_data = {
                'itag': audio_stream.itag,
                'filesize': round(audio_stream.filesize / (1024 * 1024), 2)
            }
        return jsonify({
            'title': yt.title,
            'thumbnail_url': yt.thumbnail_url,
            'streams': stream_data,
            'audio_stream': audio_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/download_video")
def download_video():
    url = request.args.get('url')
    itag = request.args.get('itag')
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            stream.download(filename=tmp_file.name)
            return send_file(tmp_file.name, as_attachment=True, download_name=f"{yt.title}.mp4")
    except Exception as e:
        return str(e), 400

@app.route("/download_audio")
def download_audio():
    url = request.args.get('url')
    itag = request.args.get('itag')
    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            stream.download(filename=tmp_file.name)
            audio = AudioFileClip(tmp_file.name)
            mp3_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            audio.write_audiofile(mp3_file.name, codec='libmp3lame', bitrate='320k')
            return send_file(mp3_file.name, as_attachment=True, download_name=f"{yt.title}.mp3")
    except Exception as e:
        return str(e), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
