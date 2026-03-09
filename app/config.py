#Will not be using this config.py. Do load_dotenv() in every graph !
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY")
    BRIGHTDATA_API_KEY: str = os.getenv("BRIGHTDATA_API_KEY")
    #DATABASE_URL: str = os.getenv("DATABASE_URL")

settings = Settings()