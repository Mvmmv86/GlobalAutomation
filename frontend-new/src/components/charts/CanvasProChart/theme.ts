/**
 * Chart Themes - Dark and Light
 */

import { ChartTheme } from './types'

export const DARK_THEME: ChartTheme = {
  background: '#131722',
  grid: {
    color: 'rgba(42, 46, 57, 0.5)',
    lineWidth: 1
  },
  candle: {
    up: {
      body: '#26a69a',
      wick: '#26a69a',
      border: '#26a69a'
    },
    down: {
      body: '#ef5350',
      wick: '#ef5350',
      border: '#ef5350'
    }
  },
  volume: {
    up: 'rgba(38, 166, 154, 0.5)',
    down: 'rgba(239, 83, 80, 0.5)'
  },
  crosshair: {
    color: 'rgba(255, 255, 255, 0.3)',
    lineWidth: 1,
    labelBackground: '#363a45',
    labelText: '#d1d4dc'
  },
  text: {
    primary: '#d1d4dc',
    secondary: '#787b86',
    fontSize: 12,
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  indicators: {
    ema9: '#2962ff',
    ema20: '#ff6d00',
    ema50: '#e91e63',
    sma20: '#9c27b0',
    sma50: '#00bcd4'
  },
  orders: {
    stopLoss: '#ef4444',
    takeProfit: '#10b981',
    position: '#3b82f6',
    dragPreview: '#60a5fa'
  }
}

export const LIGHT_THEME: ChartTheme = {
  background: '#ffffff',
  grid: {
    color: 'rgba(0, 0, 0, 0.06)',
    lineWidth: 1
  },
  candle: {
    up: {
      body: '#089981',
      wick: '#089981',
      border: '#089981'
    },
    down: {
      body: '#f23645',
      wick: '#f23645',
      border: '#f23645'
    }
  },
  volume: {
    up: 'rgba(8, 153, 129, 0.5)',
    down: 'rgba(242, 54, 69, 0.5)'
  },
  crosshair: {
    color: 'rgba(0, 0, 0, 0.2)',
    lineWidth: 1,
    labelBackground: '#e0e3eb',
    labelText: '#131722'
  },
  text: {
    primary: '#131722',
    secondary: '#787b86',
    fontSize: 12,
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  indicators: {
    ema9: '#2962ff',
    ema20: '#ff6d00',
    ema50: '#e91e63',
    sma20: '#9c27b0',
    sma50: '#00bcd4'
  },
  orders: {
    stopLoss: '#dc2626',
    takeProfit: '#059669',
    position: '#2563eb',
    dragPreview: '#3b82f6'
  }
}

export function getTheme(theme: 'dark' | 'light'): ChartTheme {
  return theme === 'dark' ? DARK_THEME : LIGHT_THEME
}
