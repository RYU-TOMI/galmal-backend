# -*- coding: utf-8 -*-
"""받은편지함에서 구독 신청/취소 메일을 스캔해 현재 구독자 목록을 계산.

설계: 구독자 명단을 파일로 저장하지 않고 매번 메일함에서 재계산한다.
- 공개 저장소에 구독자 이메일(PII)이 절대 남지 않음
- 상태 파일 관리 불필요 (메일함이 곧 DB)
- BODY.PEEK로 읽어 읽음 상태를 바꾸지 않음 (mail_ingest의 UNSEEN 처리와 충돌 방지)

메일 규약:
- 구독: 제목에 '구독신청', 제목/본문에 노선 코드(예: ICN-FUK) 또는 '전체'
- 해지: 제목에 '구독취소'. **제목에** 노선 코드가 있으면 해당 노선만, 없으면 전체 해지.
        🔴 해지는 본문을 읽지 않는다(BB37) — 아래 `apply_message` 참조.
"""
import email
import email.utils
import imaplib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mail_ingest import IMAP_HOST, decode, html_body, load_env

# 🔴 **구독 메일함 — 여기가 정본이다** (M3 T5, BB32).
#
# `theme.py`에 있던 것을 옮겼다. 사이트 정체성이 아니라 **이 파일이 IMAP으로
# 로그인하는 메일함**이기 때문이다 — `theme.py`는 프론트로 가고, 같이 딸려가면
# 화면이 적는 주소와 우리가 읽는 메일함이 **각자 살게 된다.**
#
# ⚠️ 갈리면 조용한 정도가 아니라 **반송조차 안 온다**(둘 다 실재하는 주소라).
# 사용자는 신청했다고 믿고 우리는 신청이 없다고 믿는다.
# 아래 셋이 `publish.py`를 통해 `meta.json`의 `subscribe`로 나가고, 프론트는
# 그걸 읽어 mailto를 만든다 — **지어내지 않게 하는 게 그 필드의 존재 이유다.**
SUBSCRIBE_ADDR = "flightpromokr@gmail.com"
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


EXCLUDE = "!"          # `"!ICN-FUK"` — 전체 구독자가 그 노선만 뺐다


def wants(routes, code):
    """이 구독자에게 `code` 노선 알림을 보내도 되는가.

    판정을 발송 쪽에 두지 않는 이유: 제외 표기(`!`)를 아는 곳이 둘이 되면 하루는
    하나가 틀린다. 그리고 여기서 틀리면 **해지한 사람에게 메일이 간다.**
    """
    if EXCLUDE + code in routes:
        return False
    return "ALL" in routes or code in routes


def apply_message(subs, sender, subject, body=""):
    """구독/해지 메일 한 통을 `subs`에 반영한다. IMAP을 모른다 — 그래서 테스트할 수 있다.

    🔴 **해지는 제목에서만 노선을 읽는다** (BB37, 2026-09-20).
    알림 메일 푸터가 "제목 '구독취소'로 **회신**"하라고 안내하는데, 회신은 원문을 인용한다.
    예전엔 본문에서도 노선을 찾았고 푸터에 예시 `ICN-FUK`가 있었다 → 인용문 속 예시를 집어
    「ICN-FUK만 해지」로 처리했다. **전체 해지를 요청한 사람이 계속 구독자로 남았다** —
    본인은 해지했다고 믿고 우리는 계속 보낸다(정보통신망법 수신거부 의무).

    어느 쪽으로 틀릴지 고른 것이다: 본문에 코드를 적은 사람은 그 노선만이 아니라 **전부**
    해지된다(과잉). 과잉 해지는 다시 신청하면 되지만 과소 해지는 법 위반이다.
    구독은 그대로 본문도 읽는다 — 사이트의 mailto가 본문에 코드를 넣는다(계약 `route_token`).

    `ALL` 구독자가 한 노선만 해지하면 `"!ICN-FUK"`로 남긴다. 예전엔 `discard`가 아무것도
    안 지워 **해지가 조용히 무시됐다.** 그 노선을 다시 신청하거나 전체를 다시 신청하면 풀린다.
    """
    if SUBSCRIBE in subject:
        route = _extract_route(subject) or _extract_route(body) or "ALL"
        mine = subs.setdefault(sender, set())
        if route == "ALL":
            mine.difference_update({r for r in mine if r.startswith(EXCLUDE)})
        mine.discard(EXCLUDE + route)
        mine.add(route)
    elif UNSUBSCRIBE in subject:
        route = _extract_route(subject)
        mine = subs.get(sender)
        if mine is None:
            return
        if route is None or route == "ALL":
            del subs[sender]
            return
        mine.discard(route)
        if "ALL" in mine:
            mine.add(EXCLUDE + route)
        if not any(not r.startswith(EXCLUDE) for r in mine):
            del subs[sender]


def load_subscribers(addr=None, pw=None):
    """{구독자 이메일: {노선코드 | 'ALL' | '!노선코드', ...}} 반환. 신청/취소를 시간순 적용.

    돌려받은 집합은 직접 뒤지지 말고 `wants(routes, code)`로 묻는다.
    """
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
        apply_message(subs, sender, subject, html_body(msg))
    imap.logout()
    return subs


if __name__ == "__main__":
    for addr_, routes in load_subscribers().items():
        masked = addr_[:3] + "***"
        print(f"{masked}: {sorted(routes)}")
