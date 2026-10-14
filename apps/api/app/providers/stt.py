"""Speech-to-Text providers.

Provider hierarchy:
1. WhisperTranscriptionProvider — local faster-whisper, no API key
2. FallbackTranscriptionProvider — deterministic demo output (labelled)

All providers tag their output with provider name so demo output is never
presented as real AI transcription.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptSegmentOutput(BaseModel):
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float = 0.95


class TranscriptionResult(BaseModel):
    provider: str
    model: str
    segments: list[TranscriptSegmentOutput]
    language: str = "en"


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        pass


class FallbackTranscriptionProvider(TranscriptionProvider):
    """Returns deterministic demo output. Clearly labelled as demo-fallback."""

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        filename = audio_path.name.lower()
        if "fail" in filename or "corrupt" in filename:
            raise RuntimeError("Corrupted audio payload detected by transcription provider")

        segments = [
            TranscriptSegmentOutput(
                speaker="Speaker 1",
                start_time=0.0,
                end_time=14.5,
                text="[DEMO TRANSCRIPT] Welcome everyone. Today we are reviewing the system architecture, "
                     "background pipeline execution, and vector search embeddings for SignalRoom.",
                confidence=0.98,
            ),
            TranscriptSegmentOutput(
                speaker="Speaker 2",
                start_time=15.0,
                end_time=32.0,
                text="[DEMO TRANSCRIPT] The pipeline stages are validate media, extract audio, transcribe, "
                     "analyze via LLM, persist database records, embed into ChromaDB, and set action item reminders.",
                confidence=0.96,
            ),
            TranscriptSegmentOutput(
                speaker="Speaker 1",
                start_time=32.5,
                end_time=48.0,
                text="[DEMO TRANSCRIPT] We need to finalize the Docker deployment configuration "
                     "and write end-to-end tests for the complete meeting lifecycle flow. "
                     "Sarah Chen should handle the Docker Compose by next Friday.",
                confidence=0.97,
            ),
        ]
        return TranscriptionResult(
            provider="demo-fallback",
            model="signalroom-stt-demo-v1",
            segments=segments,
        )


class WhisperTranscriptionProvider(TranscriptionProvider):
    """Real transcription using faster-whisper (local, CPU-compatible, no API key).

    Model sizes: tiny (~75MB), base (~150MB), small (~500MB), medium (~1.5GB).
    On first run the model is downloaded to ~/.cache/huggingface/.
    CPU inference with int8 quantization is significantly faster than fp32.
    """

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # type: ignore[import-untyped]
                logger.info(f"Loading Whisper model '{self._model_size}' on {self._device} ({self._compute_type})")
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("Whisper model loaded successfully")
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed. Run: pip install faster-whisper"
                )

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        import asyncio

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load_model()

        def _run_transcription() -> list[TranscriptSegmentOutput]:
            segments_out = []
            try:
                segments_iter, info = self._model.transcribe(  # type: ignore[union-attr]
                    str(audio_path),
                    beam_size=5,
                    language=None,  # auto-detect
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                )
                for seg in segments_iter:
                    segments_out.append(
                        TranscriptSegmentOutput(
                            speaker="Speaker 1",  # diarization not implemented
                            start_time=seg.start,
                            end_time=seg.end,
                            text=seg.text.strip(),
                            confidence=min(1.0, max(0.0, 1.0 - abs(seg.avg_logprob + 0.5))),
                        )
                    )
                return segments_out
            except Exception as exc:
                raise RuntimeError(f"Whisper transcription failed: {exc}") from exc

        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(None, _run_transcription)

        if not segments:
            raise RuntimeError("Whisper returned no transcript segments. The audio may be silent or too short.")

        return TranscriptionResult(
            provider="faster-whisper",
            model=self._model_size,
            segments=segments,
        )


_provider_instance: TranscriptionProvider | None = None


def get_transcription_provider() -> TranscriptionProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if settings.STT_PROVIDER == "whisper":
        try:
            _provider_instance = WhisperTranscriptionProvider(
                model_size=settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
            logger.info(f"Using Whisper STT provider (model={settings.WHISPER_MODEL})")
        except Exception as exc:
            logger.warning(f"Whisper STT unavailable ({exc}), falling back to demo provider")
            _provider_instance = FallbackTranscriptionProvider()
    else:
        if settings.STT_PROVIDER != "fallback":
            logger.warning(
                f"Unknown STT_PROVIDER '{settings.STT_PROVIDER}', using fallback demo provider."
            )
        _provider_instance = FallbackTranscriptionProvider()

    return _provider_instance
