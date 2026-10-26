from pathlib import Path
from typing import Any

import chromadb

from app.core.config import settings

_chroma_client: chromadb.ClientAPI | None = None
_vector_store_error: str | None = None


def vector_store_error() -> str | None:
    return _vector_store_error


def _record_vector_store_error(error: BaseException) -> None:
    global _vector_store_error
    _vector_store_error = f"{type(error).__name__}: persistent vector store is unavailable"


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client, _vector_store_error
    if _vector_store_error:
        raise RuntimeError(_vector_store_error)
    if _chroma_client is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            _chroma_client = chromadb.PersistentClient(path=str(persist_dir))
            _chroma_client.heartbeat()
        except BaseException as error:
            _record_vector_store_error(error)
            raise RuntimeError(_vector_store_error) from error
    return _chroma_client


def get_meetings_collection() -> Any:
    try:
        client = get_chroma_client()
        return client.get_or_create_collection(name="signalroom_meetings")
    except BaseException as error:
        _record_vector_store_error(error)
        raise RuntimeError(_vector_store_error) from error
