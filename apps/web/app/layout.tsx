import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import { Activity, BarChart3, Home, Settings } from 'lucide-react'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'TradingView Gateway',
  description: 'Production-grade TradingView webhook to exchange gateway',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {/* Navigation */}
          <nav className="bg-white border-b border-gray-200">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <div className="flex-shrink-0 flex items-center">
                    <Link href="/" className="text-xl font-bold text-gray-900">
                      TradingView Gateway
                    </Link>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <Link
                      href="/"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                    >
                      <Home className="w-4 h-4 mr-2" />
                      Dashboard
                    </Link>
                    <Link
                      href="/monitoring"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      <Activity className="w-4 h-4 mr-2" />
                      Monitoring
                    </Link>
                    <Link
                      href="/metrics"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      <BarChart3 className="w-4 h-4 mr-2" />
                      Metrics
                    </Link>
                    <Link
                      href="/settings"
                      className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 hover:text-blue-600"
                    >
                      <Settings className="w-4 h-4 mr-2" />
                      Settings
                    </Link>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="flex-shrink-0">
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      Demo Mode
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main>{children}</main>
        </div>
      </body>
    </html>
  )
}