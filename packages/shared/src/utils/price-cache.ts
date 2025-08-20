interface CachedPrice {
  price: number;
  timestamp: Date;
  expiresAt: Date;
}

export class PriceCache {
  private cache = new Map<string, CachedPrice>();
  private readonly TTL_MS: number;

  constructor(ttlSeconds: number = 30) {
    this.TTL_MS = ttlSeconds * 1000;
  }

  private generateKey(exchange: string, symbol: string): string {
    return `${exchange}:${symbol}`;
  }

  get(exchange: string, symbol: string): { price: number; timestamp: Date } | null {
    const key = this.generateKey(exchange, symbol);
    const cached = this.cache.get(key);

    if (!cached) {
      return null;
    }

    // Check if expired
    if (new Date() > cached.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return {
      price: cached.price,
      timestamp: cached.timestamp,
    };
  }

  set(exchange: string, symbol: string, price: number, timestamp: Date): void {
    const key = this.generateKey(exchange, symbol);
    const expiresAt = new Date(Date.now() + this.TTL_MS);

    this.cache.set(key, {
      price,
      timestamp,
      expiresAt,
    });
  }

  clear(): void {
    this.cache.clear();
  }

  cleanup(): number {
    const now = new Date();
    let removedCount = 0;

    for (const [key, value] of this.cache.entries()) {
      if (now > value.expiresAt) {
        this.cache.delete(key);
        removedCount++;
      }
    }

    return removedCount;
  }

  size(): number {
    return this.cache.size;
  }
}

// Singleton instance for global use
export const priceCache = new PriceCache(30); // 30 seconds TTL

// Auto-cleanup every 5 minutes
setInterval(() => {
  const removed = priceCache.cleanup();
  if (removed > 0) {
    console.log(`PriceCache: Cleaned up ${removed} expired entries`);
  }
}, 5 * 60 * 1000);