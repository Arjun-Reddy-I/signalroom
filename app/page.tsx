'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/signalroom/workspace-shell'
import { hasSession } from '@/lib/api/auth'
import { getDashboardData } from '@/services/dashboard'
import { EMPTY_DASHBOARD, type DashboardData } from '@/types/signalroom'

export default function Page() {
  const router = useRouter()
  const [data, setData] = useState<DashboardData>(EMPTY_DASHBOARD)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!hasSession()) {
      router.replace('/login')
      return
    }

    void (async () => {
      try {
        const nextData = await getDashboardData()
        setData(nextData)
      } catch {
        router.replace('/login')
      } finally {
        setLoading(false)
      }
    })()
  }, [router])

  if (loading) {
    return (
      <main className="auth-shell">
        <div className="auth-panel">
          <div className="auth-brand">
            <span className="brand-mark">S</span>
            <span>Signalroom</span>
          </div>
          <h1>Loading workspace</h1>
          <p>Syncing your latest meetings and action items.</p>
        </div>
      </main>
    )
  }

  return <AppShell data={data} />
}
