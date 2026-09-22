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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
import env
import mail_guard

IMAP_HOST = "imap.gmail.com"


def load_env():
    """`(주소, 앱 비밀번호)`. 둘 중 하나라도 없으면 멈춘다.

    **둘을 한 메시지로 알린다** — 하나씩 `require()`하면 먼저 걸린 것만 말하고,
    고친 뒤 다시 돌려야 나머지를 안다.
    """
    addr, pw = env.get("MAIL_ADDRESS"), env.get("MAIL_APP_PASSWORD")
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


HEADERS = "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE AUTHENTICATION-RESULTS)])"


def _candidates(imap, fetch_all):
    """허용 도메인에서 온 메일의 ID — **서버가 거른다.**

    `UNSEEN` 전체를 내려받아 파이썬에서 거르면, 스팸이 1만 통 쌓인 날 헤더를 1만 번 받는다.
    IMAP `FROM` 검색으로 허용 도메인 것만 목록에 올린다 — 나머지는 **내려받지도 않는다.**
    (`FROM`은 부분 문자열 검색이라 표시 이름에 도메인을 적은 메일도 걸린다. 그래서 아래에서
    `mail_guard.verdict()`가 주소와 Gmail 인증 결과로 **다시** 본다.)
    """
    scope = "ALL" if fetch_all else "UNSEEN"
    ids = set()
    for domain in mail_guard.ALLOW_DOMAINS:
        _, data = imap.search(None, scope, "FROM", f'"{domain}"')
        ids.update(data[0].split())
    return sorted(ids, key=int)          # ID 오름차순 = 도착 시간순


def main():
    # --all: 읽음 처리된 메일 포함 전체 재수집 (백필용, UNIQUE 제약으로 중복 방지). 상한을 걸지 않는다.
    fetch_all = "--all" in sys.argv
    addr, pw = load_env()
    conn = db.connect()          # 공개 커밋용: 메타데이터만
    raw = db.connect_raw()       # 로컬 전용: 본문 포함 (파싱 개발용)
    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    imap.login(addr, pw)
    imap.select("INBOX")

    _, data = imap.search(None, "ALL" if fetch_all else "UNSEEN")
    n_all = len(data[0].split())
    ids = _candidates(imap, fetch_all)
    # 허용 목록의 조용한 실패는 「새로 구독한 항공사를 목록에 안 넣은 것」이다. 그 메일은 영영 안 뜬다.
    # 실패로 만들지는 않는다(스팸이 오는 날마다 빨개진다). **숫자로 보이게만** 한다.
    print(f"안 읽은 메일 {n_all}통 · 허용 도메인 후보 {len(ids)}통 · 허용 밖 {n_all - len(ids)}통(내려받지 않음)")

    accepted, rejected = [], []
    for mid in ids:
        _, hdr = imap.fetch(mid, HEADERS)             # PEEK — 거른 메일에 \Seen 을 붙이지 않는다
        head = email.message_from_bytes(hdr[0][1])
        why = mail_guard.verdict(head.get("From"), head.get_all("Authentication-Results"))
        (accepted if why == mail_guard.OK else rejected).append((mid, why))

    now, later = (accepted, []) if fetch_all else mail_guard.take(accepted)
    saved = 0
    for mid, _ in now:
        _, msg_data = imap.fetch(mid, "(RFC822)")     # 여기서 \Seen — 받아들인 메일만 소비한다
        msg = email.message_from_bytes(msg_data[0][1])
        received, sender = msg.get("Date", ""), decode(msg.get("From"))
        subject = decode(msg.get("Subject"))
        # 구독 신청/취소 메일은 subscriptions.py가 처리 — 공개 DB에 저장 금지(PII)
        if "구독신청" in subject or "구독취소" in subject:
            print(f"  건너뜀(구독 메일): {subject[:50]}")
            continue
        conn.execute(
            "INSERT OR IGNORE INTO emails (received_at, sender, subject) VALUES (?,?,?)",
            (received, sender, subject))
        raw.execute(
            """INSERT OR IGNORE INTO emails_raw
               (received_at, sender, subject, body_html) VALUES (?,?,?,?)""",
            (received, sender, subject, html_body(msg)))
        saved += 1
        print(f"  저장: {subject[:60]}")
    conn.commit()
    raw.commit()
    conn.close()
    raw.close()
    imap.logout()
    print(f"완료: {saved}건 저장")

    # 데이터는 위에서 이미 커밋했다. 여기서부터는 **사람에게 알리는 일**이다 —
    # 스텝이 실패하면 워크플로의 「상태 점검」이 잡을 빨간불로 만들고 GitHub가 메일을 보낸다.
    problems = []
    n_auth = sum(1 for _, why in rejected if why == mail_guard.NOT_AUTHENTICATED)
    if n_auth:
        problems.append(
            f"허용 도메인을 단 메일 {n_auth}통이 Gmail 인증(dmarc=pass)을 통과하지 못했다 — "
            "항공사 사칭이거나 그 항공사의 발송 설정 사고다. 저장·파싱하지 않았고 안 읽은 채로 뒀다. "
            "메일함에서 직접 확인하고 읽음 처리할 것(안 하면 매일 다시 알린다).")
    if later:
        problems.append(
            f"상한({mail_guard.MAX_PER_RUN}통)을 넘었다 — {len(later)}통을 다음 실행으로 미뤘다. "
            "평소는 주 3~4통이다. 폭주를 의심할 것.")
    if problems:
        raise SystemExit("메일 수집 경보: " + " / ".join(problems))


if __name__ == "__main__":
    main()
