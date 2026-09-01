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
import re
import unittest
from pathlib import Path

import dests
from discover_data import ORIGIN_HUBS, ORIGIN_NORM

TAGS_MD = Path(__file__).resolve().parent.parent / "TAGS.md"
# | `IATA` | 도시 | 전 | `태그`, `태그`... | **카드** |  ← 4열이 dests.py에 넣을 값
ASSIGN_ROW_RE = re.compile(r"^\|\s*`([A-Z]{3})`\s*\|([^|]*)\|[^|]*\|([^|]*)\|", re.M)

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

    def test_tag_order_matches_the_assignment_table(self):
        """`tags`는 **순서 있는 배열**이다 — `TAGS.md` 순서를 그대로 유지한다.

        2026-08-22부터 카드 표시가 "하위 전부 + 상위 1개, 최대 4개"라
        **배열 순서가 화면에 보이는 태그와 순서를 그대로 결정**한다.
        누군가 `sorted()`로 정리하면 계약 위반은 아니지만 표시가 조용히 바뀐다.
        그래서 배정표와 순서까지 대조한다.
        """
        table = TAGS_MD.read_text(encoding="utf-8")
        want = {iata: re.findall(r"`([^`]+)`", col)
                for iata, _, col in ASSIGN_ROW_RE.findall(table)
                if re.findall(r"`([^`]+)`", col)}
        self.assertTrue(want, "TAGS.md 배정표를 읽지 못했다 — 표 형식 변경 의심")
        self.assertEqual(set(want), set(dests.DEST),
                         "TAGS.md와 dests.py의 목적지 집합이 다르다")
        mismatched = sorted(
            f"{iata}: {dests.DEST[iata][4]} != {want[iata]}"
            for iata in want if dests.DEST[iata][4] != want[iata])
        self.assertEqual(mismatched, [], f"배정표와 다른 목적지: {mismatched}")

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


class CityCodeTest(unittest.TestCase):
    """도시 코드 → 대표 공항 정규화 (BB15).

    광역 수집 API가 공항이 아니라 도시 코드를 준다. 이 매핑이 깨지면
    도쿄·오사카·파리가 **조용히 사라진다** — 에러 없이 딜만 없어지므로
    화면을 봐도 모른다. 실제로 2026-08-28까지 그 상태였다.
    """

    def test_every_mapping_lands_in_the_dictionary(self):
        """대표 공항이 사전에 없으면 정규화해도 여전히 버려진다."""
        stray = sorted(f"{c}→{a}" for c, a in dests.CITY_TO_AIRPORT.items()
                       if a not in dests.DEST)
        self.assertEqual(stray, [], f"사전에 없는 대표 공항: {stray}")

    def test_city_codes_do_not_shadow_airport_codes(self):
        """도시 코드가 사전 키와 겹치면 `canonical()`이 원본을 덮어쓴다.

        겹치는 코드(BKK·SHA·JKT처럼 도시=공항인 것)는 애초에 매핑이 필요 없다.
        """
        overlap = sorted(set(dests.CITY_TO_AIRPORT) & set(dests.DEST))
        self.assertEqual(overlap, [], f"사전 키와 겹치는 도시 코드: {overlap}")

    def test_canonical_passes_known_airports_through(self):
        self.assertEqual(dests.canonical("FUK"), "FUK")
        self.assertEqual(dests.canonical("BKK"), "BKK")

    def test_canonical_maps_city_codes(self):
        self.assertEqual(dests.canonical("TYO"), "NRT")
        self.assertEqual(dests.canonical("OSA"), "KIX")
        self.assertEqual(dests.canonical("PAR"), "CDG")

    def test_canonical_leaves_unknown_codes_alone(self):
        """모르는 코드는 그대로 흘려보내고 `is_destination()`이 거른다."""
        self.assertEqual(dests.canonical("ZZZ"), "ZZZ")
        self.assertFalse(dests.is_destination(dests.canonical("ZZZ")))

    def test_link_code_widens_representative_airports(self):
        """예약 링크는 도시 코드로 넓힌다 (BB16).

        광역 수집이 도시 단위라 그 딜이 나리타인지 하네다인지 모른다. 대표 공항으로
        링크를 걸면 사용자가 클릭했을 때 **우리가 보여준 가격이 없을 수 있다.**
        2026-09-01에 예약처 4곳을 실제로 열어 전부 도시 코드를 받는 것을 확인했다.
        """
        self.assertEqual(dests.link_code("NRT"), "TYO")
        self.assertEqual(dests.link_code("KIX"), "OSA")
        self.assertEqual(dests.link_code("JFK"), "NYC")
        self.assertEqual(dests.link_code("CDG"), "PAR")

    def test_link_code_leaves_single_airport_cities_alone(self):
        """도시=공항인 곳은 넓힐 게 없다."""
        for code in ("FUK", "BKK", "CJU", "DAD"):
            with self.subTest(code=code):
                self.assertEqual(dests.link_code(code), code)

    def test_link_mapping_round_trips(self):
        """`canonical`과 `link_code`가 서로의 역이어야 한다.

        어긋나면 수집한 목적지와 링크가 가리키는 목적지가 달라진다.
        """
        for city, airport in dests.CITY_TO_AIRPORT.items():
            with self.subTest(city=city):
                self.assertEqual(dests.canonical(city), airport)
                self.assertEqual(dests.link_code(airport), city)

    def test_the_big_cities_are_reachable(self):
        """회귀 방지 — 이 도시들이 다시 사라지면 발견 피드의 핵심 상품이 빠진다."""
        for city, ko in (("TYO", "도쿄"), ("OSA", "오사카"), ("PAR", "파리"),
                         ("LON", "런던"), ("NYC", "뉴욕"), ("SPK", "삿포로")):
            with self.subTest(city=city):
                code = dests.canonical(city)
                self.assertTrue(dests.is_destination(code), f"{city} 정규화 실패")
                self.assertEqual(dests.DEST[code][0], ko)


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
