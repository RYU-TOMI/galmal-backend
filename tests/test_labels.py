# -*- coding: utf-8 -*-
"""labels — 코드→한글명이 어긋나지 않는가.

`labels.CITY`와 `dests`에 같은 지식이 두 곳으로 있었고, 부산·대구가 `dests`에만
있어서 노선 페이지 제목이 `"PUS → 도쿄"`로 나갔다(2026-09-01, 부산 노선 추가 때).
이 프로젝트에서 반복해 만난 "같은 사실이 두 곳에 있으면 갈라진다"의 또 다른 사례다.
"""
import json
import unittest
from pathlib import Path

import config
import dests
from dests import REGION_NAME
from labels import CITY, city, region_of


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
    """지역 표시명의 정본은 `dests.REGION_NAME`이다 (BB26 → BE10 T4).

    예전엔 `labels.REGION`·`labels.REGION_NAME`·`dests.REGION_NAME` 셋이 각자
    지역을 알고 있었다. `labels.REGION`은 초기 26개 노선만 담아 목적지를 넓힐
    때마다 조용히 `"etc"`로 떨어졌고(89곳 중 59곳 불일치), 어휘까지 갈라져
    **괌이 지도에서는 "휴양·섬", 노선 페이지에서는 "국내·괌"** 이었다.

    그 뒤 기획의 `COPY.md` §2b 표와 대조했는데, 저장소가 갈리면서 그 문서가
    두 벌이 됐다(R8). 이제 코드 쪽 한 곳(`REGION_NAME`)이 정본이고, 여기서는
    **계약의 지역 코드(`vocab.json`)와 빈틈없이 맞물리는지**만 본다.
    """

    VOCAB = Path(__file__).resolve().parent.parent / "contract" / "v1" / "vocab.json"

    def test_every_contract_region_has_a_name(self):
        """계약이 약속한 지역 코드 전부에 이름이 있고, 계약 밖 코드엔 이름이 없다.

        빠지면 `REGION_NAME[region_of(dest)]`로 직접 인덱싱하는 곳이 KeyError로 죽는다.
        남으면 계약에 없는 지역이 화면 어딘가에서 이름을 달고 나올 수 있다.
        """
        regions = set(json.loads(self.VOCAB.read_text(encoding="utf-8"))["region"])
        self.assertEqual(sorted(regions - set(REGION_NAME)), [], "이름 없는 지역 코드")
        self.assertEqual(sorted(set(REGION_NAME) - regions), [], "계약 밖 지역 코드")
        self.assertTrue(all(REGION_NAME[r].strip() for r in regions), "빈 표시명")

    def test_region_comes_only_from_the_destination_dictionary(self):
        """`labels`가 자체 지역 사전을 다시 갖지 않는가 — 갈라짐의 원인이었다."""
        import labels
        for gone in ("REGION", "REGION_NAME", "REGION_CHIPS"):
            with self.subTest(symbol=gone):
                self.assertFalse(hasattr(labels, gone),
                                 f"labels.{gone}이 되살아났다 — dests가 정본이다")
        for code, entry in dests.DEST.items():
            with self.subTest(code=code):
                self.assertEqual(region_of(code), entry[2])

    def test_unknown_destination_falls_back_to_etc(self):
        self.assertEqual(region_of("ZZZ"), "etc")


if __name__ == "__main__":
    unittest.main()
