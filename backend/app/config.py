import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str  = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str  = os.getenv("GOOGLE_API_KEY", "")
    GROQ_API_KEY: str    = os.getenv("GROQ_API_KEY", "")
    BROWSERLESS_TOKEN: str = os.getenv("BROWSERLESS_TOKEN", "")
    ENVIRONMENT: str     = os.getenv("ENVIRONMENT", "development")

    # Priority: Groq (free, fast) > Gemini > OpenAI
    USE_GROQ:   bool = bool(os.getenv("GROQ_API_KEY", ""))
    USE_GEMINI: bool = bool(os.getenv("GOOGLE_API_KEY", "")) and not bool(os.getenv("GROQ_API_KEY", ""))

    # Groq model — llama-3.3-70b-versatile is excellent and free
    LLM_MODEL: str = (
        "llama-3.3-70b-versatile" if bool(os.getenv("GROQ_API_KEY", ""))
        else ("gemini-2.5-flash"  if bool(os.getenv("GOOGLE_API_KEY", ""))
              else "gpt-4o-mini")
    )
    LLM_TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 2048

    # Scraping settings
    SCRAPE_TIMEOUT: int = 30000
    WAIT_FOR_NETWORK_IDLE: int = 2000

    # Memory settings
    MEMORY_WINDOW_SIZE: int = 15

settings = Settings()
