# -*- coding: utf-8 -*-
"""deals.json 계약 검증기 — `CONTRACT.md`를 기계적으로 강제한다.

3세션 분업에서 `CONTRACT.md`는 문서일 뿐 강제력이 없었다. 백엔드가 필드를
빠뜨리거나 타입을 바꿔도 아무도 모르고, 프론트에서 터진 뒤에야 발견된다.
이 검증기가 그 사이를 막는다.

두 방향으로 검사한다:
  1. **생산 로직** — 인메모리 DB로 `build_deals_json()`을 돌린 결과가 계약에 맞나
  2. **커밋된 산출물** — 실제로 발행된 `docs/v1/deals.json`이 계약에 맞나

둘은 성격이 다르다. 1은 코드가 옳은지, 2는 배포된 것이 옳은지 본다.

필드 목록과 통제 어휘는 `contract/v1/`(`deal.schema.json`·`vocab.json`)에서 읽는다
(BE10, R8 C안). 목록은 거기 한 곳에만 있다 — 여기 하드코딩하면 두 곳이 어긋나고,
문서 표를 파싱하면 문서가 두 벌이 되는 순간 낡은 쪽으로 검사한다. 「왜」는 기획의
`CONTRACT.md`에 남는다.
"""
import json
import re
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import config
import db
import dests
import discover_data

ROOT = Path(__file__).resolve().parent.parent
DEAL_SCHEMA = ROOT / "contract" / "v1" / "deal.schema.json"
VOCAB = ROOT / "contract" / "v1" / "vocab.json"
ARTIFACT = ROOT / "docs" / "v1" / "deals.json"


def vocab_file():
    return json.loads(VOCAB.read_text(encoding="utf-8"))


# enum 도 손으로 옮겨 적지 않는다 (BE10 T2). 예전엔 「CONTRACT.md에서 그대로 옮긴 값」을
# 여기 적었다 — 파싱은 틀리면 터지기라도 하는데 **손 사본은 틀려도 조용하다**(BB19 모양).
_V = vocab_file()
REGIONS = set(_V["region"])
HAULS = set(_V["haul"])
TIERS = set(_V["tier"])
HUBS = set(_V["hub"])

# 필드 목록을 여기 하드코딩하지 않는다(BB19). 하드코딩하면 기획이 계약에 필드를
# 추가해도 검증기가 모르고 **CI가 조용히 초록불**이 된다. 실제로 `low`·`obs_days`가
# 그렇게 통과했다 — "계약이 단일 출처"가 반쯤만 참이었다.
# 정본은 `contract/v1/deal.schema.json`이다(BE10 T1, R8 C안). 예전엔 `CONTRACT.md`의
# 마크다운 표를 파싱했는데, 저장소가 갈리면서 그 문서가 두 벌이 됐고 첫날 사본이
# 뒤처졌다 — 검증기가 **낡은 계약으로** 검사하는 상태였다. 목록은 코드 옆 한 곳에만 둔다.

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UPDATED_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
IATA_RE = re.compile(r"^[A-Z]{3}$")
KST_OFFSET = timedelta(hours=9)
ROUTE_CODES = {f"{o}-{d}" for o, d in config.ROUTES}
# `when` 통제 어휘. 고정 문구 + 패턴 — 둘 다 vocab.json 에서.
WHEN_FIXED = set(_V["when"]["fixed"])
WHEN_PATTERNS = tuple(re.compile(p["regex"]) for p in _V["when"]["patterns"])


def deal_schema():
    return json.loads(DEAL_SCHEMA.read_text(encoding="utf-8"))


def _types(prop):
    t = prop["type"]
    return t if isinstance(t, list) else [t]


def contract_fields():
    """`deal.schema.json`에서 `{필드: nullable 여부}`를 읽는다.

    계약이 단일 출처가 되려면 **필드 목록도** 여기서 나와야 한다. 그래야 필드가
    추가된 순간 검증기가 요구하기 시작하고, 생산자가 안 채우면 CI가 잡는다.
    """
    schema = deal_schema()
    props = schema["properties"]
    # 이 검증기는 「있는 필드 = 전부 필수」로 읽는다. 스키마가 달리 말하면 먼저 터진다.
    if set(schema["required"]) != set(props):
        raise AssertionError("deal.schema.json 의 required 와 properties 가 다르다: "
                             f"{sorted(set(schema['required']) ^ set(props))}")
    return {name: "null" in _types(p) for name, p in props.items()}


def link_fields():
    """`links[]` 원소의 필드 집합 — 스키마에서."""
    return set(deal_schema()["properties"]["links"]["items"]["properties"])


def contract_vocab():
    """`vocab.json`의 태그 어휘를 `(어휘 집합, {하위: 상위})`로 돌려준다.

    조용히 빈 집합을 돌려주면 검사가 통과해 버려 아무 의미가 없어진다 — 그래서
    구조가 이상하면 여기서 먼저 터진다.
    """
    tags = vocab_file()["tags"]
    parent = dict(tags["sub"])
    vocab = set(tags["top"]) | set(parent)
    if not tags["top"]:
        raise AssertionError("vocab.json 에 상위 태그가 없다.")
    stray = sorted(set(parent.values()) - set(tags["top"]))
    if stray:
        raise AssertionError(f"상위로 지목됐으나 top 에 없는 태그: {stray}")
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

    # 🔴 **봉투는 여기서 안 본다.** v1의 `schema`·`generated`는 `test_publish.py`의
    # `EnvelopeTest`가 `docs/v1/*.json` 전부에 대해 검사한다. 두 곳에서 보면 갈린다.
    # (M3 T3 전에는 여기서 `updated`를 봤다 — 그 필드는 v1에 없다.)
    for key in ("origins", "deals"):
        if key not in payload:
            errs.append(f"최상위 키 누락: {key}")
    if errs:
        return errs

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
        # `when`은 통제 어휘다(계약 §when). 어휘 밖 값이 나가면 프론트의 분기가
        # 조용히 폴백으로 떨어진다 — 태그 어휘와 같은 이유로 검사한다.
        if (isinstance(dl["when"], str) and dl["when"] not in WHEN_FIXED
                and not any(p.match(dl["when"]) for p in WHEN_PATTERNS)):
            errs.append(f"{at}.when 통제 어휘 밖: {dl['when']!r} "
                        "(기획 결정 후 contract/v1/vocab.json 의 when 을 먼저 갱신해야 한다)")
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
                            "(기획 결정 후 contract/v1/vocab.json 의 tags 를 먼저 갱신해야 한다)")
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
        # `route`가 **그 딜의 허브에 속한 노선**인지 본다. 있기만 하면 통과시키면
        # 부산 딜에 인천 노선을 붙여도 잡히지 않는다 — 가격도 시세도 다른 노선으로
        # 사용자를 보내는 것이고, 그게 BB22에서 잡은 실수다.
        if dl["route"] is not None:
            if dl["route"] not in ROUTE_CODES:
                errs.append(f"{at}.route가 config.ROUTES에 없다: {dl['route']!r}")
            else:
                origin = dl["route"].split("-")[0]
                allowed = ("ICN", "GMP") if dl["o"] == "SEL" else (dl["o"],)
                if origin not in allowed:
                    errs.append(f"{at}.route의 출발 공항이 허브와 다르다: "
                                f"o={dl['o']!r}인데 route={dl['route']!r}")
                # `route`는 **공항 코드**(ICN-NRT)이고 `d`는 **도시 코드**(TYO)라
                # 직접 비교가 안 된다. 같은 변환을 거쳐 맞춘다 — 검사 의도는
                # "route가 이 딜과 다른 목적지를 가리키지 않는가"다.
                route_dest = dl["route"].split("-", 1)[1]
                if dests.link_code(route_dest) != dl["d"]:
                    errs.append(f"{at}.route의 목적지가 d와 다르다: "
                                f"d={dl['d']!r}인데 route={dl['route']!r} "
                                f"(도시 코드로는 {dests.link_code(route_dest)!r})")

        if dl["low"] is not None and not (_num(dl["low"]) and dl["low"] > 0):
            errs.append(f"{at}.low가 양수가 아니다: {dl['low']!r}")
        if not (_num(dl["obs_days"]) and dl["obs_days"] >= 0):
            errs.append(f"{at}.obs_days가 0 이상이 아니다: {dl['obs_days']!r}")
        # 계약: 이력이 없으면 low=null, obs_days=0. 둘이 어긋나면 한쪽이 거짓말이다.
        if (dl["low"] is None) != (dl["obs_days"] == 0):
            errs.append(f"{at}.low와 obs_days가 어긋난다: "
                        f"low={dl['low']!r}, obs_days={dl['obs_days']!r}")

        if not (_num(dl["price"]) and dl["price"] > 0):
            errs.append(f"{at}.price가 양수가 아니다: {dl['price']!r}")
        # nullable 필드는 null이면 검사를 건너뛴다 — 계약이 허용한 값이다.
        # null 자체의 적법성은 위 `wrongly_null` 검사가 계약 표를 보고 판단한다.
        if dl["median"] is not None and not (_num(dl["median"]) and dl["median"] > 0):
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
        link_keys = link_fields()
        if not isinstance(links, list) or not 3 <= len(links) <= 5:
            shown = len(links) if isinstance(links, list) else repr(links)
            errs.append(f"{at}.links 개수가 3~5가 아니다: {shown}")
        else:
            for j, ln in enumerate(links):
                if not isinstance(ln, dict) or set(ln) != link_keys:
                    errs.append(f"{at}.links[{j}] 구조가 다르다: {ln!r}")
                    continue
                if not (ln["name"] and ln["tag"]):
                    errs.append(f"{at}.links[{j}] name/tag가 비었다")
                # `ad`는 화면의 "(광고)" 고지를 켜는 값이다(법적 의무).
                # 참/거짓이 아닌 값이 새면 프론트의 `=== true` 판정이 조용히 어긋난다.
                if not isinstance(ln["ad"], bool):
                    errs.append(f"{at}.links[{j}].ad가 boolean이 아니다: {ln['ad']!r}")
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
    """검증기가 딛고 선 계약 파일 자체가 읽히는가."""

    def test_field_list_is_readable(self):
        """필드 목록이 계약에서 나와야 검증기가 계약을 따라간다(BB19).

        하드코딩하면 필드가 추가돼도 검증기가 모르고 CI가 조용히 통과한다.
        실제로 `low`·`obs_days`가 그렇게 며칠 방치됐다.
        """
        fields = contract_fields()
        self.assertGreaterEqual(len(fields), 15, "필드가 비정상적으로 적다")
        for core in ("o", "d", "price", "links"):
            self.assertIn(core, fields)

    def test_nullable_is_read_from_the_type(self):
        """`["string","null"]`만 null 허용으로 읽는가 — 틀리면 필수 필드가 null로 새도 통과한다."""
        fields = contract_fields()
        for nullable in ("ret", "seen", "low", "median", "route"):
            self.assertTrue(fields.get(nullable), f"{nullable}은 null 허용이어야 한다")
        for required in ("o", "d", "price", "obs_days"):
            self.assertFalse(fields.get(required), f"{required}은 필수여야 한다")

    def test_every_field_says_what_it_means(self):
        """스키마가 정본이 되면서 **의미 설명도 여기로** 왔다 — 비면 「왜」가 사라진다."""
        props = deal_schema()["properties"]
        items = list(props.items())
        items += [(f"links[].{k}", p)
                  for k, p in props["links"]["items"]["properties"].items()]
        empty = [k for k, p in items if not p.get("description", "").strip()]
        self.assertEqual(empty, [], f"설명이 없는 필드: {empty}")

    def test_link_fields_come_from_the_schema(self):
        self.assertEqual(link_fields(), {"name", "tag", "ad", "url"})

    def test_when_vocabulary_covers_the_contract_table(self):
        """`when` 어휘 검사가 계약 §when의 7단계를 전부 받아들이는가.

        고정 문구 넷과 패턴 셋으로 되어 있어 태그처럼 목록만으로는 안 된다.
        어휘 밖 값이 나가면 프론트 분기가 조용히 폴백으로 떨어진다.
        """
        for ok in ("이번 주말", "다음 주말", "이번 주", "이번 달", "다음 달",
                   "11월", "3월", "내년 1월", "내년 12월", "2028년 3월"):
            with self.subTest(value=ok):
                self.assertTrue(
                    ok in WHEN_FIXED or any(p.match(ok) for p in WHEN_PATTERNS),
                    f"계약이 허용한 값인데 검사가 거부한다: {ok}")
        for bad in ("9월달", "내년봄", "2027-03", "곧", "내년", "13월달"):
            with self.subTest(value=bad):
                self.assertFalse(
                    bad in WHEN_FIXED or any(p.match(bad) for p in WHEN_PATTERNS),
                    f"어휘 밖인데 검사가 통과시킨다: {bad}")

    def test_vocabulary_is_readable(self):
        self.assertGreaterEqual(len(contract_tags()), 5, "어휘가 비정상적으로 적다")

    def test_dictionary_stays_inside_the_vocabulary(self):
        """`dests.py`에 어휘 밖 태그가 들어오면 여기서 잡힌다.

        `야시장`·`유적`·`트레킹`이 조용히 들어왔던 것도 검사가 없어서였다.
        어휘를 늘리려면 기획 결정 → `contract/v1/vocab.json` 갱신이 계약 변경 절차다.
        """
        outside = sorted({t for v in dests.DEST.values() for t in v[4]} - contract_tags())
        self.assertEqual(outside, [], f"vocab.json 어휘에 없는 태그: {outside}")

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
        # DOCS를 빈 임시 폴더로 돌린다 — 안 그러면 하한선(BB1)이 **진짜 산출물**의
        # 딜 수와 비교해 테스트 데이터를 미달로 보고 None을 준다.
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(discover_data, "DOCS", Path(tmp)):
                return discover_data.build_deals_json(self.conn)

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
    """배포된 `docs/v1/deals.json`이 계약에 맞는가.

    생산 로직이 옳아도 커밋된 산출물이 옛 스키마로 남아 있으면, 그걸 픽스처로
    쓰는 프론트가 어긋난다. 그래서 파일 자체도 검사한다.

    발행물은 크론이 매일 커밋한다 — **없는 게 정상인 날이 없다.** 예전엔 없으면 skip 이었고,
    그러면 `docs/v1`이 통째로 지워져도 CI 가 초록불이다(BE14 T3). 없으면 실패한다.
    """

    def test_artifact_satisfies_the_contract(self):
        self.assertTrue(ARTIFACT.exists(), "docs/v1/deals.json 이 없다 — 발행물이 지워졌다")
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        errs = validate(payload, *contract_vocab())
        self.assertEqual(errs, [], "커밋된 산출물의 계약 위반:\n  " + "\n  ".join(errs))


if __name__ == "__main__":
    unittest.main()
