# -*- coding: utf-8 -*-
"""카드 밀도 비교 — "패널에 몇 장 보이나".

실제 deals.json(서울 출발)로 그린다. 카드 높이는 CSS 값에서 산술로 계산해 표에 근거를 남긴다.
소유: 기획 세션. 산출물 design/density.html
"""
import json, io, os
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))

TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {"리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
       "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포", "사원", "유적", "고성", "미술관"}
# 임계값은 _fmt.py 한 곳에만 둔다 — 여기서 다시 적으면 갈라진다(2026-09-01)
from _fmt import TIERS


def tier(d):
    v = d.get("discount", 0)
    for lo, t in TIERS:
        if v >= lo:
            return t
    return None


def direct(d):
    """직항 배지는 중·장거리에만. 근거리 직항은 당연해서 배지가 아니다."""
    return d["transfers"] == 0 and d["haul"] != "short"


def card_tags(tags):
    s = [t for t in tags if t in SUB]
    tp = [t for t in tags if t in TOP]
    return (s + tp[:1] if s else tp[:2])[:4]


deals = [x for x in D["deals"] if x["o"] == "SEL"]
deals.sort(key=lambda x: x["price"])

# ── 높이 산술 (root 16px) ─────────────────────────────────────
def px(rem, lh=1.25):
    return rem * 16 * lh

ROW_CITY = px(.98)                  # 도시명 줄
ROW_PRICE = px(1.18, 1.2) + 2       # 가격 줄 + margin
ROW_DMAIN = px(.72, 1.3) + 5        # 날짜 주 라인 + margin
ROW_DSUB = px(.64, 1.3) + 2         # 날짜 보조 라인 + margin
ROW_TAGS = px(.58, 1.3) + 6 + 8     # 태그(패딩·테두리) + margin
# 날짜와 태그를 한 줄에 놓으면 둘 중 큰 쪽이 줄 높이를 정한다
ROW_DATETAG = max(px(.72, 1.3), px(.58, 1.3) + 6) + 8
PAD = 10 * 2 + 1.5 * 2              # 카드 패딩 + 테두리

PANEL_H, GAP, HERO_H, SORTBAR = 700, 9, 236, 44

VARIANTS = [
    ("D0", "지금 확정한 카드", [ROW_CITY, ROW_PRICE, ROW_DMAIN, ROW_DSUB, ROW_TAGS], 62,
     "훅 줄은 이미 뺐다(F18). 남은 다섯 줄은 전부 일을 한다.", ""),
    ("D1", "날짜를 한 줄로", [ROW_CITY, ROW_PRICE, ROW_DMAIN, ROW_TAGS], 62,
     "두 단의 이득은 <b>위계</b>지 줄 수가 아니다. 색·굵기·자릿수 정렬로 같은 위계를 한 줄에 낸다.", "dsub"),
    ("D2", "태그를 사진 위로", [ROW_CITY, ROW_PRICE, ROW_DMAIN, ROW_DSUB], 62,
     "태그가 <b>세로를 안 먹는다.</b> 작은 썸네일엔 아예 안 넣고, "
     "히어로처럼 <b>사진이 큰 자리에만</b> 얹는다.", "tagover"),
    ("D3", "둘 다", [ROW_CITY, ROW_PRICE, ROW_DMAIN], 62,
     "D1 + D2. 정보는 거의 그대로인데 세로만 줄었다.", "both"),
    ("D4", "한 줄 리스트", [ROW_PRICE, ROW_DMAIN], 40,
     "도시명과 가격을 <b>같은 줄</b>에. 사진이 40px으로 작아지고 태그·도장이 사라진다.", "list"),
    ("D5", "날짜 옆에 태그", [ROW_CITY, ROW_PRICE, ROW_DATETAG], 62,
     "날짜를 한 줄로 줄이고, <b>비는 오른쪽에 태그를 앉힌다.</b> "
     "태그 개수가 그대로라 &lsquo;즐길 게 많다&rsquo;는 신호가 남는다.", "datetag"),
]
RECOMMEND = "D2"   # 2026-09-01 사용자 확정


def card_h(rows, thumb):
    return int(round(max(sum(rows), thumb) + PAD))


def fits(h):
    room = PANEL_H - SORTBAR - HERO_H - GAP
    return (room + GAP) / float(h + GAP)


CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:var(--sea)}
.wrap{max-width:1400px;margin:0 auto;padding:44px 30px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 34px;max-width:780px;line-height:1.75}
h2{font-size:1.12rem;margin:52px 0 8px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 20px;max-width:860px}
.cols{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.col{width:392px}
.chead{display:flex;align-items:baseline;gap:8px}
.cid{font-size:.66rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.cnm{font-weight:800;font-size:.94rem}
.cdesc{color:var(--sub);font-size:.78rem;line-height:1.6;min-height:46px;margin:5px 0 9px}
.metric{display:flex;gap:7px;margin-bottom:9px}
.mt{flex:1;background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 9px;text-align:center}
.mt b{display:block;font-size:1.16rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums;line-height:1.2}
.mt b small{font-size:.58rem;font-weight:700;color:var(--sub)}
.mt span{font-size:.62rem;color:var(--sub);font-weight:700}
.mt.win{border-color:var(--accent);background:#FFF6F3}
.mt.win b{color:var(--accent)}
.panel{width:380px;height:700px;background:var(--sea);border:1px solid var(--line);
 border-radius:14px;overflow:hidden;position:relative;padding:0 10px}
.sortbar{height:44px;display:flex;align-items:center;gap:6px;font-size:.62rem}
.spill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:4px 10px;font-weight:800;color:var(--sub)}
.spill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.feed{display:flex;flex-direction:column;gap:9px}
.fcard{display:flex;gap:11px;background:#fff;border:1.5px solid var(--line);
 border-radius:13px;padding:10px;overflow:hidden}
.thumb{flex:none;border-radius:10px;position:relative;overflow:hidden;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center}
.frow{display:flex;justify-content:space-between;align-items:center;gap:6px}
.fcity{font-size:.98rem;font-weight:900;letter-spacing:-.02em;line-height:1.25;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:2px}
.price{font-weight:900;font-size:1.18rem;line-height:1.2;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.6em;font-weight:700;color:var(--sub);margin-left:2px}
.dmain{font-size:.72rem;line-height:1.3;font-weight:800;margin-top:5px;font-variant-numeric:tabular-nums}
.dsub{font-size:.64rem;line-height:1.3;font-weight:700;color:var(--sub);margin-top:2px;font-variant-numeric:tabular-nums}
.wk{color:var(--sub);font-weight:700}
.tags{display:flex;gap:4px;margin-top:8px;flex-wrap:nowrap;overflow:hidden}
.dtrow{display:flex;align-items:center;justify-content:space-between;gap:8px;
 margin-top:8px;min-width:0;overflow:hidden}
.dtrow .dmain{margin-top:0;flex:none}
.dtrow .tags{margin-top:0;flex:0 1 auto;justify-content:flex-end}
.rec{font-size:.56rem;font-weight:900;background:var(--accent);color:#fff;
 border-radius:4px;padding:2px 6px;margin-left:2px;vertical-align:2px}
.tag{font-size:.58rem;line-height:1.3;background:transparent;border:1px solid var(--line);
 border-radius:5px;padding:2px 7px;color:var(--sub);font-weight:700;white-space:nowrap}
.bdg{font-size:.6rem;font-weight:800;border-radius:99px;padding:2px 9px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:4px}
.stamp.t1{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-size:.54rem;padding:1px 5px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.6rem;padding:2px 7px}
.stamp.t3{transform:rotate(-9deg);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.62rem;padding:2px 8px;box-shadow:0 0 0 2px #fff,0 0 0 4px rgba(242,96,63,.2)}
.phtags{position:absolute;left:6px;right:6px;bottom:6px;display:flex;gap:3px;flex-wrap:wrap}
.ovtag{font-size:.52rem;font-weight:800;color:#fff;background:rgba(6,20,18,.5);
 border-radius:4px;padding:1px 6px;white-space:nowrap}
.hero{flex-direction:column;gap:0}
.pick{position:absolute;left:8px;top:8px;background:#fff;color:var(--accent);font-weight:900;
 font-size:.6rem;padding:2px 7px;border-radius:99px}
.cut{position:absolute;left:0;right:0;bottom:0;height:86px;pointer-events:none;
 background:linear-gradient(transparent,var(--sea) 62%)}
.fade{position:absolute;left:10px;right:10px;bottom:9px;text-align:center;font-size:.62rem;
 color:var(--sub);font-weight:800}
table{width:100%;border-collapse:collapse;font-size:.86rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.win{color:var(--accent);font-weight:900}
.callout{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:10px;padding:16px 18px;margin:20px 0;font-size:.92rem;line-height:1.8;max-width:880px}
.callout b{color:var(--accent)}
ul.k{margin:12px 0 0;padding-left:19px;color:var(--sub);font-size:.89rem;max-width:880px}
ul.k li{margin:8px 0}ul.k b{color:var(--ink)}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
"""


def money(v):
    return "{:,}".format(v)


def render_card(d, v, hero=False):
    vid = v[5]
    t = tier(d)
    tg = card_tags(d["tags"])
    thumb_px = v[3]
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    # 2026-09-01 확정: 사진 위 태그는 "큰 사진"에만. 작은 썸네일엔 태그를 안 넣는다.
    ov = ("" if not (vid in ("tagover", "both") and tg and hero)
          else '<div class="phtags">%s</div>'
               % "".join('<span class="ovtag">%s</span>' % x for x in tg[:4]))

    if hero:
        th = ('<div class="thumb" style="width:100%%;height:104px;margin-bottom:9px">'
              '<span class="pick">오늘의 발견</span>%s</div>' % ov)
    else:
        th = '<div class="thumb" style="width:%dpx;height:%dpx">%s</div>' % (thumb_px, thumb_px, ov)

    if vid == "list":
        body = ('<div class="prow"><span class="fcity">%s</span>'
                '<span class="price">%s<small>원</small></span></div>'
                '<div class="dmain">%s <span class="wk">&middot; %s</span></div>'
                % (d["ko"], money(d["price"]), d["dep"], d.get("nights", "")))
    else:
        rows = ['<div class="frow"><span class="fcity">%s</span>%s</div>' % (d["ko"], stamp)]
        rows.append('<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
                    % (money(d["price"]), bdg))
        if vid == "datetag":
            rows.append('<div class="dtrow"><span class="dmain">%s <span class="wk">&middot; %s</span></span>'
                        '<span class="tags">%s</span></div>'
                        % (d["dep"], d.get("nights", ""),
                           "".join('<span class="tag">%s</span>' % x for x in tg)))
        elif vid in ("dsub", "both"):
            rows.append('<div class="dmain">%s <span class="wk">&middot; %s &middot; %s</span></div>'
                        % (d["dep"], d.get("nights", ""), d["when"]))
        else:
            rows.append('<div class="dmain">%s</div><div class="dsub">%s &middot; %s</div>'
                        % (d["dep"], d.get("nights", ""), d["when"]))
        if vid not in ("tagover", "both", "datetag"):
            rows.append('<div class="tags">%s</div>'
                        % "".join('<span class="tag">%s</span>' % x for x in tg))
        body = "".join(rows)

    return '<div class="%s">%s<div class="fbody">%s</div></div>' % (
        "fcard hero" if hero else "fcard", th, body)


base_h = card_h(VARIANTS[0][2], VARIANTS[0][3])
cols = []
for v in VARIANTS:
    vid, name, rows, thumb, desc, _ = v
    h = card_h(rows, thumb)
    n = fits(h)
    cards = [render_card(deals[0], v, hero=True)]
    cards += [render_card(d, v) for d in deals[1:10]]
    win = " win" if vid == RECOMMEND else ""
    rec = '<span class="rec">추천</span>' if vid == RECOMMEND else ""
    cols.append(
        '<div class="col"><div class="chead"><span class="cid">%s</span>'
        '<span class="cnm">%s</span>%s</div><div class="cdesc">%s</div>'
        '<div class="metric">'
        '<div class="mt"><b>%d<small>px</small></b><span>카드 높이</span></div>'
        '<div class="mt%s"><b>%.1f</b><span>히어로 아래 장수</span></div></div>'
        '<div class="panel"><div class="sortbar">'
        '<span class="spill on">가성비순</span><span class="spill">임박순</span>'
        '<span class="spill">할인율순</span></div>'
        '<div class="feed">%s</div><div class="cut"></div>'
        '<div class="fade">&darr; 스크롤</div></div></div>'
        % (vid, name, rec, desc, h, win, n, "".join(cards)))

trs = []
for v in VARIANTS:
    vid, name, rows, thumb, _, _ = v
    h = card_h(rows, thumb)
    n = fits(h)
    delta = h - base_h
    cls = "win" if vid == RECOMMEND else ""
    trs.append('<tr><td><b>%s</b> &nbsp;%s</td><td class="num">%d</td>'
               '<td class="num">%s</td><td class="num %s">%.1f장</td>'
               '<td class="num %s">%s</td></tr>'
               % (vid, name, h, "&mdash;" if delta == 0 else "%+d" % delta,
                  cls, n, cls,
                  "기준" if delta == 0 else "%+.0f%%" % (100 * (n / fits(base_h) - 1))))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 카드 밀도</title><style>" + CSS + "</style></head><body><div class=wrap>"
    "<h1>카드 밀도 — <em>몇 장 보이나</em></h1>"
    "<p class=lede>패널 <b>380&times;700</b>에 서울 출발 실제 딜을 그렸다. "
    "카드 높이는 CSS 값에서 산술로 계산했고 &sect;02에 근거를 남겼다. "
    "<b>히어로 카드(오늘의 발견)는 다섯 안 모두 같게 뒀다</b> &mdash; 줄이는 건 그 아래다.</p>"
    "<h2><span class=n>01</span>후보</h2>"
    "<div class=cols>" + "".join(cols) + "</div>"
    "<h2><span class=n>02</span>숫자</h2>"
    "<table><tr><th>안</th><th style='text-align:right'>카드 높이</th>"
    "<th style='text-align:right'>차이</th><th style='text-align:right'>히어로 아래</th>"
    "<th style='text-align:right'>증가</th></tr>" + "".join(trs) + "</table>"
    "<p class=note>패널 700px &mdash; 정렬바 44 + 히어로 236 + 간격 9 = <b>남는 높이 411px</b>. "
    "카드 사이 간격 9px. 히어로까지 세면 각 안에 1장을 더한다.</p>"
    "<h2><span class=n>03</span>무엇을 재는가</h2>"
    "<div class=callout>&ldquo;많이 보여주는 게 좋다&rdquo;는 <b>반만 맞다.</b><br>"
    "이 서비스는 <b>정해주는</b> 것이다. 히어로 카드는 &lsquo;오늘은 이거&rsquo;라는 답이라 크게 남긴다.<br>"
    "그 아래는 <b>둘러보는 자리</b>다. 여기선 밀도가 곧 이득이다 &mdash; "
    "3장은 &lsquo;목록&rsquo;으로 안 읽히고, 스크롤을 해야 비교가 시작된다.</div>"
    "<ul class=k>"
    "<li><b>훅 줄은 이미 뺐다</b>(F18). 지금 남은 다섯 줄은 전부 일을 한다 &mdash; "
    "그래서 더 줄이려면 <b>무언가를 정말 포기</b>해야 한다.</li>"
    "<li><b>날짜 두 단의 이득은 &lsquo;위계&rsquo;지 &lsquo;줄 수&rsquo;가 아니다.</b> "
    "색&middot;굵기&middot;자릿수 정렬로 같은 위계를 한 줄에 낼 수 있다(D1). 잃는 건 거의 없다.</li>"
    "<li><b>태그를 사진 위로 올리면</b> 세로를 안 먹는다(D2). 대신 62px 썸네일엔 <b>1개만</b> 들어간다 &mdash; "
    "작은 카드에선 &lsquo;태그 개수 = 즐길 거리&rsquo; 신호를 <b>스크롤 중에 못 읽는다.</b> 그 신호는 <b>히어로와 확장 상세에서만</b> 살아 있다.</li>"
    "<li><b>D4는 잃는 게 크다.</b> 태그와 도장이 사라지면 &lsquo;왜 여기인가&rsquo;와 &lsquo;얼마나 싼가&rsquo;를 "
    "카드에서 못 읽는다. 발견 서비스에서 그건 가격보다 중요할 수 있다.</li>"
    "<li><b>D5가 답이다.</b> 날짜를 한 줄로 줄이면 그 줄 오른쪽이 <b>통째로 빈다.</b> "
    "거기에 태그를 앉히면 태그 줄 하나가 통째로 사라지는데 <b>태그 개수는 그대로다.</b> "
    "포기하는 게 없다.</li>"
    "</ul>"
    "<div class=callout style='border-left-color:#2E7D74'>"
    "<b style='color:#2E7D74'>D2로 확정</b>(2026-09-01). 129px &rarr; <b>103px</b>(&minus;20%), "
    "히어로 아래 3.0장 &rarr; <b>3.8장</b>(+27%).<br>"
    "규칙은 <b>&lsquo;사진이 큰 자리에만 사진 위 태그&rsquo;</b>다 &mdash; "
    "작은 썸네일(62px)은 태그를 담기엔 작아서 아예 넣지 않고, "
    "히어로&middot;확장 상세처럼 사진이 전폭인 자리에만 얹는다. "
    "날짜 두 단은 <b>그대로 남긴다</b>(가독성 때문에 바꾼 것이라).<br>"
    "<b>잃는 것</b> &mdash; 작은 카드에선 &lsquo;태그 개수 = 즐길 거리&rsquo; 신호를 못 읽는다. "
    "그 신호는 히어로와 상세에 남는다. 상세 설계는 <b>detail.html</b>.</div>"
    "<p class=foot>생성 <b>design/build_density.py</b> &middot; 데이터 <b>docs/data/deals.json</b>"
    "(서울 " + str(len(deals)) + "건) &middot; 확정 스펙 <b>../SPEC.md</b> &sect;CH3</p>"
    "</div></body></html>")

out = os.path.join(BASE, "density.html")
io.open(out, "w", encoding="utf-8").write(html)
print("density.html  %.1fKB  (서울 %d건)" % (len(html) / 1024.0, len(deals)))
for v in VARIANTS:
    h = card_h(v[2], v[3])
    print("  %s %-14s %3dpx   히어로 아래 %.1f장" % (v[0], v[1], h, fits(h)))
