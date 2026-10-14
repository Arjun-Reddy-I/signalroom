'use client'

import { useEffect, useState } from 'react'
import { BarChart3, Check, CalendarDays, TrendingUp } from 'lucide-react'
import { apiFetch } from '@/lib/api/client'

type Aggregates = {
  total_meetings: number
  completed_meetings: number
  active_projects: number
  open_action_items: number
  overdue_action_items: number
}

function StatBlock({
  label,
  value,
  sub,
  tone = '',
}: {
  label: string
  value: string | number
  sub?: string
  tone?: string
}) {
  return (
    <article className="stat-card">
      <span className="eyebrow">{label}</span>
      <strong className={`stat-value ${tone}`}>{value}</strong>
      {sub && <span className="stat-detail">{sub}</span>}
    </article>
  )
}

function SimpleBar({ pct, tone = 'bar-primary' }: { pct: number; tone?: string }) {
  return (
    <div className="progress-track" style={{ width: '100%', marginTop: '0.5rem' }}>
      <span
        className={tone}
        style={{
          width: `${Math.min(100, Math.max(0, pct))}%`,
          height: '8px',
          display: 'block',
          background: 'var(--primary)',
          borderRadius: '4px',
          transition: 'width 0.6s ease',
        }}
      />
    </div>
  )
}

export function AnalyticsView() {
  const [agg, setAgg] = useState<Aggregates | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void apiFetch<Aggregates>('/dashboard/aggregates')
      .then(setAgg)
      .catch(() => setAgg(null))
      .finally(() => setLoading(false))
  }, [])

  const completionRate =
    agg && agg.total_meetings > 0
      ? Math.round((agg.completed_meetings / agg.total_meetings) * 100)
      : 0

  const overdueRate =
    agg && agg.open_action_items > 0
      ? Math.round((agg.overdue_action_items / agg.open_action_items) * 100)
      : 0

  return (
    <div className="view-stack">
      <div className="view-heading">
        <div>
          <span className="eyebrow">Workspace intelligence</span>
          <h1>Analytics</h1>
        </div>
        <BarChart3 />
      </div>

      {loading ? (
        <p className="muted-text">Loading analytics…</p>
      ) : !agg ? (
        <p className="muted-text">Analytics unavailable. Ensure the API is running.</p>
      ) : (
        <>
          <div className="stats-grid">
            <StatBlock label="Total meetings" value={agg.total_meetings} sub="All time" />
            <StatBlock
              label="Completed meetings"
              value={agg.completed_meetings}
              sub={`${completionRate}% completion rate`}
            />
            <StatBlock label="Active projects" value={agg.active_projects} />
            <StatBlock
              label="Open action items"
              value={agg.open_action_items}
              sub={`${agg.overdue_action_items} overdue`}
              tone={agg.overdue_action_items > 0 ? 'amber-text' : ''}
            />
          </div>

          <div className="content-grid" style={{ marginTop: '2rem' }}>
            <section className="panel">
              <div className="section-head">
                <div>
                  <span className="eyebrow">Performance</span>
                  <h2>Meeting completion rate</h2>
                </div>
                <TrendingUp />
              </div>
              <p className="stat-value">{completionRate}%</p>
              <SimpleBar pct={completionRate} />
              <p className="stat-detail" style={{ marginTop: '0.5rem' }}>
                {agg.completed_meetings} of {agg.total_meetings} meetings fully processed
              </p>
            </section>

            <section className="panel">
              <div className="section-head">
                <div>
                  <span className="eyebrow">Follow-through</span>
                  <h2>Action item health</h2>
                </div>
                <Check />
              </div>
              <p className={`stat-value ${overdueRate > 20 ? 'amber-text' : ''}`}>
                {100 - overdueRate}%
              </p>
              <SimpleBar pct={100 - overdueRate} />
              <p className="stat-detail" style={{ marginTop: '0.5rem' }}>
                {agg.open_action_items - agg.overdue_action_items} on-track /{' '}
                {agg.overdue_action_items} overdue
              </p>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
