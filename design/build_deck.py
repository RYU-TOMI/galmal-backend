# -*- coding: utf-8 -*-
"""갈래말래 기획·디자인 — 발표용 한 페이지.

지금까지 정한 것을 하나로 모은다. 목업은 _scene.py를 그대로 써서
다른 문서와 어긋나지 않게 한다. 숫자는 전부 실측이다.
소유: 기획 세션. 산출물 design/deck.html
"""
import json, io, os, sys, collections, math

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS as APP_CSS, OBS_FLOOR, DROP_FLOOR, record
from _fmt import TIERS, TOP, SUB, tier, direct, card_tags, money
from _scene import make_scene, app

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
N = len(deals)
ctx = make_scene(D)

# ── 실측 ───────────────────────────────────────────────────────
hubs = collections.Counter(d["o"] for d in deals)
SEL_N = hubs["SEL"]
n_stamp = sum(1 for d in deals if tier(d))
n_rec = sum(1 for d in deals if not tier(d) and record(d))
zero_disc = sum(1 for d in deals if d.get("discount", 0) == 0)
wc = collections.Counter(d.get("when", "") for d in deals)
unreach = wc.get("이번 달", 0) + sum(v for k, v in wc.items()
                                   if k not in ("이번 주말", "이번 주", "이번 달", "다음 달"))
tagn = collections.Counter(t for d in deals for t in d["tags"] if t in TOP)
cities = {}
for d in deals:
    cities[d["ko"]] = tuple(card_tags(d["tags"]))
uniq = len(set(cities.values()))
ps = sorted(d["price"] for d in deals)
over_slider = sum(1 for p in ps if p > 1000000) + sum(1 for p in ps if p < 100000)

CSS = APP_CSS + """
.deck{max-width:1280px;margin:0 auto;padding:0 26px 100px}
.cover{padding:78px 0 54px;border-bottom:1px solid var(--line);margin-bottom:8px}
.eyebrow{font-size:.72rem;font-weight:900;letter-spacing:.14em;color:var(--accent);
 text-transform:uppercase;margin-bottom:14px}
.cover h1{font-size:3.1rem;line-height:1.06;letter-spacing:-.045em;margin:0 0 16px}
.cover h1 em{font-style:normal;color:var(--accent)}
.cover p{font-size:1.06rem;color:var(--sub);max-width:640px;line-height:1.72;margin:0}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin-top:34px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px 18px;min-width:132px}
.kpi b{display:block;font-size:1.72rem;letter-spacing:-.04em;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi span{font-size:.72rem;color:var(--sub);font-weight:700}
.kpi.a b{color:var(--accent)}
.sec{padding:64px 0 0}
.sec>h2{font-size:1.62rem;letter-spacing:-.035em;margin:0 0 8px;display:block}
.sec>.lead{color:var(--sub);font-size:.98rem;line-height:1.72;max-width:720px;margin:0 0 26px}
.num{font-size:.7rem;font-weight:900;color:var(--accent);letter-spacing:.12em;margin-bottom:9px}
/* 문제 카드 */
.probs{display:flex;gap:14px;flex-wrap:wrap}
.prob{flex:1;min-width:290px;background:#fff;border:1px solid var(--line);border-radius:14px;
 padding:18px 19px;border-top:3px solid var(--accent)}
.prob .big{font-size:2.1rem;font-weight:900;letter-spacing:-.045em;line-height:1.05;
 color:var(--accent);font-variant-numeric:tabular-nums}
.prob .t{font-weight:800;font-size:.96rem;margin:8px 0 6px;letter-spacing:-.02em}
.prob .d{font-size:.83rem;color:var(--sub);line-height:1.66}
.prob .fix{margin-top:11px;padding-top:10px;border-top:1px dashed var(--line);
 font-size:.83rem;line-height:1.6}
.prob .fix b{color:#1E7A50}
/* 전후 */
.ba{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}
.ba div{flex:1;min-width:250px;border-radius:12px;padding:13px 15px;font-size:.86rem;line-height:1.65}
.ba .b4{background:#fff;border:1px solid var(--line);color:var(--sub)}
.ba .af{background:#F1F8F4;border:1px solid #C6E3D2}
.ba b{display:block;font-size:.7rem;font-weight:900;letter-spacing:.1em;margin-bottom:5px}
.ba .b4 b{color:var(--sub)}.ba .af b{color:#1E7A50}
/* 결정 표 */
table.dec{width:100%;border-collapse:collapse;font-size:.88rem;background:#fff;
 border:1px solid var(--line);border-radius:13px;overflow:hidden}
table.dec th{text-align:left;font-size:.72rem;color:var(--sub);font-weight:800;
 padding:12px 14px;background:var(--soft);border-bottom:1px solid var(--line)}
table.dec td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.6}
table.dec tr:last-child td{border-bottom:0}
table.dec td.w{white-space:nowrap;font-weight:800}
/* 방법 */
.hows{display:flex;gap:14px;flex-wrap:wrap}
.how{flex:1;min-width:280px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 19px}
.how .t{font-weight:800;font-size:.98rem;letter-spacing:-.02em;margin-bottom:7px}
.how .d{font-size:.85rem;color:var(--sub);line-height:1.7}
.how .d b{color:var(--ink)}
.how .ex{margin-top:10px;background:var(--soft);border-radius:9px;padding:9px 11px;
 font-size:.78rem;line-height:1.6;color:var(--sub)}
.how .ex b{color:var(--accent)}
/* 목업 프레임 */
.shot{margin-top:6px;overflow-x:auto;padding-bottom:6px}
.cap{font-size:.78rem;color:var(--sub);margin-top:11px;line-height:1.65}
.files{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.file{background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 12px;
 font-size:.76rem;font-weight:700;font-family:ui-monospace,Consolas,monospace}
.file b{color:var(--accent);font-family:inherit}
.left{display:flex;gap:12px;flex-wrap:wrap}
.lf{flex:1;min-width:250px;background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:14px 16px;font-size:.85rem;line-height:1.65}
.lf b{display:block;font-weight:800;margin-bottom:4px}
.lf span{color:var(--sub)}
.foot2{margin-top:70px;padding-top:20px;border-top:1px solid var(--line);
 font-size:.8rem;color:var(--sub);line-height:1.8}
"""

# ⚠️ KPI는 지어내지 않는다 — 파일에서 직접 센다.
_dec = io.open(os.path.join(BASE, "..", "DECISIONS.md"), encoding="utf-8").read()
N_DEC = sum(1 for ln in _dec.splitlines() if ln.startswith("## "))
import glob as _g
N_MOCK = len([f for f in _g.glob(os.path.join(BASE, "*.html"))
              if not f.endswith("deck.html")])

KPIS = [
    (str(N), "오늘의 딜", ""),
    (str(len(cities)), "목적지", ""),
    (str(len(hubs)), "출발 허브", ""),
    (str(N_DEC), "기록된 결정", "a"),
    (str(N_MOCK), "목업", "a"),
]

PROBS = [
    ("54%", "피드 절반이 근거 없는 말을 했다",
     "카드마다 <code>경유로 확 싸진 특가</code> 같은 훅이 붙었는데, "
     "<b><code>deals.json</code>에 직항 대비 가격이 없다.</b> "
     "뒷받침할 데이터가 없는 인과를 절반이 단언하고 있었다.",
     "훅 줄을 <b>자리째 없앴다.</b> 문구를 고치면 또 지어내게 된다."),
    ("100%", "모든 카드가 &lsquo;특가&rsquo; 도장을 달았다",
     "할인율 0%인 딜도 <code>특가 0%↓</code>를 달고 있었다. "
     "지금도 <b>" + str(zero_disc) + "건(" + "%.0f" % (100.0 * zero_disc / N) + "%)</b>이 할인율 0이다. "
     "<b>모두가 특별하면 아무도 특별하지 않다.</b>",
     "임계값 <b>15/28/42%</b>. 도장이 <b>" + str(n_stamp) + "건("
     + "%.0f" % (100.0 * n_stamp / N) + "%)</b>으로 줄었다."),
    ("61%", "필터가 딜의 절반을 못 좁혔다",
     "날짜 칩에 <code>이번 달</code>도 <code>그 이후</code>도 없어 "
     "<b>" + str(unreach) + "건</b>을 골라낼 수 없었다. 예산 슬라이더는 범위가 "
     "10만~100만인데 실제는 " + money(ps[0]) + "~" + money(ps[-1]) + "원이라 "
     "<b>" + str(over_slider) + "건이 아예 밖</b>이었다.",
     "칩을 <b>화면 라벨과 같은 말</b>로 맞추고, 예산은 <b>로그 히스토그램</b>으로."),
    ("1.8장", "모바일에서 카드를 비교할 수 없었다",
     "카드가 <b>가로로</b> 흘러 390px 화면에 1.8장만 보였다. "
     "발견 서비스에서 <b>비교가 안 되는</b> 건 치명적이다.",
     "지도가 배경, 카드는 <b>3단 시트</b>. 비중을 <b>사용자가</b> 정한다."),
]

DECISIONS = [
    ("지도", "거리 단계 3버튼", "<code>가까운 곳 / 조금 더 멀리 / 아주 멀리</code>. "
     "자유 줌·팬은 안 넣는다 &mdash; <b>정해주는 서비스라 뷰도 우리가 정한다.</b> "
     "이 결정이 나중에 모바일 시트 설계를 가능하게 했다"),
    ("지도", "far 뷰를 데이터에서 계산", "고정값을 박으면 딜이 바뀔 때마다 틀어진다. "
     "경도를 정렬해 <b>가장 큰 빈 구간</b>을 찾고 그 정반대를 중심으로 삼는다"),
    ("카드", "도장 3티어 15/28/42%", "테두리 → 채움 → 그라디언트+후광. "
     "<b>희소성이 곧 의미다</b> &mdash; 30일 이력으로 검증해 T3를 1.7%로 맞췄다"),
    ("카드", "&lsquo;왜 싼가&rsquo;를 한 번만 말한다", "도장 우선, 없고 신기록이면 <code>N일 최저</code>. "
     "재는 자가 달라도(평소 시세 vs 이전 최저) <b>사용자는 같은 말을 두 번 하는 걸로 읽는다</b>"),
    ("카드", "태그는 사진이 큰 자리에만", "작은 썸네일엔 안 넣는다. "
     "카드가 <b>129→103px</b>이 되고 패널에 <b>+27%</b> 더 들어간다"),
    ("카드", "날짜는 두 단 · 출발→도착", "<code>9/8(화) → 9/16(수)</code> / <code>8박9일 · 이번 주</code>. "
     "<b>요일을 넣는다</b> &mdash; 여행은 요일로 정한다"),
    ("전환", "상세는 지도 위, 지도가 미끄러져 간다", "카드를 누르면 지도가 그 핀으로 이동한 뒤 "
     "카드가 핀에서 피어난다. <b>움직임이 시선을 데려간다</b> &mdash; "
     "<code>prefers-reduced-motion</code>이면 전부 0ms"),
    ("필터", "검색 한 줄 + 날짜·예산 알약", "누르면 어휘가 다 펼쳐져 <b>모르는 사람은 고르고 아는 사람은 친다.</b> "
     "<b>도시 이름도 같은 칸</b>에서 찾는다"),
    ("필터", "건수를 누르기 전에 보인다", "<code>50만 이하 77곳</code>. "
     "지금은 걸고 나서야 안다 &mdash; <b>0곳이 될 칩을 누르게 두지 않는다</b>"),
    ("구조", "화면0을 없앤다", "서울 기본(딜의 55%) + 헤더에서 변경. "
     "<b>딜을 바로 보여주는 게 가장 좋은 제품 설명</b>이다"),
    ("구조", "패널 폭 380px 유지", "좁히면 지구가 +7%뿐인데 카드가 빡빡해지고, "
     "넓히면 <b>채울 글자가 없다.</b> <b>바꾸지 않는 것도 결정이다</b>"),
    ("모바일", "지도가 배경, 카드는 3단 시트", "peek 1장 / half 2.6장 / full 5.2장. "
     "<b>비중은 우리가 정할 문제가 아니다</b>"),
    ("접근성", "핀은 카드의 그림자다", "지도 SVG는 <code>role=\"img\"</code>, 개별 핀은 <code>aria-hidden</code>. "
     "<b>키보드 사용자에겐 피드가 곧 지도</b> &mdash; 같은 걸 두 번 훑게 하지 않는다"),
    ("신뢰", "말할 수 없는 건 말하지 않는다", "비교 막대가 없을 때 이유를 갈라 말한다 &mdash; "
     "<code>아직 모아두지 못했어요</code>(모름)와 <code>평소와 비슷해요</code>(알아봤는데 아님)는 다르다"),
]

HOWS = [
    ("실측이 없으면 결정하지 않는다",
     "모든 결정에 <b>오늘 데이터로 잰 숫자</b>를 붙였다. "
     "느낌으로 정한 게 하나도 없다.",
     "도크 위치를 &lsquo;넓이&rsquo;가 아니라 <b>가려지는 핀 개수</b>로 쟀다 &mdash; "
     "지도는 핀을 보여주려고 있으니까. 현행 <b>4곳</b>, 확정안 <b>0곳</b>."),
    ("재는 자를 고치기 전에 눈금을 옮기지 않는다",
     "도장 임계값을 <b>한 번 유지했다가 뒤집었다.</b> "
     "유지한 근거가 <b>잘못 잰 데이터</b>였기 때문이다.",
     "&lsquo;평소 시세&rsquo;가 김포·인천을 섞어 재고 있었다. 고치니 분포가 달라졌고 "
     "<b>그제서야</b> 눈금을 옮겼다."),
    ("바꾸지 않는 것도 결정이다",
     "패널 폭은 <b>재보고 그대로 뒀다.</b> "
     "가설(&lsquo;좁히면 글자가 잘린다&rsquo;)이 틀린 것도 그대로 적었다.",
     "320px에서도 <b>잘리는 카드 0건</b>이었다 &mdash; "
     "한글 서비스는 애초에 글자가 짧다. 그래서 지표를 바꿔 다시 쟀다."),
    ("셋이 서로를 고쳤다",
     "기획·프론트·백엔드가 <b>직접 메시지를 주고받으며</b> 서로의 틀린 값을 잡았다.",
     "내가 &lsquo;신기록&rsquo; 조건에서 <b>낙폭 5%를 빠뜨렸는데</b> 백엔드가 "
     "자기 코드와 대조해 찾아냈다. 안 잡혔으면 <b>0.8% 싼 것도 &lsquo;최저가&rsquo;</b>가 됐다."),
]

LEFT = [
    ("시즌 이벤트", "벚꽃·단풍·설경을 도시별 축제 일정으로. 10월 예정"),
    ("사진", "지금은 그라디언트 자리표시자다. 실제 도시 사진이 필요하다"),
    ("성능", "<code>index.html</code> 304KB. <b>병목을 재기 전엔 안 고친다</b>"),
    ("도시 검색", "&lsquo;다낭 얼마지?&rsquo;로 오는 사람. 필터가 아니라 검색 기능이라 따로 다룬다"),
]

kpi_html = "".join('<div class="kpi %s"><b>%s</b><span>%s</span></div>' % (c, v, l)
                   for v, l, c in KPIS)
prob_html = "".join('<div class="prob"><div class="big">%s</div><div class="t">%s</div>'
                    '<div class="d">%s</div><div class="fix">→ %s</div></div>'
                    % (b, t, d, f) for b, t, d, f in PROBS)
dec_html = "".join('<tr><td class="w">%s</td><td class="w">%s</td><td>%s</td></tr>'
                   % (a, b, c) for a, b, c in DECISIONS)
how_html = "".join('<div class="how"><div class="t">%s</div><div class="d">%s</div>'
                   '<div class="ex">%s</div></div>' % (t, d, e) for t, d, e in HOWS)
left_html = "".join('<div class="lf"><b>%s</b><span>%s</span></div>' % (t, d) for t, d in LEFT)

# 실제로 있는 파일만 적는다
FILES = [f for f in ["home", "open", "search", "filters", "budget", "mobile", "origin",
                     "dockbar", "dock", "density", "detail", "panel", "stages", "card",
                     "wireframe", "storyboard", "freshness", "feed_map"]
         if os.path.exists(os.path.join(BASE, f + ".html"))]
files_html = "".join('<span class="file">%s.html</span>' % f for f in FILES)

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 기획·디자인</title><style>" + CSS + "</style></head>"
        "<body><div class=deck>"

        "<div class=cover>"
        "<div class=eyebrow>기획 · 디자인 &nbsp;/&nbsp; 2026-09-01</div>"
        "<h1>어디 갈지 <em>정해주는</em><br>항공권 발견 서비스</h1>"
        "<p>검색창에 목적지를 넣는 서비스는 이미 많다. 우리는 반대다 &mdash; "
        "<b>목적지가 없는 사람</b>에게 오늘 싼 곳을 지도로 펼쳐 보인다. "
        "이 문서는 그 화면을 어떻게 정했는지, 그리고 <b>무엇을 근거로</b> 정했는지다.</p>"
        "<div class=kpis>" + kpi_html + "</div></div>"

        "<div class=sec><div class=num>01 &nbsp;문제</div>"
        "<h2>화면이 근거 없는 말을 하고 있었다</h2>"
        "<p class=lead>기존 화면을 실제 데이터로 훑었더니 <b>주장은 많은데 근거가 없었다.</b> "
        "네 가지가 컸다.</p>"
        "<div class=probs>" + prob_html + "</div></div>"

        "<div class=sec><div class=num>02 &nbsp;확정된 화면</div>"
        "<h2>발견 홈</h2>"
        "<p class=lead>서울 출발 <b>" + str(SEL_N) + "건</b> 중 &lsquo;조금 더 멀리&rsquo; 단계 "
        "<b>" + str(len(ctx["STAGE"])) + "곳</b>을 실제 좌표로 그렸다. "
        "빈 상자가 아니라 <b>오늘 진짜 딜</b>이다.</p>"
        "<div class=shot>" + app(ctx, "FIN") + "</div>"
        "<p class=cap><b>지도가 무대, 패널이 도구.</b> 카드를 누르면 지도가 그 핀으로 미끄러진 뒤 "
        "상세가 핀에서 피어난다. 아래 검색 한 줄에서 <b>분위기와 도시 이름을 같이</b> 찾고, "
        "날짜·예산은 값이 범위라 알약으로 뺐다.</p>"
        "<div class=files>" + files_html + "</div>"
        "<p class=cap>목업 " + str(len(FILES)) + "개. 전부 <code>docs/data/deals.json</code>으로 그렸고 "
        "<code>open.html</code>은 <b>눌러볼 수 있다</b>.</p></div>"

        "<div class=sec><div class=num>03 &nbsp;결정</div>"
        "<h2>정한 것과 그 이유</h2>"
        "<p class=lead><code>DECISIONS.md</code>에 <b>" + str(N_DEC) + "건</b>이 "
        "<b>기각한 대안까지</b> 기록돼 있다. 아래는 화면에 직접 드러나는 것만 추린 것이다.</p>"
        "<table class=dec><tr><th style='width:74px'>영역</th>"
        "<th style='width:210px'>결정</th><th>왜</th></tr>" + dec_html + "</table></div>"

        "<div class=sec><div class=num>04 &nbsp;방법</div>"
        "<h2>어떻게 정했나</h2>"
        "<p class=lead>결정 자체보다 <b>이 네 가지가 이 프로젝트의 방식</b>이다.</p>"
        "<div class=hows>" + how_html + "</div></div>"

        "<div class=sec><div class=num>05 &nbsp;전후</div>"
        "<h2>한 장의 카드</h2>"
        "<div class=ba>"
        "<div class=b4><b>전</b>훅 줄이 <code>경유로 확 싸진 특가</code>를 단언 · "
        "모든 카드에 <code>특가 0%↓</code> · 태그가 세로를 먹음 · "
        "날짜가 <code>2026-09-08</code>로 날것 · 높이 <b>129px</b></div>"
        "<div class=af><b>후</b>훅 줄 제거 · 도장은 <b>" + "%.0f" % (100.0 * n_stamp / N) + "%</b>만 · "
        "태그는 사진 위로 · <code>9/8(화) → 9/16(수)</code> · 높이 <b>103px</b> "
        "(패널에 <b>+27%</b>)</div></div></div>"

        "<div class=sec><div class=num>06 &nbsp;남은 것</div>"
        "<h2>아직 안 한 것</h2>"
        "<p class=lead>모르는 걸 아는 척하지 않는 게 이 프로젝트의 원칙이라, "
        "<b>남은 것도 적어 둔다.</b></p>"
        "<div class=left>" + left_html + "</div>"
        "<p class=cap style='margin-top:16px'>&#9888; <b>이 세션엔 브라우저가 없어 "
        "실제 렌더를 못 봤다.</b> 목업의 배치·움직임은 사람이 확인해야 한다. "
        "임계값도 <b>한 달 뒤 재측정 트리거</b>를 걸어 뒀다 &mdash; "
        "성숙 구간이 15일뿐이라 지금 값은 잠정이다.</p></div>"

        "<div class=foot2>"
        "<b>갈래말래</b> &mdash; 한국 출발 항공권 특가 발견 서비스<br>"
        "기획·디자인 세션 &middot; 2026-09-01 &middot; 데이터 <code>updated "
        + D.get("updated", "") + "</code><br>"
        "문서 <code>SPEC.md</code> · <code>DECISIONS.md</code> · <code>COPY.md</code> · "
        "<code>CONTRACT.md</code> · <code>IA.md</code> · <code>FLOWS.md</code> &middot; "
        "목업 <code>design/</code>"
        "</div></div></body></html>")

io.open(os.path.join(BASE, "deck.html"), "w", encoding="utf-8").write(html)
print("deck.html  %.1fKB" % (len(html) / 1024.0))
print("  deals %d · cities %d · stamp %d · rec %d" % (N, len(cities), n_stamp, n_rec))
print("  DECISIONS.md %d개 · 표에 실은 것 %d · 목업 %d" % (N_DEC, len(DECISIONS), len(FILES)))
