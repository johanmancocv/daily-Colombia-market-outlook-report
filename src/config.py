from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    max_articles: int = int(os.getenv("MAX_ARTICLES", "35"))
    db_path: str = os.getenv("DB_PATH", "market_nowcast.sqlite3")

def settings() -> Settings:
    return Settings()
