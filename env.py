from dotenv import load_dotenv
import os

# Загружаем переменные из .env файла
load_dotenv()

# Теперь вы можете использовать переменные окружения
BOT_TOKEN = os.getenv("TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
