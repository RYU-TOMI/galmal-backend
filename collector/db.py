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

-- 구독 알림 발송 로그 (이메일은 해시로만 저장 — 공개 저장소에 PII 금지)
CREATE TABLE IF NOT EXISTS alert_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_date TEXT,
    email_hash TEXT,                 -- sha256 앞 16자
    origin TEXT,
    destination TEXT,
    depart_date TEXT,
    return_date TEXT,
    price INTEGER
);
CREATE INDEX IF NOT EXISTS idx_alert_log ON alert_log(email_hash, origin, destination);

-- 프로모션 메일에서 LLM으로 추출한 구조화 특가 정보 (공개 가능: 요약+공식 링크만)
CREATE TABLE IF NOT EXISTS mail_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT,
    airline TEXT,
    origin TEXT,                     -- 출발 도시 (없으면 NULL)
    destination TEXT,                -- 도착 도시 (없으면 NULL)
    price_krw INTEGER,               -- 광고된 편도/최저가 (없으면 NULL)
    promo_end TEXT,                  -- 판매 종료일 YYYY-MM-DD (없으면 NULL)
    summary TEXT NOT NULL,           -- 한 줄 요약
    url TEXT,                        -- 항공사 공식 프로모션 페이지 (개인화 링크 금지)
    UNIQUE(received_at, airline, destination, summary)
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
