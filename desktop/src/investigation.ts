type Attempt = {
  runId: string | null;
  cancelling: boolean;
};

// An attempt exists before Rust returns its ID. Its identity also guards
// pending invoke callbacks after a later attempt starts.
export class InvestigationFlow {
  private current: Attempt | null = null;

  begin(): Attempt | null {
    if (this.current) return null;
    this.current = { runId: null, cancelling: false };
    return this.current;
  }

  acknowledge(attempt: Attempt, runId: string): boolean {
    if (this.current !== attempt || attempt.runId !== null) return false;
    attempt.runId = runId;
    return true;
  }

  acceptsProgress(attempt: Attempt, runId: string): boolean {
    return this.current === attempt && attempt.runId === runId && !attempt.cancelling;
  }

  requestCancellation(): { attempt: Attempt; runId: string } | null {
    const attempt = this.current;
    if (!attempt?.runId || attempt.cancelling) return null;
    attempt.cancelling = true;
    return { attempt, runId: attempt.runId };
  }

  isCurrent(attempt: Attempt): boolean {
    return this.current === attempt;
  }

  retryCancellation(attempt: Attempt): boolean {
    if (!this.isCurrent(attempt)) return false;
    attempt.cancelling = false;
    return true;
  }

  finish(attempt: Attempt, runId?: string): boolean {
    if (!this.isCurrent(attempt)
        || (runId !== undefined && attempt.runId !== null && attempt.runId !== runId)) {
      return false;
    }
    this.current = null;
    return true;
  }
}
