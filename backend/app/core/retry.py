import time


def retry(func, retries=3, delay=1):
    last = None

    for _ in range(retries):
        try:
            return func()
        except Exception as e:
            last = e
            time.sleep(delay)

    raise last
