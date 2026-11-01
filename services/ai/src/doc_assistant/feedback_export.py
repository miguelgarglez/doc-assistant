"""Export reviewed feedback drafts from an existing local history database."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from doc_assistant.infra.history.sqlite import HistoryStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="existing history database")
    parser.add_argument("--conversation-id", required=True, help="conversation to export")
    args = parser.parse_args(argv)
    if not args.database.is_file():
        parser.error("history database does not exist or is not a file")
    if not args.conversation_id.strip():
        parser.error("conversation ID must not be empty")
    store = HistoryStore(args.database)
    for line in store.export_reviewed(args.conversation_id):
        sys.stdout.write(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
