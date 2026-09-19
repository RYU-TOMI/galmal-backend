# -*- coding: utf-8 -*-
"""구독/해지 메일 판정 (BB37, BE13 T2).

이 파일이 막는 것: **해지한 사람에게 메일이 계속 가는 것.** 예외도 안 나고 발송도
성공하고 받는 사람만 안다 — 그리고 그건 정보통신망법의 수신거부 의무 위반이다.

2026-09-19 점검에서 나온 실제 경로:
  알림 메일 푸터가 "제목 '구독취소'로 회신"하라고 안내한다 → 회신은 원문을 인용한다 →
  푸터에 있던 예시 `ICN-FUK`를 파서가 본문에서 집는다 → 「ICN-FUK만 해지」로 처리 →
  전체 해지를 요청한 사람이 구독자로 남는다.

🔴 인용문은 손으로 적지 않는다. **`send_alerts.build_mail()`이 실제로 만든 본문**을 인용한다 —
푸터 문구를 누가 바꿔 코드 모양이 다시 들어가도 이 테스트가 그 문구로 검사한다.

IMAP은 건드리지 않는다. 판정은 `apply_message`(순수 함수)에 있고 `load_subscribers`는
메일함을 돌며 그걸 부를 뿐이다.
"""
import unittest

import send_alerts
import subscriptions
from subscriptions import apply_message, wants

ME = "someone@example.com"

DEAL = {"origin": "ICN", "destination": "NRT", "depart_date": "2026-10-01",
        "return_date": "2026-10-05", "price": 150000, "airline": "7C",
        "is_direct": True, "transfers": 0, "return_transfers": 0,
        "discount_pct": 40, "median": 250000, "link": "https://example.com"}


def quoted_reply(text="그만 받을게요"):
    """알림 메일에 회신한 본문 — 메일 클라이언트가 원문을 `> `로 인용한 모양."""
    original = send_alerts.build_mail(ME, [DEAL]).get_payload(decode=True).decode("utf-8")
    return text + "\n\n" + "\n".join("> " + line for line in original.splitlines())


def subscribed(*routes):
    subs = {}
    for r in routes:
        apply_message(subs, ME, f"{subscriptions.SUBSCRIBE} {r}")
    return subs


class UnsubscribeReplyTest(unittest.TestCase):
    """회신으로 해지하는 사람이 **정말로 해지되는가.**"""

    def test_the_probe_is_real(self):
        """전제 확인 — 인용문에 파서가 집을 노선 코드가 **실제로 들어 있다.**

        이게 거짓이면 아래 테스트들은 아무것도 증명하지 않는다(코드가 없는 본문에서는
        옛 구현도 통과한다). 푸터에서 예시를 통째로 빼면 이 테스트가 실패하는데,
        그때는 이 테스트를 지우지 말고 인용문에 노선 코드를 직접 넣어 전제를 되살릴 것.
        """
        self.assertIsNotNone(subscriptions.ROUTE_RE.search(quoted_reply()))

    def test_reply_unsubscribes_an_all_subscriber(self):
        subs = subscribed("전체")
        apply_message(subs, ME, subscriptions.UNSUBSCRIBE, quoted_reply())
        self.assertNotIn(ME, subs)

    def test_reply_unsubscribes_a_route_subscriber_whose_route_is_not_the_example(self):
        """예시(`ICN-FUK`)가 아닌 노선의 구독자 — 옛 구현은 엉뚱한 노선을 지우고 끝났다."""
        subs = subscribed("ICN-NRT", "PUS-CJU")
        apply_message(subs, ME, "Re: " + subscriptions.UNSUBSCRIBE, quoted_reply())
        self.assertNotIn(ME, subs)

    def test_body_route_is_ignored_on_unsubscribe(self):
        """본문에 코드를 적은 해지는 **전체 해지**다 — 과잉 쪽으로 틀린다(과소는 법 위반)."""
        subs = subscribed("ICN-NRT", "ICN-FUK")
        apply_message(subs, ME, subscriptions.UNSUBSCRIBE, "ICN-FUK 만 빼주세요")
        self.assertNotIn(ME, subs)


class RouteUnsubscribeTest(unittest.TestCase):
    """제목에 노선을 적은 해지."""

    def test_subject_route_removes_only_that_route(self):
        subs = subscribed("ICN-NRT", "ICN-FUK")
        apply_message(subs, ME, f"{subscriptions.UNSUBSCRIBE} ICN-FUK", quoted_reply())
        self.assertEqual(subs[ME], {"ICN-NRT"})

    def test_last_route_removed_means_gone(self):
        subs = subscribed("ICN-FUK")
        apply_message(subs, ME, f"{subscriptions.UNSUBSCRIBE} ICN-FUK")
        self.assertNotIn(ME, subs)

    def test_all_subscriber_can_drop_one_route(self):
        """옛 구현은 `{'ALL'}.discard('ICN-FUK')` — 아무것도 안 지우고 **조용히 무시**했다."""
        subs = subscribed("전체")
        apply_message(subs, ME, f"{subscriptions.UNSUBSCRIBE} ICN-FUK")
        self.assertFalse(wants(subs[ME], "ICN-FUK"))
        self.assertTrue(wants(subs[ME], "ICN-NRT"))

    def test_resubscribing_lifts_the_exclusion(self):
        for again in ("ICN-FUK", "전체"):
            with self.subTest(again=again):
                subs = subscribed("전체")
                apply_message(subs, ME, f"{subscriptions.UNSUBSCRIBE} ICN-FUK")
                apply_message(subs, ME, f"{subscriptions.SUBSCRIBE} {again}")
                self.assertTrue(wants(subs[ME], "ICN-FUK"))

    def test_full_unsubscribe_after_exclusion_leaves_nothing(self):
        subs = subscribed("전체")
        apply_message(subs, ME, f"{subscriptions.UNSUBSCRIBE} ICN-FUK")
        apply_message(subs, ME, subscriptions.UNSUBSCRIBE)
        self.assertNotIn(ME, subs)

    def test_unsubscribe_from_a_stranger_is_a_no_op(self):
        subs = subscribed("ICN-NRT")
        apply_message(subs, "other@example.com", subscriptions.UNSUBSCRIBE)
        self.assertEqual(subs, {ME: {"ICN-NRT"}})


class SubscribeTest(unittest.TestCase):
    """구독 쪽은 **안 바뀌었다** — 계약(`meta.subscribe.route_token`)이 본문에 코드를 넣게 한다."""

    def test_route_in_body_is_read(self):
        subs = {}
        apply_message(subs, ME, subscriptions.SUBSCRIBE,
                      "노선: ICN-FUK (인천 → 후쿠오카)\n\n이 메일을 그대로 보내주시면 구독이 신청됩니다.")
        self.assertEqual(subs[ME], {"ICN-FUK"})

    def test_no_route_means_all(self):
        """계약이 경고하는 동작 그대로 — 형식이 어긋나면 실패가 아니라 전 노선 구독이다."""
        subs = {}
        apply_message(subs, ME, subscriptions.SUBSCRIBE, "안녕하세요")
        self.assertEqual(subs[ME], {"ALL"})

    def test_unrelated_subject_changes_nothing(self):
        subs = subscribed("ICN-NRT")
        apply_message(subs, ME, "문의드립니다", "ICN-FUK")
        self.assertEqual(subs, {ME: {"ICN-NRT"}})


class WantsTest(unittest.TestCase):
    def test_matrix(self):
        for routes, code, expected in [
                ({"ALL"}, "ICN-FUK", True),
                ({"ICN-FUK"}, "ICN-FUK", True),
                ({"ICN-NRT"}, "ICN-FUK", False),
                ({"ALL", "!ICN-FUK"}, "ICN-FUK", False),
                ({"ALL", "!ICN-FUK"}, "ICN-NRT", True),
        ]:
            with self.subTest(routes=routes, code=code):
                self.assertEqual(wants(routes, code), expected)

    def test_send_alerts_asks_wants(self):
        """발송 쪽이 집합을 직접 뒤지면 제외(`!`)를 모른다 → 해지한 노선이 나간다."""
        import inspect
        src = inspect.getsource(send_alerts.main)
        self.assertIn("wants(", src)
        self.assertNotIn('"ALL" in routes', src)


if __name__ == "__main__":
    unittest.main()
