import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'
import { QueryProvider } from '@/lib/providers/query-provider'

export const metadata: Metadata = {
  title: 'QuantaBench — Honest quantum optimization benchmarks',
  description: 'Compare QAOA against classical portfolio solvers with transparent, reproducible results.',
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: 'white',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <QueryProvider>
          {children}
        </QueryProvider>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
