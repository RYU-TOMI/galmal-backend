# -*- coding: utf-8 -*-
"""전용 Gmail 계정에서 항공사 프로모션 메일을 IMAP으로 수집해 SQLite에 저장.

준비물 (.env):
  MAIL_ADDRESS=계정@gmail.com
  MAIL_APP_PASSWORD=구글 앱 비밀번호 (2단계 인증 켠 뒤 발급)

사용: python collector/mail_ingest.py
파싱(노선/가격 추출)은 이후 단계에서 LLM으로 처리 — 여기서는 원문 저장까지만.
"""
import email
import email.header
import imaplib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

IMAP_HOST = "imap.gmail.com"


def load_env():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    values = dict(os.environ)
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                values.setdefault(k.strip(), v.strip())
    addr, pw = values.get("MAIL_ADDRESS"), values.get("MAIL_APP_PASSWORD")
    if not addr or not pw:
        raise SystemExit("MAIL_ADDRESS / MAIL_APP_PASSWORD를 .env에 설정하세요.")
    return addr, pw


def decode(value):
    if not value:
        return ""
    parts = email.header.decode_header(value)
    return "".join(p.decode(enc or "utf-8", "replace") if isinstance(p, bytes) else p
                   for p, enc in parts)


def html_body(msg):
    for part in msg.walk():
        if part.get_content_type() in ("text/html", "text/plain"):
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def main():
    addr, pw = load_env()
    conn = db.connect()
    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    imap.login(addr, pw)
    imap.select("INBOX")
    _, data = imap.search(None, "UNSEEN")
    ids = data[0].split()
    print(f"새 메일 {len(ids)}건")
    for mid in ids:
        _, msg_data = imap.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        conn.execute(
            "INSERT INTO emails (received_at, sender, subject, body_html) VALUES (?,?,?,?)",
            (msg.get("Date", ""), decode(msg.get("From")),
             decode(msg.get("Subject")), html_body(msg)))
        print(f"  저장: {decode(msg.get('Subject'))[:60]}")
    conn.commit()
    conn.close()
    imap.logout()


if __name__ == "__main__":
    main()
