#!/usr/bin/env python3
"""Query the Iron Bottom Sound IV FTS corpus."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DATABASE = ROOT / "resources" / "derived" / "rag" / "iron_bottom_sound_rules.sqlite3"


def fts_expression(term: str) -> str:
    tokens = [token.replace('"', '""') for token in re.findall(r"\S+", term.strip())]
    if not tokens:
        raise ValueError("Query term cannot be empty")
    return " AND ".join(f'"{token}"' for token in tokens)


def query(term: str, limit: int) -> list[tuple]:
    if not DATABASE.exists():
        raise SystemExit("Corpus is missing. Run build_rule_corpus.py first.")
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            """
            SELECT p.source, p.page, p.chunk, p.method, snippet(page_fts, 1, '[', ']', ' … ', 24)
            FROM page_fts
            JOIN pages p ON p.rowid = page_fts.rowid
            WHERE page_fts MATCH ?
            ORDER BY bm25(page_fts)
            LIMIT ?
            """,
            (fts_expression(term), limit),
        ).fetchall()
    finally:
        connection.close()
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("term")
    parser.add_argument("--limit", type=int, default=12)
    arguments = parser.parse_args()
    for source, page, chunk, method, snippet in query(arguments.term, arguments.limit):
        print(f"{source} | PDF/entry page {page} | chunk {chunk} | {method}\n  {snippet}")
