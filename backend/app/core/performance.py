import time
from functools import wraps


def measure(name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            print(f"[PERF] {name}: {duration:.3f}s")
            return result

        return wrapper

    return decorator
