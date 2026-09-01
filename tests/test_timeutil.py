# -*- coding: utf-8 -*-
"""timeutil — `found_at`이 UTC라는 사실의 단일 출처 (BB10·BB11).

이 프로젝트에서 UTC/KST 혼동으로 잘못된 결론이 세 번 나왔다. 마지막 것(BB11)은
`discover_data`는 올바르게 변환하는데 `fetch_breadth`가 같은 걸 다시, 틀리게
구현해서 생겼다. 그래서 이 파일이 검사하는 건 변환 결과만이 아니라
**두 곳이 같은 함수를 쓰고 있는지**다 — 갈라지는 순간이 사고의 시작이다.
"""
import unittest
from datetime import datetime, timedelta, timezone

import discover_data
import fetch_breadth
import timeutil

UTC = timezone.utc


class SingleSourceTest(unittest.TestCase):
    """지식이 한 곳에만 있는가. 갈라지면 하나는 반드시 틀린다."""

    def test_discover_data_reuses_the_shared_converter(self):
        """`discover_data`가 자체 변환을 다시 구현하면 실패한다."""
        self.assertIs(discover_data._seen_kst, timeutil.parse_found_at)

    def test_both_modules_agree_on_the_same_input(self):
        """수집(fetch_breadth)과 생산(discover_data)이 같은 시각으로 읽어야 한다.

        어긋나면 "수집 때는 신선했는데 내보낼 때는 오래된 값"이 되어,
        딜이 있다 없다 하는 재현 불가능한 버그가 된다.
        """
        raw = "2026-08-18T03:17:35"
        now = datetime(2026, 8, 18, 21, 17, 35, tzinfo=timeutil.KST)  # 정확히 9시간 뒤
        self.assertEqual(discover_data._seen_kst(raw), timeutil.parse_found_at(raw))
        self.assertAlmostEqual(timeutil.age_hours(raw, now), 9.0, places=6)


class ParseTest(unittest.TestCase):
    """경계에서 aware로 만든다 — naive인 채 흘려보내지 않는다."""

    def test_naive_input_is_utc(self):
        got = timeutil.parse_found_at("2026-08-18T03:17:35")
        self.assertEqual(got.isoformat(), "2026-08-18T12:17:35+09:00")

    def test_result_is_always_aware(self):
        """naive가 새어나가면 어딘가에서 다른 naive와 빼진다."""
        self.assertIsNotNone(timeutil.parse_found_at("2026-08-18T03:17:35").tzinfo)

    def test_existing_offset_is_respected(self):
        """향후 API가 오프셋을 붙여주면 UTC로 덮어쓰지 않는다."""
        self.assertEqual(timeutil.parse_found_at("2026-08-18T12:17:35+09:00").isoformat(),
                         "2026-08-18T12:17:35+09:00")

    def test_unusable_values_are_none(self):
        for raw in (None, "", "어제쯤", "2026-13-99T99:99:99", 12345):
            with self.subTest(raw=raw):
                self.assertIsNone(timeutil.parse_found_at(raw))


class AgeTest(unittest.TestCase):
    """나이는 **시간 단위**로 잰다 — `.days`는 내림이라 의도와 어긋난다(BB10)."""

    NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)

    def age(self, hours_ago):
        raw = (self.NOW - timedelta(hours=hours_ago)).replace(tzinfo=None).isoformat()
        return timeutil.age_hours(raw, self.NOW)

    def test_age_is_fractional(self):
        """95.5시간이 '3일'로 뭉개지지 않는다."""
        self.assertAlmostEqual(self.age(95.5), 95.5, places=6)

    def test_unusable_value_is_none(self):
        self.assertIsNone(timeutil.age_hours("어제쯤", self.NOW))

    def test_boundary_matches_the_declared_window(self):
        """`MAX_AGE_HOURS`가 이름 그대로 96시간에서 자른다.

        예전엔 `MAX_AGE_DAYS = 3`이라 써놓고 `.days` 내림 때문에 95시간59분까지
        통과시켰다. 이름과 동작이 다르면 아무도 실제 창을 모른다.
        """
        cut = fetch_breadth.MAX_AGE_HOURS
        self.assertEqual(cut, 96)
        self.assertLessEqual(self.age(95.9), cut)    # 통과
        self.assertGreater(self.age(96.1), cut)      # 컷

    def test_a_naive_local_clock_would_have_been_wrong(self):
        """BB11 회귀 방지 — KST 벽시계로 빼면 9시간이 부풀려진다.

        그 9시간 때문에 도쿄(ICN) 148,796원이 잘리고 더 비싼 GMP 편이 노출됐다.
        """
        raw = (self.NOW - timedelta(hours=94)).replace(tzinfo=None).isoformat()
        correct = timeutil.age_hours(raw, self.NOW)
        naive_kst = (self.NOW.astimezone(timeutil.KST).replace(tzinfo=None)
                     - datetime.fromisoformat(raw)).total_seconds() / 3600
        self.assertAlmostEqual(correct, 94.0, places=6)
        self.assertAlmostEqual(naive_kst, 103.0, places=6)
        self.assertLessEqual(correct, fetch_breadth.MAX_AGE_HOURS)      # 살아야 하고
        self.assertGreater(naive_kst, fetch_breadth.MAX_AGE_HOURS)      # 예전엔 잘렸다


if __name__ == "__main__":
    unittest.main()
