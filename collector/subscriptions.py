# -*- coding: utf-8 -*-
"""받은편지함에서 구독 신청/취소 메일을 스캔해 현재 구독자 목록을 계산.

설계: 구독자 명단을 파일로 저장하지 않고 매번 메일함에서 재계산한다.
- 공개 저장소에 구독자 이메일(PII)이 절대 남지 않음
- 상태 파일 관리 불필요 (메일함이 곧 DB)
- BODY.PEEK로 읽어 읽음 상태를 바꾸지 않음 (mail_ingest의 UNSEEN 처리와 충돌 방지)

메일 규약:
- 구독: 제목에 '구독신청', 제목/본문에 노선 코드(예: ICN-FUK) 또는 '전체'
- 해지: 제목에 '구독취소', 노선 코드가 있으면 해당 노선만, 없으면 전체 해지
"""
import email
import email.utils
import imaplib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mail_ingest import IMAP_HOST, decode, html_body, load_env

SUBSCRIBE = "구독신청"
UNSUBSCRIBE = "구독취소"
ROUTE_RE = re.compile(r"\b([A-Z]{3})\s*[-→~]\s*([A-Z]{3})\b")
ALL_RE = re.compile(r"전체|ALL", re.I)


def _extract_route(text):
    """텍스트에서 'ICN-FUK' 같은 노선 코드 또는 '전체'(ALL)를 추출."""
    m = ROUTE_RE.search(text or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    if ALL_RE.search(text or ""):
        return "ALL"
    return None


def load_subscribers(addr=None, pw=None):
    """{구독자 이메일: {노선코드 or 'ALL', ...}} 반환. 신청/취소를 시간순 적용."""
    if not addr:
        addr, pw = load_env()
    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    imap.login(addr, pw)
    imap.select("INBOX", readonly=True)
    _, data = imap.search(None, "ALL")
    subs = {}
    for mid in data[0].split():  # ID 오름차순 = 도착 시간순
        _, hdr = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        msg = email.message_from_bytes(hdr[0][1])
        subject = decode(msg.get("Subject"))
        if SUBSCRIBE not in subject and UNSUBSCRIBE not in subject:
            continue
        _, full = imap.fetch(mid, "(BODY.PEEK[])")
        msg = email.message_from_bytes(full[0][1])
        sender = email.utils.parseaddr(msg.get("From", ""))[1].lower()
        if not sender:
            continue
        route = _extract_route(subject) or _extract_route(html_body(msg))
        if SUBSCRIBE in subject:
            subs.setdefault(sender, set()).add(route or "ALL")
        else:  # 구독취소
            if route and sender in subs:
                subs[sender].discard(route)
                if not subs[sender]:
                    del subs[sender]
            else:
                subs.pop(sender, None)
    imap.logout()
    return subs


if __name__ == "__main__":
    for addr_, routes in load_subscribers().items():
        masked = addr_[:3] + "***"
        print(f"{masked}: {sorted(routes)}")
