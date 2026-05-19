from google import genai
from tudim.config import settings

client = genai.Client(api_key=settings.gemini_api_key)