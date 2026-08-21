# -*- coding: utf-8 -*-
"""detect_deals.py — 특가 판정.

판정 기준(`config.py`): 같은 노선·같은 유형(직항/경유)의 최근 30일 가격 중앙값 대비
65% 이하. 표본이 10건 미만이면 보류. 이 판정이 알림 메일과 `deals_latest.txt`로 나간다.

DB는 매번 `:memory:`에 `db.SCHEMA`로 새로 만든다 — 실 `data/prices.db`는 크론이
매일 커밋해 쌓는 되돌릴 수 없는 데이터라 테스트가 건드리면 안 된다.
"""
import sqlite3
import unittest

import config
import db
from detect_deals import compute_deals

ROUTE = ("ICN", "FUK")      # config.ROUTES에 있는 노선이어야 판정 대상이 된다
TODAY = "2026-08-20"
OLD = "2026-06-01"          # 30일 기준 밖


def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(db.SCHEMA)
    return conn


def add(conn, price, fetched=TODAY, direct=True, dest=None, depart="2026-09-16"):
    conn.execute(
        """INSERT INTO offers (fetched_date, origin, destination, depart_date,
                               return_date, price, airline, transfers,
                               return_transfers, link)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (fetched, ROUTE[0], dest or ROUTE[1], depart, "2026-09-20", price,
         "KE", 0 if direct else 1, 0 if direct else 1, "https://example.test/x"))


def add_baseline(conn, price, count, **kw):
    """같은 가격 여러 건 — UNIQUE 제약을 피하려 출발일을 달리한다."""
    for i in range(count):
        add(conn, price, depart=f"2026-09-{i + 1:02d}", **kw)


class SampleSizeTest(unittest.TestCase):
    """표본이 적으면 시세를 믿을 수 없으므로 판정 자체를 보류한다.

    주의: **특가 후보 행 자신도 표본에 포함된다.** 시세 계산과 특가 조회가 같은
    `offers` 테이블을 보기 때문이다. 그래서 경계를 세려면 후보 1건을 빼고 채워야 한다.
    """

    def test_below_minimum_samples_yields_nothing(self):
        """총 9건(기준선 8 + 후보 1) — 압도적으로 싼 값이 있어도 판정하지 않는다."""
        conn = memory_db()
        add_baseline(conn, 100000, config.MIN_SAMPLES - 2)
        add(conn, 10000, depart="2026-10-01")
        self.assertEqual(compute_deals(conn), [])

    def test_at_minimum_samples_it_judges(self):
        """총 10건(기준선 9 + 후보 1) — 딱 문턱에 닿으면 판정한다."""
        conn = memory_db()
        add_baseline(conn, 100000, config.MIN_SAMPLES - 1)
        add(conn, 10000, depart="2026-10-01")
        self.assertTrue(compute_deals(conn))


class ThresholdTest(unittest.TestCase):
    """중앙값의 65%가 경계. 경계값 자체는 포함된다(`price <= threshold`)."""

    def base(self):
        conn = memory_db()
        add_baseline(conn, 100000, 20)             # 중앙값 100,000 → 문턱 65,000
        return conn

    def test_exactly_on_the_threshold_counts(self):
        conn = self.base()
        add(conn, 65000, depart="2026-10-01")
        self.assertEqual([d["price"] for d in compute_deals(conn)], [65000])

    def test_just_above_the_threshold_does_not(self):
        conn = self.base()
        add(conn, 65001, depart="2026-10-01")
        self.assertEqual(compute_deals(conn), [])

    def test_discount_percentage(self):
        conn = self.base()
        add(conn, 50000, depart="2026-10-01")
        deal = compute_deals(conn)[0]
        self.assertEqual(deal["median"], 100000)
        self.assertEqual(deal["discount_pct"], 50)

    def test_only_the_three_cheapest_are_reported(self):
        conn = self.base()
        for i, p in enumerate((30000, 40000, 50000, 60000)):
            add(conn, p, depart=f"2026-10-{i + 1:02d}")
        prices = [d["price"] for d in compute_deals(conn)]
        self.assertEqual(prices, [30000, 40000, 50000])


class DirectAndTransferAreJudgedApartTest(unittest.TestCase):
    """직항과 경유는 시세가 다르다. 섞으면 싼 경유가 직항 시세를 끌어내린다."""

    def test_transfer_price_does_not_trigger_a_direct_deal(self):
        conn = memory_db()
        add_baseline(conn, 200000, 20, direct=True)     # 직항 시세 20만
        add_baseline(conn, 100000, 20, direct=False)    # 경유 시세 10만
        # 12만: 직항 시세의 60%(특가)지만 경유로 들어온 값이다.
        add(conn, 120000, direct=False, depart="2026-10-01")
        self.assertEqual(compute_deals(conn), [],
                         "경유 12만은 경유 시세(10만) 대비 비싸므로 특가가 아니다")

    def test_each_type_uses_its_own_median(self):
        conn = memory_db()
        add_baseline(conn, 200000, 20, direct=True)
        add_baseline(conn, 100000, 20, direct=False)
        add(conn, 60000, direct=False, depart="2026-10-01")   # 경유 시세의 60%
        deals = compute_deals(conn)
        self.assertEqual(len(deals), 1)
        self.assertFalse(deals[0]["is_direct"])
        self.assertEqual(deals[0]["median"], 100000)


class BaselineWindowTest(unittest.TestCase):
    """시세는 최근 30일만 본다. 오래된 가격은 시세 계산에서 빠진다."""

    def test_old_rows_are_excluded_from_the_median(self):
        conn = memory_db()
        add_baseline(conn, 1000000, 20, fetched=OLD)   # 30일 밖의 비싼 값
        add_baseline(conn, 100000, 20, fetched=TODAY)
        add(conn, 65000, depart="2026-10-01")
        deal = compute_deals(conn)[0]
        self.assertEqual(deal["median"], 100000,
                         "30일 밖 100만원이 시세에 섞이면 문턱이 올라간다")


class LatestFetchDateTest(unittest.TestCase):
    """오늘의 특가는 DB의 최신 수집일 기준이다.

    Actions 러너는 UTC라 `date.today()`가 KST와 어긋난다. 그래서 코드가
    `MAX(fetched_date)`를 쓰는데, 그게 실제로 동작하는지 본다.
    """

    def test_deals_come_from_the_latest_fetch_only(self):
        conn = memory_db()
        add_baseline(conn, 100000, 20, fetched="2026-08-19")
        add(conn, 50000, fetched="2026-08-19", depart="2026-10-01")  # 어제의 특가
        add(conn, 55000, fetched=TODAY, depart="2026-10-02")         # 오늘의 특가
        prices = [d["price"] for d in compute_deals(conn)]
        self.assertEqual(prices, [55000], "어제 특가는 오늘 목록에 남지 않는다")

    def test_no_offers_at_all_is_not_a_crash(self):
        """수집이 통째로 실패한 날에도 예외 없이 빈 목록이어야 한다."""
        self.assertEqual(compute_deals(memory_db()), [])


if __name__ == "__main__":
    unittest.main()
