"""LLM providers for meeting analysis.

Provider hierarchy:
1. OllamaLLMProvider — local Ollama server (no API key, free)
2. OpenAILLMProvider — requires OPENAI_API_KEY
3. FallbackLLMProvider — deterministic demo output (labelled)

All providers return MeetingAnalysisResult validated through Pydantic.
Demo fallback is clearly tagged as 'demo-fallback'.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class ActionItemExtraction(BaseModel):
    title: str
    description: str | None = None
    owner_name: str | None = None
    due_days_offset: int = 3
    priority: str = "medium"
    confidence: float = 0.95


class DecisionExtraction(BaseModel):
    title: str
    description: str | None = None
    category: str = "General"
    confidence: float = 0.95


class MeetingAnalysisResult(BaseModel):
    provider: str
    model: str
    summary_text: str
    key_points: list[str]
    decisions: list[DecisionExtraction]
    action_items: list[ActionItemExtraction]


class LLMProvider(ABC):
    @abstractmethod
    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        pass


# ── Structured output prompt ────────────────────────────────────────────────

_ANALYSIS_PROMPT = """You are an expert meeting analyst for a professional workspace. Analyze the meeting transcript below and extract structured data.

Return ONLY a valid JSON object (no markdown code blocks, no extra text) matching this exact schema:
{{
  "summary_text": "2-4 sentence summary covering the main topic, key outcomes, and any important context",
  "key_points": ["Specific point 1", "Specific point 2", "Specific point 3", "Specific point 4"],
  "decisions": [
    {{
      "title": "Short imperative title of what was decided",
      "description": "What was decided, why, and any conditions or caveats",
      "category": "Architecture|Product|Process|Business|Technical|General",
      "confidence": 0.95
    }}
  ],
  "action_items": [
    {{
      "title": "Verb phrase describing the task (e.g. 'Set up CI pipeline', 'Draft proposal for client')",
      "description": "Specific details about what needs to be done",
      "owner_name": "Full name of the person responsible, or null if unclear",
      "due_days_offset": 7,
      "priority": "high|medium|low",
      "confidence": 0.90
    }}
  ]
}}

Important rules:
- Extract ONLY decisions and actions that were explicitly stated in the transcript
- For owner_name: use names mentioned in the transcript, or null if unclear — never invent names
- For due_days_offset: use 1-3 for "today/tomorrow/ASAP", 7 for "this week/next week", 14 for "two weeks", 30 for "this month"
- Mark confidence < 0.75 for ambiguous or inferred items
- key_points should be specific facts, not generic statements
- If a section has no items, use an empty array []

Meeting date: {meeting_date}

Transcript:
{transcript}"""


def _parse_llm_response(raw: str, provider: str, model: str) -> MeetingAnalysisResult:
    """Parse and validate LLM JSON response."""
    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        data = json.loads(text)
        return MeetingAnalysisResult(
            provider=provider,
            model=model,
            summary_text=data.get("summary_text", "Summary not available."),
            key_points=data.get("key_points", []),
            decisions=[DecisionExtraction(**d) for d in data.get("decisions", [])],
            action_items=[ActionItemExtraction(**a) for a in data.get("action_items", [])],
        )
    except (json.JSONDecodeError, ValidationError, KeyError) as exc:
        raise ValueError(f"Failed to parse LLM response: {exc}\nRaw response:\n{raw[:500]}") from exc


# ── Ollama ──────────────────────────────────────────────────────────────────

class OllamaLLMProvider(LLMProvider):
    """Uses a locally running Ollama server (http://localhost:11434 by default).

    Install Ollama: https://ollama.ai
    Pull a model: ollama pull llama3.2
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for Ollama. It should already be installed.")

        prompt = _ANALYSIS_PROMPT.format(
            meeting_date=meeting_date.strftime("%Y-%m-%d"),
            transcript=transcript_text[:8000],  # truncate for context window
        )

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Forces Ollama to return pure JSON (supported in ollama >= 0.1.9)
            "options": {"temperature": 0.1, "num_predict": 2048},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
                raw = resp.json().get("response", "")
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Cannot connect to Ollama at {self._base_url}. "
                    "Ensure Ollama is running: 'ollama serve'"
                )
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f"Ollama API error {exc.response.status_code}: {exc.response.text[:200]}")

        # Retry once if parse fails
        try:
            return _parse_llm_response(raw, provider="ollama", model=self._model)
        except ValueError as first_err:
            logger.warning(f"First parse attempt failed: {first_err}. Retrying with explicit JSON instruction.")
            # Second attempt with stronger JSON instruction
            payload["prompt"] = prompt + "\n\nIMPORTANT: Return ONLY the JSON object. No explanations."
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
                raw2 = resp.json().get("response", "")
            return _parse_llm_response(raw2, provider="ollama", model=self._model)


# ── OpenAI ──────────────────────────────────────────────────────────────────

class OpenAILLMProvider(LLMProvider):
    """Uses OpenAI chat completions API with JSON mode."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model

    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required")

        prompt = _ANALYSIS_PROMPT.format(
            meeting_date=meeting_date.strftime("%Y-%m-%d"),
            transcript=transcript_text[:12000],
        )

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                return _parse_llm_response(raw, provider="openai", model=self._model)
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f"OpenAI API error {exc.response.status_code}: {exc.response.text[:200]}")


# ── Gemini ───────────────────────────────────────────────────────────────────

class GeminiLLMProvider(LLMProvider):
    """Uses Google Gemini API (gemini-1.5-flash by default — fast and free-tier friendly).

    Docs: https://ai.google.dev/api/generate-content
    Free tier: 15 RPM, 1M TPD — sufficient for a meeting analysis workload.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self._api_key = api_key
        self._model = model
        # Model name can be passed with or without the "models/" prefix
        model_path = model if model.startswith("models/") else f"models/{model}"
        self._base_url = f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent"

    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for Gemini. It should already be installed.")

        prompt = _ANALYSIS_PROMPT.format(
            meeting_date=meeting_date.strftime("%Y-%m-%d"),
            transcript=transcript_text[:12000],
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    self._base_url,
                    params={"key": self._api_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:300]
                raise RuntimeError(f"Gemini API error {exc.response.status_code}: {body}")
            except (KeyError, IndexError) as exc:
                raise RuntimeError(f"Unexpected Gemini response structure: {exc}")

        # Retry once on parse failure
        try:
            return _parse_llm_response(raw, provider="gemini", model=self._model)
        except ValueError as first_err:
            logger.warning(f"Gemini parse attempt 1 failed: {first_err}. Retrying.")
            payload["contents"][0]["parts"][0]["text"] = (
                prompt + "\n\nCRITICAL: Your response must be ONLY the JSON object. No markdown, no explanation."
            )
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self._base_url,
                    params={"key": self._api_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                raw2 = data["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_llm_response(raw2, provider="gemini", model=self._model)


# ── Fallback ─────────────────────────────────────────────────────────────────

class FallbackLLMProvider(LLMProvider):
    """Returns deterministic demo output. Clearly labelled as demo-fallback.

    Used when no LLM provider is configured. All outputs are tagged
    '[DEMO]' to prevent confusion with real AI analysis.
    """

    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        if "fail" in transcript_text.lower():
            raise RuntimeError("LLM analysis failed on corrupted content")

        return MeetingAnalysisResult(
            provider="demo-fallback",
            model="signalroom-llm-demo-v1",
            summary_text=(
                "[DEMO] The team held a technical architecture sync to review the background worker pipeline, "
                "multi-tenant database schema, and ChromaDB vector search integration. "
                "Key implementation decisions were finalized."
            ),
            key_points=[
                "[DEMO] Database queue uses SKIP LOCKED for lock-free parallel execution",
                "[DEMO] Structured JSON outputs strictly validated via Pydantic schemas",
                "[DEMO] ChromaDB stores hybrid search embeddings for transcript passages",
            ],
            decisions=[
                DecisionExtraction(
                    title="[DEMO] Adopt database job queue with SKIP LOCKED",
                    description="Use processing_jobs table to avoid Redis dependency.",
                    category="Architecture",
                    confidence=0.99,
                )
            ],
            action_items=[
                ActionItemExtraction(
                    title="[DEMO] Finalize Docker Compose production deployment configuration",
                    description="Include postgres, chromadb, web, api, and worker services.",
                    owner_name="Sarah Chen",
                    due_days_offset=3,
                    priority="high",
                    confidence=0.98,
                ),
                ActionItemExtraction(
                    title="[DEMO] Implement e2e tests for complete meeting lifecycle flow",
                    description="Verify upload, pipeline progress polling, and search.",
                    owner_name="David Kim",
                    due_days_offset=5,
                    priority="medium",
                    confidence=0.95,
                ),
            ],
        )


_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    # Use SmartLLMProvider when Gemini key is present — it chains Gemini → Ollama → Fallback
    if settings.GEMINI_API_KEY:
        _provider_instance = SmartLLMProvider()
        logger.info(
            f"Using SmartLLM provider chain: Gemini({settings.GEMINI_LLM_MODEL}) "
            f"→ Ollama({settings.LLM_MODEL}) → Demo fallback"
        )
    elif settings.LLM_PROVIDER == "ollama":
        _provider_instance = OllamaLLMProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.LLM_MODEL,
        )
        logger.info(f"Using Ollama LLM provider (model={settings.LLM_MODEL})")
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        _provider_instance = OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
        )
        logger.info(f"Using OpenAI LLM provider (model={settings.LLM_MODEL})")
    else:
        logger.warning("No LLM configured. Using demo fallback. Set GEMINI_API_KEY or LLM_PROVIDER=ollama.")
        _provider_instance = FallbackLLMProvider()

    return _provider_instance


class SmartLLMProvider(LLMProvider):
    """Tries providers in priority order: Ollama (local) → Gemini → Demo fallback.

    Ollama goes first since it's local and has no rate limits.
    Gemini is tried if Ollama is unavailable.
    Demo fallback is always last.
    """

    def __init__(self) -> None:
        self._providers: list[LLMProvider] = []
        # Ollama first — local, fast, no rate limits
        self._providers.append(OllamaLLMProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.LLM_MODEL,
        ))
        # Gemini second — cloud fallback when Ollama is down
        if settings.GEMINI_API_KEY:
            self._providers.append(GeminiLLMProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_LLM_MODEL,
            ))
        # Demo fallback always last
        self._providers.append(FallbackLLMProvider())

    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        last_error: Exception = RuntimeError("No providers available")
        for provider in self._providers:
            try:
                result = await provider.analyze_transcript(transcript_text, meeting_date)
                if result.provider != "demo-fallback":
                    logger.info(f"SmartLLM: used {result.provider}/{result.model}")
                return result
            except Exception as exc:
                logger.warning(
                    f"SmartLLM: {type(provider).__name__} failed ({exc!s:.100}), trying next provider"
                )
                last_error = exc
        raise last_error
