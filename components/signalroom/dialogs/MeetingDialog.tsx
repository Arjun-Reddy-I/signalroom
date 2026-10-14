'use client'

import { X } from 'lucide-react'
import { type Meeting, formatDateLong, getMeetingStatusTone } from '@/types/signalroom'

export function MeetingDialog({ meeting, onClose }: { meeting: Meeting; onClose: () => void }) {
  return (
    <div
      className="dialog-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="dialog meeting-dialog">
        <button className="dialog-close" onClick={onClose} aria-label="Close meeting">
          <X />
        </button>
        <div className="eyebrow">
          {meeting.project} / {formatDateLong(meeting.date)}
        </div>
        <h2>{meeting.title}</h2>
        <p>{meeting.summary}</p>
        <div className="detail-grid">
          <div>
            <span className="eyebrow">Status</span>
            <strong className={getMeetingStatusTone(meeting.status)}>{meeting.status}</strong>
          </div>
          <div>
            <span className="eyebrow">Confidence</span>
            <strong>{meeting.confidence ? `${meeting.confidence}%` : 'Processing'}</strong>
          </div>
          <div>
            <span className="eyebrow">Duration</span>
            <strong>{meeting.duration}</strong>
          </div>
          <div>
            <span className="eyebrow">Participants</span>
            <strong>{meeting.attendees.length ? meeting.attendees.join(', ') : 'Unavailable'}</strong>
          </div>
        </div>
        {meeting.decisions.length > 0 && (
          <div className="dialog-section">
            <span className="eyebrow">Decisions</span>
            <ul>{meeting.decisions.map((d, i) => <li key={i}>{d}</li>)}</ul>
          </div>
        )}
        {meeting.actionItems.length > 0 && (
          <div className="dialog-section">
            <span className="eyebrow">Action items</span>
            <ul>{meeting.actionItems.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </div>
        )}
        <a
          className="button-primary dialog-wide"
          href={`/meetings/${meeting.id}`}
          style={{ textAlign: 'center', display: 'block' }}
        >
          Open meeting detail
        </a>
      </div>
    </div>
  )
}
