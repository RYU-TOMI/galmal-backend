# -*- coding: utf-8 -*-
"""수집 실패가 실패로 보이는가 (BB2).

예전엔 두 수집기 모두 공항·노선별로 예외를 삼키고 `continue`했다. 그래서
**5개 공항이 전부 죽어도 exit 0**이었고, 워크플로가 그대로 진행돼 빈 산출물을
커밋·배포했다. 역설적으로 스텝이 제대로 실패하면 잡이 멈춰 커밋이 안 되고
사이트가 어제 상태로 남는다 — 그쪽이 안전하다.

정책은 둘 다 같다:
  - **일부 실패는 넘어간다** (나머지 데이터는 쓸모가 있다)
  - **전부 실패하거나 한 건도 못 건지면 종료 코드 1**

네트워크와 실 DB는 건드리지 않는다. `fetch_*`와 `db.connect`를 갈아끼운다.
"""
import contextlib
import io
import sqlite3
import unittest
from unittest import mock

import config
import db
import fetch_breadth
import fetch_prices
from dests import ORIGINS


@contextlib.contextmanager
def quiet():
    """수집기의 진행 로그를 삼킨다 — 진짜 실패 메시지가 묻히지 않게."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA)
    return conn


def breadth_row(dest="FUK", price=100000):
    """신선도 컷을 통과하는 광역 응답 1건."""
    import timeutil
    from datetime import timedelta
    found = (timeutil.now_kst() - timedelta(hours=1)).astimezone(
        timeutil.FOUND_AT_TZ).replace(tzinfo=None)
    return {"destination": dest, "value": price, "number_of_changes": 0,
            "depart_date": "2026-12-01", "return_date": "2026-12-05",
            "found_at": found.isoformat()}


class BreadthFailureTest(unittest.TestCase):
    """광역 수집(fetch_breadth)."""

    def run_main(self, side_effect):
        conn = memory_conn()
        with mock.patch.object(fetch_breadth, "load_token", return_value="t"), \
                mock.patch.object(fetch_breadth.db, "connect", return_value=conn), \
                mock.patch.object(fetch_breadth, "fetch_origin", side_effect=side_effect), \
                mock.patch.object(fetch_breadth.time, "sleep"), quiet():
            fetch_breadth.main()

    def test_total_failure_exits_nonzero(self):
        """모든 공항이 실패하면 조용히 끝나지 않는다."""
        with self.assertRaises(SystemExit) as cm:
            self.run_main(ConnectionError("API down"))
        self.assertIn("모두 실패", str(cm.exception))

    def test_partial_failure_is_tolerated(self):
        """한 공항만 죽었으면 나머지 데이터로 계속 간다."""
        calls = {"n": 0}

        def side_effect(token, origin):
            calls["n"] += 1
            if origin == "ICN":
                raise ConnectionError("일시 장애")
            return [breadth_row()]

        self.run_main(side_effect)                      # 예외 없이 끝나야 한다
        self.assertEqual(calls["n"], len(ORIGINS))

    def test_empty_response_exits_nonzero(self):
        """호출은 됐는데 한 건도 못 건지면 그것도 실패다.

        목적지 코드 체계가 바뀌면(BB15) 이 모양으로 나타난다 — 에러는 없는데
        전부 걸러진다. 조용히 넘어가면 아무도 모른다.
        """
        with self.assertRaises(SystemExit) as cm:
            self.run_main(lambda token, origin: [])
        self.assertIn("0건", str(cm.exception))

    def test_unknown_destinations_only_also_fails(self):
        """응답은 있지만 전부 사전 밖이면 저장분이 0건 → 실패."""
        with self.assertRaises(SystemExit):
            self.run_main(lambda token, origin: [breadth_row(dest="ZZZ")])

    def test_healthy_run_does_not_exit(self):
        self.run_main(lambda token, origin: [breadth_row()])


class PricesFailureTest(unittest.TestCase):
    """노선 수집(fetch_prices) — 같은 정책이 적용되는가."""

    def run_main(self, side_effect):
        conn = memory_conn()
        with mock.patch.object(fetch_prices, "load_token", return_value="t"), \
                mock.patch.object(fetch_prices.db, "connect", return_value=conn), \
                mock.patch.object(fetch_prices, "fetch_route", side_effect=side_effect), \
                mock.patch.object(fetch_prices.time, "sleep"), quiet():
            fetch_prices.main()

    def test_total_failure_exits_nonzero(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(ConnectionError("API down"))
        self.assertIn("모두 실패", str(cm.exception))

    def test_partial_failure_is_tolerated(self):
        first = config.ROUTES[0]

        def side_effect(token, origin, dest):
            if (origin, dest) == first:
                raise ConnectionError("일시 장애")
            return [{"departure_at": "2026-12-01T10:00:00", "return_at": "2026-12-05T10:00:00",
                     "price": 100000, "airline": "KE", "transfers": 0,
                     "return_transfers": 0, "link": "/x"}]

        self.run_main(side_effect)

    def test_empty_response_exits_nonzero(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(lambda token, o, d: [])
        self.assertIn("0건", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
