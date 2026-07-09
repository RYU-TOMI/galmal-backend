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

CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT,
    sender TEXT,
    subject TEXT,
    body_html TEXT,
    processed INTEGER DEFAULT 0
);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    try:
        conn.execute("ALTER TABLE offers ADD COLUMN return_transfers INTEGER")
    except sqlite3.OperationalError:
        pass  # 이미 존재
    return conn
