from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


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


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        pass


class FallbackTranscriptionProvider(TranscriptionProvider):
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        filename = audio_path.name.lower()
        if "fail" in filename or "corrupt" in filename:
            raise RuntimeError("Corrupted audio payload detected by transcription provider")

        segments = [
            TranscriptSegmentOutput(
                speaker="Alex Morgan",
                start_time=0.0,
                end_time=14.5,
                text="Welcome everyone. Today we are reviewing the system architecture, background pipeline execution, and vector search embeddings for SignalRoom.",
                confidence=0.98,
            ),
            TranscriptSegmentOutput(
                speaker="Sarah Chen",
                start_time=15.0,
                end_time=32.0,
                text="The pipeline stages are validate media, extract audio, transcribe, analyze via LLM, persist database records, embed into ChromaDB, and set action item reminders.",
                confidence=0.96,
            ),
            TranscriptSegmentOutput(
                speaker="David Kim",
                start_time=32.5,
                end_time=48.0,
                text="We will ensure all action items are extracted with target deadlines and assigned to participants with high confidence.",
                confidence=0.97,
            ),
        ]
        return TranscriptionResult(
            provider="demo-fallback",
            model="signalroom-stt-v1",
            segments=segments,
        )


def get_transcription_provider() -> TranscriptionProvider:
    return FallbackTranscriptionProvider()
