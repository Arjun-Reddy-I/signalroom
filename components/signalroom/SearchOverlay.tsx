'use client'

import { useState } from 'react'
import { CalendarDays, Check, FileText, Search, Sparkles } from 'lucide-react'
import { type DashboardData, type Meeting, formatDateLong, isActionDone } from '@/types/signalroom'
import { apiFetch } from '@/lib/api/client'

type SearchHit = {
  meeting_id: string
  meeting_title: string
  content_type: string
  text: string
  score: number
  metadata: Record<string, unknown>
}

function EmptyState({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="empty-state">
      <Sparkles />
      <strong>{title}</strong>
      <span>{copy}</span>
    </div>
  )
}

export function SearchOverlay({
  data,
  onClose,
  onOpenMeeting,
}: {
  data: DashboardData
  onClose: () => void
  onOpenMeeting: (meeting: Meeting) => void
}) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function handleSearch(q: string) {
    setQuery(q)
    if (q.trim().length < 2) {
      setHits([])
      setSearched(false)
      return
    }
    setLoading(true)
    try {
      const res = await apiFetch<{ hits: SearchHit[]; total: number }>(
        `/search?q=${encodeURIComponent(q)}&limit=15`,
      )
      setHits(res.hits)
      setSearched(true)
    } catch {
      // Fall back to local data search
      const normalized = q.toLowerCase()
      const localHits: SearchHit[] = [
        ...data.meetings
          .filter((m) => `${m.title} ${m.project} ${m.summary}`.toLowerCase().includes(normalized))
          .map((m) => ({
            meeting_id: m.id,
            meeting_title: m.title,
            content_type: 'meeting',
            text: m.summary,
            score: 0.8,
            metadata: {},
          })),
        ...data.actionItems
          .filter((a) => `${a.title} ${a.owner}`.toLowerCase().includes(normalized))
          .map((a) => ({
            meeting_id: a.source,
            meeting_title: a.source,
            content_type: 'action_item',
            text: a.title,
            score: 0.7,
            metadata: { owner: a.owner, status: a.status },
          })),
      ]
      setHits(localHits)
      setSearched(true)
    } finally {
      setLoading(false)
    }
  }

  const contentIcon = (type: string) => {
    switch (type) {
      case 'transcript': return <CalendarDays />
      case 'summary': return <FileText />
      case 'decision': return <FileText />
      case 'action_item': return <Check />
      default: return <Search />
    }
  }

  return (
    <div
      className="search-layer"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="search-dialog">
        <div className="search-input-wrap">
          <Search />
          <input
            autoFocus
            value={query}
            onChange={(e) => void handleSearch(e.target.value)}
            placeholder="Search meetings, tasks, decisions, transcripts"
            aria-label="Global search"
          />
          <kbd>ESC</kbd>
        </div>
        <div className="search-results">
          {loading && (
            <div className="search-hint">
              <span>Searching workspace...</span>
            </div>
          )}
          {!loading && !searched && (
            <div className="search-hint">
              <Sparkles />
              <span>Search meeting transcripts, summaries, decisions, and tasks</span>
            </div>
          )}
          {!loading && searched && hits.length === 0 && (
            <EmptyState title="No matches" copy="Try a meeting title, decision, action item, or person name." />
          )}
          {!loading &&
            hits.map((hit, i) => (
              <button
                key={i}
                className="search-result"
                onClick={() => {
                  const match = data.meetings.find((m) => m.id === hit.meeting_id)
                  if (match) {
                    onOpenMeeting(match)
                    onClose()
                  } else {
                    window.location.href = `/meetings/${hit.meeting_id}`
                  }
                }}
              >
                {contentIcon(hit.content_type)}
                <span>
                  <strong>{hit.meeting_title}</strong>
                  <small>
                    {hit.content_type.replace('_', ' ')} — {hit.text.slice(0, 80)}
                    {hit.text.length > 80 ? '…' : ''}
                  </small>
                </span>
              </button>
            ))}
        </div>
      </div>
    </div>
  )
}
