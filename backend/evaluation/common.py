import time
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
RESULTS.mkdir(exist_ok=True)


def with_retry(fn, tries: int = 6):
    """Retry on Groq free-tier rate limits (HTTP 429) instead of failing the whole evaluation."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            if i < tries - 1 and ("429" in msg or "rate limit" in msg or "rate_limit" in msg):
                wait = 15 * (i + 1)
                print(f"   rate limited, waiting {wait}s ...", flush=True)
                time.sleep(wait)
            else:
                raise
