# -*- coding: utf-8 -*-
"""메일 방어선 — 누구의 메일을 받아들이나, 한 번에 몇 통까지인가 (BE15).

구독 주소는 공개돼 있다. 이 파일이 막는 것:
  · 스팸 발신자·제목이 **공개 `prices.db`에 커밋되는 것**(BB39) — 되돌릴 수 없다
  · 스팸이 LLM 과금을 태우고, 월 한도에 닿아 진짜 항공사 메일 파싱이 **조용히** 멈추는 것
  · 항공사를 사칭한 메일이 `mail_deals`에 공격자의 URL을 심는 것

반대쪽 실패도 본다 — **허용 목록이 진짜 항공사 메일을 조용히 버리는 것.** 그래서 공개 DB에
쌓인 과거 발신자 전부가 통과하는지 여집합으로 센다.

`mail_guard`는 표준 라이브러리만 쓴다. IMAP·LLM은 건드리지 않는다.
"""
import sqlite3
import unittest
from pathlib import Path

import mail_guard
from mail_guard import (NOT_ALLOWED, NOT_AUTHENTICATED, OK, allowed_domain,
                        authenticated, run_batch, sender_domain, take, verdict)

ROOT = Path(__file__).resolve().parent.parent


def gmail_ar(domain, dmarc="pass", dkim=True, serv="mx.google.com"):
    """Gmail이 붙이는 모양 그대로(2026-09-20 실측) — 줄바꿈·들여쓰기까지."""
    parts = [serv]
    if dkim:
        parts.append(f"\r\n       dkim=pass header.i=@{domain} header.s=s1 header.b=AbCd1234")
    parts.append(f"\r\n       spf=pass (google.com: domain of bounce@{domain} designates 1.2.3.4 "
                 f"as permitted sender) smtp.mailfrom=bounce@{domain}")
    parts.append(f"\r\n       dmarc={dmarc} (p=REJECT sp=REJECT dis=NONE) header.from={domain}")
    return ";".join(parts)


class SenderDomainTest(unittest.TestCase):
    def test_reads_the_address_not_the_display_name(self):
        """🔴 옛 코드는 헤더 문자열에서 도메인을 **부분 문자열로** 찾았다. 허용 목록에 그 방식을 쓰면
        표시 이름에 `koreanair.com`이라고 적기만 해도 통과한다."""
        self.assertEqual(sender_domain('"koreanair.com 이벤트" <x@spam.biz>'), "spam.biz")
        self.assertEqual(verdict('"koreanair.com" <x@spam.biz>', [gmail_ar("spam.biz")]), NOT_ALLOWED)

    def test_plain_and_named_forms(self):
        self.assertEqual(sender_domain("대한항공 <News@KoreanAir.com>"), "koreanair.com")
        self.assertEqual(sender_domain("news@jejuair.net"), "jejuair.net")

    def test_unusable_headers(self):
        for raw in (None, "", "항공사", "<>"):
            with self.subTest(raw=raw):
                self.assertEqual(sender_domain(raw), "")
                self.assertEqual(verdict(raw, [gmail_ar("koreanair.com")]), NOT_ALLOWED)


class AllowListTest(unittest.TestCase):
    def test_subdomains_are_allowed(self):
        self.assertTrue(allowed_domain("jinair.com"))
        self.assertTrue(allowed_domain("marketing.jinair.com"))      # 실제로 이 주소로 온다

    def test_lookalikes_are_not(self):
        for d in ("notjinair.com", "jinair.com.evil.biz", "jinair.co", "gmail.com", ""):
            with self.subTest(domain=d):
                self.assertFalse(allowed_domain(d))

    def test_every_sender_we_ever_stored_is_still_allowed(self):
        """허용 목록의 조용한 실패 — **진짜 항공사 메일을 버리는 것** — 을 여집합으로 센다.

        공개 DB에 쌓인 과거 발신자 중 걸러지는 것이 **0**이어야 한다. 건수는 기대하지 않는다(매주 는다).
        """
        conn = sqlite3.connect(f"file:{(ROOT / 'data' / 'prices.db').as_posix()}?mode=ro", uri=True)
        try:
            senders = [s for (s,) in conn.execute("SELECT DISTINCT sender FROM emails")]
        finally:
            conn.close()
        self.assertTrue(senders, "emails 테이블이 비었다 — 이 검사가 아무것도 보지 않는다")
        dropped = sorted({sender_domain(s) for s in senders if not allowed_domain(sender_domain(s))})
        self.assertEqual(dropped, [], f"과거에 받던 발신 도메인이 허용 목록에서 빠졌다: {dropped}")


class AuthenticatedTest(unittest.TestCase):
    """`From`은 위조할 수 있다 — Gmail의 인증 결과로 확인한다."""

    def test_real_shape_passes(self):
        self.assertTrue(authenticated([gmail_ar("koreanair.com")], "koreanair.com"))

    def test_dmarc_pass_without_dkim_passes(self):
        """이스타항공의 실제 모양 — DKIM 서명 없이 SPF 정렬로 DMARC를 통과한다.
        DKIM을 기준으로 삼았다면 이 메일을 버렸다(실측 35통 중 1통)."""
        self.assertTrue(authenticated([gmail_ar("eastarjet.com", dkim=False)], "eastarjet.com"))

    def test_spoofed_from_fails(self):
        """`From: event@koreanair.com`으로 적은 스팸 — Gmail은 `dmarc=fail`을 남긴다."""
        ar = [gmail_ar("koreanair.com", dmarc="fail")]
        self.assertFalse(authenticated(ar, "koreanair.com"))
        self.assertEqual(verdict("대한항공 <event@koreanair.com>", ar), NOT_AUTHENTICATED)

    def test_header_from_must_match_the_from_domain(self):
        self.assertFalse(authenticated([gmail_ar("spam.biz")], "koreanair.com"))

    def test_only_gmails_own_header_counts(self):
        self.assertFalse(authenticated([gmail_ar("koreanair.com", serv="mx.evil.biz")], "koreanair.com"))

    def test_a_forged_header_below_gmails_is_ignored(self):
        """🔴 공격자가 미리 넣어 둔 가짜 통과 헤더. 헤더는 위에 쌓이므로 Gmail 것이 **첫째**다."""
        real_fail, forged_pass = gmail_ar("koreanair.com", dmarc="fail"), gmail_ar("koreanair.com")
        self.assertFalse(authenticated([real_fail, forged_pass], "koreanair.com"))

    def test_missing_header_fails(self):
        for ar in (None, [], [""]):
            with self.subTest(ar=ar):
                self.assertFalse(authenticated(ar, "koreanair.com"))

    def test_the_whole_verdict(self):
        self.assertEqual(verdict("진에어 <news@marketing.jinair.com>",
                                 [gmail_ar("marketing.jinair.com")]), OK)


class CapTest(unittest.TestCase):
    def test_oldest_first_and_the_rest_waits(self):
        now, later = take(range(25), cap=20)
        self.assertEqual((now, later), (list(range(20)), [20, 21, 22, 23, 24]))

    def test_under_the_cap_nothing_waits(self):
        self.assertEqual(take([1, 2, 3]), ([1, 2, 3], []))

    def test_the_cap_is_far_above_normal_traffic(self):
        """평소는 주 3~4통이다. 상한이 평소 근처면 매주 헛경보가 나고, 헛경보는 무시당한다."""
        self.assertGreaterEqual(mail_guard.MAX_PER_RUN, 10)


class RunBatchTest(unittest.TestCase):
    """파싱 실패를 **세고 넘어간다** — 삼키지도, 루프를 죽이지도 않는다."""

    class Boom(Exception):
        pass

    def test_failures_are_counted_and_the_loop_goes_on(self):
        seen = []

        def handle(x):
            seen.append(x)
            if x % 2:
                raise self.Boom(x)

        done, failed = run_batch([1, 2, 3, 4], handle, self.Boom)
        self.assertEqual((done, failed), (2, [1, 3]))
        self.assertEqual(seen, [1, 2, 3, 4], "실패 뒤의 메일도 끝까지 처리해야 한다")

    def test_a_bug_is_not_swallowed(self):
        """`retryable`이 아닌 예외(코드 버그)는 그대로 터진다 — 실패로 세어 버리면 버그가 숨는다."""
        def handle(x):
            raise ValueError(x)
        with self.assertRaises(ValueError):
            run_batch([1], handle, self.Boom)

    def test_all_good(self):
        self.assertEqual(run_batch([1, 2], lambda x: None, self.Boom), (2, []))


if __name__ == "__main__":
    unittest.main()
