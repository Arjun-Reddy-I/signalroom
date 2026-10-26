'use client'

import { X } from 'lucide-react'
import { motion } from 'framer-motion'
import { type Meeting, formatDateLong, getMeetingStatusTone } from '@/types/signalroom'
import { layoutTransition } from '@/lib/motion'

export function MeetingDialog({ meeting, onClose }: { meeting: Meeting; onClose: () => void }) {
  return (
    <div
      className="dialog-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        className="dialog meeting-dialog"
        role="dialog"
        aria-modal="true"
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        transition={layoutTransition}
      >
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
      </motion.div>
    </div>
  )
}
