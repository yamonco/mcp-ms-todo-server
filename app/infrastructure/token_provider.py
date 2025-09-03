from pathlib import Path
from app.config import cfg


class FileTokenProvider:
    def __init__(self, path: str | None = None):
        self.path = Path(path or cfg.token_file)

    def get_token(self) -> str:
        if not self.path.exists():
            return ""
        import json
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("access_token", "")

