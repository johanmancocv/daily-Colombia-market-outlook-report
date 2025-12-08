import sqlite3
from typing import Iterable, Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  source TEXT,
  region TEXT,
  topic TEXT,
  title TEXT,
  published TEXT,
  fetched_at TEXT,
  text TEXT
);

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  as_of TEXT,
  model TEXT,
  score REAL,
  json TEXT,
  created_at TEXT
);
"""

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.executescript(SCHEMA)
    return conn

def upsert_articles(conn: sqlite3.Connection, rows: Iterable[Dict[str, Any]]) -> int:
    cur = conn.cursor()
    n = 0
    for r in rows:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO articles
                   (url, source, region, topic, title, published, fetched_at, text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["url"], r["source"], r["region"], r["topic"], r["title"],
                 r.get("published"), r.get("fetched_at"), r.get("text"))
            )
            if cur.rowcount:
                n += 1
        except Exception:
            # Keep pipeline running even if one row is weird
            pass
    conn.commit()
    return n

def latest_articles(conn: sqlite3.Connection, limit: int = 50):
    cur = conn.cursor()
    cur.execute(
        """SELECT source, region, topic, title, url, published
           FROM articles
           ORDER BY COALESCE(published, fetched_at) DESC
           LIMIT ?""",
        (limit,)
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def save_report(conn: sqlite3.Connection, as_of: str, model: str, score: float, json_str: str, created_at: str):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO reports(as_of, model, score, json, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (as_of, model, score, json_str, created_at)
    )
    conn.commit()

def latest_articles_for_date(conn: sqlite3.Connection, day: str, limit: int = 50):
    """
    day: 'YYYY-MM-DD' (Bogotá). Devuelve SOLO artículos de ese día.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source, region, topic, title, url, published
        FROM articles
        WHERE substr(COALESCE(published, fetched_at), 1, 10) = ?
        ORDER BY COALESCE(published, fetched_at) DESC
        LIMIT ?
        """,
        (day, limit),
    )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
