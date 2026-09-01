# -*- coding: utf-8 -*-
"""labels — 코드→한글명이 어긋나지 않는가.

`labels.CITY`와 `dests`에 같은 지식이 두 곳으로 있었고, 부산·대구가 `dests`에만
있어서 노선 페이지 제목이 `"PUS → 도쿄"`로 나갔다(2026-09-01, 부산 노선 추가 때).
이 프로젝트에서 반복해 만난 "같은 사실이 두 곳에 있으면 갈라진다"의 또 다른 사례다.
"""
import unittest

import config
import dests
from labels import CITY, city


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


if __name__ == "__main__":
    unittest.main()
