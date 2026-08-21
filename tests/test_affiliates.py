# -*- coding: utf-8 -*-
"""affiliates.py — 예약처 비교 링크 빌더.

이 링크들이 `deals.json`의 `links[]`로 그대로 나가고(`CONTRACT.md`), 사용자가
실제로 눌러 예약처로 넘어간다. 날짜 포맷이 하나만 틀려도 예약처가 엉뚱한 날을
띄우는데, 화면상으로는 링크가 멀쩡해 보여서 **눈으로는 발견되지 않는 종류의 버그**다.

⚠️ 격리: `_env()`는 `os.environ` → 저장소 루트 `.env` 순으로 읽는다. 이 저장소에는
   실제 `.env`가 있으므로 그대로 두면 테스트 결과가 개발자 머신마다 달라진다.
   `_ENV_FILE`을 없는 경로로 갈아끼우고 `os.environ`만 통제한다.
"""
import contextlib
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

import affiliates
from affiliates import (_ddmm, _yymmdd, _yyyymmdd, aviasales_link,
                        compare_links, google_flights_link, naver_link,
                        skyscanner_link, trip_link)

DEP, RET = "2026-09-16", "2026-09-17"
NO_ENV_FILE = Path(__file__).resolve().parent / "_없는파일.env"

TRIP_ENV = {"TP_MARKER": "12345", "TP_TRIP_TRS": "777",
            "TP_TRIP_P": "888", "TP_TRIP_CAMPAIGN": "99"}


@contextlib.contextmanager
def isolated(env=None):
    """`.env` 파일을 무시하고 주어진 환경변수만 보이게 하는 컨텍스트."""
    with mock.patch.object(affiliates, "_ENV_FILE", NO_ENV_FILE),             mock.patch.dict("os.environ", env or {}, clear=True):
        yield


class DateFormatTest(unittest.TestCase):
    """예약처마다 날짜 표기가 다르다. 셋 다 같은 날을 가리켜야 한다."""

    def test_ddmm_is_day_then_month(self):
        """Aviasales는 일-월 순서(1609 = 9월 16일). 월-일로 뒤집히기 쉬운 자리."""
        self.assertEqual(_ddmm("2026-09-16"), "1609")

    def test_yymmdd(self):
        self.assertEqual(_yymmdd("2026-09-16"), "260916")

    def test_yyyymmdd(self):
        self.assertEqual(_yyyymmdd("2026-09-16"), "20260916")

    def test_single_digit_parts_are_zero_padded(self):
        """1월 2일이 '21'이 아니라 '0201'이어야 한다."""
        self.assertEqual(_ddmm("2027-01-02"), "0201")
        self.assertEqual(_yymmdd("2027-01-02"), "270102")
        self.assertEqual(_yyyymmdd("2027-01-02"), "20270102")


class LinkFormatTest(unittest.TestCase):
    """예약처별 URL 구조. 왕복과 편도가 갈리는 지점을 함께 본다."""

    def test_skyscanner_round_trip(self):
        self.assertEqual(
            skyscanner_link("ICN", "FUK", DEP, RET),
            "https://www.skyscanner.co.kr/transport/flights/icn/fuk/260916/260917/"
            "?adults=1&currency=KRW&market=KR&locale=ko-KR")

    def test_skyscanner_one_way_omits_return_segment(self):
        url = skyscanner_link("ICN", "FUK", DEP, None)
        self.assertIn("/icn/fuk/260916/?", url)
        self.assertNotIn("260917", url)

    def test_naver_marks_domestic_routes(self):
        """네이버는 국내선/국제선 경로가 갈린다. 제주행은 domestic이어야 한다."""
        self.assertIn("/domestic/", naver_link("GMP", "CJU", DEP, None))

    def test_naver_marks_international_routes(self):
        self.assertIn("/international/", naver_link("ICN", "FUK", DEP, None))

    def test_naver_return_leg_is_reversed(self):
        """귀국편은 출발지와 도착지가 뒤집힌 구간으로 붙는다."""
        self.assertEqual(
            naver_link("ICN", "FUK", DEP, RET),
            "https://flight.naver.com/flights/international/"
            "ICN-FUK-20260916/FUK-ICN-20260917?adult=1&fareType=Y")

    def test_aviasales_segment_packs_codes_and_dates(self):
        """ICN + 1609 + FUK + 1709 + 승객수 1."""
        with isolated():
            self.assertEqual(aviasales_link("ICN", "FUK", DEP, RET),
                             "https://www.aviasales.com/search/ICN1609FUK17091")

    def test_google_flights_query_is_encoded(self):
        url = google_flights_link("ICN", "FUK", DEP, RET)
        self.assertTrue(url.startswith(
            "https://www.google.com/travel/flights?hl=ko&curr=KRW&q="))
        q = urllib.parse.unquote(url.split("q=", 1)[1])
        self.assertEqual(q, "ICN to FUK on 2026-09-16 through 2026-09-17")

    def test_trip_link_is_korean_locale(self):
        """제휴 미설정이어도 사용자는 한국어 Trip.com으로 보낸다(UX 우선)."""
        with isolated():
            url = trip_link("ICN", "FUK", DEP, RET)
        self.assertTrue(url.startswith("https://kr.trip.com/flights/showfarefirst"))
        self.assertIn("locale=ko-KR", url)
        self.assertIn("triptype=rt", url)

    def test_trip_link_one_way_flag(self):
        with isolated():
            self.assertIn("triptype=ow", trip_link("ICN", "FUK", DEP, None))


class AffiliateWrappingTest(unittest.TestCase):
    """수수료 마커가 붙는 조건. 여기가 틀리면 수익이 0이 되거나 광고 고지가 어긋난다."""

    def test_trip_stays_bare_until_all_four_values_exist(self):
        """네 값 중 하나만 빠져도 래핑하지 않는다 — 깨진 제휴 링크보다 낫다."""
        partial = dict(TRIP_ENV)
        del partial["TP_TRIP_CAMPAIGN"]
        with isolated(partial):
            self.assertTrue(trip_link("ICN", "FUK", DEP, RET)
                            .startswith("https://kr.trip.com/"))

    def test_trip_wraps_when_fully_configured(self):
        with isolated(TRIP_ENV):
            url = trip_link("ICN", "FUK", DEP, RET)
        self.assertTrue(url.startswith("https://tp.media/r?marker=12345"))
        # 원본 링크는 u= 파라미터에 통째로 인코딩돼 들어간다
        target = urllib.parse.unquote(url.split("&u=", 1)[1])
        self.assertTrue(target.startswith("https://kr.trip.com/flights/showfarefirst"))

    def test_aviasales_marker_is_appended_only_when_present(self):
        with isolated():
            self.assertNotIn("marker", aviasales_link("ICN", "FUK", DEP, RET))
        with isolated({"TP_MARKER": "12345"}):
            self.assertTrue(aviasales_link("ICN", "FUK", DEP, RET)
                            .endswith("?marker=12345"))


class CompareLinksTest(unittest.TestCase):
    """`deals.json`의 `links[]`가 되는 배열. 계약이 개수를 가변(3~5)으로 약속했다."""

    def links(self, env=None):
        with isolated(env):
            return compare_links("ICN", "FUK", DEP, RET)

    def test_shape_matches_the_contract(self):
        """각 원소는 name·tag·url 세 키를 갖는다."""
        for link in self.links():
            self.assertEqual(set(link), {"name", "tag", "url"})
            self.assertTrue(link["name"] and link["tag"])
            self.assertTrue(link["url"].startswith("https://"))

    def test_korean_shops_only_without_a_marker(self):
        """마커가 없으면 수수료가 0이므로 영어 예약처(Aviasales)는 숨긴다."""
        names = [x["name"] for x in self.links()]
        self.assertEqual(names, ["스카이스캐너", "네이버 항공권", "구글 항공권", "Trip.com"])

    def test_aviasales_appears_only_when_it_earns(self):
        names = [x["name"] for x in self.links({"TP_MARKER": "12345"})]
        self.assertEqual(names[-1], "Aviasales")
        self.assertEqual(len(names), 5)

    def test_order_is_stable(self):
        """순서 = 화면 노출 순서(`CONTRACT.md`). 스카이스캐너가 항상 처음."""
        self.assertEqual(self.links()[0]["name"], "스카이스캐너")
        self.assertEqual(self.links({"TP_MARKER": "1"})[0]["name"], "스카이스캐너")


if __name__ == "__main__":
    unittest.main()
