from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    bifrost_base_url: str
    bifrost_api_key: str
    cheap_model: str
    coder_model: str
    max_tokens: int = Field(default=30_000, gt=0)
    max_steps: int = Field(default=15, gt=0)
    ledger_path: Path = Path("budgetdev_ledger.sqlite3")

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        values = {
            "bifrost_base_url": os.getenv("BIFROST_BASE_URL"),
            "bifrost_api_key": os.getenv("BIFROST_API_KEY"),
            "cheap_model": os.getenv("BUDGETDEV_CHEAP_MODEL"),
            "coder_model": os.getenv("BUDGETDEV_CODER_MODEL"),
            "max_tokens": os.getenv("BUDGETDEV_MAX_TOKENS", "30000"),
            "max_steps": os.getenv("BUDGETDEV_MAX_STEPS", "15"),
            "ledger_path": os.getenv("BUDGETDEV_LEDGER_PATH", "budgetdev_ledger.sqlite3"),
        }
        return cls(**values)
