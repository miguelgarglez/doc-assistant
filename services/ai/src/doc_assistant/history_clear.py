"""Delete local history through the running web proxy, including queued writes."""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import sys
from urllib.parse import urlsplit


def clear(url: str) -> int:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("URL must be a local HTTP origin")
    host = parsed.hostname or ""
    try:
        local = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if not local or parsed.port is None:
        raise ValueError("URL must include a loopback address and port")
    origin = f"http://{parsed.netloc}"
    connection = http.client.HTTPConnection(
        "127.0.0.1" if host == "localhost" else host, parsed.port, timeout=10
    )
    try:
        connection.request("DELETE", "/api/history/conversations", headers={"Origin": origin})
        response = connection.getresponse()
        data = response.read()
        if response.status != 200:
            raise RuntimeError(f"History service returned HTTP {response.status}")
        return int(json.loads(data)["deleted"])
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="web proxy origin, e.g. http://127.0.0.1:3300")
    parser.add_argument(
        "--yes", action="store_true", help="confirm deletion of all history and feedback"
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("pass --yes to confirm deletion")
    try:
        print(f"Deleted {clear(args.url)} requests")
    except (ValueError, RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
