import json
from pathlib import Path

from doc_assistant.api import app

path = Path(__file__).resolve().parents[1] / "openapi.json"
path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
