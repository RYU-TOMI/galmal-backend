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
import os
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

import affiliates
import env as env_mod
from affiliates import (_ddmm, _yymmdd, _yyyymmdd, aviasales_link,
                        compare_links, google_flights_link, naver_link,
                        skyscanner_link, trip_link)

DEP, RET = "2026-09-16", "2026-09-17"
NO_ENV_FILE = Path(__file__).resolve().parent / "_없는파일.env"

TRIP_ENV = {"TP_MARKER": "12345", "TP_TRIP_TRS": "777",
            "TP_TRIP_P": "888", "TP_TRIP_CAMPAIGN": "99"}


@contextlib.contextmanager
def isolated(env=None):
    """`.env` 파일을 무시하고 주어진 환경변수만 보이게 하는 컨텍스트.

    `.env` 를 읽는 곳이 `collector/env.py` 한 곳으로 모였으므로(BE18) 거기를 가린다.
    예전엔 `affiliates._ENV_FILE` 을 가렸는데, 그때는 모듈마다 자기 경로를 들고 있었다.
    """
    with mock.patch.object(env_mod, "ENV_FILE", NO_ENV_FILE), mock.patch.dict("os.environ", env or {}, clear=True):
        env_mod._cache.clear()          # 경로가 바뀌었으니 파일 캐시를 버린다
        try:
            yield
        finally:
            env_mod._cache.clear()


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
            # 🔴 `adultsv2` 다. `adults` 는 스카이스캐너가 **읽지 않는다**(BB42, 2026-09-22 브라우저 실측:
            # `?adults=2` → 화면 「성인 1명」). 기본값이 1인이라 예전엔 결과가 우연히 맞았다.
            "?adultsv2=1&currency=KRW&market=KR&locale=ko-KR")

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
        # `for 1 adults` 는 비문이지만 구글이 「성인 1명」으로 읽는다(2026-09-22 실측).
        # 1인에도 넣는 이유: `pax_url` 의 `{n}`→`1` 이 `url` 과 바이트가 같아야 한다(계약 §links[]).
        self.assertEqual(q, "ICN to FUK on 2026-09-16 through 2026-09-17 for 1 adults")

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
        """각 원소의 키(`ad` 2026-09-02 · `pax_url` 2026-09-22 추가).

        **계약의 `required` 와 같은 집합**이어야 한다 — 키를 늘리면서 계약을 안 고치면
        소비자는 없는 줄 알고, 계약만 고치고 생산을 안 하면 검증기가 그날부터 실패한다.
        """
        for link in self.links():
            self.assertEqual(set(link), {"name", "tag", "ad", "url", "pax_url"})
            self.assertTrue(link["name"] and link["tag"])
            self.assertIsInstance(link["ad"], bool)
            self.assertTrue(link["url"].startswith("https://"))
            self.assertTrue(link["pax_url"] is None or link["pax_url"].startswith("https://"))

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


class AdFlagTest(unittest.TestCase):
    """`ad` — 화면의 "(광고)" 고지가 붙는 근거 (프론트 요청 2026-09-02).

    고지는 법적 의무다(정보통신망법·공정위 — `CLAUDE.md`). 프론트가 이름·순서·
    URL 모양으로 추측하면 제휴 구성이 바뀌는 날 **조용히** 틀려지므로, 판정을
    아는 백엔드가 단언한다. 여기서 지키는 건 **선언과 실제가 갈리지 않는 것**이다.
    """

    def links(self, env=None):
        with isolated(env):
            return compare_links("ICN", "FUK", DEP, RET)

    @staticmethod
    def earns(url):
        """URL이 실제로 수수료를 추적하는가 — 마커 또는 tp.media 래퍼."""
        return "marker=" in url or url.startswith("https://tp.media/")

    def test_ad_is_true_exactly_when_the_url_earns(self):
        """선언(`ad`)과 실제(URL)가 어긋나면 고지가 거짓말이 된다.

        URL 빌더만 고치고 `ad`를 안 고치는 실수를 여기서 잡는다. 이게 이 파일에서
        가장 중요한 단언이다 — 나머지는 이 불변식의 특수한 경우일 뿐이다.
        """
        for env in (None, {"TP_MARKER": "12345"}, dict(TRIP_ENV)):
            for link in self.links(env):
                with self.subTest(env=env, name=link["name"]):
                    self.assertEqual(link["ad"], self.earns(link["url"]))

    def test_nothing_is_an_ad_without_affiliate_config(self):
        """제휴 설정이 하나도 없으면 (광고)가 붙을 링크도 없다."""
        self.assertEqual([x["name"] for x in self.links() if x["ad"]], [])

    def test_aviasales_is_the_only_ad_with_just_a_marker(self):
        """내일 크론의 상태 — 마커만 있고 Trip.com은 미승인."""
        ads = [x["name"] for x in self.links({"TP_MARKER": "12345"}) if x["ad"]]
        self.assertEqual(ads, ["Aviasales"])

    def test_trip_becomes_an_ad_once_approved(self):
        """Trip.com 승인 시 tp.media 래퍼가 붙어 그때부터 제휴 링크가 된다.

        Aviasales만 하드코딩했다면 승인되는 날 고지가 조용히 빠졌을 것이다.
        `ad`를 `_trip_configured()`로 계산하는 이유가 이것이다.
        """
        before = {x["name"]: x["ad"] for x in self.links()}
        after = {x["name"]: x["ad"] for x in self.links(dict(TRIP_ENV))}
        self.assertFalse(before["Trip.com"])
        self.assertTrue(after["Trip.com"])

    def test_neutral_shops_are_never_ads(self):
        """우리가 수수료를 안 받는 곳에 (광고)가 뜨면 그것도 거짓 고지다."""
        for env in (None, {"TP_MARKER": "12345"}, dict(TRIP_ENV)):
            flags = {x["name"]: x["ad"] for x in self.links(env)}
            for name in ("스카이스캐너", "네이버 항공권", "구글 항공권"):
                with self.subTest(env=env, name=name):
                    self.assertFalse(flags[name])


if __name__ == "__main__":
    unittest.main()


class CommittedArtifactTest(unittest.TestCase):
    """🔴 커밋된 `deals.json`에 수수료 경로가 살아 있는가 (BB30).

    위 `AdFlagTest`는 **함수**를 본다. 마커가 없으면 링크를 빼는 게 옳은 동작이므로
    거기선 결함이 아니다. 결함은 **그 결과물이 커밋될 때** 생긴다.

    2026-09-08, 프론트가 `index.html` 충돌을 `CLAUDE.md`의 「재빌드로 해결」
    절차대로 풀었는데 로컬에 `TP_MARKER`가 없어 **딜 125건 전부에서 Aviasales
    링크가 빠진 파일**이 나왔다. 커밋 직전에 알아채 복구했다.

    **눈으로는 못 잡는다** — 지도도 카드도 멀쩡히 뜨고 수익 링크만 없다.
    `publish.py`가 stderr로 외치지만 **사람은 경고를 넘긴다.** 그래서 여기서
    막는다. 배포되는 건 파일이고, 이 테스트는 그 파일을 본다.

    (`test_site_url.DeployedArtifactTest`와 같은 부류 — 코드가 아니라 산출물을 본다.)
    """

    @classmethod
    def setUpClass(cls):
        import json
        path = Path(__file__).resolve().parent.parent / "docs" / "v1" / "deals.json"
        if not path.exists():
            raise unittest.SkipTest("deals.json이 아직 생성되지 않았다")
        cls.deals = json.loads(path.read_text(encoding="utf-8"))["deals"]
        if not cls.deals:
            raise unittest.SkipTest("딜이 비어 있다")

    def test_every_deal_keeps_an_earning_link(self):
        """수수료가 붙는 링크가 하나도 없는 딜이 있으면 실패한다."""
        # 딜 객체를 통째로 비교하면 실패 메시지가 4천자짜리 dict 덤프가 된다.
        # 읽히지 않는 실패는 안 잡히는 것과 비슷하다 — 노선 코드만 보여준다.
        naked = [f"{d['o']}-{d['d']}" for d in self.deals
                 if not any(AdFlagTest.earns(l["url"]) for l in d.get("links", []))]
        self.assertEqual(
            naked[:5], [],
            f"수수료 경로가 없는 딜 {len(naked)}/{len(self.deals)}건 — "
            "시크릿 없이 재빌드한 산출물일 수 있다 (BACKEND.md BB30)")

    def test_ad_disclosure_matches_the_committed_urls(self):
        """`ad` 표기와 실제 URL이 커밋본에서도 일치하는가.

        고지는 법적 의무라(`CLAUDE.md`) 코드가 맞아도 **파일이 틀리면** 소용없다.
        """
        for i, d in enumerate(self.deals):
            for l in d.get("links", []):
                with self.subTest(deal=i, name=l.get("name")):
                    self.assertEqual(l.get("ad", False), AdFlagTest.earns(l["url"]))


class PaxUrlTest(unittest.TestCase):
    """인원 `{n}` 링크 — 계약 §links[] `pax_url` (DECISIONS 2026-09-22 (4)).

    이 파일이 막는 것: **화면에선 2명을 골랐는데 예약처는 1명으로 열리는 것.** 예외도 안 나고
    링크도 열리고 사람만 모른다 — 실제로 스카이스캐너가 그 상태였다(BB42, `adults` 를 안 읽는다).

    예약처마다 인원을 받는 자리가 다르다(2026-09-22 브라우저 실측):
        스카이스캐너 `adultsv2=` · 네이버 `adult=` · Trip.com `quantity=` ·
        구글 `q` 자연어 `for N adults` · Aviasales **경로 끝 숫자**
    그래서 소비자에게 「무엇을 바꾸라」가 아니라 **완성된 URL 한 벌**을 준다.
    """

    ARGS = ("ICN", "TYO", "2026-12-01", "2026-12-08")

    def links(self, **env):
        with mock.patch.dict(os.environ, {"TP_MARKER": "12345", **env}, clear=False):
            return affiliates.compare_links(*self.ARGS)

    def test_one_passenger_is_byte_identical_to_url(self):
        """🔴 계약의 보장 ① — 두 필드가 갈릴 자리를 없앤다.

        갈리면 아무도 모른다: `url` 로 연 사람과 `pax_url` 로 연 사람이 **다른 화면**을 본다.
        """
        for l in self.links():
            with self.subTest(name=l["name"]):
                self.assertEqual(l["pax_url"].replace("{n}", "1"), l["url"])

    def test_every_booker_carries_the_token_exactly_once(self):
        for l in self.links():
            with self.subTest(name=l["name"]):
                self.assertIsNotNone(l["pax_url"])
                self.assertEqual(l["pax_url"].count("{n}"), 1)

    def test_token_is_outside_url_encoding(self):
        """🔴 계약의 보장 ② — 인코딩 안에 묻히면 소비자가 `{n}` 을 찾지 못한다.

        구글은 `q` 를 인코딩하고 Trip.com 제휴 래퍼는 target 전체를 인코딩해 감싼다.
        **제휴가 켜진 상태**로도 본다 — 지금 `TP_TRIP_*` 가 없어 래퍼가 안 씌워지므로,
        승인되는 날 조용히 깨지는 것을 막으려면 여기서 미리 켜 봐야 한다.
        """
        for env in ({}, {"TP_TRIP_TRS": "t", "TP_TRIP_P": "p", "TP_TRIP_CAMPAIGN": "c"}):
            for l in self.links(**env):
                with self.subTest(name=l["name"], wrapped=bool(env)):
                    self.assertNotIn("%7B", l["pax_url"].upper())
                    self.assertNotIn(affiliates._PAX_TOKEN, l["pax_url"])
                    self.assertNotIn(affiliates._PAX_TOKEN, l["url"])

    def test_each_booker_actually_carries_the_count(self):
        """인원을 바꾸면 **그 예약처가 읽는 자리**가 바뀐다 (2026-09-22 실측 형태 그대로)."""
        want = {
            "스카이스캐너": "adultsv2=3",      # 🔴 adults= 가 아니다 (BB42)
            "네이버 항공권": "adult=3",         # 단수형
            "Trip.com": "quantity=3",
            "구글 항공권": "for%203%20adults",  # 자연어 — 인코딩된 채로 들어간다
            "Aviasales": "TYO08123",           # 경로 끝 숫자
        }
        got = {l["name"]: l["pax_url"].replace("{n}", "3") for l in self.links()}
        self.assertEqual(set(got), set(want))
        for name, needle in want.items():
            with self.subTest(name=name):
                self.assertIn(needle, got[name])

    def test_skyscanner_never_uses_the_ignored_name(self):
        """BB42 회귀 방지 — `adults=` 는 스카이스캐너가 **읽지 않는다.**

        기본값이 1인이라 예전엔 결과가 우연히 맞았다. 되돌아가면 인원이 조용히 무시된다.
        """
        sky = next(l for l in self.links() if l["name"] == "스카이스캐너")
        for url in (sky["url"], sky["pax_url"]):
            self.assertNotIn("adults=", url)
            self.assertIn("adultsv2=", url)


