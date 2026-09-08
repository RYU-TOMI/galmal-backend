# -*- coding: utf-8 -*-
"""v1 API 계약 검증기 (`CONTRACT.md` §v1, `SPLIT.md` M1 T3).

계약은 **두 세션 사이의 약속**이라 한쪽이 조용히 어기면 반대편이 M2에서 발견한다.
그때는 이미 프론트가 그 응답을 전제로 코드를 짜 놓은 뒤다. 여기서 먼저 잡는다.

이 파일이 지키는 것 셋:

**① 봉투와 모양** — `schema`·`generated`(오프셋 필수)·블록별 필드.

**② P7 — 백엔드는 사실을, 프론트는 말을 낸다.**
`"9월"`·`"월요일"` 같은 **완성된 문장이 응답에 섞이면 실패**한다. 옮기다 보면
습관으로 `fmt_month`를 부르게 되는데, 그 순간 프론트가 문구를 못 바꾼다.

**③ 🔴 창은 백엔드, 임계는 프론트 — 그리고 이 응답으로 현행 화면이 재현되는가.**
M1의 DoD가 「계약이 현행 노선 페이지의 모든 숫자를 덮는가」다. 계약에 적힌
프론트 규칙(`n>=3`·앞에서 10개·상위 8개)을 실제로 적용해 **현행 `route_page()`가
쓰는 값과 대조**한다. 하나라도 어긋나면 M2에서 프론트가 막힌다.
"""
import json
import re
import unittest
from datetime import datetime
from pathlib import Path

import config
import publish_v1
import subscriptions
import theme
from build_site import WINDOW_DAYS, airline_min, month_min, weekday_min

V1 = Path(__file__).resolve().parent.parent / "docs" / "v1"

# 화면 문자열이 새어 들어왔는지 보는 자국. 응답 어디에도 있으면 안 된다.
DISPLAY_LEAK = re.compile(r"\d+월|월요일|[월화수목금토일]요일|원$")


def load(rel):
    return json.loads((V1 / rel).read_text(encoding="utf-8"))


class EnvelopeTest(unittest.TestCase):
    """모든 응답의 최상위 두 키 (`CONTRACT.md` §공통 규칙)."""

    @classmethod
    def setUpClass(cls):
        if not (V1 / "meta.json").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.files = sorted(V1.rglob("*.json"))

    def test_every_response_declares_its_schema(self):
        for f in self.files:
            with self.subTest(file=f.name):
                self.assertEqual(json.loads(f.read_text(encoding="utf-8"))["schema"],
                                 "v1")

    def test_generated_carries_an_offset(self):
        """🔴 오프셋이 없으면 날짜 경계에서 하루가 **조용히** 어긋난다.

        화면이 신선도를 표시하고 있어(`발견가 · N일 전 가격`) 티가 안 난다.
        현행 `updated`의 `"2026-08-06 00:15"`가 바로 그 모양이라 v1에서 버렸다.
        """
        for f in self.files:
            with self.subTest(file=f.name):
                raw = json.loads(f.read_text(encoding="utf-8"))["generated"]
                parsed = datetime.fromisoformat(raw)
                self.assertIsNotNone(parsed.tzinfo, f"{raw}에 오프셋이 없다")


class MetaTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not (V1 / "meta.json").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.meta = load("meta.json")

    def test_window_comes_from_the_single_source(self):
        """`meta`가 30을 따로 들고 있으면 창을 바꾸는 날 한쪽만 바뀐다."""
        self.assertEqual(self.meta["window_days"], WINDOW_DAYS)

    def test_counts_match_what_was_published(self):
        self.assertEqual(self.meta["counts"]["routes"],
                         len(load("routes/index.json")["routes"]))
        self.assertEqual(self.meta["counts"]["deals"],
                         len(load("deals.json")["deals"]))

    def test_subscribe_protocol_is_present(self):
        for key in ("address", "subject_subscribe",
                    "subject_unsubscribe", "route_token"):
            self.assertIn(key, self.meta["subscribe"])

    def test_subject_lines_come_from_the_parser_not_a_copy(self):
        """🔴 이 파일에서 가장 중요한 단언.

        `meta.json`의 존재 이유가 **「프론트가 규약을 지어내지 않게」**인데, 값이
        파서와 다른 곳에서 오면 그 보장이 사라진다. 그리고 그건 조용히 틀리는 게
        아니라 **반대로 동작한다** — `_extract_route()`가 노선을 못 찾으면
        `load_subscribers()`가 `route or "ALL"`로 받아(`subscriptions.py:61`)
        도쿄만 신청한 사람이 36노선 메일을 받는다.

        파서 상수를 바꿔서 발행값이 따라오는지 본다. 문자열을 복사해 두면 실패한다.
        """
        real = subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE
        subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE = "구독요청", "구독해지"
        try:
            sub = publish_v1.meta_payload({}, False)["subscribe"]
            self.assertEqual(sub["subject_subscribe"], "구독요청")
            self.assertEqual(sub["subject_unsubscribe"], "구독해지")
        finally:
            subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE = real

    def test_address_is_the_mailbox_we_actually_poll(self):
        self.assertEqual(self.meta["subscribe"]["address"], theme.SUBSCRIBE_ADDR)

    def test_route_token_matches_what_the_parser_accepts(self):
        """본문에 실제로 들어갈 코드가 `ROUTE_RE`를 통과하는가."""
        sample = self.meta["subscribe"]["route_token"].replace("{code}", "ICN-FUK")
        self.assertEqual(subscriptions._extract_route(f"노선: {sample}"), "ICN-FUK")


class RoutePayloadTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not (V1 / "routes").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.routes = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                      for p in (V1 / "routes").glob("*.json") if p.stem != "index"}
        if not cls.routes:
            raise unittest.SkipTest("노선 응답이 없다")

    def test_blocks_have_the_contracted_fields(self):
        for code, r in self.routes.items():
            with self.subTest(route=code):
                self.assertEqual(set(r["summary"]), {"cheapest", "median", "n"})
                for x in r["trend"]:
                    self.assertEqual(set(x), {"date", "price"})
                for x in r["months"]:
                    self.assertEqual(set(x), {"m", "price", "n"})
                for x in r["weekdays"]:
                    self.assertEqual(set(x), {"wd", "price", "n"})
                for x in r["airlines"]:
                    self.assertEqual(set(x), {"code", "name", "min", "n"})

    def test_trend_has_no_sample_count(self):
        """하루 = 한 점이라 `n`이 항상 1에 수렴한다 — 넣으면 군더더기다."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["trend"]:
                    self.assertNotIn("n", x)

    def test_months_are_machine_readable_not_display_strings(self):
        """`"2026-09"`를 보내지 `"9월"`을 보내지 않는다 (P7)."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["months"]:
                    self.assertRegex(x["m"], r"^\d{4}-\d{2}$")

    def test_weekdays_are_integers_not_names(self):
        """`0=일 … 6=토`. `"월"`로 바꾸는 건 표시 결정이라 프론트 몫이다."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["weekdays"]:
                    self.assertIsInstance(x["wd"], int)
                    self.assertIn(x["wd"], range(7))

    def test_no_display_string_leaks_anywhere(self):
        """🔴 P7의 포괄 방어 — 옮기다 습관으로 `fmt_month`를 부르면 여기서 걸린다.

        항공사 이름은 예외다. 그건 문장이 아니라 **참조 데이터**다(`deal.ko`와 같다).
        """
        for code, r in self.routes.items():
            probe = dict(r)
            probe["airlines"] = [{k: v for k, v in a.items() if k != "name"}
                                 for a in r["airlines"]]
            with self.subTest(route=code):
                leak = DISPLAY_LEAK.search(json.dumps(probe, ensure_ascii=False))
                self.assertIsNone(leak, f"{code}: 화면 문자열이 샜다 — {leak}")

    def test_backend_does_not_drop_thin_buckets(self):
        """창은 백엔드, 임계는 프론트 — **얇다고 버리지 않는다.**

        발행값이 필터를 끈 것과 같아야 한다. 화면이 3건 미만을 버리는 건
        `route_page()`의 기본값이지 사실이 아니다.
        """
        import db
        conn = db.connect()
        try:
            for code, r in self.routes.items():
                o, d = code.split("-")
                with self.subTest(route=code):
                    self.assertEqual(
                        len(r["months"]),
                        len(month_min(conn, o, d, min_samples=1, limit=None)))
                    self.assertEqual(
                        len(r["airlines"]),
                        len(airline_min(conn, o, d, limit=None)))
        finally:
            conn.close()


class ReproducesTheCurrentScreenTest(unittest.TestCase):
    """🔴 M1의 DoD — 이 응답으로 현행 노선 페이지를 다시 그릴 수 있는가.

    계약에 적힌 프론트 규칙을 실제로 적용해 현행 `route_page()`가 쓰는 값과 대조한다.
    하나라도 빠지면 **M2에서 프론트가 막힌다** — 그때는 이미 늦다.

        months    n >= 3 인 것만, 월 오름차순 앞에서 10개
        airlines  최저가 오름차순 상위 8개
        weekdays  전부 (건수 필터 없음)
    """

    @classmethod
    def setUpClass(cls):
        if not (V1 / "routes").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        import db
        cls.conn = db.connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_front_rules_reproduce_every_number(self):
        for origin, dest in config.ROUTES:
            code = f"{origin}-{dest}"
            path = V1 / "routes" / f"{code}.json"
            if not path.exists():
                continue
            r = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(route=code):
                self.assertEqual(
                    [(x["m"], x["price"]) for x in r["months"] if x["n"] >= 3][:10],
                    [(m, p) for m, p, _ in month_min(self.conn, origin, dest)])
                self.assertEqual(
                    [(x["code"], x["min"], x["n"])
                     for x in sorted(r["airlines"], key=lambda x: x["min"])][:8],
                    list(airline_min(self.conn, origin, dest)))
                self.assertEqual(
                    [(x["wd"], x["price"]) for x in r["weekdays"]],
                    [(wd, p) for wd, p, _ in weekday_min(self.conn, origin, dest)])

    def test_summary_matches_the_page_headline(self):
        """히어로의 최저가·중앙값·「가격 N건」이 그대로 나오는가."""
        from build_site import route_summary
        for origin, dest in config.ROUTES:
            path = V1 / "routes" / f"{origin}-{dest}.json"
            if not path.exists():
                continue
            s = json.loads(path.read_text(encoding="utf-8"))["summary"]
            with self.subTest(route=f"{origin}-{dest}"):
                self.assertEqual((s["cheapest"], s["median"], s["n"]),
                                 route_summary(self.conn, origin, dest))


if __name__ == "__main__":
    unittest.main()
