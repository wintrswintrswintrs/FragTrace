"""
parse_worker.py

Standalone entrypoint that parses a single .dem file and prints the
resulting stats payload as JSON to stdout.

This is invoked as a SEPARATE PROCESS by the FastAPI server (main.py)
rather than imported and called in-process. This matters because the
underlying Rust demo parser can panic on malformed input (e.g. a 0-byte
or truncated .dem file), and a Rust panic crossing the Python/Rust FFI
boundary can in some cases abort the entire process rather than raise a
cleanly-catchable Python exception. Running each parse in its own
subprocess means a crash only takes down that subprocess — the API
server keeps running and can report a clean error to the client.

Usage:
    python parse_worker.py <path_to_demo.dem>

Exit code 0  -> success, JSON payload on stdout
Exit code 1  -> parse failed, error message on stderr
"""

from __future__ import annotations

import json
import sys

from stats_engine import parse_demo_file


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: parse_worker.py <path_to_demo.dem>", file=sys.stderr)
        return 1

    demo_path = sys.argv[1]
    try:
        payload = parse_demo_file(demo_path)
    except Exception as exc:  # noqa: BLE001
        print(f"PARSE_ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
