import telebot
import os
from TTS.api import TTS

# Создаем экземпляр бота с токеном
bot_token = "8060928204:AAGTqyGeZnKnJLHNbm2CV5qir1eqJ8XJfQM"
bot = telebot.TeleBot(bot_token)

# Инициализация модели для мужского голоса
tts_model = TTS(model_name="tts_models/ru/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)

# Функция для генерации голосового сообщения
def generate_voice(text, filename="voice_output.wav"):
    tts_model.tts_to_file(text=text, speaker=tts_model.speakers[0], language=tts_model.languages[0], file_path=filename)

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне текст, и я озвучу его мужским голосом!")

# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def text_to_speech(message):
    user_text = message.text

    # Генерация голосового файла
    voice_file = "voice_output.wav"
    generate_voice(user_text, voice_file)

    # Отправка голосового файла пользователю
    with open(voice_file, 'rb') as audio:
        bot.send_voice(message.chat.id, audio)

    # Удаление временного файла после отправки
    os.remove(voice_file)

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
