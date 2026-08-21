# -*- coding: utf-8 -*-
"""dests.py 사전 정합성 — 목적지를 추가할 때의 회귀 방지.

지금(2026-08-22) 사전은 깨끗하다(DEST 84 = DEST_COORD 84). 그러니 이 테스트는
버그를 잡으려는 게 아니라 **앞으로 깨지는 걸 막으려는 것**이다.

특히 좌표 누락은 조용히 실패한다: `dest_coord()`가 None을 돌려주면
`build_deals_json()`이 그 목적지를 예외 없이 건너뛴다. 목적지를 추가했는데
지도에 안 나타나는 종류의 버그라 자동 검사의 값어치가 크다.

enum 값(region/haul/tier)은 `CONTRACT.md`가 프론트에 약속한 목록이므로
여기 리터럴로 고정한다. 사전에 새 값이 생기면 계약 위반으로 잡힌다.
"""
import unittest

import dests
from discover_data import ORIGIN_HUBS, ORIGIN_NORM

# CONTRACT.md의 deal 객체 정의에서 그대로 옮긴 값
REGIONS = {"jp", "cn", "sea", "island", "oc", "eu", "am", "etc", "dom"}
HAULS = {"short", "mid", "long"}


class DestDictionaryTest(unittest.TestCase):
    """DEST / DEST_COORD / MAJOR 세 사전이 서로 어긋나지 않는가."""

    def test_every_destination_has_coordinates(self):
        """좌표 없는 목적지는 발견 피드에서 조용히 사라진다."""
        missing = sorted(set(dests.DEST) - set(dests.DEST_COORD))
        self.assertEqual(missing, [], f"좌표가 없는 목적지: {missing}")

    def test_no_orphan_coordinates(self):
        """사전에 없는 좌표는 죽은 항목 — 지우거나 DEST에 넣어야 한다."""
        orphans = sorted(set(dests.DEST_COORD) - set(dests.DEST))
        self.assertEqual(orphans, [], f"DEST에 없는 좌표: {orphans}")

    def test_major_tier_is_a_subset_of_destinations(self):
        """MAJOR에만 있고 DEST에 없는 코드는 LOD 등급이 새는 것."""
        stray = sorted(dests.MAJOR - set(dests.DEST))
        self.assertEqual(stray, [], f"DEST에 없는 MAJOR: {stray}")

    def test_coordinates_are_in_range(self):
        """위도 ±90 / 경도 ±180. 부호나 자릿수 오타를 잡는다."""
        for iata, (lat, lon) in dests.DEST_COORD.items():
            with self.subTest(iata=iata):
                self.assertTrue(-90 <= lat <= 90, f"{iata} 위도 {lat}")
                self.assertTrue(-180 <= lon <= 180, f"{iata} 경도 {lon}")

    def test_entry_shape_matches_the_contract(self):
        """DEST 값은 (한글명, 국가, region, haul, tags) 5-튜플이고 enum을 지킨다."""
        for iata, entry in dests.DEST.items():
            with self.subTest(iata=iata):
                self.assertEqual(len(entry), 5)
                ko, country, region, haul, tags = entry
                self.assertTrue(ko and isinstance(ko, str))
                self.assertTrue(country and isinstance(country, str))
                self.assertIn(region, REGIONS)
                self.assertIn(haul, HAULS)
                self.assertIsInstance(tags, list)
                self.assertTrue(tags, f"{iata} 태그가 비었다")
                for tag in tags:
                    self.assertIsInstance(tag, str)

    # 태그 통제 어휘 일치는 검사하지 않는다 — BB9 참조.
    # dests.py docstring은 9종을 선언하는데 실제로는 12종이 쓰인다
    # (야시장·유적·트레킹). 어느 쪽이 맞는지 정해진 뒤에 검사를 넣는다.

    def test_helpers_agree_with_the_dictionaries(self):
        """dest_coord / is_destination / tier가 사전과 같은 답을 내는가."""
        sample = next(iter(dests.DEST))
        self.assertEqual(dests.dest_coord(sample), dests.DEST_COORD[sample])
        self.assertTrue(dests.is_destination(sample))
        self.assertFalse(dests.is_destination("ZZZ"))
        self.assertIsNone(dests.dest_coord("ZZZ"))
        self.assertEqual(dests.tier(sample),
                         "major" if sample in dests.MAJOR else "minor")
        self.assertEqual(dests.tier("ZZZ"), "minor")


class OriginTest(unittest.TestCase):
    """출발 공항(한국) 쪽 사전. 여기가 어긋나면 그 공항 딜이 통째로 사라진다."""

    def test_every_origin_has_coordinates(self):
        self.assertEqual(set(dests.ORIGINS), set(dests.ORIGIN_COORD))

    def test_normaliser_covers_every_origin(self):
        """수집 대상 공항이 전부 허브로 정규화되는가.

        `ORIGIN_NORM`에 없는 공항은 `build_deals_json()`이 `continue`로 버린다.
        새 출발 공항을 `dests.ORIGINS`에만 넣고 여기 빠뜨리면 수집은 되는데
        화면에는 안 나오는 상태가 된다.
        """
        self.assertEqual(set(ORIGIN_NORM), set(dests.ORIGINS))

    def test_normalised_hubs_exist(self):
        """정규화 결과는 전부 실재하는 허브여야 한다(`origins` 키가 된다)."""
        self.assertTrue(set(ORIGIN_NORM.values()) <= set(ORIGIN_HUBS))

    def test_hub_coordinates_are_in_range(self):
        for hub, (name, lat, lon) in ORIGIN_HUBS.items():
            with self.subTest(hub=hub):
                self.assertTrue(name and isinstance(name, str))
                self.assertTrue(-90 <= lat <= 90)
                self.assertTrue(-180 <= lon <= 180)


if __name__ == "__main__":
    unittest.main()
