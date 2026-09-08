# -*- coding: utf-8 -*-
"""노선 통계의 **창(window)** — 언제 것을 세는가 (BB29).

계약 v1이 세운 규칙은 **「창은 백엔드, 임계는 프론트」**다.
- **창**: 어느 기간을 분석하나 (최근 30일 · 오늘 이후 출발) → 여기
- **임계**: 이 숫자를 보여줘도 되나 (버킷 2개 미만이면 안 그린다) → 프론트

BB29가 그 규칙의 첫 시험이었고, **두 축이 다르다는 걸 한 줄로 증명했다**:
2026-09-08에 `ICN-NRT`의 2026-08 버킷은 **915건**으로 36개 노선 전체에서 가장
튼튼했는데, 8월은 이미 지나서 아무 쓸모가 없었다. 얇아서 틀린 게 아니라
**지나서** 틀린 것이라 임계로는 원리적으로 못 거른다.

그날 배포본 5장이 이렇게 말하고 있었다:

    ICN-GUM · ICN-HKG · ICN-LAX · ICN-NGO   "8월 출발이 가장 저렴합니다"
    ICN-KUL                                  "7월 출발이 가장 저렴합니다"

🔴 **코드는 처음부터 틀렸고 데이터가 짧아서 안 보였다.** `offers.depart_date`가
2026-07-09부터라 이력이 두 달을 넘긴 2026-09에야 지난 달 버킷이 생겼다.
**시간이 지나야 드러나는 종류라 리뷰로는 못 잡는다** — 그래서 테스트로 잠근다.
"""
import sqlite3
import unittest
from datetime import timedelta

import db
import timeutil
from build_site import month_min, weekday_min


def seed(conn, rows):
    """rows: [(depart_date, price), ...] — 한 노선(ICN-XXX)에 넣는다."""
    conn.executemany(
        """INSERT INTO offers
           (fetched_date, origin, destination, depart_date, price, airline)
           VALUES ('2026-09-01', 'ICN', 'XXX', ?, ?, 'KE')""", rows)


def months(dep, n=3, price=100_000):
    """같은 출발일 `n`건 — `HAVING COUNT(*)>=3`을 넘기기 위한 최소 표본."""
    return [(dep.isoformat(), price)] * n


class MonthWindowTest(unittest.TestCase):
    """`month_min`은 오늘 이후 출발만 센다."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)
        self.today = timeutil.today_kst()

    def tearDown(self):
        self.conn.close()

    def test_past_departure_month_is_excluded(self):
        """이 파일의 존재 이유 — 살 수 없는 달을 추천하지 않는다."""
        past = self.today.replace(day=1) - timedelta(days=40)
        seed(self.conn, months(past))
        self.assertEqual(month_min(self.conn, "ICN", "XXX"), [])

    def test_future_departure_month_is_kept(self):
        future = self.today + timedelta(days=60)
        seed(self.conn, months(future, price=158_000))
        got = month_min(self.conn, "ICN", "XXX")
        self.assertEqual(got, [(future.strftime("%Y-%m"), 158_000)])

    def test_today_itself_is_still_bookable(self):
        """경계 — 오늘 출발은 아직 살 수 있다. `>` 가 아니라 `>=` 다."""
        seed(self.conn, months(self.today))
        self.assertEqual(len(month_min(self.conn, "ICN", "XXX")), 1)

    def test_a_huge_past_bucket_still_loses_to_a_thin_future_one(self):
        """🔴 **표본 임계로는 못 거른다**는 것 — BB29의 핵심.

        지난 달에 915건, 다음 달에 3건을 넣는다. 표본만 보면 지난 달이
        압도적이지만 **살 수 없으므로 답이 아니다.** 거르는 축은 창이다.
        """
        past = self.today.replace(day=1) - timedelta(days=40)
        future = self.today + timedelta(days=60)
        seed(self.conn, months(past, n=915, price=50_000))
        seed(self.conn, months(future, n=3, price=900_000))
        got = month_min(self.conn, "ICN", "XXX")
        self.assertEqual([m for m, _ in got], [future.strftime("%Y-%m")])
        # 화면은 이 결과의 최솟값으로 "○월 출발이 가장 저렴합니다"를 쓴다.
        self.assertEqual(min(got, key=lambda r: r[1])[1], 900_000)

    def test_window_uses_the_users_today_not_the_runners(self):
        """🔴 `today_utc()`로 바꿔 쓰면 여기서 갈린다 — 크론은 UTC 러너에서 돈다.

        KST 새벽 3시는 전날 18시 UTC다. 그 순간 두 함수는 **다른 날**을 준다.
        어제 출발을 넣고 KST 기준으로 오늘을 하루 앞세우면,
        - `today_kst()`(옳음) → 어제는 지났으므로 **버린다**
        - `today_utc()`(틀림) → 어제가 아직 '오늘'이라 **남는다**

        `timeutil`이 용도를 갈라둔 이유가 정확히 이것이고(BB13·BB17),
        `NaiveTodayDebtTest`가 지키는 규율의 실제 사용처다.
        """
        yesterday = self.today - timedelta(days=1)
        seed(self.conn, months(yesterday))
        real_kst, real_utc = timeutil.today_kst, timeutil.today_utc
        timeutil.today_kst = lambda: self.today          # KST로는 오늘
        timeutil.today_utc = lambda: yesterday           # UTC로는 아직 어제
        try:
            self.assertEqual(month_min(self.conn, "ICN", "XXX"), [],
                             "today_utc()를 쓰면 지난 출발이 하루 더 살아남는다")
        finally:
            timeutil.today_kst, timeutil.today_utc = real_kst, real_utc


class WeekdayWindowTest(unittest.TestCase):
    """요일은 **창을 걸지 않는다** — 같은 규칙을 잘못 복사하는 걸 막는다.

    요일은 순환한다. 지난 화요일의 가격도 "화요일은 싼가"에 대한 유효한 증거다.
    달과 달리 '지나서 못 산다'가 성립하지 않으므로 창을 걸면 표본만 잃는다.
    """

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(db.SCHEMA)

    def tearDown(self):
        self.conn.close()

    def test_past_departures_still_count_for_weekday(self):
        past = timeutil.today_kst() - timedelta(days=90)
        seed(self.conn, [(past.isoformat(), 120_000)])
        self.assertEqual(len(weekday_min(self.conn, "ICN", "XXX")), 1)


if __name__ == "__main__":
    unittest.main()
