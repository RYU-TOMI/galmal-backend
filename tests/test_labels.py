# -*- coding: utf-8 -*-
"""labels — 코드→한글명이 어긋나지 않는가.

`labels.CITY`와 `dests`에 같은 지식이 두 곳으로 있었고, 부산·대구가 `dests`에만
있어서 노선 페이지 제목이 `"PUS → 도쿄"`로 나갔다(2026-09-01, 부산 노선 추가 때).
이 프로젝트에서 반복해 만난 "같은 사실이 두 곳에 있으면 갈라진다"의 또 다른 사례다.
"""
import unittest

import config
import dests
from labels import CITY, REGION, REGION_NAME, city, region_of


class CityNameTest(unittest.TestCase):

    def test_every_route_endpoint_has_a_korean_name(self):
        """`config.ROUTES`의 모든 코드가 한글로 나와야 한다.

        노선을 새로 추가할 때 이름이 빠지면 **페이지 제목·본문·SEO 설명에
        코드가 그대로 노출된다.** 화면을 봐야 알 수 있는 종류라 여기서 막는다.
        """
        raw = sorted({c for pair in config.ROUTES for c in pair if city(c) == c})
        self.assertEqual(raw, [], f"한글명이 없는 코드: {raw}")

    def test_origin_airports_are_named(self):
        for code in dests.ORIGINS:
            with self.subTest(code=code):
                self.assertNotEqual(city(code), code)

    def test_falls_back_to_the_destination_dictionary(self):
        """`CITY`에 없어도 `dests.DEST`(84곳)가 있으면 한글로 나온다."""
        self.assertNotIn("MLE", CITY)
        self.assertEqual(city("MLE"), "몰디브")

    def test_the_two_dictionaries_do_not_diverge(self):
        """`CITY`와 `dests`가 같은 코드를 다르게 부르면 안 된다.

        2026-09-01 현재 `CITY`는 `dests`의 **부분집합이고 이름도 전부 같다.**
        그래서 폴백만으로 충분하다. 한쪽만 고치면 화면에 따라 다른 이름이 나오는데,
        어느 화면이 어느 사전을 쓰는지는 아무도 기억하지 않는다.
        """
        both = {**{k: dests.ORIGINS[k] for k in dests.ORIGINS},
                **{k: v[0] for k, v in dests.DEST.items()}}
        diverged = sorted(f"{k}: CITY={CITY[k]!r} dests={both[k]!r}"
                          for k in CITY if k in both and CITY[k] != both[k])
        self.assertEqual(diverged, [], f"두 사전이 어긋난다: {diverged}")

        orphan = sorted(k for k in CITY if k not in both)
        self.assertEqual(orphan, [], f"CITY에만 있어 dests가 모르는 코드: {orphan}")

    def test_unknown_code_passes_through(self):
        self.assertEqual(city("ZZZ"), "ZZZ")


class RegionTest(unittest.TestCase):
    """지역도 같은 지식이 두 곳에 있다 — `labels.REGION`과 `dests.DEST[..][2]`.

    `REGION`은 초기 26개 노선만 담고 있어서 목적지를 넓힐 때마다 조용히 `"etc"`로
    떨어졌다. 2026-09-02 기준 89곳 중 59곳이 어긋났고, 노선 페이지 브레드크럼에
    **`부산 → 상하이`가 "기타"로** 나가고 있었다. 이제 JSON-LD로 검색엔진에도
    나가므로 조용히 틀리면 더 나쁘다.
    """

    def test_route_destinations_are_not_dumped_into_etc(self):
        """노선 페이지가 생기는 목적지는 `dests`가 아는 지역으로 나와야 한다."""
        wrong = sorted(
            f"{o}-{d}: {region_of(d)} != {dests.DEST[d][2]}"
            for o, d in config.ROUTES
            if dests.is_destination(d)
            and region_of(d) == "etc" and dests.DEST[d][2] != "etc")
        self.assertEqual(wrong, [], f"지역이 '기타'로 떨어진 노선: {wrong}")

    def test_region_name_covers_everything_region_of_can_return(self):
        """`build_site`가 `REGION_NAME[region_of(dest)]`로 **직접 인덱싱**한다.

        폴백이 `dests`의 키(`island`·`oc`)를 돌려줄 수 있으므로 여기 빠지면
        노선 페이지 생성이 KeyError로 죽는다.
        """
        produced = {region_of(d) for d in dests.DEST}
        missing = sorted(produced - set(REGION_NAME))
        self.assertEqual(missing, [], f"REGION_NAME에 없는 지역 코드: {missing}")

    def test_known_taxonomy_divergence_is_only_these_two(self):
        """`REGION`에 있는 코드는 폴백이 안 걸리므로 두 사전이 계속 다르다.

        GUM(국내·괌 vs 휴양·섬) · SYD(미주·대양주 vs 대양주)는 **표시 문구 문제**라
        기획이 정한다(BB26). 여기서 고정해 두면 새로 갈라지는 건 실패로 잡힌다.
        """
        diverged = sorted(
            code for code in dests.DEST
            if code in REGION and REGION[code] != dests.DEST[code][2])
        self.assertEqual(diverged, ["GUM", "SYD"],
                         f"알려진 것 말고 새로 갈라진 코드가 있다: {diverged}")


if __name__ == "__main__":
    unittest.main()
