# -*- coding: utf-8 -*-
"""정적 SVG 차트 (의존성 없음).

dataviz 규격: 2px 라인 / 10% 영역 채움 / 막대 ≤24px·상단 4px 라운드·2px 간격 /
가는 실선 그리드 / 선택적 직접 라벨 / 텍스트는 데이터 색을 입지 않음 /
hover는 투명 히트영역 + <title> 네이티브 툴팁.
"""
import math


def compact_won(v):
    """158000 -> '15.8만', 1262987 -> '126만'"""
    man = v / 10000
    return f"{man:.0f}만" if man >= 100 else f"{man:.1f}만"


def _nice_ticks(vmin, vmax, count=3):
    span = max(vmax - vmin, 1)
    raw = span / count
    mag = 10 ** math.floor(math.log10(raw))
    step = next((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), 10 * mag)
    start = math.floor(vmin / step) * step
    ticks = []
    t = start
    while t <= vmax + step * 0.5:
        if t >= vmin - step * 0.5:
            ticks.append(int(t))
        t += step
    return ticks or [int(vmin), int(vmax)]


def line_chart(rows, label_fmt, width=680, height=230):
    """rows: [(라벨, 값), ...] 시계열. 끝점과 최저점만 직접 라벨."""
    if len(rows) < 2:
        return "<p class='empty'>데이터가 아직 충분하지 않습니다. 매일 수집되어 곧 채워집니다.</p>"
    vals = [v for _, v in rows]
    ticks = _nice_ticks(min(vals), max(vals))
    lo, hi = min(min(vals), ticks[0]), max(max(vals), ticks[-1])
    span = (hi - lo) or 1
    ml, mr, mt, mb = 54, 58, 16, 28
    pw, ph = width - ml - mr, height - mt - mb

    def px(i):
        return ml + i * pw / (len(rows) - 1)

    def py(v):
        return mt + ph - (v - lo) / span * ph

    parts = []
    for t in ticks:
        y = round(py(t), 1)
        parts.append(f'<line class="gridline" x1="{ml}" y1="{y}" x2="{ml + pw}" y2="{y}"/>')
        parts.append(f'<text class="axis" x="{ml - 8}" y="{y + 4}" text-anchor="end">{compact_won(t)}</text>')

    pts = [(round(px(i), 1), round(py(v), 1)) for i, (_, v) in enumerate(rows)]
    line = " ".join(f"{x},{y}" for x, y in pts)
    parts.append(f'<polygon class="plot-area" points="{ml},{mt + ph} {line} {ml + pw},{mt + ph}"/>')
    parts.append(f'<polyline class="plot-line" points="{line}"/>')

    # x축: 첫/마지막 라벨만
    parts.append(f'<text class="axis" x="{ml}" y="{height - 8}">{label_fmt(rows[0][0])}</text>')
    parts.append(f'<text class="axis" x="{ml + pw}" y="{height - 8}" text-anchor="end">{label_fmt(rows[-1][0])}</text>')

    # 직접 라벨: 최저점 + 끝점 (선택적)
    imin = min(range(len(vals)), key=lambda i: vals[i])
    ilast = len(vals) - 1
    for i, cls in ((imin, "plot-dot-hi"), (ilast, "plot-dot")):
        x, y = pts[i]
        parts.append(f'<circle class="{cls}" cx="{x}" cy="{y}" r="4"/>')
    if imin != ilast:
        x, y = pts[imin]
        anchor = "start" if imin < len(rows) / 2 else "end"
        dx = 8 if anchor == "start" else -8
        parts.append(f'<text class="plot-label" x="{x + dx}" y="{y - 9}" text-anchor="{anchor}">최저 {vals[imin]:,}원</text>')
    x, y = pts[ilast]
    parts.append(f'<text class="plot-label" x="{x + 8}" y="{y + 4}">{vals[ilast]:,}원</text>')

    # hover 히트영역
    slot = pw / (len(rows) - 1)
    for i, (lab, v) in enumerate(rows):
        x = px(i) - slot / 2
        parts.append(f'<rect class="hit" x="{round(x, 1)}" y="{mt}" width="{round(slot, 1)}" height="{ph}">'
                     f'<title>{label_fmt(lab)} · {v:,}원</title></rect>')

    return (f'<svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="가격 추이 차트">{"".join(parts)}</svg>')


def bar_chart(rows, width=680, height=200):
    """rows: [(라벨, 값), ...] 범주형. 최저값 막대를 강조색 + 라벨."""
    if not rows:
        return "<p class='empty'>데이터가 아직 충분하지 않습니다.</p>"
    vals = [v for _, v in rows]
    lo = 0
    hi = max(vals) * 1.12
    mt, mb, ml, mr = 22, 26, 8, 8
    pw, ph = width - ml - mr, height - mt - mb
    slot = pw / len(rows)
    bw = min(24.0, slot - 2)          # ≤24px, 이웃과 2px 간격
    ibest = min(range(len(vals)), key=lambda i: vals[i])
    parts = []
    for i, (lab, v) in enumerate(rows):
        h = (v - lo) / (hi - lo) * ph
        x = ml + i * slot + (slot - bw) / 2
        y = mt + ph - h
        r = min(4.0, bw / 2, h)
        cls = "bar-best" if i == ibest else "bar"
        parts.append(
            f'<path class="{cls}" d="M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} '
            f'Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} L{x + bw - r:.1f},{y:.1f} '
            f'Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} L{x + bw:.1f},{y + h:.1f} Z">'
            f'<title>{lab} · {v:,}원</title></path>')
        parts.append(f'<text class="plot-label" x="{x + bw / 2:.1f}" y="{y - 6:.1f}" '
                     f'text-anchor="middle">{compact_won(v)}</text>')
        parts.append(f'<text class="axis" x="{x + bw / 2:.1f}" y="{height - 8}" '
                     f'text-anchor="middle">{lab}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="구간별 최저가 비교">{"".join(parts)}</svg>')
