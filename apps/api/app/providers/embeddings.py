"""Embedding providers for vector search.

Provider hierarchy (from best to fallback):
1. SentenceTransformersEmbeddingProvider — local, no API key, real embeddings
2. OpenAIEmbeddingProvider — requires OPENAI_API_KEY
3. FallbackEmbeddingProvider — deterministic hash-based (for testing only)

All providers return a list[float] of the same dimension for a given model.
"""
import hashlib
import logging
import math
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class FallbackEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based pseudo-embedding. For CI/testing only.

    Produces 384-dimensional vectors from SHA-256 hash. Similarity scores
    are meaningless. All results are labelled 'demo-fallback'.
    """

    _DIM = 384

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Extend to 384 dims by cycling through the 32-byte hash
        raw = []
        for i in range(self._DIM):
            raw.append(digest[i % 32])
        # Normalize to unit vector in [-1, 1]
        total = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / total for v in raw]

    @property
    def dimension(self) -> int:
        return self._DIM

    @property
    def provider_name(self) -> str:
        return "demo-fallback"


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """Uses sentence-transformers for local, real embeddings.

    Default model: all-MiniLM-L6-v2 (384-dim, ~80MB download, no API key needed).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
                logger.info(f"Loading sentence-transformers model: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
                logger.info("Sentence-transformers model loaded successfully")
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers"
                )

    async def embed(self, text: str) -> list[float]:
        import asyncio
        self._load_model()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._model.encode, text)  # type: ignore[union-attr]
        return result.tolist()

    @property
    def dimension(self) -> int:
        return 384

    @property
    def provider_name(self) -> str:
        return f"sentence-transformers/{self._model_name}"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Uses OpenAI text-embedding-3-small (1536-dim)."""

    _DIM = 1536

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for OpenAI embeddings")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": text, "model": self._model},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    @property
    def dimension(self) -> int:
        return self._DIM

    @property
    def provider_name(self) -> str:
        return f"openai/{self._model}"


_provider_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if settings.EMBEDDING_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        _provider_instance = OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )
    elif settings.EMBEDDING_PROVIDER == "sentence_transformers":
        try:
            _provider_instance = SentenceTransformersEmbeddingProvider(
                model_name=settings.EMBEDDING_MODEL
            )
            logger.info(f"Using sentence-transformers embedding provider: {settings.EMBEDDING_MODEL}")
        except Exception as e:
            logger.warning(f"sentence-transformers unavailable ({e}), falling back to demo provider")
            _provider_instance = FallbackEmbeddingProvider()
    else:
        if settings.EMBEDDING_PROVIDER != "fallback":
            logger.warning(
                f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}', using fallback. "
                "Set EMBEDDING_PROVIDER=sentence_transformers for local real embeddings."
            )
        _provider_instance = FallbackEmbeddingProvider()

    return _provider_instance
