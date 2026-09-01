# -*- coding: utf-8 -*-
"""아래 바 재설계 — 위치는 그대로, 크기와 조작을 바꾼다.

사용자 판단(2026-09-01): "위치는 F0가 맞는데 크기랑 디자인이 별로다.
분위기를 다 나열해놓고 클릭 말고 검색이나 토글도 괜찮겠다."

셸은 _scene.py를 쓴다. 각 안을 풀사이즈 홈 화면으로 그린다.
소유: 기획 세션. 산출물 design/dockbar.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS, BOXES, DOCK_NAME, DOCK_H, MOODS_N
from _scene import make_scene, covered, app

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
ctx = make_scene(D)
ALL, STAGE = ctx["ALL"], ctx["STAGE"]

KINDS = ["G0", "G1", "G2", "G3"]

DESC = {
    "G0": ("현행", "no",
           "날짜·분위기·예산 <b>세 줄을 늘 펼쳐 둔다.</b> 분위기 6개가 전부 나열돼 있고, "
           "라벨 칸(<code>날짜·분위기·예산</code>)이 가로를 또 먹는다. "
           "쓰지 않을 때도 <b>90px</b>을 차지한다."),
    "G1": ("추천", "rec",
           "<b>알약 셋</b>만 남기고 나머지는 눌렀을 때 위로 펼친다. 고른 값이 알약에 그대로 남아"
           "(<code>문화 &times;</code>) 펼치지 않아도 뭘 걸었는지 안다. "
           "<b>90 &rarr; 44px.</b> 오른쪽에 결과 수를 둬서 필터가 <b>무슨 일을 했는지</b> 바로 보인다. "
           "<b>아래 그림은 분위기를 펼친 상태</b>다."),
    "G2": ("", "",
           "<b>검색 한 줄</b>이 주인공이다. 고른 건 입력창 안에 <b>토큰</b>으로 들어가고, "
           "타이핑하면 어휘가 위로 뜬다(그림은 그 상태). 날짜·예산만 알약으로 옆에 둔다.<br>"
           "분위기와 <b>도시 이름을 같은 칸에서</b> 찾을 수 있는 게 진짜 이득이다."),
    "G3": ("", "",
           "G2를 <b>한 줄에 눌러 담았다.</b> 검색창을 좁히고 토큰을 밖으로 뺐다. "
           "가장 작지만(44px) 검색창이 좁아 <b>플레이스홀더로 예시를 못 보여준다</b> &mdash; "
           "무엇을 칠 수 있는지 알기 어렵다."),
}

secs = ""
for k in KINDS:
    badge, cls, desc = DESC[k]
    n = covered(ctx, BOXES[k])
    b = ('<span style="font-size:.6rem;font-weight:900;background:#F2603F;color:#fff;'
         'border-radius:4px;padding:2px 7px;vertical-align:3px">추천</span>' if cls == "rec"
         else '<span style="font-size:.6rem;font-weight:900;background:#6C7B78;color:#fff;'
              'border-radius:4px;padding:2px 7px;vertical-align:3px">현행</span>' if cls == "no" else "")
    color = "#1E7A50" if n == 0 else ("#F2603F" if n >= 4 else "#17201F")
    secs += ('<h2><span class="n">%s</span>%s %s</h2>'
             '<p class="note" style="margin-bottom:12px">%s<br>'
             '<b style="font-size:1.02rem">높이 %dpx</b> '
             '<span style="opacity:.5">|</span> '
             '<b style="color:%s;font-size:1.02rem">가려지는 핀 %d곳</b> '
             '<span style="opacity:.6">/ 무대 %d곳</span></p>%s'
             % (k, DOCK_NAME[k], b, desc, DOCK_H[k], color, n, len(STAGE), app(ctx, k)))

trs = ""
for k in KINDS:
    n = covered(ctx, BOXES[k])
    w = "win" if k == "G1" else ""
    memo = {"G0": "분위기 6개를 늘 나열한다",
            "G1": "누르면 펼친다 · 고른 값이 알약에 남는다",
            "G2": "타이핑으로 찾는다 · <b>도시 이름도 같이</b>",
            "G3": "가장 작다 · 예시를 못 보여준다"}[k]
    trs += ('<tr><td><b>%s</b> &nbsp;%s</td><td class="num %s">%dpx</td>'
            '<td class="num %s">%d곳</td><td>%s</td></tr>'
            % (k, DOCK_NAME[k], w, DOCK_H[k], w, n, memo))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 아래 바 재설계</title><style>" + CSS + "</style></head><body><div class=wrap>"
        "<h1>아래 바 &mdash; <em>작게, 다 나열하지 않고</em></h1>"
        "<p class=lede><b>위치는 그대로 아래</b>다. 바꾸는 건 <b>크기</b>와 <b>조작</b> 둘이다 &mdash; "
        "지금은 분위기 6개를 전부 펼쳐 두고 90px을 쓴다.<br>"
        "네 안을 각각 풀사이즈 홈으로 그렸다. 서울 출발 " + str(len(ALL)) + "건 중 "
        "&lsquo;조금 더 멀리&rsquo; 단계 " + str(len(STAGE)) + "곳이 실제 좌표이고, "
        "<b>가려지는 핀은 회색</b>이다.</p>"
        "<table><tr><th>안</th><th style='text-align:right'>높이</th>"
        "<th style='text-align:right'>가려지는 핀</th><th>조작</th></tr>" + trs + "</table>"
        + secs +
        "<h2><span class=n>왜</span>G1을 추천하나</h2>"
        "<div class=callout>고친 건 <b>모양이 아니라 &lsquo;늘 펼쳐 둔다&rsquo;는 전제</b>다.<br>"
        "필터는 가끔 쓰는 도구인데 분위기 6개를 항상 보여줄 이유가 없다. "
        "<b>90 &rarr; 44px</b>이면 가려지는 핀이 <b>" + str(covered(ctx, BOXES["G0"])) + "곳 &rarr; "
        + str(covered(ctx, BOXES["G1"])) + "곳</b>이 된다.</div>"
        "<ul class=k>"
        "<li><b>고른 값이 알약에 남는다.</b> <code>문화 &times;</code>가 그대로 보이므로 "
        "펼치지 않아도 지금 뭘 걸었는지 안다. 현행은 칩이 눌린 걸 보려면 도크를 들여다봐야 한다.</li>"
        "<li><b>결과 수를 오른쪽에 둔다.</b> <code>56곳</code> &mdash; 필터가 무슨 일을 했는지 "
        "바로 보인다. 지금은 필터를 걸어도 몇 곳이 남았는지 피드를 세어야 안다.</li>"
        "<li><b>검색(G2)이 매력적이지만 이 제품엔 이르다.</b> 우리는 "
        "<b>목적지를 정해주는</b> 서비스다 &mdash; 검색창은 &lsquo;무엇을 찾을지 아는 사람&rsquo;의 도구이고, "
        "우리 사용자는 <b>그걸 모르는 채로 온다.</b> 어휘가 6개뿐이라 타이핑이 클릭보다 느리기도 하다.</li>"
        "<li><b>다만 G2의 진짜 이득은 따로 있다</b> &mdash; <b>도시 이름을 같은 칸에서 찾는 것.</b> "
        "&lsquo;다낭 얼마지?&rsquo;라는 사람은 지금 갈 곳이 없다. "
        "그건 <b>필터가 아니라 검색 기능</b>이라 따로 다룰 안건으로 남긴다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>펼쳤을 때는 G1도 가린다.</b> 위 G1 그림은 분위기를 펼친 상태다. "
        "닫으면 " + str(covered(ctx, BOXES["G1"])) + "곳으로 돌아온다. "
        "<b>모바일에서는</b> 알약 셋이 한 줄에 들어가고 팝오버가 그대로 하단 시트가 된다 &mdash; "
        "확장 상세와 같은 패턴이라 새로 배울 게 없다.</p>"
        "<p class=note>분위기별 딜 수(실측): "
        + " &middot; ".join("<b>%s</b> %d곳" % (k, v) for k, v in MOODS_N.items()) + "</p>"
        "<p class=foot>생성 <b>design/build_dockbar.py</b> &middot; 셸 <b>design/_scene.py</b> &middot; "
        "데이터 <b>docs/data/deals.json</b> &middot; 위치 비교 <b>dock.html</b> &middot; "
        "확정 홈 <b>home.html</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "dockbar.html"), "w", encoding="utf-8").write(html)
print("dockbar.html  %.1fKB" % (len(html) / 1024.0))
for k in KINDS:
    # cp949 콘솔에서 em-dash가 깨지므로 이름은 빼고 숫자만 찍는다
    print("  %s  %3dpx  covered %d / %d" % (k, DOCK_H[k], covered(ctx, BOXES[k]), len(STAGE)))
