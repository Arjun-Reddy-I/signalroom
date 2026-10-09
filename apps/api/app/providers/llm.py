from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class ActionItemExtraction(BaseModel):
    title: str
    description: str | None = None
    owner_name: str | None = None
    due_days_offset: int = 3  # days relative to meeting start
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


class FallbackLLMProvider(LLMProvider):
    async def analyze_transcript(
        self, transcript_text: str, meeting_date: datetime
    ) -> MeetingAnalysisResult:
        if "fail" in transcript_text.lower():
            raise RuntimeError("LLM analysis failed on corrupted content")

        return MeetingAnalysisResult(
            provider="demo-fallback",
            model="signalroom-llm-v1",
            summary_text="The team held a technical architecture sync to review the background worker pipeline, multi-tenant database schema, and ChromaDB vector search integration. Key implementation decisions were finalized.",
            key_points=[
                "Database queue uses SKIP LOCKED for lock-free parallel execution",
                "Structured JSON outputs strictly validated via Pydantic schemas",
                "ChromaDB stores hybrid search embeddings for transcript passages",
            ],
            decisions=[
                DecisionExtraction(
                    title="Adopt database job queue with SKIP LOCKED",
                    description="Use processing_jobs table to avoid Redis dependency.",
                    category="Architecture",
                    confidence=0.99,
                )
            ],
            action_items=[
                ActionItemExtraction(
                    title="Finalize Docker Compose production deployment configuration",
                    description="Include postgres, chromadb, web, api, and worker services.",
                    owner_name="Sarah Chen",
                    due_days_offset=3,
                    priority="high",
                    confidence=0.98,
                ),
                ActionItemExtraction(
                    title="Implement e2e tests for complete meeting lifecycle flow",
                    description="Verify upload, pipeline progress polling, and search.",
                    owner_name="David Kim",
                    due_days_offset=5,
                    priority="medium",
                    confidence=0.95,
                ),
            ],
        )


def get_llm_provider() -> LLMProvider:
    return FallbackLLMProvider()
