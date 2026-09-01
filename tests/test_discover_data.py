# -*- coding: utf-8 -*-
"""discover_data.py의 순수 함수 테스트 — `_median`, `_when_label`.

두 함수는 `deals.json`의 `median`·`when` 필드를 직접 결정한다(`CONTRACT.md`).
할인율·`nights` 계산은 순수 함수가 아니라 `build_deals_json()` 본문에 인라인으로
있어 여기서 다루지 않는다 → BE0 T3의 end-to-end 검증에서 확인한다.

⚠️ `_when_label` 테스트 일부는 **현재 동작을 박제한 것이지 올바른 사양이 아니다.**
   해당 케이스에 BB 번호를 달아 두었다(`BACKEND.md` 곁가지 백로그).
   BE2에서 고치면 이 테스트들이 실패하면서 무엇이 바뀌었는지 알려준다.
"""
import contextlib
import io
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

    def test_this_weekend_is_this_calendar_week(self):
        """`이번 주말` = **이번 주(월~일)의 금·토·일.** 기준일 8/22는 토요일이다."""
        self.assertEqual(self.label(2026, 8, 21), "이번 주말")   # 금 (어제)
        self.assertEqual(self.label(2026, 8, 22), "이번 주말")   # 토 (오늘)
        self.assertEqual(self.label(2026, 8, 23), "이번 주말")   # 일

    def test_next_weekend_has_its_own_label(self):
        """BB21 해결: 다음 주 금·토·일은 `다음 주말`이다.

        예전엔 "9일 이내 + 금·토·일"이라 이것들이 전부 `이번 주말`로 나갔다.
        금·토·일에 접속하면 다음 주말 3일이 통째로 오라벨됐고, 임박 신호라
        사용자 행동에 직접 영향을 줬다.
        """
        self.assertEqual(self.label(2026, 8, 28), "다음 주말")   # 금, +6
        self.assertEqual(self.label(2026, 8, 29), "다음 주말")   # 토, +7
        self.assertEqual(self.label(2026, 8, 30), "다음 주말")   # 일, +8

    def test_this_week_excludes_next_week(self):
        """`이번 주`도 달력 기준이다 — 다음 주 평일은 `이번 달`로 떨어진다."""
        self.assertEqual(self.label(2026, 8, 31), "이번 달")     # 월, 다음 주·같은 달
        self.assertEqual(self.label(2026, 9, 1), "다음 달")      # 화, 다음 주·다음 달

    def test_weekday_in_this_week_is_this_week(self):
        """기준일이 토요일이라 이번 주 평일은 이미 지났다 — 과거도 이번 주다."""
        self.assertEqual(self.label(2026, 8, 19), "이번 주")     # 수 (지난)

    def test_a_week_can_cross_a_month(self):
        """달을 넘어도 이번 주면 이번 주다 — 1·2가 4·5보다 먼저다."""
        self.assertEqual(_when_label(date(2026, 10, 3), date(2026, 9, 30)),
                         "이번 주말")                             # 수 기준 토
        self.assertEqual(_when_label(date(2026, 10, 1), date(2026, 9, 30)),
                         "이번 주")                               # 수 기준 목

    def test_next_month(self):
        self.assertEqual(self.label(2026, 9, 1), "다음 달")      # 화, +10

    def test_month_after_next_uses_month_name(self):
        self.assertEqual(self.label(2026, 10, 1), "10월")        # 목, +40

    def test_year_end_rolls_over_to_january(self):
        """12월 기준 '다음 달'은 이듬해 1월. `nxt_year` 보정이 동작하는지."""
        self.assertEqual(_when_label(date(2027, 1, 4), date(2026, 12, 15)), "다음 달")

    def test_january_of_a_later_year_is_not_next_month(self):
        """'다음 달'은 달뿐 아니라 **연도까지** 맞아야 한다.

        2026-12 기준 '다음 달'은 2027-01뿐이다. 2028-01은 달이 같아도 걸러진다.
        """
        self.assertEqual(_when_label(date(2028, 1, 4), date(2026, 12, 15)),
                         "2028년 1월")

    # ---- BB7·BB8 수정 후 사양 ----

    def test_this_month_has_its_own_label(self):
        """BB7 해결: 이번 달 출발은 '이번 달'.

        예전엔 '8월'로 나왔다. 오늘이 8월인데 '8월'은 아무 말도 아니고,
        월초에는 딜의 3분의 1이 이 상태였다(2026-09-01 실측 44/126).
        """
        # 기준일 8/22(토)의 '이번 주'는 8/17~8/23이므로 8/25·8/31은 다음 주다.
        # 다음 주 **평일**은 주말만큼 특별하지 않아 `이번 달`로 떨어진다(기획 판단).
        self.assertEqual(self.label(2026, 8, 25), "이번 달")      # 화, 다음 주
        self.assertEqual(self.label(2026, 8, 31), "이번 달")      # 월, 다다음 주

    def test_next_year_is_marked_as_such(self):
        """BB8 해결: 이듬해 출발은 '내년 N월'.

        예전엔 '3월'이라 지나간 3월과 구분되지 않았다. 출발일 범위가 약 1년이라
        '7월'이 지난 7월이 아니라 내년 7월인 경우가 실제로 있었다.
        """
        self.assertEqual(self.label(2027, 3, 1), "내년 3월")
        self.assertEqual(self.label(2027, 7, 1), "내년 7월")

    def test_two_years_out_spells_the_year(self):
        """2년 이상 뒤는 '내년'이 아니다. 현재 데이터엔 없지만 방어적으로 둔다."""
        self.assertEqual(self.label(2028, 3, 1), "2028년 3월")

    def test_same_year_later_months_keep_the_bare_month(self):
        """같은 해 2개월 이후는 그대로 월 이름 — 연도가 자명하다."""
        self.assertEqual(self.label(2026, 11, 20), "11월")

    def test_past_departure_falls_into_this_week(self):
        """과거 날짜는 '이번 주'가 된다(`delta <= 7`이 음수도 통과).

        `build_deals_json()`이 미래 출발만 조회하므로 실사용에는 나타나지 않는다.
        함수 단독 동작을 기록해 둔다.
        """
        self.assertEqual(self.label(2026, 8, 19), "이번 주")     # 수, -3



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
        """7일 넘게 관측되지 않은 가격은 내보내지 않는다.

        ⚠️ 이 픽스처는 **현재 파이프라인이 만들 수 없는 상태**다. 수집이 96h 넘은
        가격을 안 받고 창이 3일이라 후보의 seen 나이 상한이 정확히 7일이기 때문이다.
        즉 이 테스트는 "지금 일어나는 일"이 아니라 **수집 정책이 넓어졌을 때
        이 컷이 여전히 동작하는지**를 지킨다. 그게 이 상수를 남겨 둔 이유다.
        """
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


class RouteCodeTest(unittest.TestCase):
    """`route`는 **실제로 만들어진 페이지**만 가리킨다 (BB22).

    `config.ROUTES` 목록으로 판정하면 노선을 새로 추가한 날 페이지가 아직 없는데도
    값이 나가 프론트가 404를 본다. `route_page()`는 수집 이력이 없으면 파일을
    만들지 않기 때문이다. 그래서 빌드가 실제로 만든 목록을 받아 대조한다.
    """

    def test_only_generated_pages_are_referenced(self):
        available = {"ICN-FUK", "GMP-CJU"}
        self.assertEqual(discover_data._route_code("ICN", "FUK", available), "ICN-FUK")
        self.assertIsNone(discover_data._route_code("PUS", "FUK", available),
                          "페이지가 없으면 None이어야 한다")

    def test_empty_set_yields_no_routes(self):
        """빌드가 페이지를 하나도 못 만든 날에도 404를 내보내지 않는다."""
        self.assertIsNone(discover_data._route_code("ICN", "FUK", set()))

    def test_origin_airport_decides_not_the_hub(self):
        """허브가 아니라 **실제 공항**으로 판정한다.

        김포 딜에 `ICN-` 코드를 붙이면 다른 노선의 시세를 보여주게 된다.
        """
        available = {"ICN-CJU", "GMP-CJU"}
        self.assertEqual(discover_data._route_code("GMP", "CJU", available), "GMP-CJU")
        self.assertEqual(discover_data._route_code("ICN", "CJU", available), "ICN-CJU")


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
        # 보존 경고를 삼킨다 — 테스트 출력에서 진짜 실패가 묻히지 않게.
        with mock.patch.object(discover_data, "DOCS", Path(tmp)),                 contextlib.redirect_stdout(io.StringIO()):
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


class PriorHistoryTest(unittest.TestCase):
    """`low`·`obs_days` — 이전 관측 기간의 최저가와 관측 일수.

    **오늘(이번 수집 창)을 빼는 게 핵심이다.** `price`가 이미 최근 3~4일 중
    최저가라, 그걸 포함하고 "최저냐"를 물으면 동어반복이 된다 — 실측으로 41%가
    "최저"로 나왔고, 빼고 재면 신기록 22% / 낙폭 5% 이상은 7%로 떨어진다.
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        self.today = date.today()

    def add(self, price, days_ago, origin="ICN", dest="FUK"):
        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)
        self.conn.execute(
            """INSERT OR REPLACE INTO broad_offers
               (fetched_date, origin, destination, price, transfers,
                depart_date, return_date, found_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            ((self.today - timedelta(days=days_ago)).isoformat(), origin, dest, price, 0,
             (self.today + timedelta(days=30)).isoformat(),
             (self.today + timedelta(days=33)).isoformat(), fresh.isoformat()))

    def build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(discover_data, "DOCS", Path(tmp)),                     contextlib.redirect_stdout(io.StringIO()):
                discover_data.build_deals_json(self.conn)
                raw = (Path(tmp) / "data" / "deals.json").read_text(encoding="utf-8")
        return json.loads(raw)["deals"][0]

    def test_today_is_excluded_from_low(self):
        """오늘 값이 제일 싸도 `low`에 들어가지 않는다 — 그래야 비교가 성립한다."""
        self.add(200000, days_ago=10)
        self.add(150000, days_ago=8)
        self.add(90000, days_ago=0)            # 오늘, 최저가
        deal = self.build()
        self.assertEqual(deal["price"], 90000)
        self.assertEqual(deal["low"], 150000, "오늘 값이 low에 섞이면 안 된다")
        self.assertLess(deal["price"], deal["low"], "신기록으로 판정 가능해야 한다")

    def test_the_whole_window_is_excluded_not_just_today(self):
        """수집 창(3일) 전체가 빠진다. 창 안의 값은 `price` 후보이지 비교 대상이 아니다."""
        self.add(300000, days_ago=10)
        self.add(120000, days_ago=2)           # 창 안 — low에 들어가면 안 된다
        self.add(100000, days_ago=0)
        self.assertEqual(self.build()["low"], 300000)

    def test_obs_days_counts_prior_observation_days(self):
        for d in (5, 6, 7, 8):
            self.add(200000 + d, days_ago=d)
        self.add(100000, days_ago=0)
        self.assertEqual(self.build()["obs_days"], 4)

    def test_no_history_yields_null_and_zero(self):
        """계약: 이력이 없으면 `low`는 null, `obs_days`는 0."""
        self.add(100000, days_ago=0)
        deal = self.build()
        self.assertIsNone(deal["low"])
        self.assertEqual(deal["obs_days"], 0)

    def test_history_is_grouped_by_city_not_airport(self):
        """알갱이는 `(허브, 도시)` — 딜의 중복 제거 키와 같아야 한다.

        인천·김포는 같은 서울 허브이므로 이력이 합쳐진다. 안 그러면
        "17일 중 최저"가 그 카드가 가리키는 도시의 말이 아니게 된다.
        """
        self.add(500000, days_ago=10, origin="ICN")
        self.add(200000, days_ago=9, origin="GMP")   # 같은 서울 허브
        self.add(100000, days_ago=0, origin="ICN")
        deal = self.build()
        self.assertEqual(deal["o"], "SEL")
        self.assertEqual(deal["low"], 200000, "인천·김포 이력이 합쳐져야 한다")
        self.assertEqual(deal["obs_days"], 2)

if __name__ == "__main__":
    unittest.main()
