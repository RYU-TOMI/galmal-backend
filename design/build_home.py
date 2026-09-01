# -*- coding: utf-8 -*-
"""발견 홈 — 지금까지 확정한 것을 한 화면에 모은 목업.

빈 상자가 아니라 실제 deals.json으로 채운다. 움직임은 없다(전환은 open.html).
확정된 것은 검은 번호, 아직 안 정했거나 코드에 미반영인 것은 흰 번호.
셸은 _scene.py를 쓴다 — dock.html과 같은 함수라 둘이 어긋나지 않는다.
소유: 기획 세션. 산출물 design/home.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS, BOXES, OBS_FLOOR, DROP_FLOOR, record
from _fmt import tier, TIERS
from _scene import make_scene, covered, app

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
ctx = make_scene(D)
ALL, STAGE, OPEN, HERO = ctx["ALL"], ctx["STAGE"], ctx["OPEN"], ctx["HERO"]

# 2026-09-01 확정: 검색 바 + 날짜·예산 알약
DOCK = "FIN"

BADGES = [
    (1, 16, 14, False),                                  # 단계바
    (2, OPEN["_x"] - 130, OPEN["_y"] - 252, False),      # 열린 상세
    (3, OPEN["_x"] + 16, OPEN["_y"] - 6, False),         # 핀 강조
    (4, 838, 74, False),                                 # 히어로 사진 태그
    (5, 838, 268, False),                                # 작은 카드 태그 없음
    (6, 1154, 268, False),                               # 도장 / 신기록
    (7, 1154, 330, False),                               # 직항 배지
    (8, 838, 330, False),                                # 날짜 두 단
    (9, 26, 596, False),                                 # 검색 바
    (10, 700, 596, False),                               # 날짜·예산 알약
]
badges = "".join('<span class="b%s" style="left:%dpx;top:%dpx">%d</span>'
                 % (" q" if q else "", x, y, n) for n, x, y, q in BADGES)

ROWS = [
    (1, False, "거리 단계 3버튼 · 담백한 라벨",
     "<code>가까운 곳 / 조금 더 멀리 / 아주 멀리</code>. 자유 줌·팬은 안 넣는다 &mdash; "
     "정해주는 서비스라 뷰도 우리가 정한다. "
     "<b>현행 코드는 아직 <code>＋ 동남아 / ＋ 유럽·미주</code>다</b>(프론트 CH1).", "08-22"),
    (2, False, "상세는 지도 위에 뜬다",
     "카드를 누르면 <b>지도가 그 핀으로 미끄러진 뒤</b> 카드가 핀에서 피어난다. "
     "움직임이 시선을 데려가므로 &lsquo;어디로 가는지&rsquo;가 그대로 보인다. "
     "눌러볼 수 있는 목업은 <b>open.html</b>.", "09-01"),
    (3, False, "핀 확대 + 이름표 + 항로",
     "패널과 지도가 <b>각자 자기 언어로</b> 반응한다. 핀을 눌러도 대칭으로 동작한다 &mdash; "
     "패널이 그 카드로 스크롤한다.", "09-01"),
    (4, False, "히어로는 사진 위에 태그",
     "사진이 전폭이라 태그를 담을 수 있다. 개수가 곧 <b>즐길 게 얼마나 많은가</b>다(2~4개 가변).", "09-01"),
    (5, False, "작은 카드엔 태그 없음",
     "62px 썸네일은 태그를 담기엔 작다. 여기선 <b>어디·얼마·언제</b>만 읽으면 된다. "
     "카드가 <b>129px &rarr; 103px</b>이 되고 패널에 <b>+27%</b> 더 들어간다(<b>density.html</b>).", "09-01"),
    (6, False, "카드는 &lsquo;왜 싼가&rsquo;를 한 번만 말한다",
     "도장 3티어(<code>15/28/42%</code>) <b>우선</b>, 도장이 없고 신기록이면 <code>N일 최저</code>. "
     "<b>둘을 동시에 달지 않는다</b> &mdash; 재는 자가 달라도 사용자는 같은 말을 두 번 하는 걸로 읽는다. "
     "<b>상세에서는 둘 다</b> 보인다.", "09-01"),
    (7, False, "직항 배지는 가격 줄 우측",
     "도장과 <b>형태를 다르게</b> 한다(둥근 청록 채움, 기울기 없음). "
     "근거리 직항은 당연해서 안 붙인다 &mdash; <b>중·장거리만</b>.", "08-22"),
    (8, False, "날짜는 두 단 · 출발 &rarr; 도착",
     "<code>9/8(화) &rarr; 9/16(수)</code>가 주 라인, <code>8박9일 · 이번 주</code>가 보조 라인. "
     "<b>요일을 넣는다</b> &mdash; 여행은 요일로 정한다. 편도면 <code>9/8(화) 편도</code>.", "09-01"),
    (9, False, "검색 한 줄 &mdash; 분위기 <b>와</b> 목적지",
     "누르면 <b>어휘가 다 펼쳐지고</b>(모르는 사람은 고른다), 치면 걸러진다(아는 사람은 친다). "
     "<b>도시 이름도 같은 칸에서</b> 찾는다 &mdash; 분위기는 <b>필터</b>, 목적지는 <b>이동</b>. "
     "상태 다섯은 <b>search.html</b>.", "09-01"),
    (10, False, "날짜 &middot; 예산은 알약 + 팝오버",
     "값이 <b>범위</b>라 타이핑으로 고르기 나빠 검색창에 안 넣었다. "
     "날짜는 <b>언제 &times; 며칠</b> 두 축(<b>filters.html</b>), "
     "예산은 <b>히스토그램 + 바로가기 칩</b>(<b>budget.html</b>).", "09-01"),
]

trs = "".join('<tr><td class="k"><span class="num2%s">%d</span>%s</td><td>%s</td>'
              '<td class="k" style="color:%s">%s</td></tr>'
              % (" q" if q else "", n, title, desc, "#6C7B78" if q else "#1E7A50", when)
              for n, q, title, desc, when in ROWS)

n_rec = sum(1 for d in ALL if not tier(d) and record(d))
n_stamp = sum(1 for d in ALL if tier(d))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 확정 홈</title><style>" + CSS +
    "\n.k{white-space:nowrap;font-weight:800}"
    "</style></head><body><div class=wrap>"
    "<h1>발견 홈 &mdash; <em>지금까지 정한 것</em></h1>"
    "<p class=lede>빈 상자가 아니라 <b>실제 딜</b>로 채웠다. 서울 출발 " + str(len(ALL)) + "건 중 "
    "&lsquo;조금 더 멀리&rsquo; 단계에 드는 " + str(len(STAGE)) + "곳을 실제 좌표로 그렸다. "
    "움직임은 없다 &mdash; 전환은 <b>open.html</b>에서 눌러볼 수 있다.<br>"
    "<b>번호 열 개가 전부 확정</b>이고, 아직 안 정한 것은 &sect;03에 따로 모았다.</p>"
    + app(ctx, DOCK, badges) +
    "<h2><span class=n>01</span>번호 설명</h2>"
    "<table><tr><th style='width:250px'>무엇을</th><th>내용</th>"
    "<th style='width:74px'>확정</th></tr>" + trs + "</table>"
    "<h2><span class=n>02</span>오늘 화면에서 몇 건이 무엇을 다나</h2>"
    "<table><tr><th style='width:180px'>표시</th><th style='text-align:right;width:70px'>건수</th>"
    "<th>조건</th></tr>"
    "<tr><td><b>도장</b> 3티어</td><td class=num>" + str(n_stamp) + "건</td>"
    "<td><code>discount &ge; " + str(TIERS[-1][0]) + "%</code> "
    "(T1 " + str(TIERS[-1][0]) + " · T2 " + str(TIERS[1][0]) + " · T3 " + str(TIERS[0][0]) + ") "
    "&mdash; <b>평소 시세</b> 대비</td></tr>"
    "<tr><td><b>신기록</b> <code>N일 최저</code></td><td class=num>" + str(n_rec) + "건</td>"
    "<td><code>obs_days &ge; " + str(OBS_FLOOR) + "</code> &middot; <code>price &lt; low</code> &middot; "
    "<b>낙폭 &ge; " + str(int(DROP_FLOOR * 100)) + "%</b> &mdash; <b>이전 최저</b> 대비. "
    "도장이 있으면 표시하지 않는다</td></tr></table>"
    "<p class=note>낙폭 조건이 핵심이다 &mdash; <code>0.8% 더 쌈</code>은 기술적으로 신기록이지만 "
    "사용자에겐 <b>같은 가격</b>이다. 그런 걸 &lsquo;최저가&rsquo;라 부르면 문구 전체의 신뢰가 깎인다. "
    "한 번 빠뜨렸다가 백엔드가 잡아줬다.</p>"
    "<h2><span class=n>03</span>아직 안 정한 것</h2>"
    "<table><tr><th style='width:170px'>안건</th><th>메모</th></tr>"
    "<tr><td class=k>패널 폭 &mdash; <b>다음</b></td><td>지금 <b>380px</b>. 넓히면 카드가 여유롭지만 "
    "<b>지도가 좁아져 지구가 작아진다</b> &mdash; 미주까지 담아야 해서(호 286.7&deg;) 무대 폭이 곧 배율이다. "
    "다만 <b>&lsquo;스르륵 이동&rsquo;이 확정돼</b> 처음부터 다 보일 필요는 줄었다.</td></tr>"
    "<tr><td class=k>화면0</td><td>출발지를 고르는 첫 화면을 지금처럼 <b>따로</b> 둘지, "
    "지도 위에서 바로 고르게 할지.</td></tr>"
    "<tr><td class=k>모바일</td><td>지도와 카드 비중. 상세는 <b>하단 시트로 확정</b>.</td></tr>"
    "</table>"
    "<p class=note>&#9888; <b>이 세션엔 브라우저가 없어 실제 렌더를 못 본다.</b> "
    "겹치거나 어색한 곳이 있으면 알려주면 고친다.</p>"
    "<p class=foot>생성 <b>design/build_home.py</b> &middot; 셸 <b>design/_scene.py</b> &middot; "
    "데이터 <b>docs/data/deals.json</b> (<code>updated " + D.get("updated", "") + "</code>) &middot; "
    "확정 스펙 <b>../SPEC.md</b> &middot; 근거 <b>../DECISIONS.md</b><br>"
    "곁 목업 &mdash; 전환 <b>open.html</b> · 도크 <b>dock.html</b> · 밀도 <b>density.html</b></p>"
    "</div></body></html>")

io.open(os.path.join(BASE, "home.html"), "w", encoding="utf-8").write(html)
print("home.html  %.1fKB" % (len(html) / 1024.0))
print("  무대 '조금 더 멀리' %d곳 / 서울 전체 %d건" % (len(STAGE), len(ALL)))
print("  히어로 %s · 열린 상세 %s (%s)" % (HERO["ko"], OPEN["ko"], tier(OPEN)))
print("  도장 %d건 · 신기록 표시 %d건 (obs>=%d, 낙폭>=%d%%)"
      % (n_stamp, n_rec, OBS_FLOOR, int(DROP_FLOOR * 100)))
