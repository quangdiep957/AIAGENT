import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# bạn cần export API key trước khi chạy
# export OPENAI_API_KEY="sk-xxxx"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MONGODB_CONNECTION = os.getenv("CONNECTION", "")
