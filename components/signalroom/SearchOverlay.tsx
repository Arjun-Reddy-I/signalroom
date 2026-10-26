'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
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
  const [error, setError] = useState('')

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  async function handleSearch(q: string) {
    setQuery(q)
    if (q.trim().length < 2) {
      setHits([])
      setSearched(false)
      setError('')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch<{ hits: SearchHit[]; total: number }>(
        `/search?q=${encodeURIComponent(q)}&limit=15`,
      )
      setHits(res.hits)
      setSearched(true)
    } catch (err: unknown) {
      setHits([])
      setSearched(true)
      setError(err instanceof Error ? err.message : 'Search is unavailable. Try again.')
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
    <motion.div
      className="search-layer"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div className="search-dialog" initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.99 }} transition={{ duration: 0.24 }}>
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
          {!loading && error && (
            <div className="search-error" role="alert">
              <strong>Search unavailable</strong>
              <span>{error}</span>
              <button className="button-quiet" onClick={() => void handleSearch(query)}>Retry</button>
            </div>
          )}
          {!loading && searched && !error && hits.length === 0 && (
            <EmptyState title="No matches" copy="Try a meeting title, decision, action item, or person name." />
          )}
          {!loading &&
            hits.length > 0 &&
            (() => {
              const groups = hits.reduce<Record<string, SearchHit[]>>((acc, hit) => {
                const key = hit.content_type
                if (!acc[key]) acc[key] = []
                acc[key].push(hit)
                return acc
              }, {})
              return Object.keys(groups).map((type) => (
                <div key={type} className="search-group">
                  <span className="search-group-label">
                    {type === 'action_item'
                      ? 'Action Items'
                      : type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                  </span>
                  {groups[type].map((hit, i) => (
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
              ))
            })()}
        </div>
      </motion.div>
    </motion.div>
  )
}
