import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Calcula o número ideal de casas decimais baseado no valor do preço
 * Para meme coins e ativos de baixo valor, precisamos de mais casas decimais
 */
export function getOptimalDecimals(value: number): number {
  const absValue = Math.abs(value)
  if (absValue === 0) return 2
  if (absValue >= 1000) return 2      // BTC, ETH - $1000+ = 2 decimais
  if (absValue >= 1) return 4         // SOL, AVAX - $1-$999 = 4 decimais
  if (absValue >= 0.01) return 6      // Low cap coins - $0.01-$0.99 = 6 decimais
  if (absValue >= 0.0001) return 8    // Meme coins - $0.0001-$0.0099 = 8 decimais
  return 10                           // Ultra low - menos de $0.0001 = 10 decimais
}

export function formatCurrency(value: number, currency = 'USDT', decimals?: number): string {
  // Se decimais não foi especificado, calcular automaticamente
  const optimalDecimals = decimals ?? getOptimalDecimals(value)
  return new Intl.NumberFormat('pt-BR', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: optimalDecimals,
  }).format(value) + ` ${currency}`
}

export function formatPercentage(value: number, decimals = 2): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100)
}

export function formatNumber(value: number, decimals = 8): string {
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(date))
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func(...args), delay)
  }
}

export function truncateAddress(address: string, start = 6, end = 4): string {
  if (address.length <= start + end) return address
  return `${address.slice(0, start)}...${address.slice(-end)}`
}