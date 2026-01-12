from dotenv import load_dotenv
import os

load_dotenv()
print(f"Key loaded: {bool(os.environ.get('GEMINI_API_KEY'))}")
print(f"CWD: {os.getcwd()}")
