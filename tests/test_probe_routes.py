# -*- coding: utf-8 -*-
"""노선 후보 측정 — 7일 **연속** 중앙값으로 가른다 (기획 결정 2026-09-28 (2)).

조용히 틀릴 수 있는 자리:
  · 하루 빠졌는데 앞뒤를 이어 붙여 「7일」로 센다 → 연속이 아닌 7점으로 넣는다
  · 같은 날 두 번 돌면(주·예비·손) 두 점이 된다 → 한 날이 두 번 센다
  · 측정이 `offers`에 들어간다 → 아직 안 넣은 노선이 페이지·특가 판정의 입력이 된다
네트워크와 실 DB·실 `data/route_probe.json`은 건드리지 않는다.
"""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest import mock

import db
import probe_routes
from probe_routes import THRESHOLD, WINDOW, record, streak, verdict

D = date(2026, 10, 5)


def rows(n, direct=0):
    return [{"transfers": 0 if i < direct else 1} for i in range(n)]


def filled(counts, end=D, route="ICN-CNX"):
    """`counts`를 `end`에서 거꾸로 하루씩 채운다(최신이 앞)."""
    data = {}
    for i, n in enumerate(counts):
        record(data, route, date.fromordinal(end.toordinal() - i).isoformat(), rows(n))
    return data


class StreakTest(unittest.TestCase):
    def test_counts_back_from_today(self):
        self.assertEqual(streak(filled([9, 12, 30]), "ICN-CNX", D), [9, 12, 30])

    def test_a_missing_day_breaks_the_streak(self):
        data = filled([9, 12, 30])
        del data["ICN-CNX"][date(2026, 10, 4).isoformat()]
        self.assertEqual(streak(data, "ICN-CNX", D), [9])

    def test_no_value_today_is_an_empty_streak(self):
        """오늘 측정이 실패했으면 어제까지의 연속을 「오늘까지」로 치지 않는다."""
        self.assertEqual(streak(filled([9, 12], end=date(2026, 10, 4)), "ICN-CNX", D), [])

    def test_same_day_twice_is_one_point(self):
        data = filled([9])
        record(data, "ICN-CNX", D.isoformat(), rows(40, direct=5))
        self.assertEqual(streak(data, "ICN-CNX", D), [40])
        self.assertEqual(data["ICN-CNX"][D.isoformat()], {"n": 40, "direct": 5})


class VerdictTest(unittest.TestCase):
    def test_waits_until_the_window_is_full(self):
        self.assertTrue(verdict([50] * (WINDOW - 1)).startswith("측정 중"))

    def test_median_at_threshold_passes(self):
        counts = [THRESHOLD] * WINDOW
        self.assertTrue(verdict(counts).startswith("✅"))

    def test_median_below_threshold_fails(self):
        self.assertTrue(verdict([9, 9, 9, 9, 30, 30, 30]).startswith("❌"))   # 중앙 9

    def test_one_good_day_does_not_carry_it(self):
        """하루치 판정이 틀렸던 이유 그대로 — 한 날이 튀어도 중앙값은 안 움직인다."""
        self.assertTrue(verdict([200, 7, 7, 7, 7, 7, 7]).startswith("❌"))

    def test_only_the_latest_window_counts(self):
        """오래된 좋은 날이 최근 7일 판정을 끌어올리지 않는다."""
        self.assertTrue(verdict([7] * WINDOW + [90] * 10).startswith("❌"))


class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "route_probe.json"
        self.pub = Path(tmp.name) / "prices.db"
        with closing(sqlite3.connect(self.pub)) as c:
            c.executescript(db.SCHEMA)

    def run_main(self, fetch):
        with mock.patch.object(probe_routes, "PATH", self.path), \
             mock.patch.object(probe_routes.fetch_prices, "load_token", lambda: "t"), \
             mock.patch.object(probe_routes.fetch_prices, "fetch_route", fetch), \
             mock.patch.object(probe_routes.timeutil, "today_utc", lambda: D), \
             mock.patch.object(db, "connect", lambda: sqlite3.connect(self.pub)), \
             mock.patch("builtins.print"):
            probe_routes.main()

    def test_every_candidate_is_recorded(self):
        self.run_main(lambda tok, o, d: rows(9, direct=6))
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(data), sorted(f"{o}-{d}" for o, d in probe_routes.CANDIDATES))
        for route in data:
            self.assertEqual(data[route], {D.isoformat(): {"n": 9, "direct": 6}})

    def test_history_is_kept(self):
        self.path.write_text(json.dumps({"ICN-CNX": {"2026-10-04": {"n": 23, "direct": 12}}}), encoding="utf-8")
        self.run_main(lambda tok, o, d: rows(9))
        self.assertEqual(sorted(json.loads(self.path.read_text(encoding="utf-8"))["ICN-CNX"]),
                         ["2026-10-04", D.isoformat()])

    def test_offers_are_never_written(self):
        """🔴 아직 안 넣은 노선이다 — `offers`에 들어가면 노선 페이지·특가 판정의 입력이 된다."""
        self.run_main(lambda tok, o, d: [{"transfers": 0, "price": 1, "departure_at": "2026-11-01"}] * 12)
        with closing(sqlite3.connect(self.pub)) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM offers").fetchone()[0], 0)

    def test_a_failure_is_loud_but_the_others_are_saved(self):
        def fetch(tok, o, d):
            if d == "CNX":
                raise OSError("timeout")
            return rows(11)
        with self.assertRaises(SystemExit) as cm:
            self.run_main(fetch)
        self.assertIn("ICN-CNX", str(cm.exception))
        self.assertEqual(sorted(json.loads(self.path.read_text(encoding="utf-8"))), ["ICN-HIJ"])

    def test_output_is_lf(self):
        self.run_main(lambda tok, o, d: rows(9))
        self.assertNotIn(b"\r\n", self.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
