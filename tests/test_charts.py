# -*- coding: utf-8 -*-
"""charts — 표본이 부족할 때 차트를 그리지 않는가 (BE4).

**막대 하나짜리 차트는 비교할 게 없어서 차트가 아니다.** 그런데 그 상태가
예외로 보이지 않는다 — SVG는 멀쩡히 그려지고 숫자도 맞다. 화면을 열어봐야
"이게 왜 하나지?" 하고 알아챈다.

새 노선이 들어오면 **처음 한 달간 반드시 이 상태를 지난다.** 2026-09-03에
타이중을 넣었더니 11건이 전부 9월 출발이라 월별 차트에 9월 막대 하나만 섰고,
상단 요약은 "9월 출발이 가장 저렴합니다"라고 적었다 — 9월밖에 없으니
동어반복이다. 기획이 헤드리스 크롬으로 페이지를 실제로 렌더해서 찾았다.

여기서 지키는 건 **두 차트가 같은 기준을 쓴다**는 것이다. 예전엔 추이 차트가
`len(rows) < 2`, 막대 차트가 `not rows`라 막대 하나는 통과했다.
"""
import unittest

from charts import NOT_ENOUGH, bar_chart, line_chart


def fmt(x):
    return str(x)


class InsufficientDataTest(unittest.TestCase):
    """표본이 하나뿐이면 그리지 않고 안내로 대체한다."""

    def test_bar_chart_needs_at_least_two_bars(self):
        """막대 하나는 비교가 아니다 — 새 노선이 처음 한 달간 겪는 상태."""
        self.assertEqual(bar_chart([("9월", 200_658)]), NOT_ENOUGH)

    def test_bar_chart_draws_from_two(self):
        out = bar_chart([("9월", 200_658), ("10월", 180_000)])
        self.assertIn("<svg", out)
        self.assertNotEqual(out, NOT_ENOUGH)

    def test_line_chart_needs_at_least_two_points(self):
        self.assertEqual(line_chart([("09-02", 200_658)], fmt), NOT_ENOUGH)

    def test_line_chart_draws_from_two(self):
        out = line_chart([("09-02", 200_658), ("09-03", 190_000)], fmt)
        self.assertIn("<svg", out)

    def test_both_charts_use_the_same_threshold(self):
        """기준이 갈리면 한쪽만 안내가 뜬다 — 실제로 그랬다.

        같은 입력 개수에 대해 두 차트가 **같은 판단**을 해야 한다.
        """
        for n in (0, 1, 2, 3):
            rows = [(str(i), 100_000 + i) for i in range(n)]
            with self.subTest(n=n):
                self.assertEqual(bar_chart(rows) == NOT_ENOUGH,
                                 line_chart(rows, fmt) == NOT_ENOUGH)

    def test_empty_input_is_handled(self):
        self.assertEqual(bar_chart([]), NOT_ENOUGH)
        self.assertEqual(line_chart([], fmt), NOT_ENOUGH)

    def test_notice_is_a_single_source(self):
        """두 차트가 각자 문구를 들고 있으면 한쪽만 고쳐진다."""
        self.assertIn("데이터가 아직 충분하지 않습니다", NOT_ENOUGH)
        self.assertIn("매일 수집되어 곧 채워집니다", NOT_ENOUGH)


if __name__ == "__main__":
    unittest.main()
