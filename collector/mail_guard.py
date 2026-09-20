# -*- coding: utf-8 -*-
"""메일 수집·파싱의 방어선 — **누구의 메일을 받아들이나, 한 번에 몇 통까지인가** (BE15).

구독 주소는 공개돼 있다(`meta.json`·사이트 푸터·이 저장소). 스팸이 받은편지함에 쏟아지면:

  · 한국 스팸은 법적으로 제목에 `(광고)`를 단다 → `parse_mail`의 제목 사전필터를 **오히려 통과**해 LLM 과금이 붙는다
  · 월 지출 한도에 닿으면 진짜 항공사 메일 파싱이 멈춘다
  · 발신자·제목이 공개 `prices.db`의 `emails` 테이블로 **커밋된다**(BB39) — 공개 저장소의 이력은 되돌릴 수 없다
  · 항공사를 사칭한 메일이 `mail_deals`에 공격자의 URL을 심는다

그래서 차단 목록(`google.com`·`gmail.com`만 거르던 옛 `SKIP_SENDERS`)을 **허용 목록**으로 뒤집었다.

**이 모듈은 순수 로직만 갖는다** — IMAP도 DB도 LLM도 모른다. `parse_mail.py`는 `anthropic`을
import하는데 CI(`test.yml`)는 의존성을 설치하지 않으므로, 판정을 거기 두면 테스트할 수 없다.
"""
import email.utils
import re

# 항공사 뉴스레터의 발신 도메인. **하위 도메인은 자동으로 포함된다**(`marketing.jinair.com`).
#
# 출처: 2026-09-20까지 실제로 받은 35통의 From 도메인 전부(11종 → 등록 도메인 10개).
# `tests/test_mail_guard.py`가 공개 DB에 쌓인 과거 발신자가 **하나도 안 걸러지는지** 확인한다.
#
# ⚠️ 새 항공사 뉴스레터를 구독하면 **여기에 먼저 추가한다.** 안 하면 그 메일은 목록에도 안 뜬다 —
#    `mail_ingest`가 실행마다 「허용 밖 안 읽은 메일 N통」을 찍으니 그 숫자가 늘면 의심할 것.
ALLOW_DOMAINS = (
    "airbusan.com", "airpremia.com", "eastarjet.com", "flyairseoul.com", "flyasiana.com",
    "jejuair.net", "jinair.com", "koreanair.com", "trinityairways.com", "twayair.com",
)

# `Authentication-Results`를 붙인 서버. Gmail이 수신 시점에 **맨 위에** 붙인다.
AUTHSERV = "mx.google.com"

# 한 실행이 받아들이는 메일 수의 상한. 평소는 주 3~4통이다(2026-09 실측) —
# 이 수에 닿았다는 것 자체가 경보다. 넘친 메일은 **안 읽은 채로 남아** 다음 실행이 가져간다.
#
# 상한을 파싱이 아니라 **수집**에 거는 이유: `mail_ingest`가 읽는 순간 그 메일은 소비되고(BB33)
# 본문 DB는 러너와 함께 사라진다. 파싱에서 자르면 잘린 메일은 영영 다시 오지 않는다.
MAX_PER_RUN = 20


def sender_domain(from_header):
    """`From` 헤더 → 주소의 도메인(소문자). 주소가 없으면 `""`.

    🔴 헤더 문자열에서 도메인을 **찾지 않는다.** 표시 이름은 보내는 사람이 마음대로 적는다 —
    `"koreanair.com" <x@spam.biz>`를 부분 문자열로 찾으면 통과한다(옛 `SKIP_SENDERS`가 그 방식이었다).
    """
    addr = email.utils.parseaddr(from_header or "")[1]
    return addr.rpartition("@")[2].strip().lower() if "@" in addr else ""


def allowed_domain(domain):
    """허용 도메인 자신이거나 그 **하위 도메인**인가. `notjinair.com`·`jinair.com.evil.biz`는 아니다."""
    return any(domain == d or domain.endswith("." + d) for d in ALLOW_DOMAINS)


def authenticated(auth_results, domain):
    """Gmail이 「이 메일은 정말 `domain`이 보냈다」고 확인했는가.

    `From`은 위조할 수 있다. 허용 목록만 두면 `From: event@koreanair.com`으로 적은 스팸이 통과한다.
    Gmail은 수신할 때 SPF·DKIM·DMARC를 검사해 결과를 헤더로 남긴다:

        Authentication-Results: mx.google.com; dkim=pass header.i=@x; spf=pass …; dmarc=pass … header.from=x

    기준은 **`dmarc=pass` + `header.from`이 From 도메인과 같음**이다.
    2026-09-20 실측(받은편지함의 항공사 메일 35통 전부): 헤더는 통마다 정확히 1개, 전부 `mx.google.com`,
    **35/35 `dmarc=pass`**, `header.from` == From 도메인. DKIM을 기준으로 삼으면 안 된다 —
    이스타항공은 DKIM 서명 없이 SPF 정렬로 DMARC를 통과한다(1통). DKIM을 요구했으면 그 메일을 버렸다.

    🔴 **첫 번째 헤더만 본다.** 헤더는 받는 서버가 위에 쌓는다. 공격자가 본문에 미리 넣어 둔
    가짜 `Authentication-Results: mx.google.com; dmarc=pass …`는 Gmail 것보다 **아래**에 있다.
    """
    if not auth_results:
        return False
    first = " ".join(auth_results[0].split())
    serv, _, rest = first.partition(";")
    if serv.strip().lower() != AUTHSERV:
        return False
    if not re.search(r"\bdmarc=pass\b", rest):
        return False
    m = re.search(r"\bheader\.from=([\w.-]+)", rest)
    return bool(m) and m.group(1).lower() == domain


# 거른 이유. `mail_ingest`가 이유별로 센다 — 「인증 실패」는 공격이거나 항공사 설정 사고라서 시끄럽게 다룬다.
OK, NOT_ALLOWED, NOT_AUTHENTICATED = "ok", "허용 밖 도메인", "인증 실패"


def verdict(from_header, auth_results):
    """이 메일을 받아들일 것인가 → `OK` | `NOT_ALLOWED` | `NOT_AUTHENTICATED`."""
    domain = sender_domain(from_header)
    if not domain or not allowed_domain(domain):
        return NOT_ALLOWED
    if not authenticated(auth_results, domain):
        return NOT_AUTHENTICATED
    return OK


def take(items, cap=MAX_PER_RUN):
    """`(이번에 처리할 것, 다음으로 미룰 것)`. 앞에서부터 — 오래된 메일이 먼저다."""
    items = list(items)
    return items[:cap], items[cap:]


def run_batch(items, handle, retryable):
    """`handle(item)`을 하나씩 부른다. `retryable` 예외는 **세고 넘어간다.** → `(성공 수, 실패한 item 목록)`.

    옛 `parse_mail`은 `APIStatusError`만 잡아 조용히 `continue`했다. 두 가지가 샜다:
      · 월 한도에 닿아 전부 실패해도 **스텝은 초록불**이다 — 항공사 메일 파싱이 멈춘 걸 아무도 모른다
      · 연결 오류(`APIConnectionError`)는 안 잡혀 **루프가 통째로 죽고** 뒤의 메일이 다 버려진다
    호출자는 실패 목록이 비어 있지 않으면 **종료 코드 1**을 낸다(BB2와 같은 방식).
    """
    done, failed = 0, []
    for item in items:
        try:
            handle(item)
            done += 1
        except retryable:
            failed.append(item)
    return done, failed
