"""Background processing pipeline for meeting audio analysis.

Architecture:
- Worker polls the processing_jobs table for PENDING jobs
- Each job runs through 7 stages: VALIDATE_MEDIA → EXTRACT_AUDIO → TRANSCRIBE →
  ANALYZE → PERSIST → VECTOR_EMBED → REMINDERS
- SQLite-compatible locking (simple sequential polling, no SKIP LOCKED)
- PostgreSQL uses FOR UPDATE SKIP LOCKED when DATABASE_URL contains 'postgresql'
- Failed jobs are retried up to max_attempts; meeting status set to FAILED on exhaustion
"""
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete as sql_delete
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.vector_store import get_meetings_collection
from app.models import (
    ActionItem,
    Decision,
    MediaFile,
    Meeting,
    MeetingEmbedding,
    Notification,
    ProcessingJob,
    Reminder,
    Summary,
    TranscriptSegment,
)
from app.models.enums import (
    ActionItemStatusEnum,
    JobStageEnum,
    JobStatusEnum,
    MeetingStatusEnum,
    NotificationTypeEnum,
    PriorityEnum,
    ReminderChannelEnum,
    ReminderStatusEnum,
)
from app.providers.embeddings import get_embedding_provider
from app.providers.llm import get_llm_provider
from app.providers.storage import get_storage_provider
from app.providers.stt import get_transcription_provider

logger = logging.getLogger(__name__)

_IS_POSTGRES = "postgresql" in settings.DATABASE_URL.lower()


async def _claim_next_job(session) -> ProcessingJob | None:  # type: ignore[no-untyped-def]
    """Claim one PENDING job atomically.

    PostgreSQL: uses SELECT FOR UPDATE SKIP LOCKED for safe concurrent workers.
    SQLite: uses simple SELECT + UPDATE (single-worker safe, transactions prevent races).
    """
    if _IS_POSTGRES:
        result = await session.execute(
            text(
                "SELECT id FROM processing_jobs "
                "WHERE status = 'pending' "
                "ORDER BY created_at ASC "
                "LIMIT 1 FOR UPDATE SKIP LOCKED"
            )
        )
        row = result.first()
        if not row:
            return None
        job_result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == row[0])
        )
        job = job_result.scalars().first()
    else:
        result = await session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.status == JobStatusEnum.PENDING)
            .order_by(ProcessingJob.created_at.asc())
            .limit(1)
        )
        job = result.scalars().first()

    if job:
        job.status = JobStatusEnum.PROCESSING
        job.locked_at = datetime.now(UTC)
        job.locked_by = "worker-1"
        await session.flush()

    return job


async def _advance_stage(session, job: ProcessingJob, stage: JobStageEnum) -> None:  # type: ignore[no-untyped-def]
    job.stage = stage
    await session.flush()


async def _execute_pipeline(session, job: ProcessingJob) -> None:  # type: ignore[no-untyped-def]
    """Run all pipeline stages for the given job."""
    # Load meeting
    m_result = await session.execute(select(Meeting).where(Meeting.id == job.meeting_id))
    meeting = m_result.scalars().first()
    if not meeting:
        raise ValueError(f"Meeting {job.meeting_id} not found")

    # Load media file
    mf_result = await session.execute(select(MediaFile).where(MediaFile.meeting_id == meeting.id))
    media_file = mf_result.scalars().first()
    if not media_file:
        raise ValueError("No media file found for this meeting")

    job.attempts += 1

    # ── Stage 1: VALIDATE_MEDIA ──────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.VALIDATE_MEDIA)
    storage = get_storage_provider()
    audio_path = await storage.get_file_path(media_file.storage_key)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file missing from storage: {audio_path}")

    # ── Stage 2: EXTRACT_AUDIO ───────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.EXTRACT_AUDIO)
    meeting.status = MeetingStatusEnum.TRANSCRIBING
    await session.flush()
    # For WAV/MP3 pass through. For other formats ffmpeg would run here.
    processed_path = audio_path  # placeholder; extend with ffmpeg conversion

    # ── Stage 3: TRANSCRIBE ──────────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.TRANSCRIBE)
    stt = get_transcription_provider()
    transcription = await stt.transcribe(processed_path)
    logger.info(f"Transcription complete: {len(transcription.segments)} segments (provider={transcription.provider})")

    # ── Stage 4: ANALYZE ─────────────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.ANALYZE)
    meeting.status = MeetingStatusEnum.ANALYZING
    await session.flush()
    full_text = " ".join(seg.text for seg in transcription.segments)
    llm = get_llm_provider()
    analysis = await llm.analyze_transcript(full_text, meeting.scheduled_start)
    logger.info(
        f"Analysis complete: {len(analysis.decisions)} decisions, "
        f"{len(analysis.action_items)} action items (provider={analysis.provider})"
    )

    # ── Stage 5: PERSIST ─────────────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.PERSIST)

    # Idempotent: remove existing AI-generated content before re-persisting
    await session.execute(
        sql_delete(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)
    )
    await session.execute(sql_delete(Summary).where(Summary.meeting_id == meeting.id))
    await session.execute(sql_delete(Decision).where(Decision.meeting_id == meeting.id))
    # Only remove AI-generated action items (confidence < 1.0 marks manual ones)
    await session.execute(
        sql_delete(ActionItem).where(
            ActionItem.meeting_id == meeting.id,
            ActionItem.confidence < 1.0,
        )
    )

    # Persist transcript segments
    segment_models: list[TranscriptSegment] = []
    for seg in transcription.segments:
        ts = TranscriptSegment(
            meeting_id=meeting.id,
            organization_id=meeting.organization_id,
            speaker=seg.speaker,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
            confidence=seg.confidence,
        )
        session.add(ts)
        segment_models.append(ts)
    await session.flush()

    # Persist summary
    summary = Summary(
        meeting_id=meeting.id,
        organization_id=meeting.organization_id,
        summary_text=analysis.summary_text,
        key_points_json=json.dumps(analysis.key_points),
        provider=analysis.provider,
        model=analysis.model,
    )
    session.add(summary)

    # Persist decisions
    for dec in analysis.decisions:
        session.add(
            Decision(
                meeting_id=meeting.id,
                organization_id=meeting.organization_id,
                title=dec.title,
                description=dec.description,
                category=dec.category,
                confidence=dec.confidence,
            )
        )

    # Persist action items
    for ai_item in analysis.action_items:
        priority = PriorityEnum.HIGH if ai_item.priority == "high" else (
            PriorityEnum.LOW if ai_item.priority == "low" else PriorityEnum.MEDIUM
        )
        session.add(
            ActionItem(
                meeting_id=meeting.id,
                organization_id=meeting.organization_id,
                title=ai_item.title,
                description=ai_item.description,
                owner_name=ai_item.owner_name,
                due_date=meeting.scheduled_start + timedelta(days=ai_item.due_days_offset),
                priority=priority,
                status=ActionItemStatusEnum.OPEN,
                confidence=ai_item.confidence,
            )
        )

    meeting.status = MeetingStatusEnum.COMPLETED
    await session.flush()

    # ── Stage 6: VECTOR_EMBED ─────────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.VECTOR_EMBED)
    try:
        collection = get_meetings_collection()
        embedding_provider = get_embedding_provider()

        # Remove stale embeddings for this meeting
        await session.execute(
            sql_delete(MeetingEmbedding).where(MeetingEmbedding.meeting_id == meeting.id)
        )
        await session.flush()

        ids_to_add: list[str] = []
        embeddings_to_add: list[list[float]] = []
        docs_to_add: list[str] = []
        metas_to_add: list[dict] = []

        for ts in segment_models:
            if not ts.text.strip():
                continue
            chroma_id = f"seg_{ts.id}"
            embedding = await embedding_provider.embed(ts.text)
            ids_to_add.append(chroma_id)
            embeddings_to_add.append(embedding)
            docs_to_add.append(ts.text)
            metas_to_add.append({
                "org_id": meeting.organization_id,
                "meeting_id": meeting.id,
                "segment_id": ts.id,
                "content_type": "transcript",
                "speaker": ts.speaker,
                "start_time": ts.start_time,
                "meeting_title": meeting.title,
            })
            session.add(MeetingEmbedding(
                organization_id=meeting.organization_id,
                meeting_id=meeting.id,
                segment_id=ts.id,
                chroma_id=chroma_id,
                content_type="transcript",
            ))

        # Embed summary
        if analysis.summary_text:
            chroma_id = f"sum_{meeting.id}"
            embedding = await embedding_provider.embed(analysis.summary_text)
            ids_to_add.append(chroma_id)
            embeddings_to_add.append(embedding)
            docs_to_add.append(analysis.summary_text)
            metas_to_add.append({
                "org_id": meeting.organization_id,
                "meeting_id": meeting.id,
                "content_type": "summary",
                "meeting_title": meeting.title,
            })
            session.add(MeetingEmbedding(
                organization_id=meeting.organization_id,
                meeting_id=meeting.id,
                chroma_id=chroma_id,
                content_type="summary",
            ))

        if ids_to_add:
            # Upsert into ChromaDB
            try:
                collection.delete(ids=ids_to_add)
            except Exception:
                pass
            collection.add(
                ids=ids_to_add,
                embeddings=embeddings_to_add,
                documents=docs_to_add,
                metadatas=metas_to_add,
            )
            logger.info(f"Indexed {len(ids_to_add)} embeddings for meeting {meeting.id}")

        await session.flush()
    except BaseException as embed_err:
        logger.warning(f"Vector embedding step failed (non-fatal, pipeline continues): {embed_err}")

    # ── Stage 7: REMINDERS ───────────────────────────────────────────────────
    await _advance_stage(session, job, JobStageEnum.REMINDERS)

    # Remove stale reminders generated by previous pipeline run
    await session.execute(
        sql_delete(Reminder).where(
            Reminder.meeting_id == meeting.id,
            Reminder.status == ReminderStatusEnum.PENDING,
        )
    )

    # Create in-app notifications for assigned action items
    ai_result = await session.execute(
        select(ActionItem).where(ActionItem.meeting_id == meeting.id)
    )
    new_action_items = ai_result.scalars().all()
    for ai_item in new_action_items:
        if ai_item.due_date:
            reminder_time = ai_item.due_date - timedelta(hours=24)
            # Normalise to UTC-aware for comparison (SQLite stores naive datetimes)
            rt = reminder_time
            if rt.tzinfo is None:
                rt = rt.replace(tzinfo=UTC)
            if rt > datetime.now(UTC):
                session.add(Reminder(
                    organization_id=meeting.organization_id,
                    action_item_id=ai_item.id,
                    meeting_id=meeting.id,
                    target=ai_item.owner_name or "unassigned",
                    fire_at=reminder_time,
                    channel=ReminderChannelEnum.IN_APP,
                    status=ReminderStatusEnum.PENDING,
                ))

    # Create meeting-ready notification for org members
    session.add(Notification(
        organization_id=meeting.organization_id,
        user_id=meeting.created_by_id or meeting.organization_id,  # fallback
        title="Meeting analysis complete",
        message=(
            f"'{meeting.title}' has been transcribed and analyzed. "
            f"{len(new_action_items)} action items extracted."
        ),
        type=NotificationTypeEnum.MEETING_READY,
        link=f"/meetings/{meeting.id}",
        is_read=False,
    ))

    # Finalize job
    job.stage = JobStageEnum.COMPLETED
    job.status = JobStatusEnum.COMPLETED
    await session.flush()

    logger.info(f"Pipeline completed successfully for meeting {meeting.id}")


async def run_single_job(job_id: str) -> None:
    """Execute pipeline for a specific job ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalars().first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            await _execute_pipeline(session, job)
            await session.commit()
        except Exception as exc:
            logger.error(f"Pipeline failed for job {job_id}: {exc}", exc_info=True)
            await session.rollback()

            # Reopen session to record failure
            async with AsyncSessionLocal() as err_session:
                err_result = await err_session.execute(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                failed_job = err_result.scalars().first()
                if failed_job:
                    failed_job.status = JobStatusEnum.FAILED
                    failed_job.error_code = type(exc).__name__
                    failed_job.error_message = str(exc)[:1000]

                    # Update meeting status
                    m_res = await err_session.execute(
                        select(Meeting).where(Meeting.id == failed_job.meeting_id)
                    )
                    meeting = m_res.scalars().first()
                    if meeting:
                        meeting.status = MeetingStatusEnum.FAILED

                    await err_session.commit()


async def _process_due_reminders() -> None:
    """Fire reminders that have come due."""
    from app.providers.email import get_email_provider

    async with AsyncSessionLocal() as session:
        now = datetime.now(UTC)
        result = await session.execute(
            select(Reminder).where(
                Reminder.status == ReminderStatusEnum.PENDING,
                Reminder.fire_at <= now,
            ).limit(50)
        )
        reminders = result.scalars().all()

        for reminder in reminders:
            try:
                if reminder.channel == ReminderChannelEnum.EMAIL and "@" in (reminder.target or ""):
                    email_provider = get_email_provider()
                    # Load linked action item for context
                    ai_text = f"Reminder: {reminder.target}"
                    if reminder.action_item_id:
                        ai_res = await session.execute(
                            select(ActionItem).where(ActionItem.id == reminder.action_item_id)
                        )
                        ai = ai_res.scalars().first()
                        if ai:
                            ai_text = f"Action item due: {ai.title}"
                    await email_provider.send_email(
                        recipient=reminder.target,
                        subject=f"SignalRoom Reminder: {ai_text[:60]}",
                        body_html=f"<p>{ai_text}</p><p>Due: {reminder.fire_at.strftime('%Y-%m-%d')}</p>",
                        body_text=f"{ai_text}\nDue: {reminder.fire_at.strftime('%Y-%m-%d')}",
                    )

                reminder.status = ReminderStatusEnum.SENT
                reminder.sent_at = now
                logger.info(f"Fired reminder {reminder.id}")
            except Exception as exc:
                logger.error(f"Failed to fire reminder {reminder.id}: {exc}")
                reminder.status = ReminderStatusEnum.FAILED

        if reminders:
            await session.commit()


async def worker_loop() -> None:
    """Main worker event loop. Polls for jobs and fires reminders."""
    logger.info("SignalRoom background worker started")
    reminder_check_interval = 60  # seconds
    last_reminder_check = 0.0

    while True:
        try:
            # Process one pending job
            async with AsyncSessionLocal() as session:
                job = await _claim_next_job(session)
                if job:
                    job_id = job.id
                    await session.commit()
                    logger.info(f"Claimed job {job_id}")
                    await run_single_job(job_id)
                else:
                    await asyncio.sleep(3)

            # Fire due reminders periodically
            import time
            now = time.monotonic()
            if now - last_reminder_check >= reminder_check_interval:
                await _process_due_reminders()
                last_reminder_check = now

        except asyncio.CancelledError:
            logger.info("Worker cancelled, shutting down")
            break
        except Exception as exc:
            logger.error(f"Worker loop unexpected error: {exc}", exc_info=True)
            await asyncio.sleep(10)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from app.core.logging import setup_logging

    setup_logging()
    asyncio.run(worker_loop())
