# -*- coding: utf-8 -*-
"""v1 API 계약 검증기 (`CONTRACT.md` §v1).

계약은 **두 세션 사이의 약속**이라 한쪽이 조용히 어기면 반대편이 M2에서 발견한다.
그때는 이미 프론트가 그 응답을 전제로 코드를 짜 놓은 뒤다. 여기서 먼저 잡는다.

이 파일이 지키는 것 셋:

**① 봉투와 모양** — `schema`·`generated`(오프셋 필수)·블록별 필드.

**② P7 — 백엔드는 사실을, 프론트는 말을 낸다.**
`"9월"`·`"월요일"` 같은 **완성된 문장이 응답에 섞이면 실패**한다. 백엔드가 표시 문자열을
만들어 넣는 순간 프론트가 문구를 못 바꾼다. (옛 포매터 `labels.fmt_month`는 BE13 T3에서 지웠다.)

**③ 🔴 창은 백엔드, 임계는 프론트 — 그리고 이 응답으로 현행 화면이 재현되는가.**
M1의 DoD가 「계약이 현행 노선 페이지의 모든 숫자를 덮는가」다. 계약에 적힌
프론트 규칙(`n>=3`·앞에서 10개·상위 8개)을 실제로 적용해 **현행 화면이
쓰는 값과 대조**했다. M3 T3에서 옛 HTML이 사라져 그 대조는 끝났고,
남은 것은 **발행값이 계약을 지키는가**다.
"""
import json
import re
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import config
import db
import dests
import discover_data
import publish
import subscriptions
import timeutil
from route_stats import WINDOW_DAYS, airline_min, month_min, weekday_min

V1 = Path(__file__).resolve().parent.parent / "docs" / "v1"

# 화면 문자열이 새어 들어왔는지 보는 자국. 응답 어디에도 있으면 안 된다.
DISPLAY_LEAK = re.compile(r"\d+월|월요일|[월화수목금토일]요일|원$")


def load(rel):
    return load_from(V1, rel)


def load_from(v1, rel):
    return json.loads((v1 / rel).read_text(encoding="utf-8"))


def published_clock():
    """시계를 **산출물이 발행된 그 시각**(`meta.generated`)에 고정한다 (BE9 T1, BB34).

    커밋된 `docs/v1/`을 즉석 계산과 대조하는 테스트는 창(`today_utc()-30일`,
    `depart_date >= today_kst()`)이 시각에 따라 움직여서 **발행한 날에만** 통과했다.
    크론이 매일 새로 만들고 같은 날 돌던 구형에선 안 보였지만, push마다 도는
    `test.yml`은 크론 다음 날 아침부터 헛 빨간불이다(실측: +1일에 55건 실패).

    「지금」이 아니라 「발행한 순간」과 대조해야 같은 질문이 된다. DB와 `docs/v1/`은
    크론이 한 커밋으로 같이 올리므로 그 시각의 DB 상태가 곧 커밋된 DB다.

    `timeutil`만 고정하면 된다 — 창을 여는 코드가 전부 거기를 거친다(규칙이다).
    """
    at = datetime.fromisoformat(load("meta.json")["generated"])
    return mock.patch.multiple(
        timeutil,
        now_kst=lambda: at.astimezone(timeutil.KST),
        today_utc=lambda: at.astimezone(timezone.utc).date())


class EnvelopeTest(unittest.TestCase):
    """모든 응답의 최상위 두 키 (`CONTRACT.md` §공통 규칙)."""

    @classmethod
    def setUpClass(cls):
        if not (V1 / "meta.json").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.files = sorted(V1.rglob("*.json"))

    def test_every_response_declares_its_schema(self):
        for f in self.files:
            with self.subTest(file=f.name):
                self.assertEqual(json.loads(f.read_text(encoding="utf-8"))["schema"],
                                 "v1")

    def test_generated_carries_an_offset(self):
        """🔴 오프셋이 없으면 날짜 경계에서 하루가 **조용히** 어긋난다.

        화면이 신선도를 표시하고 있어(`발견가 · N일 전 가격`) 티가 안 난다.
        현행 `updated`의 `"2026-08-06 00:15"`가 바로 그 모양이라 v1에서 버렸다.
        """
        for f in self.files:
            with self.subTest(file=f.name):
                raw = json.loads(f.read_text(encoding="utf-8"))["generated"]
                parsed = datetime.fromisoformat(raw)
                self.assertIsNotNone(parsed.tzinfo, f"{raw}에 오프셋이 없다")


class GeneratedIsRequiredTest(unittest.TestCase):
    """🔴 `generated`를 빼먹으면 **조용히 지금 시각**이 아니라 **터져야** 한다 (BE9 T2, BB35).

    기본값 `or now_kst()`가 있던 시절엔 새 payload가 넘기기를 빼먹어도 돌았다 —
    그 파일만 초 단위로 갈리고, 프론트는 섞인 스냅숏으로 보고 배포를 멈춘다.
    원인이 백엔드 한 줄인데 증상은 프론트 배포 실패로 나타나 엉뚱한 데를 판다.
    """

    def test_every_payload_function_demands_it(self):
        for name, args in (("_envelope", ()),
                           ("meta_payload", ({}, False)),
                           ("deals_payload", (None, set())),
                           ("route_payload", (None, "ICN", "FUK")),
                           ("vocab_payload", ())):
            with self.subTest(fn=name), self.assertRaises(TypeError):
                getattr(publish, name)(*args)

    def test_naive_time_is_refused(self):
        """오프셋 없는 시각은 날짜 경계에서 하루가 조용히 어긋난다."""
        with self.assertRaises(ValueError):
            publish._envelope(datetime(2026, 9, 17, 11, 45))


def snapshot_errors(v1):
    """`CONTRACT.md` §공통 규칙의 스냅숏 규칙 위반 목록 (BE9 T3, BB35).

        meta = G · routes/index = G · routes/{code}(index에 실린 것) = G · vocab = G
        deals = G (preserved=false) · deals < G (preserved=true)

    `vocab.json`(BE11)은 딜 보존과 무관하다 — 보존일에도 `== G`다(CONTRACT §5).
    **없으면 위반이다.** 「있으면 본다」로 두면 발행이 파일을 빠뜨려도 조용히 통과한다.

    프론트가 받은 응답들로 「섞인 스냅숏」(CDN이 파일마다 따로 캐시)을 잡는 규칙이다.
    백엔드가 먼저 어기면 프론트 배포가 매일 멈춘다.

    **`routes/index.json` 기준으로만** 본다 — 계약이 소비자에게 index 기준으로 받으라고 적었다.
    (예전엔 표본이 0이 된 노선의 파일이 어제 시각으로 디스크에 남았다. BE14 T2부터 발행이 지운다 —
    디렉터리와 index 의 일치는 `OrphanRouteTest`가 따로 본다.)
    """
    def read(rel):
        return json.loads((v1 / rel).read_text(encoding="utf-8"))

    meta = read("meta.json")
    g = datetime.fromisoformat(meta["generated"])
    errs = []

    def same(rel):
        got = datetime.fromisoformat(read(rel)["generated"])
        if got != g:
            errs.append(f"{rel}: {got.isoformat()} != meta {g.isoformat()}")

    same("routes/index.json")
    if not (v1 / "vocab.json").exists():
        errs.append("vocab.json 이 없다")
    else:
        same("vocab.json")
    for r in read("routes/index.json")["routes"]:
        same(f"routes/{r['code']}.json")
    dg = datetime.fromisoformat(read("deals.json")["generated"])
    if meta["preserved"] and not dg < g:
        errs.append(f"deals.json: preserved=true 인데 {dg.isoformat()} 가 meta 보다 이르지 않다")
    if not meta["preserved"] and dg != g:
        errs.append(f"deals.json: preserved=false 인데 {dg.isoformat()} != meta {g.isoformat()}")
    return errs


class PublishedToTempDir(unittest.TestCase):
    """인메모리 DB + 임시 `docs/`로 `publish()`를 **실제로** 돌리는 바탕. 테스트는 없다."""

    NOW = datetime(2026, 9, 18, 7, 12, 3, tzinfo=timeutil.KST)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        docs = Path(self.tmp.name)
        self.v1 = docs / "v1"
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        today = self.NOW.date()
        # 노선 둘에 표본을 넣는다 — routes/{code}.json 이 실제로 나오게
        for o, d in config.ROUTES[:2]:
            self.conn.execute(
                "INSERT INTO offers (fetched_date, origin, destination, depart_date, "
                "price, airline, transfers) VALUES (?,?,?,?,?,?,0)",
                (today.isoformat(), o, d,
                 (today + timedelta(days=40)).isoformat(), 150000, "KE"))
        for p in (mock.patch.object(discover_data, "DOCS", docs),
                  mock.patch.object(publish, "V1", self.v1),
                  mock.patch.multiple(timeutil, now_kst=lambda: self.NOW,
                                      today_utc=lambda: self.NOW.astimezone(timezone.utc).date())):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.conn.close)
        self.addCleanup(self.tmp.cleanup)

    def _publish(self):
        with mock.patch("builtins.print"):
            return publish.publish(self.conn)


class SnapshotRuleTest(PublishedToTempDir):
    """🔴 한 번의 발행이 낸 응답의 `generated` 규칙 (BE9 T3, BB35).

    **보존일 케이스가 핵심이다.** 규칙이 처음엔 「전부 같다」였다 — 보존일이 아닌 날
    39개가 전부 같은 걸 보고 올렸고, 하한선 미달(BB1)이면 `deals.json`이 어제 시각으로
    남는 분기를 못 봤다. 그대로 잠갔으면 보존일마다 프론트 배포가 멈췄다.
    **한 날의 관측은 규칙의 근거가 아니다** — 그래서 두 분기를 둘 다 실제로 발행해 본다.
    """

    def test_ordinary_day_every_response_shares_one_time(self):
        n_routes, preserved = self._publish()
        self.assertFalse(preserved)
        self.assertEqual(n_routes, 2)
        self.assertEqual(snapshot_errors(self.v1), [])
        self.assertEqual(load_from(self.v1, "deals.json")["generated"],
                         self.NOW.isoformat(timespec="seconds"))

    def test_preserved_day_deals_is_older_and_the_rest_is_now(self):
        """하한선 미달 → `deals.json`은 어제 것 그대로, 나머지는 오늘."""
        yesterday = (self.NOW - timedelta(days=1)).isoformat(timespec="seconds")
        self.v1.mkdir(parents=True)
        (self.v1 / "deals.json").write_text(json.dumps(
            {"schema": "v1", "generated": yesterday, "origins": {},
             "deals": [{}] * discover_data.MIN_DEALS}), encoding="utf-8")
        # 옛 노선 파일이 어제 시각으로 남아 있다 — index 에 없으니 규칙 밖이어야 한다
        (self.v1 / "routes").mkdir()
        (self.v1 / "routes" / "ICN-XXX.json").write_text(json.dumps(
            {"schema": "v1", "generated": yesterday}), encoding="utf-8")

        _, preserved = self._publish()

        self.assertTrue(preserved)
        self.assertEqual(load_from(self.v1, "deals.json")["generated"], yesterday)
        self.assertTrue(load_from(self.v1, "meta.json")["preserved"])
        # 참조 데이터는 보존 대상이 아니다 — 보존일에도 오늘 G (CONTRACT §5)
        self.assertEqual(load_from(self.v1, "vocab.json")["generated"],
                         self.NOW.isoformat(timespec="seconds"))
        self.assertEqual(snapshot_errors(self.v1), [])

    def test_the_rule_catches_what_actually_went_wrong(self):
        """반례 — 구형 `05d0de9`의 `docs/v1`: deals만 42초 이르고 `preserved=false`.

        M1 때 deals의 `generated`를 분 단위 `updated`에서 만들던 흔적이다(프론트 제보).
        검사기가 이걸 통과시키면 위의 두 테스트도 헛것이다.
        """
        self._publish()
        meta = load_from(self.v1, "meta.json")
        meta["generated"] = "2026-09-08T15:28:42+09:00"
        (self.v1 / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        # 05d0de9 때는 vocab.json 이 없었다 — 반례를 옮기려고 meta 와 같은 시각에 맞춘다
        for rel in ["routes/index.json", "vocab.json"] + [
                f"routes/{r['code']}.json"
                for r in load_from(self.v1, "routes/index.json")["routes"]]:
            x = load_from(self.v1, rel)
            x["generated"] = "2026-09-08T15:28:42+09:00"
            (self.v1 / rel).write_text(json.dumps(x), encoding="utf-8")
        deals = load_from(self.v1, "deals.json")
        deals["generated"] = "2026-09-08T15:28:00+09:00"
        (self.v1 / "deals.json").write_text(json.dumps(deals), encoding="utf-8")

        errs = snapshot_errors(self.v1)
        self.assertEqual(len(errs), 1, errs)
        self.assertIn("deals.json", errs[0])

    def test_committed_artifact_follows_the_rule(self):
        # 없으면 skip 이 아니라 실패다 — 발행물이 통째로 지워져도 초록불이면 안 된다(BE14 T3)
        self.assertTrue((V1 / "meta.json").exists(), "docs/v1/meta.json 이 없다 — 발행물이 지워졌다")
        self.assertEqual(snapshot_errors(V1), [])


class OrphanRouteTest(PublishedToTempDir):
    """발행에서 빠진 노선의 파일이 **남지 않는가** (BE14 T2).

    남으면 옛 `generated`를 단 통계가 그 URL에서 계속 서빙된다. index에 없어 스냅숏 규칙은
    통과하므로 아무도 모른다 — 노선을 빼는 날, 또는 한 노선의 수집이 30일 끊긴 날 생긴다.
    """

    def _codes_on_disk(self):
        return {p.stem for p in (self.v1 / "routes").glob("*.json")} - {"index"}

    def test_a_route_no_longer_published_is_removed(self):
        self._publish()
        orphan = self.v1 / "routes" / "ICN-ZZZ.json"
        orphan.write_text('{"schema":"v1","generated":"2026-06-01T07:00:00+09:00"}',
                          encoding="utf-8")
        self._publish()
        self.assertFalse(orphan.exists(), "index 에 없는 노선 파일이 디스크에 남았다")

    def test_published_routes_and_index_survive(self):
        self._publish()
        self._publish()
        listed = {r["code"] for r in load_from(self.v1, "routes/index.json")["routes"]}
        self.assertEqual(len(listed), 2)                  # 픽스처가 표본을 넣은 노선 둘
        self.assertEqual(self._codes_on_disk(), listed)
        self.assertTrue((self.v1 / "routes" / "index.json").exists())

    def test_a_route_whose_samples_dried_up_disappears(self):
        """노선은 목록에 그대로인데 **창 안 표본이 0이 된** 경우 — 실제로 올 경로다."""
        self._publish()
        o, d = config.ROUTES[0]
        self.conn.execute("DELETE FROM offers WHERE origin=? AND destination=?", (o, d))
        self._publish()
        self.assertNotIn(f"{o}-{d}", self._codes_on_disk())
        self.assertEqual(snapshot_errors(self.v1), [])

    def test_committed_routes_dir_matches_the_index(self):
        self.assertTrue((V1 / "routes" / "index.json").exists(),
                        "docs/v1/routes/index.json 이 없다 — 발행물이 지워졌다")
        listed = {r["code"] for r in load("routes/index.json")["routes"]}
        on_disk = {p.stem for p in (V1 / "routes").glob("*.json")} - {"index"}
        self.assertEqual(on_disk, listed)


class VocabPublishTest(PublishedToTempDir):
    """`/v1/vocab.json`은 정본 파일을 **그대로** 싣는가 (BE11 T2, CONTRACT §5).

    기대값을 여기 손으로 적지 않는다 — 적으면 그게 또 하나의 사본이 된다(R8).
    정본 파일을 읽어 `$comment`를 빼는 일도 **발행 코드와 다른 방법으로** 한다.
    같은 함수로 기대값을 만들면 그 함수가 틀려도 테스트가 따라 틀린다.
    """

    @staticmethod
    def contract_without_comments():
        # json 파서 훅으로 뺀다 — publish._strip_comments 와 독립이다
        return json.loads(publish.VOCAB_SRC.read_text(encoding="utf-8"),
                          object_pairs_hook=lambda ps: {k: v for k, v in ps
                                                        if k != "$comment"})

    def setUp(self):
        super().setUp()
        self._publish()
        self.raw = (self.v1 / "vocab.json").read_text(encoding="utf-8")
        self.got = json.loads(self.raw)

    def test_body_is_the_contract_file_verbatim(self):
        # 봉투(`schema`·`generated`)와 **백엔드가 더하는 표시명**을 뺀 나머지가 정본과 같아야 한다.
        # 표시명은 정본 파일에 없는 파생값이다 — `region_name`(BE11) · `airport_name`(2026-09-22 §oa).
        body = {k: v for k, v in self.got.items()
                if k not in ("schema", "generated", "region_name", "airport_name")}
        self.assertEqual(body, self.contract_without_comments())

    def test_no_comment_leaks_even_nested(self):
        """`tags.$comment`·`when.$comment`까지 — 최상위만 빼면 설명 문장이 API로 나간다."""
        self.assertNotIn("$comment", self.raw)

    def test_order_that_means_something_is_kept(self):
        """`tags.top` = 칩 순서, `when.fixed` = 판정·칩 순서. dict 비교는 순서를 안 본다."""
        want = self.contract_without_comments()
        self.assertEqual(self.got["tags"]["top"], want["tags"]["top"])
        self.assertEqual(self.got["when"]["fixed"], want["when"]["fixed"])

    def test_region_names_come_from_the_destination_dictionary(self):
        self.assertEqual(self.got["region_name"],
                         {r: dests.REGION_NAME[r] for r in self.got["region"]})


class AirportNameTest(PublishedToTempDir):
    """`/v1/vocab.json`의 `airport_name` — 딜의 `oa`를 사람이 읽는 이름으로 (계약 §oa).

    없으면 소비자가 손 사본을 만들고, 공항이 늘어나는 날 조용히 **코드가 화면에 뜬다**
    (`region_name`을 계약에 실은 이유와 같다).
    """

    def test_it_is_the_dictionary_itself(self):
        """기대값을 손으로 적지 않는다 — 적으면 그게 또 하나의 사본이다(R8)."""
        self._publish()
        self.assertEqual(load_from(self.v1, "vocab.json")["airport_name"], dict(dests.ORIGINS))

    def test_every_departure_airport_has_a_name(self):
        """🔴 여집합 — 딜이 내보내는 `oa` 중 이름 없는 것이 하나도 없어야 한다."""
        self._publish()
        names = load_from(self.v1, "vocab.json")["airport_name"]
        used = {d["oa"] for d in load_from(self.v1, "deals.json")["deals"]}
        self.assertEqual(used - set(names), set(), "이름 없는 출발 공항이 있다")


class MetaTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not (V1 / "meta.json").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.meta = load("meta.json")

    def test_window_comes_from_the_single_source(self):
        """`meta`가 30을 따로 들고 있으면 창을 바꾸는 날 한쪽만 바뀐다."""
        self.assertEqual(self.meta["window_days"], WINDOW_DAYS)

    def test_counts_match_what_was_published(self):
        self.assertEqual(self.meta["counts"]["routes"],
                         len(load("routes/index.json")["routes"]))
        self.assertEqual(self.meta["counts"]["deals"],
                         len(load("deals.json")["deals"]))

    def test_subscribe_protocol_is_present(self):
        for key in ("address", "subject_subscribe",
                    "subject_unsubscribe", "route_token"):
            self.assertIn(key, self.meta["subscribe"])

    def test_subject_lines_come_from_the_parser_not_a_copy(self):
        """🔴 이 파일에서 가장 중요한 단언.

        `meta.json`의 존재 이유가 **「프론트가 규약을 지어내지 않게」**인데, 값이
        파서와 다른 곳에서 오면 그 보장이 사라진다. 그리고 그건 조용히 틀리는 게
        아니라 **반대로 동작한다** — `_extract_route()`가 노선을 못 찾으면
        `load_subscribers()`가 `route or "ALL"`로 받아(`subscriptions.py:61`)
        도쿄만 신청한 사람이 36노선 메일을 받는다.

        파서 상수를 바꿔서 발행값이 따라오는지 본다. 문자열을 복사해 두면 실패한다.
        """
        real = (subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE,
                subscriptions.SUBSCRIBE_ADDR)
        (subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE,
         subscriptions.SUBSCRIBE_ADDR) = "구독요청", "구독해지", "다른@메일함.com"
        try:
            sub = publish.meta_payload({}, False, timeutil.now_kst())["subscribe"]
            self.assertEqual(sub["subject_subscribe"], "구독요청")
            self.assertEqual(sub["subject_unsubscribe"], "구독해지")
            # 🔴 주소도 파서에서 온다 (M3 T5, BB32). 문자열을 복사해 두면 여기서 걸린다 —
            # 갈리면 화면이 적는 주소와 우리가 읽는 메일함이 달라지고 **반송조차 안 온다.**
            self.assertEqual(sub["address"], "다른@메일함.com")
        finally:
            (subscriptions.SUBSCRIBE, subscriptions.UNSUBSCRIBE,
             subscriptions.SUBSCRIBE_ADDR) = real

    def test_address_is_the_mailbox_we_actually_poll(self):
        """발행된 주소가 **IMAP으로 로그인하는 그 메일함**인가.

        T5 전에는 `theme.SUBSCRIBE_ADDR`과 비교했는데, 그건 화면 쪽 상수였다 —
        「우리가 읽는 메일함」이 아니라 「화면이 적는 주소」를 확인한 셈이다.
        """
        self.assertEqual(self.meta["subscribe"]["address"],
                         subscriptions.SUBSCRIBE_ADDR)

    def test_route_token_matches_what_the_parser_accepts(self):
        """본문에 실제로 들어갈 코드가 `ROUTE_RE`를 통과하는가."""
        sample = self.meta["subscribe"]["route_token"].replace("{code}", "ICN-FUK")
        self.assertEqual(subscriptions._extract_route(f"노선: {sample}"), "ICN-FUK")


class RoutePayloadTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not (V1 / "routes").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        cls.routes = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                      for p in (V1 / "routes").glob("*.json") if p.stem != "index"}
        if not cls.routes:
            raise unittest.SkipTest("노선 응답이 없다")

    def test_blocks_have_the_contracted_fields(self):
        for code, r in self.routes.items():
            with self.subTest(route=code):
                self.assertEqual(set(r["summary"]), {"cheapest", "median", "n"})
                for x in r["trend"]:
                    self.assertEqual(set(x), {"date", "price"})
                for x in r["months"]:
                    self.assertEqual(set(x), {"m", "price", "n"})
                for x in r["weekdays"]:
                    self.assertEqual(set(x), {"wd", "price", "n"})
                for x in r["airlines"]:
                    self.assertEqual(set(x), {"code", "name", "min", "n"})

    def test_trend_has_no_sample_count(self):
        """하루 = 한 점이라 `n`이 항상 1에 수렴한다 — 넣으면 군더더기다."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["trend"]:
                    self.assertNotIn("n", x)

    def test_months_are_machine_readable_not_display_strings(self):
        """`"2026-09"`를 보내지 `"9월"`을 보내지 않는다 (P7)."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["months"]:
                    self.assertRegex(x["m"], r"^\d{4}-\d{2}$")

    def test_weekdays_are_integers_not_names(self):
        """`0=일 … 6=토`. `"월"`로 바꾸는 건 표시 결정이라 프론트 몫이다."""
        for code, r in self.routes.items():
            with self.subTest(route=code):
                for x in r["weekdays"]:
                    self.assertIsInstance(x["wd"], int)
                    self.assertIn(x["wd"], range(7))

    def test_no_display_string_leaks_anywhere(self):
        """🔴 P7의 포괄 방어 — 누가 월·요일을 표시 문자열로 만들어 넣으면 여기서 걸린다.

        항공사 이름은 예외다. 그건 문장이 아니라 **참조 데이터**다(`deal.ko`와 같다).
        """
        for code, r in self.routes.items():
            probe = dict(r)
            probe["airlines"] = [{k: v for k, v in a.items() if k != "name"}
                                 for a in r["airlines"]]
            with self.subTest(route=code):
                leak = DISPLAY_LEAK.search(json.dumps(probe, ensure_ascii=False))
                self.assertIsNone(leak, f"{code}: 화면 문자열이 샜다 — {leak}")

    def test_backend_does_not_drop_thin_buckets(self):
        """창은 백엔드, 임계는 프론트 — **얇다고 버리지 않는다.**

        발행값이 필터를 끈 것과 같아야 한다. 화면이 3건 미만을 버리는 건
        `route_page()`의 기본값이지 사실이 아니다.
        """
        import db
        with published_clock(), closing(db.connect()) as conn:
            for code, r in self.routes.items():
                o, d = code.split("-")
                with self.subTest(route=code):
                    self.assertEqual(
                        len(r["months"]),
                        len(month_min(conn, o, d, min_samples=1, limit=None)))
                    self.assertEqual(
                        len(r["airlines"]),
                        len(airline_min(conn, o, d, limit=None)))


class ReproducesTheCurrentScreenTest(unittest.TestCase):
    """🔴 M1의 DoD — 이 응답으로 현행 노선 페이지를 다시 그릴 수 있는가.

    계약에 적힌 프론트 규칙을 실제로 적용해 현행 `route_page()`가 쓰는 값과 대조한다.
    하나라도 빠지면 **M2에서 프론트가 막힌다** — 그때는 이미 늦다.

        months    n >= 3 인 것만, 월 오름차순 앞에서 10개
        airlines  최저가 오름차순 상위 8개
        weekdays  전부 (건수 필터 없음)
    """

    @classmethod
    def setUpClass(cls):
        if not (V1 / "routes").exists():
            raise unittest.SkipTest("v1이 아직 발행되지 않았다")
        import db
        cls.conn = db.connect()
        # 클래스 전체가 커밋된 산출물과의 대조라 시계도 클래스 단위로 고정한다
        cls.clock = published_clock()
        cls.clock.start()

    @classmethod
    def tearDownClass(cls):
        cls.clock.stop()
        cls.conn.close()

    def test_front_rules_reproduce_every_number(self):
        for origin, dest in config.ROUTES:
            code = f"{origin}-{dest}"
            path = V1 / "routes" / f"{code}.json"
            if not path.exists():
                continue
            r = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(route=code):
                self.assertEqual(
                    [(x["m"], x["price"]) for x in r["months"] if x["n"] >= 3][:10],
                    [(m, p) for m, p, _ in month_min(self.conn, origin, dest)])
                self.assertEqual(
                    [(x["code"], x["min"], x["n"])
                     for x in sorted(r["airlines"], key=lambda x: x["min"])][:8],
                    list(airline_min(self.conn, origin, dest)))
                self.assertEqual(
                    [(x["wd"], x["price"]) for x in r["weekdays"]],
                    [(wd, p) for wd, p, _ in weekday_min(self.conn, origin, dest)])

    def test_summary_matches_the_page_headline(self):
        """히어로의 최저가·중앙값·「가격 N건」이 그대로 나오는가."""
        from route_stats import route_summary
        for origin, dest in config.ROUTES:
            path = V1 / "routes" / f"{origin}-{dest}.json"
            if not path.exists():
                continue
            s = json.loads(path.read_text(encoding="utf-8"))["summary"]
            with self.subTest(route=f"{origin}-{dest}"):
                self.assertEqual((s["cheapest"], s["median"], s["n"]),
                                 route_summary(self.conn, origin, dest))


if __name__ == "__main__":
    unittest.main()
