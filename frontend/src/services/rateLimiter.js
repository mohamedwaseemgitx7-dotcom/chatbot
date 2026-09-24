/**
 * Token-bucket rate limiter (client side).
 * The bucket holds `capacity` tokens; each message spends one; tokens refill at `refillPerSecond`.
 * The real limit must also be enforced on the server — this only protects the UI and gives quick feedback.
 */
export class TokenBucket {
  constructor({ capacity = 5, refillPerSecond = 0.5 } = {}) {
    this.capacity = capacity;
    this.refillPerSecond = refillPerSecond;
    this.tokens = capacity;
    this.lastRefill = Date.now();
  }

  refill() {
    const now = Date.now();
    const elapsedSeconds = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSeconds * this.refillPerSecond);
    this.lastRefill = now;
  }

  /** @returns {{ allowed: boolean, retryInSeconds: number }} */
  tryConsume() {
    this.refill();
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return { allowed: true, retryInSeconds: 0 };
    }
    const retryInSeconds = Math.ceil((1 - this.tokens) / this.refillPerSecond);
    return { allowed: false, retryInSeconds };
  }
}
