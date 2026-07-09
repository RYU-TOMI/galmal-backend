# -*- coding: utf-8 -*-
"""SQLite 저장소. 표준 라이브러리만 사용."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prices.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_date TEXT NOT NULL,          -- 수집일 (YYYY-MM-DD)
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    depart_date TEXT NOT NULL,
    return_date TEXT,
    price INTEGER NOT NULL,              -- KRW
    airline TEXT,
    transfers INTEGER,               -- 가는 편 경유 횟수
    return_transfers INTEGER,        -- 오는 편 경유 횟수
    link TEXT,
    UNIQUE(fetched_date, origin, destination, depart_date, return_date, airline, price)
);
CREATE INDEX IF NOT EXISTS idx_offers_route ON offers(origin, destination, fetched_date);

-- 공개 저장소에 커밋되는 DB이므로 메일 메타데이터만 저장 (본문은 emails_raw.db)
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT,
    sender TEXT,
    subject TEXT,
    UNIQUE(received_at, sender, subject)
);
"""

RAW_SCHEMA = """
CREATE TABLE IF NOT EXISTS emails_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT,
    sender TEXT,
    subject TEXT,
    body_html TEXT,
    processed INTEGER DEFAULT 0,
    UNIQUE(received_at, sender, subject)
);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # 구버전 emails 테이블(본문 포함)은 공개 커밋 대상이므로 메타데이터 전용으로 재생성
    cols = [c[1] for c in conn.execute("PRAGMA table_info(emails)")]
    if "body_html" in cols:
        conn.execute("DROP TABLE emails")
    conn.executescript(SCHEMA)
    try:
        conn.execute("ALTER TABLE offers ADD COLUMN return_transfers INTEGER")
    except sqlite3.OperationalError:
        pass  # 이미 존재
    return conn


def connect_raw():
    """메일 본문 보관용 로컬 전용 DB (git 제외)."""
    raw_path = DB_PATH.parent / "emails_raw.db"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(raw_path)
    conn.executescript(RAW_SCHEMA)
    return conn
