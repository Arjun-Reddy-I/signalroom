'use client'

import { useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'signalroom-theme'

export function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') return getSystemTheme()
  return mode
}

export function applyTheme(mode: ThemeMode): void {
  if (typeof document === 'undefined') return
  const resolved = resolveTheme(mode)
  document.documentElement.dataset.theme = resolved
  document.documentElement.style.colorScheme = resolved
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'dark'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

export function saveTheme(mode: ThemeMode): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEY, mode)
}

export function useThemeMode() {
  const [theme, setTheme] = useState<ThemeMode>('system')

  useEffect(() => {
    setTheme(getStoredTheme())
    applyTheme(getStoredTheme())

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (getStoredTheme() === 'system') applyTheme('system')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    applyTheme(theme)
    saveTheme(theme)
  }, [theme])

  return { theme, setTheme }
}
