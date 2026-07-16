from dotenv import load_dotenv

# Mission Control edits this ignored file from the local Integration Center.
# It must remain authoritative across uvicorn reloads; otherwise the reloader can
# pass stale integration values back into a freshly started worker process.
load_dotenv(override=True)
