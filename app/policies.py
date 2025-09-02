import time
from typing import Callable, Any, Tuple

def retry_with_backoff(fn: Callable[[], Any], *, retries: int = 4, base: float = 0.8) -> Tuple[bool, Any]:
    last_err = None
    for attempt in range(retries):
        try:
            return True, fn()
        except Exception as e:
            last_err = e
            sleep = base * (2 ** attempt)
            time.sleep(sleep)
    return False, last_err
