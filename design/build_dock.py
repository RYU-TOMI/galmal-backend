# -*- coding: utf-8 -*-
"""필터 도크 4안 — 각각 풀사이즈 홈 화면으로 그린다.

가려지는 넓이가 아니라 **가려지는 핀 개수**로 잰다. 지도는 핀을 보여주려고 있다.
셸은 _scene.py를 쓴다 — 같은 화면을 두 곳에서 그리면 하나는 틀어진다.
소유: 기획 세션. 산출물 design/dock.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS, BOXES, DOCK_NAME, OBS_FLOOR, DROP_FLOOR, record
from _fmt import tier
from _scene import make_scene, covered, app

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
ctx = make_scene(D)
ALL, STAGE = ctx["ALL"], ctx["STAGE"]

DESC = {
    "F0": ("현행", "no",
           "지도 아래를 <b>가로로 통째</b>로 덮는다. 세 줄을 늘 펼쳐 두므로 쓰지 않을 때도 자리를 차지한다. "
           "라벨 칸(<code>날짜·분위기·예산</code>)이 가로를 또 먹는다."),
    "F1": ("추천", "rec",
           "필요할 때만 펼친다. 평소엔 <b>알약 세 개</b>뿐이고 고른 값이 알약에 그대로 남는다"
           "(<code>문화 &times;</code>). 좌상단 단계바와 <b>대칭</b>이 된다 &mdash; "
           "왼쪽은 &lsquo;어디까지&rsquo;, 오른쪽은 &lsquo;무엇을&rsquo;. "
           "<b>아래 그림은 <code>분위기</code>를 펼친 상태</b>다."),
    "F2": ("", "",
           "지도에서 <b>완전히 치운다.</b> &lsquo;지도는 무대, 패널은 도구&rsquo; 원칙엔 가장 맞다. "
           "대신 <b>패널 밀도를 깎는다</b> &mdash; 방금 태그를 들어내 얻은 +27%를 도로 쓴다. "
           "히어로가 아래로 밀린 걸 보라."),
    "F3": ("", "",
           "늘 보이고 누르기 쉽다. 다만 <b>세로로 길게</b> 가려서 "
           "지도 왼쪽(우리 기준 서쪽·동남아 방향)이 통째로 막힌다."),
}

secs = ""
for k in ("F0", "F1", "F2", "F3"):
    badge, cls, desc = DESC[k]
    n = covered(ctx, BOXES[k])
    b = ('<span style="font-size:.6rem;font-weight:900;background:#F2603F;color:#fff;'
         'border-radius:4px;padding:2px 7px;vertical-align:3px">추천</span>' if cls == "rec"
         else '<span style="font-size:.6rem;font-weight:900;background:#6C7B78;color:#fff;'
              'border-radius:4px;padding:2px 7px;vertical-align:3px">현행</span>' if cls == "no" else "")
    color = "#1E7A50" if n == 0 else ("#F2603F" if n >= 4 else "#17201F")
    secs += ('<h2><span class="n">%s</span>%s %s</h2>'
             '<p class="note" style="margin-bottom:12px">%s<br>'
             '<b style="color:%s;font-size:1.02rem">가려지는 핀 %d곳</b> '
             '<span style="opacity:.6">/ 무대 %d곳</span></p>%s'
             % (k, DOCK_NAME[k], b, desc, color, n, len(STAGE), app(ctx, k)))

trs = ""
for k in ("F0", "F1", "F2", "F3"):
    n = covered(ctx, BOXES[k])
    w = "win" if k == "F1" else ""
    memo = {"F0": "늘 펼쳐져 있다", "F1": "쓸 때만 펼친다",
            "F2": "지도엔 없다 · <b>패널이 좁아진다</b>", "F3": "늘 펼쳐져 있다"}[k]
    trs += ('<tr><td><b>%s</b> &nbsp;%s</td><td class="num %s">%d곳</td>'
            '<td class="num">%s</td><td>%s</td></tr>'
            % (k, DOCK_NAME[k], w, n,
               "0%%" if not BOXES[k] else "%.0f%%" % (100.0 * n / len(STAGE)), memo))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 필터 도크 4안</title><style>" + CSS + "</style></head><body><div class=wrap>"
        "<h1>필터 도크 &mdash; <em>네 가지를 다 그렸다</em></h1>"
        "<p class=lede>네 안을 <b>각각 풀사이즈 홈 화면</b>으로 그렸다. 도크만 다르고 나머지는 같다. "
        "서울 출발 " + str(len(ALL)) + "건 중 &lsquo;조금 더 멀리&rsquo; 단계 " + str(len(STAGE)) + "곳이 실제 좌표다.<br>"
        "가려지는 <b>넓이</b>가 아니라 <b>핀 개수</b>로 쟀다 &mdash; 지도는 핀을 보여주려고 있다. "
        "<b>가려지는 핀은 회색</b>으로 뒀다.</p>"
        "<table><tr><th>안</th><th style='text-align:right'>가려지는 핀</th>"
        "<th style='text-align:right'>비율</th><th>메모</th></tr>" + trs + "</table>"
        + secs +
        "<h2><span class=n>왜</span>F1을 추천하나</h2>"
        "<div class=callout>현행(F0)이 별로인 이유는 <b>모양이 아니라 크기</b>다. "
        "세 줄을 늘 펼쳐 두느라 지도 아래를 통째로 덮고, 거기에 핀이 <b>" + str(covered(ctx, BOXES["F0"])) + "곳</b> 깔려 있다.<br>"
        "필터는 <b>가끔 쓰는 도구</b>다. 늘 펼쳐 둘 이유가 없다.</div>"
        "<ul class=k>"
        "<li><b>좌상단 단계바와 대칭이 된다.</b> 왼쪽은 &lsquo;어디까지 볼까&rsquo;, 오른쪽은 &lsquo;무엇을 볼까&rsquo; "
        "&mdash; 둘 다 지도를 다루는 손잡이라 같은 높이에 있는 게 맞다.</li>"
        "<li><b>고른 값이 알약에 남는다.</b> <code>문화 &times;</code>처럼 보이므로 펼치지 않아도 "
        "지금 뭘 걸었는지 안다. F0은 칩이 눌린 걸 보려면 도크를 들여다봐야 한다.</li>"
        "<li><b>패널 밀도를 안 깎는다.</b> F2는 원칙엔 맞지만 카드를 밀어낸다.</li>"
        "<li><b>모바일에서 같은 모양이 된다.</b> 알약 셋은 좁은 폭에서도 한 줄에 들어가고, "
        "팝오버는 그대로 <b>하단 시트</b>가 되면 된다 &mdash; 확장 상세와 같은 패턴이라 새로 배울 게 없다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>펼쳤을 때는 F1도 가린다.</b> 위 F1 그림은 <code>분위기</code>를 펼친 상태다. "
        "다만 <b>쓰는 순간에만</b>이고 닫으면 " + str(covered(ctx, BOXES["F1"])) + "곳으로 돌아온다.</p>"
        "<p class=foot>생성 <b>design/build_dock.py</b> &middot; 셸 <b>design/_app.py</b> &middot; "
        "데이터 <b>docs/data/deals.json</b> &middot; 확정 홈 <b>home.html</b> &middot; 스펙 <b>../SPEC.md</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "dock.html"), "w", encoding="utf-8").write(html)
print("dock.html  %.1fKB" % (len(html) / 1024.0))
for k in ("F0", "F1", "F2", "F3"):
    print("  %s %-18s 가려지는 핀 %2d / %d곳" % (k, DOCK_NAME[k], covered(ctx, BOXES[k]), len(STAGE)))
print("  신기록(obs>=%d) 표시 카드: %d건" % (OBS_FLOOR, sum(1 for d in ALL if not tier(d) and record(d))))
