import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

const themeScript = `
  (() => {
    try {
      const stored = localStorage.getItem('signalroom-theme')
      const mode = stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
      const resolved = mode === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : mode
      document.documentElement.dataset.theme = resolved
      document.documentElement.style.colorScheme = resolved
    } catch (error) {
      document.documentElement.dataset.theme = 'dark'
      document.documentElement.style.colorScheme = 'dark'
    }
  })();
`

export const metadata: Metadata = {
  title: 'Signalroom — Northstar Studio',
  description: 'A calm command center for creative work.',
  generator: 'Signalroom',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#17151d',
  userScalable: false,
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
