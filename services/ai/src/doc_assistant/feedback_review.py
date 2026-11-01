"""Mark local feedback reviewed using an expected answer read from stdin."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from doc_assistant.history import HistoryStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="existing history database")
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument("--feedback-id", required=True)
    args = parser.parse_args(argv)
    if not args.database.is_file():
        parser.error("history database does not exist or is not a file")
    if not args.conversation_id.strip() or not args.feedback_id.strip():
        parser.error("conversation and feedback IDs must not be empty")
    answer = sys.stdin.read()
    if not answer.strip():
        parser.error("expected answer on stdin must not be empty")
    store = HistoryStore(args.database)
    if not store.review_feedback(args.conversation_id, args.feedback_id, answer):
        print("feedback not found in conversation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
