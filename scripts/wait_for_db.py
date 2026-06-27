import os
import socket
import sys
import time
from urllib.parse import urlparse


def _database_host_and_port() -> tuple[str, int] | None:
    database_url = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        return None

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        return None

    host = parsed.hostname
    if not host:
        raise ValueError("Database URL is missing a host")

    return host, parsed.port or 5432


def main() -> int:
    target = _database_host_and_port()
    if target is None:
        print("No network database configured; skipping wait.")
        return 0

    host, port = target
    timeout_seconds = float(os.getenv("DB_WAIT_TIMEOUT_SECONDS", "60"))
    interval_seconds = float(os.getenv("DB_WAIT_INTERVAL_SECONDS", "2"))
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                print(f"Database is reachable at {host}:{port}.")
                return 0
        except OSError as exc:
            last_error = exc
            print(f"Waiting for database at {host}:{port}: {exc}", flush=True)
            time.sleep(interval_seconds)

    print(
        f"Timed out after {timeout_seconds:.0f}s waiting for database at {host}:{port}: {last_error}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
