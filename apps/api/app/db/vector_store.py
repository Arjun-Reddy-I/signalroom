from pathlib import Path
from typing import Any

import chromadb

from app.core.config import settings

_chroma_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
    return _chroma_client


def get_meetings_collection() -> Any:
    client = get_chroma_client()
    return client.get_or_create_collection(name="signalroom_meetings")
