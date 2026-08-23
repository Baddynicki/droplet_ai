from dotenv import load_dotenv
import os

load_dotenv()  # Automatically loads backend/.env

print(os.getenv("GEMINI_API_KEY"))