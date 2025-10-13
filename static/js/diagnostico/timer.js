
export class CountdownTimer {
  /**
   * @param {number} remainingSeconds - segundos restantes (int)
   * @param {function} onTick - callback(remainingSeconds)
   * @param {function} onFinish - callback()
   */
  constructor({ remainingSeconds = 0, onTick = null, onFinish = null }) {
    this.remaining = Math.max(0, Math.floor(remainingSeconds));
    this.onTick = onTick;
    this.onFinish = onFinish;
    this.interval = null;
    this.startedAt = null;
  }

  start() {
    if (this.interval) clearInterval(this.interval);
    this.startedAt = new Date();
    this._tick();
    this.interval = setInterval(() => this._tick(), 1000);
  }

  _tick() {
    const now = new Date();
    const elapsedSec = Math.floor((now - this.startedAt) / 1000);
    const currentRemaining = Math.max(0, this.remaining - elapsedSec);

    if (this.onTick) this.onTick(currentRemaining);

    if (currentRemaining <= 0) {
      // detener primero para evitar múltiples invocaciones
      this.stop();
      if (this.onFinish) this.onFinish();
    }
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  getRemainingSeconds() {
    if (!this.startedAt) return this.remaining;
    const now = new Date();
    const elapsedSec = Math.floor((now - this.startedAt) / 1000);
    return Math.max(0, this.remaining - elapsedSec);
  }
}
