'use client'

import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { type NewProjectInput } from '@/types/signalroom'

export function ProjectDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void
  onCreate: (input: NewProjectInput) => void
}) {
  const [input, setInput] = useState<NewProjectInput>({ name: '', client: '' })
  const [touched, setTouched] = useState(false)
  const valid = input.name.trim().length > 1 && input.client.trim().length > 1

  return (
    <div
      className="dialog-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="dialog" role="dialog" aria-modal="true">
        <button className="dialog-close" aria-label="Close dialog" onClick={onClose}>
          <X />
        </button>
        <span className="dialog-mark">
          <Plus />
        </span>
        <span className="eyebrow">New workspace record</span>
        <h2>Create a new project</h2>
        <p>Projects are saved to the connected workspace.</p>
        <div className="dialog-fields">
          <label>
            Project name
            <input
              autoFocus
              value={input.name}
              onChange={(e) => setInput({ ...input, name: e.target.value })}
              placeholder="e.g. Brand refresh"
            />
          </label>
          <label>
            Client
            <input
              value={input.client}
              onChange={(e) => setInput({ ...input, client: e.target.value })}
              placeholder="e.g. Northstar Health"
            />
          </label>
        </div>
        {touched && !valid && (
          <p className="form-error">Add a project name and client to continue.</p>
        )}
        <div className="dialog-actions">
          <button className="button-quiet" onClick={onClose}>
            Cancel
          </button>
          <button
            className="button-primary"
            onClick={() => {
              setTouched(true)
              if (valid) onCreate(input)
            }}
          >
            <Plus /> Add project
          </button>
        </div>
      </div>
    </div>
  )
}
