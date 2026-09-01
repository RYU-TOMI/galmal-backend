# -*- coding: utf-8 -*-
"""discover_data.py의 순수 함수 테스트 — `_median`, `_when_label`.

두 함수는 `deals.json`의 `median`·`when` 필드를 직접 결정한다(`CONTRACT.md`).
할인율·`nights` 계산은 순수 함수가 아니라 `build_deals_json()` 본문에 인라인으로
있어 여기서 다루지 않는다 → BE0 T3의 end-to-end 검증에서 확인한다.

⚠️ `_when_label` 테스트 일부는 **현재 동작을 박제한 것이지 올바른 사양이 아니다.**
   해당 케이스에 BB 번호를 달아 두었다(`BACKEND.md` 곁가지 백로그).
   BE2에서 고치면 이 테스트들이 실패하면서 무엇이 바뀌었는지 알려준다.
"""
import json
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import db
import discover_data
from discover_data import (MIN_DEALS, MIN_RATIO, SEEN_MAX_DAYS, _median,
                           _seen_kst, _when_label)


class MedianTest(unittest.TestCase):
    """`_median` — broad_offers 이력에서 '평소 시세'를 뽑는 함수."""

    def test_empty_returns_none(self):
        """빈 이력은 None. 호출부가 `_median(hist) or dd["price"]`로 폴백한다."""
        self.assertIsNone(_median([]))

    def test_odd_count_takes_middle(self):
        """홀수 개는 가운데 값."""
        self.assertEqual(_median([10, 20, 30]), 20)

    def test_even_count_floors_the_average(self):
        """짝수 개는 두 값의 평균을 **정수 나눗셈**으로 내린다(`//`). 1.5가 아니라 1."""
        self.assertEqual(_median([1, 2]), 1)
        self.assertEqual(_median([10, 20, 30, 41]), 25)

    def test_input_need_not_be_sorted(self):
        """정렬되지 않은 입력도 내부에서 정렬해 계산한다."""
        self.assertEqual(_median([30, 10, 20]), 20)

    def test_single_value(self):
        """1건뿐이면 그 값이 곧 시세 — 할인율이 0이 되는 경로."""
        self.assertEqual(_median([42522]), 42522)


class WhenLabelTest(unittest.TestCase):
    """`_when_label` — 출발일을 상대 날짜 문구로. 조건 네 겹의 우선순위가 핵심.

    기준일은 2026-08-22(토)로 고정한다. 요일에 따라 결과가 갈리므로
    `date.today()`를 쓰면 테스트가 날마다 달라진다.
    """

    TODAY = date(2026, 8, 22)          # 토요일

    def label(self, y, m, d):
        return _when_label(date(y, m, d), self.TODAY)

    def test_today_on_a_weekend_is_weekend(self):
        """당일 출발이라도 금·토·일이면 '이번 주말'."""
        self.assertEqual(self.label(2026, 8, 22), "이번 주말")   # 토

    def test_sunday_within_nine_days_is_weekend(self):
        self.assertEqual(self.label(2026, 8, 23), "이번 주말")   # 일, +1

    def test_weekday_within_a_week_is_this_week(self):
        """주말 조건에 걸리지 않는 평일은 7일 이내면 '이번 주'."""
        self.assertEqual(self.label(2026, 8, 27), "이번 주")     # 목, +5

    def test_weekend_rule_wins_over_this_week(self):
        """+7일이라 '이번 주'에도 해당하지만, 주말 조건이 먼저라 '이번 주말'."""
        self.assertEqual(self.label(2026, 8, 29), "이번 주말")   # 토, +7

    def test_weekend_window_extends_to_nine_days(self):
        """주말 조건의 창은 9일이라 '이번 주'(7일)보다 넓다."""
        self.assertEqual(self.label(2026, 8, 30), "이번 주말")   # 일, +8

    def test_weekend_window_stops_after_nine_days(self):
        """+10일은 금요일이어도 주말 라벨이 아니다(상한 9일)."""
        self.assertEqual(_when_label(date(2026, 9, 4), date(2026, 8, 25)), "다음 달")

    def test_next_month(self):
        self.assertEqual(self.label(2026, 9, 1), "다음 달")      # 화, +10

    def test_month_after_next_uses_month_name(self):
        self.assertEqual(self.label(2026, 10, 1), "10월")        # 목, +40

    def test_year_end_rolls_over_to_january(self):
        """12월 기준 '다음 달'은 이듬해 1월. `nxt_year` 보정이 동작하는지."""
        self.assertEqual(_when_label(date(2027, 1, 4), date(2026, 12, 15)), "다음 달")

    def test_january_of_a_later_year_is_not_next_month(self):
        """'다음 달'은 달뿐 아니라 **연도까지** 맞아야 한다.

        2026-12 기준 '다음 달'은 2027-01뿐이다. 2028-01은 달이 같아도
        `nxt_year` 조건에서 걸러져 월 이름으로 떨어진다.
        """
        self.assertEqual(_when_label(date(2028, 1, 4), date(2026, 12, 15)), "1월")

    # ---- 아래 둘은 현재 동작 박제. 올바른 사양이 아니다. ----

    def test_current_month_is_labelled_with_its_own_name(self):
        """BB7: 8월에 8월 말 평일 출발이면 '8월'. 사용자에게 정보가 없는 라벨이다.

        조건 순서상 주말도(월요일) 이번 주도(+9일) 다음 달도 아니라 월 이름으로 떨어진다.
        """
        self.assertEqual(self.label(2026, 8, 31), "8월")         # 월, +9

    def test_month_label_ignores_the_year(self):
        """BB8: 이듬해 출발도 연도 없이 '3월'. 지나간 3월과 구분되지 않는다."""
        self.assertEqual(self.label(2027, 3, 1), "3월")

    def test_past_departure_falls_into_this_week(self):
        """과거 날짜는 '이번 주'가 된다(`delta <= 7`이 음수도 통과).

        `build_deals_json()`이 미래 출발만 조회하므로 실사용에는 나타나지 않는다.
        함수 단독 동작을 기록해 둔다.
        """
        self.assertEqual(self.label(2026, 8, 19), "이번 주")     # 수, -3


if __name__ == "__main__":
    unittest.main()


class SeenConversionTest(unittest.TestCase):
    """`_seen_kst` — API의 naive `found_at`(UTC)을 KST로.

    여기가 틀리면 화면의 신선도 배지가 통째로 9시간 거짓말을 한다.
    """

    def test_naive_input_is_treated_as_utc(self):
        """오프셋이 없으면 UTC로 간주해 +9시간 한 KST를 돌려준다."""
        got = _seen_kst("2026-08-18T03:17:35")
        self.assertEqual(got.isoformat(), "2026-08-18T12:17:35+09:00")

    def test_existing_offset_is_respected(self):
        """향후 API가 오프셋을 붙여 주면 그대로 존중한다(UTC로 덮어쓰지 않는다)."""
        got = _seen_kst("2026-08-18T03:17:35+00:00")
        self.assertEqual(got.isoformat(), "2026-08-18T12:17:35+09:00")
        got = _seen_kst("2026-08-18T12:17:35+09:00")
        self.assertEqual(got.isoformat(), "2026-08-18T12:17:35+09:00")

    def test_unusable_values_become_none(self):
        """계약상 `seen`은 null을 허용한다 — 프론트가 배지를 생략한다."""
        for raw in (None, "", "어제쯤", "2026-13-99T99:99:99", 12345):
            with self.subTest(raw=raw):
                self.assertIsNone(_seen_kst(raw))


class BuildDealsSeenTest(unittest.TestCase):
    """`build_deals_json`이 `seen`을 실제로 채우고 유령 가격을 거르는가.

    `DOCS`를 임시 폴더로 갈아끼운다 — 안 그러면 커밋된 `docs/data/deals.json`
    (프론트 픽스처)을 테스트가 덮어쓴다.
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        self.today = date.today()

    def add(self, dest, price, seen_days_ago, fetched_days_ago=0, origin="ICN"):
        """`seen`이 며칠 전인 딜 1건. 출발일은 항상 미래.

        `broad_offers`의 PK가 `(수집일, 출발지, 목적지)`라 **하루에 같은 노선은
        1건뿐**이다. 같은 도시의 딜을 둘 이상 만들려면 수집일을 달리해야 하며,
        실제 파이프라인도 3일 창에 여러 날짜 행이 겹쳐 들어오는 구조다.
        """
        found = (datetime.now(timezone.utc) - timedelta(days=seen_days_ago))
        fetched = self.today - timedelta(days=fetched_days_ago)
        self.conn.execute(
            """INSERT INTO broad_offers (fetched_date, origin, destination, price,
                                         transfers, depart_date, return_date, found_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (fetched.isoformat(), origin, dest, price, 0,
             (self.today + timedelta(days=30)).isoformat(),
             (self.today + timedelta(days=33)).isoformat(),
             found.replace(tzinfo=None).isoformat()))

    def build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(discover_data, "DOCS", Path(tmp)):
                discover_data.build_deals_json(self.conn)
                written = (Path(tmp) / "data" / "deals.json").read_text(encoding="utf-8")
        return json.loads(written)

    def test_seen_is_emitted_with_kst_offset(self):
        self.add("FUK", 100000, seen_days_ago=1)
        deal = self.build()["deals"][0]
        self.assertTrue(deal["seen"].endswith("+09:00"), deal["seen"])

    def test_fresh_deals_survive_the_hard_cut(self):
        self.add("FUK", 100000, seen_days_ago=SEEN_MAX_DAYS - 1)
        self.assertEqual(len(self.build()["deals"]), 1)

    def test_ghost_prices_are_dropped(self):
        """7일 넘게 관측되지 않은 가격은 내보내지 않는다."""
        self.add("FUK", 100000, seen_days_ago=SEEN_MAX_DAYS + 1)
        self.assertEqual(self.build()["deals"], [])

    def test_the_cut_runs_before_deduplication(self):
        """유령 가격이 최저가라도, 같은 도시의 멀쩡한 딜이 살아남아야 한다.

        컷을 중복 제거 뒤에 두면 싼 유령이 대표로 뽑힌 다음 잘려서
        후쿠오카가 통째로 사라진다.
        """
        self.add("FUK", 10000, seen_days_ago=SEEN_MAX_DAYS + 1, fetched_days_ago=1)
        self.add("FUK", 90000, seen_days_ago=1, fetched_days_ago=0)
        deals = self.build()["deals"]
        self.assertEqual([d["price"] for d in deals], [90000],
                         "신선한 딜이 살아남아야 한다")

    def test_no_deals_still_produces_a_valid_shape(self):
        """0건인 날에도 계약 형태는 유지된다."""
        out = self.build()
        self.assertEqual(out["deals"], [])
        self.assertEqual(out["origins"], {})
        self.assertIn("updated", out)


class ArtifactGuardTest(unittest.TestCase):
    """수집이 무너진 날 좋은 산출물을 나쁜 것으로 덮지 않는가 (BB1 / 기획 F1).

    화면이 완전한 막다른 길이 되는 걸 생성 쪽에서 막는다. 파일을 안 쓰면
    `build_index()`가 기존 것을 읽어 인라인하므로 사이트는 어제 딜을 계속 보여 준다.
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        self.today = date.today()

    def add(self, n, origin="ICN"):
        """서로 다른 **도시** n곳을 넣는다.

        중복 제거 키가 `(허브, 한글도시명)`이라 공항 코드로 세면 안 된다 —
        도쿄(NRT/HND)·오사카(KIX/ITM)처럼 한 도시에 공항이 둘인 곳이 6군데다.
        """
        import dests
        seen_ko, codes = set(), []
        for c in dests.DEST:
            ko = dests.DEST[c][0]
            if dests.dest_coord(c) and ko not in seen_ko:
                seen_ko.add(ko)
                codes.append(c)
            if len(codes) == n:
                break
        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
        for i, code in enumerate(codes):
            self.conn.execute(
                """INSERT INTO broad_offers (fetched_date, origin, destination, price,
                                             transfers, depart_date, return_date, found_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (self.today.isoformat(), origin, code, 100000 + i, 0,
                 (self.today + timedelta(days=30)).isoformat(),
                 (self.today + timedelta(days=33)).isoformat(), fresh.isoformat()))
        return len(codes)

    def build_into(self, tmp):
        with mock.patch.object(discover_data, "DOCS", Path(tmp)):
            return discover_data.build_deals_json(self.conn)

    def seed_previous(self, tmp, count):
        """이전 산출물을 흉내 낸다."""
        d = Path(tmp) / "data"
        d.mkdir(parents=True, exist_ok=True)
        (d / "deals.json").write_text(json.dumps(
            {"updated": "2026-09-01 07:10", "origins": {},
             "deals": [{"price": i} for i in range(count)]}), encoding="utf-8")

    def test_empty_day_preserves_the_previous_artifact(self):
        """딜 0건이어도 기존 파일을 덮지 않는다 — 이게 F1의 생성 쪽 방어다."""
        with tempfile.TemporaryDirectory() as tmp:
            self.seed_previous(tmp, 100)
            self.assertEqual(self.build_into(tmp), -1)
            kept = json.loads((Path(tmp) / "data" / "deals.json").read_text(encoding="utf-8"))
            self.assertEqual(len(kept["deals"]), 100, "이전 산출물이 남아 있어야 한다")
            self.assertEqual(kept["updated"], "2026-09-01 07:10",
                             "updated도 예전 시각 그대로 — 어제 데이터에 오늘 도장을 찍지 않는다")

    def test_a_sharp_drop_is_treated_as_an_accident(self):
        """절반 이하로 떨어지면 사고로 본다(실측 평소 변동은 최대 -12.5%)."""
        n = self.add(MIN_DEALS + 5)
        with tempfile.TemporaryDirectory() as tmp:
            self.seed_previous(tmp, int(n / MIN_RATIO) + 10)
            self.assertEqual(self.build_into(tmp), -1)

    def test_a_normal_day_writes_through(self):
        """평소 변동 범위면 그대로 쓴다."""
        n = self.add(MIN_DEALS + 20)
        with tempfile.TemporaryDirectory() as tmp:
            self.seed_previous(tmp, n + 3)
            self.assertEqual(self.build_into(tmp), n)

    def test_no_previous_artifact_always_writes(self):
        """지킬 이전 산출물이 없으면 적은 건수라도 쓴다 — 그게 최선이다."""
        self.add(2)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.build_into(tmp), 2)

    def test_a_degraded_previous_does_not_lock_us_out(self):
        """이전 파일이 이미 하한선 미만이면 검사를 걸지 않는다.

        안 그러면 한 번 망가진 파일이 영원히 보존돼 정상 데이터가 못 들어온다.
        """
        self.add(3)
        with tempfile.TemporaryDirectory() as tmp:
            self.seed_previous(tmp, 5)          # 이전도 하한선 미만
            self.assertEqual(self.build_into(tmp), 3)
