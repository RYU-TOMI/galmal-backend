# -*- coding: utf-8 -*-
"""discover_data.py의 순수 함수 테스트 — `_median`, `_when_label`.

두 함수는 `deals.json`의 `median`·`when` 필드를 직접 결정한다(`CONTRACT.md`).
할인율·`nights` 계산은 순수 함수가 아니라 `build_deals_json()` 본문에 인라인으로
있어 여기서 다루지 않는다 → BE0 T3의 end-to-end 검증에서 확인한다.

⚠️ `_when_label` 테스트 일부는 **현재 동작을 박제한 것이지 올바른 사양이 아니다.**
   해당 케이스에 BB 번호를 달아 두었다(`BACKEND.md` 곁가지 백로그).
   BE2에서 고치면 이 테스트들이 실패하면서 무엇이 바뀌었는지 알려준다.
"""
import unittest
from datetime import date

from discover_data import _median, _when_label


class MedianTest(unittest.TestCase):
    """`_median` — broad_offers 이력에서 '평소 시세'를 뽑는 함수."""

    def test_empty_returns_none(self):
        """빈 이력은 None. 호출부가 `_median(hist) or dd["price"]`로 폴백한다."""
        self.assertIsNone(_median([]))

    def test_odd_count_takes_middle(self):
        """홀수 개는 가운데 값."""
        self.assertEqual(_median([10, 20, 30]), 20)

    def test_even_count_floors_the_average(self):
        """짝수 개는 두 값의 평균을 **정수 나눗셈**으로 내린다(`//`). 1.5가 아니라 1."""
        self.assertEqual(_median([1, 2]), 1)
        self.assertEqual(_median([10, 20, 30, 41]), 25)

    def test_input_need_not_be_sorted(self):
        """정렬되지 않은 입력도 내부에서 정렬해 계산한다."""
        self.assertEqual(_median([30, 10, 20]), 20)

    def test_single_value(self):
        """1건뿐이면 그 값이 곧 시세 — 할인율이 0이 되는 경로."""
        self.assertEqual(_median([42522]), 42522)


class WhenLabelTest(unittest.TestCase):
    """`_when_label` — 출발일을 상대 날짜 문구로. 조건 네 겹의 우선순위가 핵심.

    기준일은 2026-08-22(토)로 고정한다. 요일에 따라 결과가 갈리므로
    `date.today()`를 쓰면 테스트가 날마다 달라진다.
    """

    TODAY = date(2026, 8, 22)          # 토요일

    def label(self, y, m, d):
        return _when_label(date(y, m, d), self.TODAY)

    def test_today_on_a_weekend_is_weekend(self):
        """당일 출발이라도 금·토·일이면 '이번 주말'."""
        self.assertEqual(self.label(2026, 8, 22), "이번 주말")   # 토

    def test_sunday_within_nine_days_is_weekend(self):
        self.assertEqual(self.label(2026, 8, 23), "이번 주말")   # 일, +1

    def test_weekday_within_a_week_is_this_week(self):
        """주말 조건에 걸리지 않는 평일은 7일 이내면 '이번 주'."""
        self.assertEqual(self.label(2026, 8, 27), "이번 주")     # 목, +5

    def test_weekend_rule_wins_over_this_week(self):
        """+7일이라 '이번 주'에도 해당하지만, 주말 조건이 먼저라 '이번 주말'."""
        self.assertEqual(self.label(2026, 8, 29), "이번 주말")   # 토, +7

    def test_weekend_window_extends_to_nine_days(self):
        """주말 조건의 창은 9일이라 '이번 주'(7일)보다 넓다."""
        self.assertEqual(self.label(2026, 8, 30), "이번 주말")   # 일, +8

    def test_weekend_window_stops_after_nine_days(self):
        """+10일은 금요일이어도 주말 라벨이 아니다(상한 9일)."""
        self.assertEqual(_when_label(date(2026, 9, 4), date(2026, 8, 25)), "다음 달")

    def test_next_month(self):
        self.assertEqual(self.label(2026, 9, 1), "다음 달")      # 화, +10

    def test_month_after_next_uses_month_name(self):
        self.assertEqual(self.label(2026, 10, 1), "10월")        # 목, +40

    def test_year_end_rolls_over_to_january(self):
        """12월 기준 '다음 달'은 이듬해 1월. `nxt_year` 보정이 동작하는지."""
        self.assertEqual(_when_label(date(2027, 1, 4), date(2026, 12, 15)), "다음 달")

    def test_january_of_a_later_year_is_not_next_month(self):
        """'다음 달'은 달뿐 아니라 **연도까지** 맞아야 한다.

        2026-12 기준 '다음 달'은 2027-01뿐이다. 2028-01은 달이 같아도
        `nxt_year` 조건에서 걸러져 월 이름으로 떨어진다.
        """
        self.assertEqual(_when_label(date(2028, 1, 4), date(2026, 12, 15)), "1월")

    # ---- 아래 둘은 현재 동작 박제. 올바른 사양이 아니다. ----

    def test_current_month_is_labelled_with_its_own_name(self):
        """BB7: 8월에 8월 말 평일 출발이면 '8월'. 사용자에게 정보가 없는 라벨이다.

        조건 순서상 주말도(월요일) 이번 주도(+9일) 다음 달도 아니라 월 이름으로 떨어진다.
        """
        self.assertEqual(self.label(2026, 8, 31), "8월")         # 월, +9

    def test_month_label_ignores_the_year(self):
        """BB8: 이듬해 출발도 연도 없이 '3월'. 지나간 3월과 구분되지 않는다."""
        self.assertEqual(self.label(2027, 3, 1), "3월")

    def test_past_departure_falls_into_this_week(self):
        """과거 날짜는 '이번 주'가 된다(`delta <= 7`이 음수도 통과).

        `build_deals_json()`이 미래 출발만 조회하므로 실사용에는 나타나지 않는다.
        함수 단독 동작을 기록해 둔다.
        """
        self.assertEqual(self.label(2026, 8, 19), "이번 주")     # 수, -3


if __name__ == "__main__":
    unittest.main()
