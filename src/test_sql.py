"""
test_sql.py
Runs every statement in every sql/*.sql file against the local SQLite test
database and reports success/failure + a preview of each result, so all 40+
business queries are validated end-to-end (Step 31 of the project spec).
"""
import sqlite3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "novastream.db"
SQL_DIR = ROOT / "sql"

def strip_comments(sql_text):
    lines = []
    for line in sql_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines)

def split_statements(sql_text):
    sql_text = strip_comments(sql_text)
    stmts = [s.strip() for s in sql_text.split(";")]
    return [s for s in stmts if s and len(s.replace("\n", "").strip()) > 0]

conn = sqlite3.connect(DB)
cur = conn.cursor()

total = 0
failed = 0
SKIP_FILES = {"01_schema.sql"}  # PostgreSQL-specific DDL (CASCADE, DISTINCT ON); validated
                                  # separately via src/build_sqlite_db.py's ported schema

for f in sorted(SQL_DIR.glob("*.sql")):
    if f.name in SKIP_FILES:
        print(f"\n{'='*70}\n{f.name}  (SKIPPED - PostgreSQL-specific syntax, see note)\n{'='*70}")
        continue
    print(f"\n{'='*70}\n{f.name}\n{'='*70}")
    text = f.read_text()
    # strip full-line comments before splitting to avoid confusing the naive splitter
    cleaned_lines = []
    for line in text.split("\n"):
        cleaned_lines.append(line)
    text_no_comment_lines = "\n".join(cleaned_lines)
    statements = split_statements(text_no_comment_lines)
    for i, stmt in enumerate(statements, 1):
        total += 1
        try:
            cur.execute(stmt)
            rows = cur.fetchall()
            preview = rows[:2]
            print(f"  [OK] stmt {i}: {len(rows)} rows -> {preview}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] stmt {i}: {e}")
            print(f"    --- statement ---\n{stmt[:300]}")

print(f"\n\nTOTAL STATEMENTS RUN: {total}, FAILED: {failed}")
conn.close()
