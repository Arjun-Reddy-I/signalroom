"""Semantic + full-text search across meeting content.

Search is scoped strictly to the authenticated user's organization.
Uses ChromaDB for semantic similarity + SQL LIKE for full-text fallback.
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_db
from app.db.vector_store import get_meetings_collection
from app.models import ActionItem, Decision, Meeting, Organization, Summary, TranscriptSegment
from app.providers.embeddings import get_embedding_provider
from app.schemas.domain import SearchHit, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
async def search_workspace(
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search meeting transcripts, summaries, decisions, and action items.

    Combines:
    1. ChromaDB semantic vector search (requires embeddings to be indexed)
    2. SQL LIKE full-text search as fallback/supplement
    """
    hits: list[SearchHit] = []
    seen_ids: set[str] = set()

    # ── 1. Vector semantic search ──────────────────────────────────────────
    try:
        embedding_provider = get_embedding_provider()
        query_embedding = await embedding_provider.embed(q)
        collection = get_meetings_collection()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit * 2, 20),
            where={"org_id": org.id},
            include=["documents", "metadatas", "distances"],
        )

        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        distances_list = results.get("distances", [[]])[0]

        for chroma_id, doc, meta, distance in zip(ids_list, docs_list, metas_list, distances_list):
            meeting_id = meta.get("meeting_id", "")
            content_type = meta.get("content_type", "transcript")
            score = max(0.0, 1.0 - float(distance))

            # Load meeting title
            m_res = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
            meeting = m_res.scalars().first()
            if not meeting:
                continue

            hit_id = f"{content_type}:{chroma_id}"
            if hit_id not in seen_ids:
                seen_ids.add(hit_id)
                hits.append(SearchHit(
                    meeting_id=meeting_id,
                    meeting_title=meeting.title,
                    content_type=content_type,
                    text=doc[:500],
                    score=round(score, 3),
                    metadata={
                        "speaker": meta.get("speaker", ""),
                        "start_time": meta.get("start_time", 0),
                        "segment_id": meta.get("segment_id", ""),
                    },
                ))
    except Exception as vec_err:
        # Vector search failed (e.g. no embeddings indexed yet) — fall through to SQL
        logger.info(f"Vector search unavailable ({vec_err}), using SQL full-text search")

    # ── 2. SQL full-text search (always runs to supplement / fill gaps) ────
    q_like = f"%{q}%"

    # Transcript segments
    ts_res = await db.execute(
        select(TranscriptSegment, Meeting.title)
        .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
        .where(
            TranscriptSegment.organization_id == org.id,
            TranscriptSegment.text.ilike(q_like),
        )
        .limit(limit)
    )
    for ts, mtitle in ts_res.all():
        hit_id = f"transcript:{ts.id}"
        if hit_id not in seen_ids:
            seen_ids.add(hit_id)
            hits.append(SearchHit(
                meeting_id=ts.meeting_id,
                meeting_title=mtitle,
                content_type="transcript",
                text=ts.text[:500],
                score=0.5,
                metadata={"speaker": ts.speaker, "start_time": ts.start_time},
            ))

    # Summaries
    sum_res = await db.execute(
        select(Summary, Meeting.title)
        .join(Meeting, Meeting.id == Summary.meeting_id)
        .where(
            Summary.organization_id == org.id,
            or_(
                Summary.summary_text.ilike(q_like),
                Summary.key_points_json.ilike(q_like),
            ),
        )
        .limit(limit)
    )
    for summ, mtitle in sum_res.all():
        hit_id = f"summary:{summ.id}"
        if hit_id not in seen_ids:
            seen_ids.add(hit_id)
            hits.append(SearchHit(
                meeting_id=summ.meeting_id,
                meeting_title=mtitle,
                content_type="summary",
                text=summ.summary_text[:500],
                score=0.6,
                metadata={},
            ))

    # Decisions
    dec_res = await db.execute(
        select(Decision, Meeting.title)
        .join(Meeting, Meeting.id == Decision.meeting_id)
        .where(
            Decision.organization_id == org.id,
            or_(Decision.title.ilike(q_like), Decision.description.ilike(q_like)),
        )
        .limit(limit)
    )
    for dec, mtitle in dec_res.all():
        hit_id = f"decision:{dec.id}"
        if hit_id not in seen_ids:
            seen_ids.add(hit_id)
            hits.append(SearchHit(
                meeting_id=dec.meeting_id,
                meeting_title=mtitle,
                content_type="decision",
                text=dec.title + (f": {dec.description}" if dec.description else ""),
                score=0.65,
                metadata={"category": dec.category or ""},
            ))

    # Action items
    ai_res = await db.execute(
        select(ActionItem, Meeting.title)
        .join(Meeting, Meeting.id == ActionItem.meeting_id)
        .where(
            ActionItem.organization_id == org.id,
            or_(ActionItem.title.ilike(q_like), ActionItem.description.ilike(q_like)),
        )
        .limit(limit)
    )
    for ai_item, mtitle in ai_res.all():
        hit_id = f"action_item:{ai_item.id}"
        if hit_id not in seen_ids:
            seen_ids.add(hit_id)
            hits.append(SearchHit(
                meeting_id=ai_item.meeting_id,
                meeting_title=mtitle,
                content_type="action_item",
                text=ai_item.title + (f": {ai_item.description}" if ai_item.description else ""),
                score=0.55,
                metadata={
                    "owner": ai_item.owner_name or "",
                    "status": str(ai_item.status),
                    "priority": str(ai_item.priority),
                },
            ))

    # Sort by score descending, cap at limit
    hits.sort(key=lambda h: h.score, reverse=True)
    hits = hits[:limit]

    return SearchResponse(query=q, hits=hits, total=len(hits))
