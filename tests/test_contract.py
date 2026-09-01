# -*- coding: utf-8 -*-
"""deals.json 계약 검증기 — `CONTRACT.md`를 기계적으로 강제한다.

3세션 분업에서 `CONTRACT.md`는 문서일 뿐 강제력이 없었다. 백엔드가 필드를
빠뜨리거나 타입을 바꿔도 아무도 모르고, 프론트에서 터진 뒤에야 발견된다.
이 검증기가 그 사이를 막는다.

두 방향으로 검사한다:
  1. **생산 로직** — 인메모리 DB로 `build_deals_json()`을 돌린 결과가 계약에 맞나
  2. **커밋된 산출물** — 실제로 배포된 `docs/data/deals.json`이 계약에 맞나

둘은 성격이 다르다. 1은 코드가 옳은지, 2는 배포된 것이 옳은지 본다.

태그 통제 어휘는 `CONTRACT.md`의 표를 **직접 파싱해서** 쓴다. 계약서가 단일
출처이므로 표를 고치면 검사가 따라온다(어휘를 여기 하드코딩하면 두 곳이 어긋난다).
"""
import json
import re
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import db
import dests
import discover_data

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "CONTRACT.md"
ARTIFACT = ROOT / "docs" / "data" / "deals.json"

REGIONS = {"jp", "cn", "sea", "island", "oc", "eu", "am", "etc", "dom"}
HAULS = {"short", "mid", "long"}
TIERS = {"major", "minor"}
HUBS = {"SEL", "PUS", "TAE", "CJU"}

# 필드 목록을 여기 하드코딩하지 않는다(BB19). 하드코딩하면 기획이 계약에 필드를
# 추가해도 검증기가 모르고 **CI가 조용히 초록불**이 된다. 실제로 `low`·`obs_days`가
# 그렇게 통과했다 — "계약이 단일 출처"가 반쯤만 참이었다.
# 표의 타입 열도 읽어 `|null` 표기에서 nullable 여부를 뽑는다.

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UPDATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
IATA_RE = re.compile(r"^[A-Z]{3}$")
# | **`해변`** | 24 | — | `리조트` · ... |   ← 상위는 굵게, 3열이 부모
# | `리조트`   | 13 | **`해변`** |          |   ← 하위는 부모를 가리킴
TAG_ROW_RE = re.compile(
    r"^\|\s*\*{0,2}`([^`]+)`\*{0,2}\s*\|\s*\d+\s*\|"
    r"\s*(?:\*{0,2}`([^`]+)`\*{0,2}|[—-]+)\s*\|", re.M)
KST_OFFSET = timedelta(hours=9)


def _cells(line):
    r"""마크다운 표 한 줄을 셀로 자른다.

    타입 열에 `string\|null`처럼 **이스케이프된 파이프**가 들어 있다. 그냥
    `split("|")`하면 거기서 잘려 `string\`만 읽히고 nullable 판정이 틀어진다.
    """
    return [c.replace(r"\|", "|").strip()
            for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def contract_fields():
    """`CONTRACT.md`의 deal 필드 표에서 `{필드: nullable 여부}`를 읽는다.

    계약이 단일 출처가 되려면 **필드 목록도** 여기서 나와야 한다. 그래야 기획이
    필드를 추가한 순간 검증기가 요구하기 시작하고, 생산자가 안 채우면 CI가 잡는다.
    """
    body = CONTRACT.read_text(encoding="utf-8")
    if "## deal 객체" not in body:
        raise AssertionError("CONTRACT.md에서 '## deal 객체' 절을 찾지 못했다. "
                             "계약이 재편됐다면 이 파서도 함께 고쳐야 한다.")
    table = body.split("## deal 객체")[1].split("### ")[0]
    fields = {}
    for line in table.splitlines():
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if len(cells) < 2:
            continue
        names = re.findall(r"`([^`]+)`", cells[0])     # `lat` `lon` 처럼 한 칸에 둘인 행
        if not names:
            continue
        nullable = "null" in cells[1]
        for name in names:
            fields[name] = nullable
    if len(fields) < 10:
        raise AssertionError(f"deal 필드 표에서 {len(fields)}개만 읽었다. 표 형식 변경 의심.")
    return fields


def contract_vocab():
    """계약서 어휘 표를 읽어 `(어휘 집합, {하위: 상위})`를 돌려준다.

    표 형식이 바뀌면(2026-08-22에 열이 2개 늘었다) 여기가 먼저 깨져야 한다.
    조용히 빈 집합을 돌려주면 검사가 통과해 버려 아무 의미가 없어진다.
    """
    parts = CONTRACT.read_text(encoding="utf-8").split("### `tags` 통제 어휘")
    if len(parts) < 2:
        raise AssertionError(
            "CONTRACT.md에서 '### `tags` 통제 어휘' 절을 찾지 못했다. "
            "계약 문서가 재편됐다면 이 파서도 함께 고쳐야 한다.")
    rows = TAG_ROW_RE.findall(parts[1])
    vocab = {tag for tag, _ in rows}
    parent = {tag: up for tag, up in rows if up}
    if not vocab:
        raise AssertionError("어휘 절은 찾았으나 태그를 하나도 못 읽었다. 표 형식 변경 의심.")
    stray = sorted(set(parent.values()) - vocab)
    if stray:
        raise AssertionError(f"상위로 지목됐으나 어휘 표에 행이 없는 태그: {stray}")
    return vocab, parent


def contract_tags():
    """어휘 집합만 필요할 때."""
    return contract_vocab()[0]


def _num(v):
    """bool은 int의 하위형이라 명시적으로 배제한다."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(payload, vocab, parent=None, fields=None):
    """계약 위반 목록을 문자열 리스트로 돌려준다. 비어 있으면 통과."""
    parent = parent or {}
    fields = fields if fields is not None else contract_fields()
    errs = []

    for key in ("updated", "origins", "deals"):
        if key not in payload:
            errs.append(f"최상위 키 누락: {key}")
    if errs:
        return errs

    if not UPDATED_RE.match(str(payload["updated"])):
        errs.append(f"updated 형식이 'YYYY-MM-DD HH:MM'이 아니다: {payload['updated']!r}")

    origins, deals = payload["origins"], payload["deals"]
    if not isinstance(origins, dict):
        return errs + ["origins가 객체가 아니다"]
    if not isinstance(deals, list):
        return errs + ["deals가 배열이 아니다"]

    for hub, meta in origins.items():
        if hub not in HUBS:
            errs.append(f"알 수 없는 출발 허브: {hub}")
        if not isinstance(meta, dict) or set(meta) != {"name", "lat", "lon"}:
            errs.append(f"origins[{hub}] 구조가 다르다: {meta!r}")
            continue
        if not meta["name"]:
            errs.append(f"origins[{hub}].name이 비었다")
        if not (_num(meta["lat"]) and -90 <= meta["lat"] <= 90):
            errs.append(f"origins[{hub}].lat 범위 이탈: {meta['lat']!r}")
        if not (_num(meta["lon"]) and -180 <= meta["lon"] <= 180):
            errs.append(f"origins[{hub}].lon 범위 이탈: {meta['lon']!r}")

    for i, dl in enumerate(deals):
        at = f"deals[{i}]"
        missing = [k for k in fields if k not in dl]
        if missing:
            errs.append(f"{at} 필드 누락: {missing}")
            continue

        wrongly_null = sorted(k for k, nullable in fields.items()
                              if not nullable and dl.get(k) is None)
        if wrongly_null:
            errs.append(f"{at} null이 허용되지 않는 필드가 null이다: {wrongly_null}")

        if dl["o"] not in origins:
            errs.append(f"{at}.o={dl['o']!r}가 origins에 없다")
        if not IATA_RE.match(str(dl["d"])):
            errs.append(f"{at}.d가 IATA 3자리가 아니다: {dl['d']!r}")
        for k in ("ko", "country", "when"):
            if not (isinstance(dl[k], str) and dl[k]):
                errs.append(f"{at}.{k}가 비었거나 문자열이 아니다: {dl[k]!r}")
        if dl["region"] not in REGIONS:
            errs.append(f"{at}.region enum 위반: {dl['region']!r}")
        if dl["haul"] not in HAULS:
            errs.append(f"{at}.haul enum 위반: {dl['haul']!r}")
        if dl["tier"] not in TIERS:
            errs.append(f"{at}.tier enum 위반: {dl['tier']!r}")

        if not isinstance(dl["tags"], list) or not dl["tags"]:
            errs.append(f"{at}.tags가 비었거나 배열이 아니다: {dl['tags']!r}")
        else:
            outside = sorted(t for t in dl["tags"] if t not in vocab)
            if outside:
                errs.append(f"{at}.tags 통제 어휘 밖: {outside} "
                            "(CONTRACT.md 어휘 표를 먼저 갱신해야 한다)")
            # 하위 태그는 반드시 자기 상위를 데리고 다녀야 한다. 깨지면 그 태그가
            # 카드에는 보이는데 필터로는 안 잡힌다(프론트 C-10과 같은 증상).
            orphan = sorted(f"{x}→{parent[x]}" for x in dl["tags"]
                            if x in parent and parent[x] not in dl["tags"])
            if orphan:
                errs.append(f"{at}.tags 하위 태그에 상위가 없다: {orphan} "
                            "(카드에는 보이는데 필터로 안 잡힌다)")

        if not (_num(dl["lat"]) and -90 <= dl["lat"] <= 90):
            errs.append(f"{at}.lat 범위 이탈: {dl['lat']!r}")
        if not (_num(dl["lon"]) and -180 <= dl["lon"] <= 180):
            errs.append(f"{at}.lon 범위 이탈: {dl['lon']!r}")
        if not (_num(dl["price"]) and dl["price"] > 0):
            errs.append(f"{at}.price가 양수가 아니다: {dl['price']!r}")
        if not (_num(dl["median"]) and dl["median"] > 0):
            errs.append(f"{at}.median이 양수가 아니다: {dl['median']!r}")
        if not (_num(dl["transfers"]) and dl["transfers"] >= 0):
            errs.append(f"{at}.transfers가 0 이상이 아니다: {dl['transfers']!r}")
        if not (_num(dl["discount"]) and 0 <= dl["discount"] <= 70):
            errs.append(f"{at}.discount가 0~70 밖이다: {dl['discount']!r}")

        if not DATE_RE.match(str(dl["dep"])):
            errs.append(f"{at}.dep 형식 위반: {dl['dep']!r}")
        if dl["ret"] is not None and not DATE_RE.match(str(dl["ret"])):
            errs.append(f"{at}.ret은 null이거나 YYYY-MM-DD여야 한다: {dl['ret']!r}")
        if not isinstance(dl["nights"], str):
            errs.append(f"{at}.nights가 문자열이 아니다: {dl['nights']!r}")

        if dl["seen"] is not None:
            try:
                seen = datetime.fromisoformat(dl["seen"])
            except (TypeError, ValueError):
                errs.append(f"{at}.seen이 ISO8601이 아니다: {dl['seen']!r}")
            else:
                if seen.utcoffset() != KST_OFFSET:
                    errs.append(f"{at}.seen이 KST(+09:00) 오프셋이 아니다: {dl['seen']!r}")

        links = dl["links"]
        if not isinstance(links, list) or not 3 <= len(links) <= 5:
            shown = len(links) if isinstance(links, list) else repr(links)
            errs.append(f"{at}.links 개수가 3~5가 아니다: {shown}")
        else:
            for j, ln in enumerate(links):
                if not isinstance(ln, dict) or set(ln) != {"name", "tag", "url"}:
                    errs.append(f"{at}.links[{j}] 구조가 다르다: {ln!r}")
                    continue
                if not (ln["name"] and ln["tag"]):
                    errs.append(f"{at}.links[{j}] name/tag가 비었다")
                if not str(ln["url"]).startswith("https://"):
                    errs.append(f"{at}.links[{j}].url이 https가 아니다: {ln['url']!r}")

    prices = [d["price"] for d in deals if _num(d.get("price"))]
    if prices != sorted(prices):
        errs.append("deals가 가격 오름차순이 아니다")

    unused = sorted(set(origins) - {d["o"] for d in deals if "o" in d})
    if unused:
        errs.append(f"딜이 없는 허브가 origins에 남아 있다: {unused}")

    # URL 딥링크(`#SEL-DAD`)가 이 유일성 위에 서 있다(기획 PH4). 중복이 생기면
    # 링크가 조용히 엉뚱한 딜을 가리킨다 — 에러도 안 나고 아무도 모른다.
    seen_keys = {}
    for i, dl in enumerate(deals):
        if "o" not in dl or "d" not in dl:
            continue
        key = f"{dl['o']}-{dl['d']}"
        if key in seen_keys:
            errs.append(f"(o, d) 조합 중복: {key} — deals[{seen_keys[key]}]와 deals[{i}]. "
                        "URL 딥링크가 딜을 유일하게 가리키지 못한다")
        seen_keys[key] = i

    return errs


class ContractParsingTest(unittest.TestCase):
    """검증기가 딛고 선 계약서 자체가 읽히는가."""

    def test_field_table_is_readable(self):
        """필드 목록이 계약에서 나와야 검증기가 계약을 따라간다(BB19).

        하드코딩하면 기획이 필드를 추가해도 검증기가 모르고 CI가 조용히 통과한다.
        실제로 `low`·`obs_days`가 그렇게 며칠 방치됐다.
        """
        fields = contract_fields()
        self.assertGreaterEqual(len(fields), 15, "필드가 비정상적으로 적다")
        for core in ("o", "d", "price", "links"):
            self.assertIn(core, fields)

    def test_escaped_pipes_do_not_break_nullable_detection(self):
        """타입 열의 `string\|null`을 제대로 읽는가.

        마크다운에서 파이프를 `\|`로 이스케이프하는데, 순진하게 자르면 거기서
        끊겨 `string\`만 읽힌다. 그러면 nullable 필드를 필수로 오판한다.
        """
        fields = contract_fields()
        for nullable in ("ret", "seen", "low"):
            self.assertTrue(fields.get(nullable), f"{nullable}은 null 허용이어야 한다")
        for required in ("o", "d", "price", "obs_days"):
            self.assertFalse(fields.get(required), f"{required}은 필수여야 한다")

    def test_vocabulary_is_readable(self):
        self.assertGreaterEqual(len(contract_tags()), 5, "어휘가 비정상적으로 적다")

    def test_dictionary_stays_inside_the_vocabulary(self):
        """`dests.py`에 어휘 밖 태그가 들어오면 여기서 잡힌다.

        `야시장`·`유적`·`트레킹`이 조용히 들어왔던 것도 검사가 없어서였다.
        어휘를 늘리려면 `CONTRACT.md` 표를 먼저 갱신하는 게 계약 변경 절차다.
        """
        outside = sorted({t for v in dests.DEST.values() for t in v[4]} - contract_tags())
        self.assertEqual(outside, [], f"CONTRACT.md 어휘 표에 없는 태그: {outside}")

    def test_every_subtag_carries_its_parent(self):
        """⭐ 계약의 핵심 불변식 — 하위 태그를 단 목적지는 상위도 함께 갖는다.

        깨지면 `야시장`이 카드에 보이는데 `미식` 필터로 안 잡힌다.
        기획의 `design/build_tags.py`도 같은 규칙을 검사하지만, 그건 배정안을
        만들 때만 돈다. 여기서 보는 건 **실제 `dests.py`에 들어간 값**이다.
        """
        _, parent = contract_vocab()
        broken = sorted(
            f"{iata}: {sub}→{parent[sub]} 없음"
            for iata, v in dests.DEST.items()
            for sub in v[4] if sub in parent and parent[sub] not in v[4])
        self.assertEqual(broken, [], f"상위 태그가 빠진 목적지: {broken}")


class GeneratedOutputTest(unittest.TestCase):
    """생산 로직이 계약을 지키는가 — 인메모리 DB로 실제 생성해 검사."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        self.vocab, self.parent = contract_vocab()
        self.today = date.today()

    def add(self, origin, dest, price, shift=0, ret=True):
        fresh = (datetime.now(timezone.utc) - timedelta(hours=5))
        self.conn.execute(
            """INSERT INTO broad_offers (fetched_date, origin, destination, price,
                                         transfers, depart_date, return_date, found_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (self.today.isoformat(), origin, dest, price, 0,
             (self.today + timedelta(days=30 + shift)).isoformat(),
             (self.today + timedelta(days=33 + shift)).isoformat() if ret else None,
             fresh.replace(tzinfo=None).isoformat()))

    def build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(discover_data, "DOCS", Path(tmp)):
                discover_data.build_deals_json(self.conn)
                raw = (Path(tmp) / "data" / "deals.json").read_text(encoding="utf-8")
        return json.loads(raw)

    def assertValid(self, payload):
        errs = validate(payload, self.vocab, self.parent)
        self.assertEqual(errs, [], "계약 위반:\n  " + "\n  ".join(errs))

    def test_typical_output_satisfies_the_contract(self):
        """네 허브가 모두 등장하는 평범한 하루.

        주의: 김포→제주는 허브가 `CJU`가 아니라 `SEL`이다. 제주는 거기서
        목적지이고, 허브는 **출발 공항**을 정규화한 값이다(ICN·GMP → SEL).
        `CJU` 허브를 만들려면 제주에서 출발하는 딜이 있어야 한다.
        """
        rows = [("ICN", "FUK", 120000), ("GMP", "CJU", 50000),
                ("PUS", "NRT", 180000), ("TAE", "TPE", 210000),
                ("CJU", "KIX", 150000)]
        for i, (o, d, p) in enumerate(rows):
            self.add(o, d, p, shift=i)
        payload = self.build()
        self.assertEqual(len(payload["deals"]), len(rows))
        self.assertEqual(set(payload["origins"]), {"SEL", "PUS", "TAE", "CJU"})
        self.assertValid(payload)

    def test_empty_day_still_satisfies_the_contract(self):
        """수집이 하나도 없는 날에도 형태는 계약대로여야 한다."""
        payload = self.build()
        self.assertEqual(payload["deals"], [])
        self.assertValid(payload)

    def test_one_way_deal_is_valid(self):
        """편도(`ret`=null, `nights`="")도 계약을 만족한다."""
        self.add("ICN", "FUK", 90000, ret=False)
        payload = self.build()
        deal = payload["deals"][0]
        self.assertIsNone(deal["ret"])
        self.assertEqual(deal["nights"], "")
        self.assertValid(payload)


class CommittedArtifactTest(unittest.TestCase):
    """배포된 `docs/data/deals.json`이 계약에 맞는가.

    생산 로직이 옳아도 커밋된 산출물이 옛 스키마로 남아 있으면, 그걸 픽스처로
    쓰는 프론트가 어긋난다. 그래서 파일 자체도 검사한다.
    """

    def test_artifact_satisfies_the_contract(self):
        if not ARTIFACT.exists():
            self.skipTest("docs/data/deals.json이 없다 (아직 생성 전)")
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        errs = validate(payload, *contract_vocab())
        self.assertEqual(errs, [], "커밋된 산출물의 계약 위반:\n  " + "\n  ".join(errs))


if __name__ == "__main__":
    unittest.main()
