import os
import sys
import socket
import requests
from flask import Flask, request, send_file
from pytube import YouTube
from moviepy.editor import AudioFileClip

app = Flask(__name__)
user_state = {}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        link = request.form["link"]
        if 'youtube.com/watch' in link or 'youtu.be/' in link:
            try:
                yt = YouTube(link)
                video_title = yt.title
                thumbnail_url = yt.thumbnail_url
                resolutions = ['144p', '240p', '360p', '480p', '540p', '720p', '720p60', '1080p', '1080p60']
                
                streams = []
                for res in resolutions:
                    stream = yt.streams.filter(res=res.replace('60', ''), fps=60 if '60' в res else None, file_extension='mp4').first()
                    if stream:
                        size = round(stream.filesize / (1024 * 1024), 2)
                        streams.append(f'<li><a href="/download/{stream.itag}">{res} MP4 ({size} MB)</a></li>')
                
                audio_stream = yt.streams.filter(only_audio=True).first()
                if audio_stream:
                    audio_size = round(audio_stream.filesize / (1024 * 1024), 2)
                    streams.append(f'<li><a href="/download_audio/{audio_stream.itag}">320kbps .mp3 ({audio_size} MB)</a></li>')

                user_state[request.remote_addr] = {
                    'link': link,
                    'title': video_title,
                    'thumbnail_url': thumbnail_url,
                }

                return f"""
                    <html>
                    <head>
                        <title>Выбор разрешения</title>
                    </head>
                    <body>
                        <h1>Выберите разрешение для скачивания: {video_title}</h1>
                        <ul>
                            {''.join(streams)}
                        </ul>
                    </body>
                    </html>
                """

            except Exception as e:
                return f"Ошибка при обработке видео. Проверьте ссылку и попробуйте снова. Ошибка: {str(e)}"
    
    return """
        <html>
        <head>
            <title>Скачиватель YouTube</title>
        </head>
        <body>
            <h1>Привет! Отправьте ссылку на видео с YouTube для скачивания.</h1>
            <form method="post">
                <input type="text" name="link" placeholder="Ссылка на YouTube" required>
                <button type="submit">Скачать</button>
            </form>
        </body>
        </html>
    """

@app.route("/download/<itag>")
def download(itag):
    user_data = user_state.get(request.remote_addr)
    if not user_data or 'link' not in user_data:
        return "Ошибка состояния. Попробуйте снова."
    
    link = user_data['link']
    yt = YouTube(link)
    stream = yt.streams.get_by_itag(itag)
    filename = stream.default_filename
    stream.download(filename=filename)
    
    return send_file(filename, as_attachment=True, download_name=filename)

@app.route("/download_audio/<itag>")
def download_audio(itag):
    user_data = user_state.get(request.remote_addr)
    if not user_data or 'link' not in user_data:
        return "Ошибка состояния. Попробуйте снова."
    
    link = user_data['link']
    yt = YouTube(link)
    stream = yt.streams.get_by_itag(itag)
    filename = stream.default_filename
    stream.download(filename=filename)
    
    audio_filename = filename.replace('.mp4', '.mp3')
    audio = AudioFileClip(filename)
    audio.write_audiofile(audio_filename, codec='libmp3lame', bitrate='320k')
    
    os.remove(filename)  # Удаляем видеофайл после конвертации
    return send_file(audio_filename, as_attachment=True, download_name=audio_filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
