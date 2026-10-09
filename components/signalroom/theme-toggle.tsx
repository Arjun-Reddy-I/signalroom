'use client'

import { Monitor, Moon, Sun } from 'lucide-react'
import { useThemeMode, type ThemeMode } from '@/lib/theme'

const options: { value: ThemeMode; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

export function ThemeToggle() {
  const { theme, setTheme } = useThemeMode()

  return (
    <div className="theme-toggle" aria-label="Theme selector">
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          className={theme === value ? 'theme-option active' : 'theme-option'}
          onClick={() => setTheme(value)}
          aria-pressed={theme === value}
          title={label}
        >
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}
