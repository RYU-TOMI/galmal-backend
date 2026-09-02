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
import json
import math
import re
import sys
import unittest
import urllib.error
import urllib.request
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


def _km(a, b):
    """두 좌표 사이 대권거리(km). 하버사인."""
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (0.5 - math.cos((la2 - la1) * p) / 2
         + math.cos(la1 * p) * math.cos(la2 * p) * (1 - math.cos((lo2 - lo1) * p)) / 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


class CoordinateSanityTest(unittest.TestCase):
    """좌표가 **있는지**가 아니라 **맞는지**를 본다 (BE3 T7).

    위의 범위 검사(-90~90)는 도쿄 자리에 서울 좌표가 들어가도 통과한다. 좌표는
    지도에 그대로 찍히는 값이라 틀리면 눈에 보이지만, **목적지 84곳을 매번
    눈으로 확인할 수는 없다.**

    벤더 참조(`api.travelpayouts.com/data/en/airports.json`)와 대조하면 확실하지만
    테스트가 네트워크에 의존하면 CI가 남의 서비스 상태에 좌우된다. 그래서
    **사전 안의 자기 일관성**으로 검증한다.

    쓰는 불변식은 `haul`이다. `dests.py`가 선언하듯 haul은 **비행시간대**
    등급(short ~3h / mid 3~6h / long 6h+)이므로 **ICN에서의 거리와 순서가
    어긋날 수 없다.** 좌표가 틀어지면 거리가 바뀌고 등급 경계가 깨진다.

    2026-09-02 실측 — 세 구간이 겹치지 않고 사이에 500km 가까운 공백이 있다:
        short  439~ 2,100km │ 507km │ mid 2,607~5,271km │ 496km │ long 5,767~11,090km
    """

    ICN = None

    @classmethod
    def setUpClass(cls):
        cls.ICN = dests.ORIGIN_COORD["ICN"]

    def bands(self):
        """haul별 (ICN 거리, 코드) 목록 — 거리 오름차순."""
        out = {}
        for iata, (_ko, _c, _r, haul, _t) in dests.DEST.items():
            coord = dests.dest_coord(iata)
            if coord:
                out.setdefault(haul, []).append((_km(self.ICN, coord), iata))
        return {h: sorted(v) for h, v in out.items()}

    def test_haul_bands_do_not_overlap(self):
        """가까운 등급의 최원거리가 먼 등급의 최근거리보다 멀면 좌표나 등급이 틀렸다.

        어느 쪽이 틀렸는지는 이 테스트가 모른다 — 다만 **둘이 어긋났다**는 건
        확실하고, 그 사실만으로 사람이 보면 금방 판별된다.
        """
        band = self.bands()
        for near, far in (("short", "mid"), ("mid", "long")):
            with self.subTest(pair=f"{near}/{far}"):
                far_end, near_code = band[near][-1]
                near_end, far_code = band[far][0]
                self.assertLess(
                    far_end, near_end,
                    f"{near} 최원거리 {near_code} {far_end:.0f}km가 "
                    f"{far} 최근거리 {far_code} {near_end:.0f}km를 넘었다 — "
                    "좌표 오타 또는 haul 오배정")

    def test_haul_is_monotonic_in_distance(self):
        """거리순으로 세우면 등급이 뒤섞이지 않는다 — 구간 검사보다 촘촘하다."""
        rank = {"short": 0, "mid": 1, "long": 2}
        rows = sorted((d, code, haul)
                      for haul, items in self.bands().items()
                      for d, code in items)
        inversions = [f"{rows[i][1]}({rows[i][2]}, {rows[i][0]:.0f}km) > "
                      f"{rows[i + 1][1]}({rows[i + 1][2]}, {rows[i + 1][0]:.0f}km)"
                      for i in range(len(rows) - 1)
                      if rank[rows[i][2]] > rank[rows[i + 1][2]]]
        self.assertEqual(inversions, [], f"거리와 haul이 역전된 곳: {inversions}")


class CanonicalShortCircuitTest(unittest.TestCase):
    """정규화가 **조용히 무력화**되는 함정을 막는다 (BE3 T7).

    `canonical()`은 이렇게 생겼다:

        if code in DEST:
            return code
        return CITY_TO_AIRPORT.get(code, code)

    **`DEST` 검사가 먼저다.** 그래서 어떤 도시 코드가 `DEST`에도 키로 남아 있으면
    `CITY_TO_AIRPORT`에 매핑을 넣어도 **아무 일도 일어나지 않는다.** 에러도 없고
    매핑은 그냥 무시된다 — 넣은 사람은 고쳤다고 믿는다.

    실제로 자카르타가 이 상태였다(`JKT`·`CGK`가 둘 다 `DEST` 키). BB15에서
    도시 코드 11개를 정규화할 때 자카르타만 빠졌고, 결과적으로 같은 도시가
    사전에 두 번 있었다.
    """

    def test_city_codes_are_not_also_dictionary_keys(self):
        """매핑의 **키**가 `DEST`에 있으면 그 매핑은 죽은 코드다."""
        shadowed = sorted(k for k in dests.CITY_TO_AIRPORT if k in dests.DEST)
        self.assertEqual(
            shadowed, [],
            f"CITY_TO_AIRPORT 키가 DEST에도 있어 정규화가 무력화된다: {shadowed}")

    def test_mapping_targets_exist(self):
        """매핑의 **값**은 실재하는 사전 키여야 한다 — 아니면 목적지가 사라진다."""
        missing = sorted(v for v in dests.CITY_TO_AIRPORT.values()
                         if v not in dests.DEST)
        self.assertEqual(missing, [], f"DEST에 없는 정규화 대상: {missing}")

    def test_link_code_round_trips_through_the_mapping(self):
        """예약 링크는 도시 코드로 나가야 한다(BE3 T4).

        `link_code()`가 역매핑을 쓰므로, 정방향이 깨지면 예약처에 공항 코드가
        나가고 사용자가 본 가격이 검색 결과에 없을 수 있다.
        """
        for city, airport in dests.CITY_TO_AIRPORT.items():
            with self.subTest(city=city):
                self.assertEqual(dests.canonical(city), airport)
                self.assertEqual(dests.link_code(airport), city)


_VENDOR_CACHE = {}


def _vendor_coords():
    """Travelpayouts 공식 참조의 코드 → (lat, lon). 실패하면 None.

    공항과 도시를 모두 읽는다 — 우리 사전 키는 대부분 공항이지만 도시 코드도 섞인다.
    """
    if "data" in _VENDOR_CACHE:
        return _VENDOR_CACHE["data"]
    out = {}
    try:
        for src in ("airports", "cities"):
            url = f"https://api.travelpayouts.com/data/en/{src}.json"
            with urllib.request.urlopen(url, timeout=30) as r:
                for row in json.loads(r.read().decode()):
                    co = row.get("coordinates") or {}
                    if row.get("code") and co.get("lat") is not None:
                        out.setdefault(row["code"], (co["lat"], co["lon"]))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        out = None
    _VENDOR_CACHE["data"] = out
    return out


class VendorCoordinateTest(unittest.TestCase):
    """좌표를 **벤더 공식 참조와 직접 대조**한다 (BE3 T7).

    왜 필요한가 — 위의 자기 일관성 검사(`CoordinateSanityTest`)는 haul 구간을
    넘는 오류만 잡는다. 2026-09-02 변이 테스트로 확인한 실제 능력:

        잡음    뉴욕 좌표를 도쿄로 · 제주 좌표를 뉴욕으로 · 경도 부호 뒤집기
        못 잡음  **도쿄 좌표를 서울로**   ← 둘 다 short라 구간이 안 깨진다

    같은 구간 안에서 뒤바뀌면 자기 일관성으로는 보이지 않는다. 그 구멍을 여기서
    막는다.

    **네트워크 실패는 skip이지 fail이 아니다.** 남의 서비스 상태로 우리 CI가
    빨개지면 아무도 테스트를 믿지 않게 되고, 그러면 진짜 실패도 무시된다.
    """

    # 정상 이탈의 실측 최대치는 이스탄불 34km(2019년 신공항 이전으로 도심과 멀다).
    # 나머지 82곳은 전부 7km 이내였다. 100km면 정상은 통과하고 도시 뒤바뀜은 걸린다
    # (가장 가까운 서로 다른 도시 쌍이 방콕 BKK-DMK 29km이므로 그보다는 커야 한다).
    MAX_KM = 100

    def test_coordinates_match_the_vendor_reference(self):
        ref = _vendor_coords()
        if not ref:
            # skip은 조용하다. 기본 출력에는 "OK (skipped=1)"만 남아서, 벤더가 몇 달간
            # 막혀 있어도 초록불이라 아무도 모른다. 이 프로젝트가 반복해서 데인 유형이
            # 정확히 그것이라(테스트가 조용히 안 돌던 것) stderr에 눈에 띄는 줄을 남긴다.
            # 검사를 fail로 바꾸지는 않는다 — 남의 서비스로 CI가 빨개지면 진짜 실패도
            # 무시하게 된다. 보이게만 한다.
            msg = ("좌표 벤더 대조를 건너뛴다 — 참조를 받지 못했다. "
                   "네트워크 또는 api.travelpayouts.com 상태를 확인할 것.")
            print("[SKIP] " + msg, file=sys.stderr)
            self.skipTest(msg)
        far, unknown = [], []
        for iata, coord in dests.DEST_COORD.items():
            want = ref.get(iata)
            if want is None:
                unknown.append(iata)
                continue
            gap = _km(coord, want)
            if gap > self.MAX_KM:
                far.append(f"{iata} {gap:.0f}km 벗어남 "
                           f"(우리 {coord} vs 참조 {want})")
        self.assertEqual(sorted(far), [], f"참조와 어긋난 좌표: {far}")
        # 참조에 없는 코드는 실패로 보지 않는다 — 벤더가 안 싣는 코드가 있다.
        # 다만 대량으로 늘면 사전이 참조 체계에서 벗어나고 있다는 신호다.
        self.assertLess(len(unknown), 5,
                        f"참조에 없는 코드가 너무 많다: {sorted(unknown)}")


if __name__ == "__main__":
    unittest.main()
