# -*- coding: utf-8 -*-
"""design/card.html 생성 — 카드 구조 변경 전/후 (PH3: F17·F18·F19).

커밋된 deals.json의 실제 딜로 그린다. 더미 데이터 없음.

    python design/build_card.py
"""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "design" / "card.html"
D = json.loads((ROOT / "docs/data/deals.json").read_text(encoding="utf-8"))

WD = ["월", "화", "수", "목", "금", "토", "일"]
STAMP_MIN = 15
TIERS = [(35, "t3"), (25, "t2"), (15, "t1")]   # 할인 도장 티어 (내림차순)
GRAD = {"해변": "linear-gradient(135deg,#8fd0e0,#2a6f8f)", "도시": "linear-gradient(135deg,#ff9a76,#c6472a)",
        "미식": "linear-gradient(135deg,#f2603f,#7a2e18)", "자연": "linear-gradient(135deg,#a8e0c0,#2a8f6c)",
        "문화": "linear-gradient(135deg,#ffcf9a,#c6652a)", "온천": "linear-gradient(135deg,#ffc07a,#e0782f)"}
CHIPS = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUBTAG = ["리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
          "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포",
          "사원", "유적", "고성", "미술관"]


def md(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.month}/{d.day}({WD[d.weekday()]})"


def transit(d):
    return "직항" if d["transfers"] == 0 else f"경유 {d['transfers']}회"


def tier(d):
    """할인 도장 티어. 임계값 미만이면 None(도장 없음)."""
    v = d.get("discount", 0)
    for lo, t in TIERS:
        if v >= lo:
            return t
    return None


def direct_badge(d):
    """직항 배지는 중·장거리에만. 근거리 직항은 75%라 당연해서 배지가 아니다."""
    return d["transfers"] == 0 and d["haul"] != "short"


def old_why(d):
    """폐기된 whyOf() — 비교용으로만 재현한다."""
    if d.get("discount", 0) >= 25:
        return f"평소보다 {d['discount']}%↓"
    if d["transfers"] > 0:
        return "경유로 확 싸진 특가"
    if d["when"] == "이번 주말":
        return "이번 주말 바로 출발"
    if d.get("discount", 0) > 0:
        return f"최근 {d['discount']}%↓ · {d['when']}"
    return f"{d['when']} 최저가"


def pick(o="SEL"):
    """네 가지 경우를 다 보여준다 — 도장/배지가 붙고 안 붙는 조합."""
    ds = [x for x in D["deals"] if x["o"] == o]
    hi = max(ds, key=lambda x: (x.get("discount", 0), -x["price"]))
    ml = next((x for x in ds if direct_badge(x) and x.get("discount", 0) < STAMP_MIN), None)
    sh = next((x for x in ds if x["transfers"] == 0 and x["haul"] == "short"
               and x.get("discount", 0) < STAMP_MIN), None)
    lo = next(x for x in ds if x["transfers"] > 0 and x.get("discount", 0) == 0)
    out = [(f"도장 {tier(hi).upper()} · 할인 {hi['discount']}%", hi)]
    if ml:
        out.append(("직항 배지 · 중·장거리 직항", ml))
    if sh:
        out.append(("배지 없음 · 근거리 직항", sh))
    out.append(("배지 없음 · 경유", lo))
    return out


def card(d, new, hero=False):
    if new:
        subs = [t for t in d.get("tags", []) if t in SUBTAG]
        tops = [t for t in d.get("tags", []) if t in CHIPS]
        tags = (subs + tops[:1] if subs else tops[:2])[:4]
    else:
        tags = d.get("tags", [])[:3]
    g = next((GRAD[t] for t in d.get("tags", []) if t in GRAD), "linear-gradient(135deg,#ffb89a,#c6502a)")
    disc = d.get("discount", 0)
    stamp = ""
    if new:
        t = tier(d)
        if t:
            stamp = f'<span class="stamp {t}">평소보다 {disc}%↓</span>'
    else:
        stamp = f'<span class="stamp t1">특가 {disc}%↓</span>'
    date = f'{md(d["dep"])}~{md(d["ret"])}' if d.get("ret") else md(d["dep"])
    nights = d.get("nights", "")
    if new:
        line = (f'<span class="wpill n">{d["when"]}</span>'
                f'<span class="dmain">{nights}</span>'
                f'<span class="dsub">{date}</span>')
    else:
        line = f'<span class="wpill">{d["when"]}</span><span class="dline">{date}'
        line += f' · {nights}</span>' if nights else '</span>'
    trans = ""
    if new:
        if direct_badge(d):
            trans = '<span class="bdg"><span class="pl">✈</span>직항</span>'
        else:
            trans = f'<span class="trtxt">{transit(d)}</span>'
    hook = "" if new else f'<div class="hook">{old_why(d)}</div>'
    badge = '<span class="pick">진짜 갈래말래?</span>' if hero else ""
    return f'''<div class="card">
      <div class="thumb" style="background:{g}">{badge}<span class="ph">사진 준비중</span></div>
      <div class="body">
        <div class="top"><div><div class="city">{d["ko"]}</div>
          <div class="when">{line}</div></div>{stamp}</div>
        <div class="prow"><div class="price">{d["price"]:,}<small>원~</small></div>{trans}</div>
        <div class="lab">발견가 <span class="sep">·</span> <span class="fr">어제 확인</span></div>
        {hook}
        <div class="tags">{"".join(f'<span class="tag">{t}</span>' for t in tags)}</div>
      </div></div>'''


def tier_samples():
    out = []
    for lo, t in TIERS:                      # 35 → 25 → 15
        hi = {"t3": 999, "t2": 35, "t1": 25}[t]
        m = [x for x in D["deals"] if lo <= x.get("discount", 0) < hi]
        n = len(m)
        out.append((t, lo, hi, n, max(m, key=lambda a: a["discount"]) if m else None))
    return out


rows = pick()
old_html = "".join(f'<div class="col"><p class="cap">{n}</p>{card(d, False)}</div>' for n, d in rows)
new_html = "".join(f'<div class="col"><p class="cap">{n}</p>{card(d, True)}</div>' for n, d in rows)

n_stamp = sum(1 for x in D["deals"] if x.get("discount", 0) >= STAMP_MIN)
n_direct = sum(1 for x in D["deals"] if x["transfers"] == 0)
tot = len(D["deals"])

# 도장 3단계 샘플 카드
samples = tier_samples()                       # [(t3..),(t2..),(t1..)]
LBL = {"t1": "T1 · 15~24%", "t2": "T2 · 25~34%", "t3": "T3 · 35%+"}
ladder = "".join(
    f'<div class="col"><p class="cap">{LBL[t]} — 오늘 {cnt}건</p>{card(d, True)}</div>'
    for t, lo, hi, cnt, d in reversed(samples) if d)
t1n, t2n, t3n = (dict((t, c) for t, lo, hi, c, d in samples)[k] for k in ("t1", "t2", "t3"))
nonen = tot - (t1n + t2n + t3n)

ml = [x for x in D["deals"] if x["haul"] != "short"]
ml_direct = sum(1 for x in ml if x["transfers"] == 0)
ml_pct = round(100 * ml_direct / tot)
s_direct = sum(1 for x in D["deals"] if x["haul"] == "short" and x["transfers"] == 0)
n_layover = sum(1 for x in D["deals"] if x["transfers"] > 0)

def _badges(x):
    return (1 if x.get("discount", 0) >= STAMP_MIN else 0) + (1 if direct_badge(x) else 0)
b0 = round(100 * sum(1 for x in D["deals"] if _badges(x) == 0) / tot)
b1 = round(100 * sum(1 for x in D["deals"] if _badges(x) == 1) / tot)
b2 = round(100 * sum(1 for x in D["deals"] if _badges(x) == 2) / tot)

HTML = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>갈래말래 — 카드 구조 확정</title><style>
:root{{--accent:#F2603F;--accent2:#C6472A;--ink:#20353A;--sub:#5E7A7C;--sea:#EDF4F3;
--line:#E6EDEC;--soft:#F0F5F4;--card:#FFF;--bg:#F4F8F7;--coast:#33534F}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:Pretendard,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;line-height:1.6}}
.wrap{{max-width:1080px;margin:0 auto;padding:44px 22px 90px}}
h1{{font-weight:900;letter-spacing:-.035em;font-size:2.2rem;margin:0 0 8px}}
h1 em{{font-style:normal;color:var(--accent)}}
.lede{{color:var(--sub);max-width:64ch;margin:0 0 10px}}
h2{{font-weight:900;font-size:1.24rem;margin:48px 0 6px;letter-spacing:-.02em}}
h2 .n{{color:var(--accent);margin-right:8px}}
.note{{color:var(--sub);font-size:.9rem;margin:0 0 16px;max-width:72ch}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}}
.row{{display:grid;gap:16px}}
@media(min-width:640px){{.row{{grid-template-columns:repeat(auto-fit,minmax(212px,1fr))}}}}
.cap{{font-size:.72rem;font-weight:800;color:var(--sub);margin:0 0 7px}}
.card{{background:#fff;border:1.5px solid var(--line);border-radius:13px;overflow:hidden}}
.thumb{{height:78px;position:relative}}
.ph{{position:absolute;right:7px;top:7px;font-size:.54rem;color:#fff9;background:#0004;
 border-radius:5px;padding:1px 5px}}
.pick{{position:absolute;left:8px;top:8px;background:#fff;color:var(--accent);font-weight:900;
 font-size:.6rem;padding:2px 7px;border-radius:99px;box-shadow:0 2px 6px #0002}}
.body{{padding:10px 12px 12px}}
.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:7px}}
.city{{font-weight:900;font-size:1.02rem;letter-spacing:-.03em}}
.when{{display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:3px;
 font-size:.7rem;font-weight:800;color:var(--ink)}}
.wpill{{background:var(--accent);color:#fff;font-weight:800;font-size:.6rem;padding:2px 8px;border-radius:99px}}
/* 후보 */
.wpill.n{{background:var(--soft);color:var(--sub);border:1px solid var(--line)}}
.dline{{font-variant-numeric:tabular-nums}}
.dsub{{display:block;font-size:.64rem;font-weight:700;color:var(--sub);margin-top:2px;font-variant-numeric:tabular-nums}}
.dmain{{font-size:.72rem;font-weight:800;color:var(--ink)}}
.wk{{color:var(--sub);font-weight:700}}

.stamp{{flex:none;font-weight:900;white-space:nowrap;border-radius:4px;position:relative}}
/* T1 — 테두리 */
.stamp.t1{{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-size:.54rem;padding:1px 5px;background:#fff}}
/* T2 — 채움 */
.stamp.t2{{transform:rotate(-8deg);background:var(--accent);color:#fff;border:0;
 font-size:.6rem;padding:2px 7px;box-shadow:0 2px 6px rgba(242,96,63,.34)}}
/* T3 — 채움 + 그라디언트 + 흰 링 + 후광 + 광택, 썸네일 위로 걸침 */
.stamp.t3{{transform:rotate(-9deg) translateY(-16px) scale(1.06);
 background:linear-gradient(135deg,#F2603F 0%,#FF8A63 42%,#C6472A 100%);color:#fff;border:0;
 font-size:.66rem;padding:3px 9px;overflow:hidden;
 box-shadow:0 0 0 2px #fff, 0 0 0 5px rgba(242,96,63,.20), 0 5px 14px rgba(198,71,42,.36)}}
.stamp.t3::after{{content:"";position:absolute;inset:0;pointer-events:none;
 background:linear-gradient(105deg,transparent 38%,rgba(255,255,255,.72) 50%,transparent 62%);
 transform:translateX(-130%);animation:sheen 2.8s ease-in-out infinite}}
@keyframes sheen{{0%,62%{{transform:translateX(-130%)}}100%{{transform:translateX(130%)}}}}
@media (prefers-reduced-motion:reduce){{.stamp.t3::after{{animation:none;opacity:0}}}}
/* 직항 배지 — 도장과 다른 종류. 기울기 없음, 중립색 */
/* 직항 배지 — 확정(B3): --coast 채움 + 흰 글자 + 비행기 기호. 기울기 없음 */
.bdg{{font-size:.6rem;font-weight:800;border-radius:99px;padding:2px 9px;
 background:var(--coast);color:#fff;border:1px solid var(--coast)}}
.bdg .pl{{margin-right:3px;font-size:.9em;opacity:.92}}
/* 기각된 후보(아래 08절 비교용) */
.bdg.b0{{background:var(--soft);color:var(--coast);border-color:#d8e4e2;font-size:.58rem;padding:2px 8px}}
.bdg.b4{{background:#fff;color:var(--coast);border:1.5px solid var(--coast);font-weight:900}}

/* ── T3 무지개 실험 (사용자 요청, 2026-08-22) ── */
/* R1 — 무지개 테두리(conic) + 코랄 채움
   ⚠️ 요소 자체를 rotate()하면 사각형 모서리가 밖으로 휘둘린다(2026-08-22 버그).
      제자리에서 그라디언트 "각도"만 돌린다. @property 미지원이면 정지된 링으로 폴백. */
@property --ang{{syntax:"<angle>";initial-value:0deg;inherits:false}}
.stamp.r1{{transform:rotate(-9deg) translateY(-16px) scale(1.06);
 background:linear-gradient(135deg,#F2603F,#C6472A);color:#fff;border:0;
 font-size:.66rem;padding:3px 9px;overflow:visible;isolation:isolate}}
.stamp.r1::before{{content:"";position:absolute;inset:-3px;border-radius:6px;z-index:-1;
 background:conic-gradient(from var(--ang,0deg),#ff5f6d,#ffc371,#f7ff7a,#5efc8d,#5ec8fc,#a97bff,#ff5f6d);
 animation:hue 4s linear infinite}}
@keyframes hue{{to{{--ang:360deg}}}}
/* R2 — 홀로그램: 상시 무지개 결 + 흐르는 광택 (코랄 채움 유지)
   ⚠️ 2026-08-22 수정: 예전엔 mix-blend-mode:screen이라 코랄 위에서 무지개가 하얗게 날아갔고,
      광택이 주기의 62%를 화면 밖에 서 있어 거의 안 보였다.
      → 무지개 결을 "배경 레이어"로 상시 깔고(텍스트 뒤), 광택은 블렌드 없이 자주 흐르게 한다. */
.stamp.r2{{transform:rotate(-9deg) translateY(-16px) scale(1.06);color:#fff;border:0;
 font-size:.66rem;padding:3px 9px;overflow:hidden;text-shadow:0 1px 2px rgba(120,30,10,.55);
 background:
   linear-gradient(115deg,rgba(255,95,109,.42),rgba(255,195,113,.42),rgba(247,255,122,.42),
   rgba(94,252,141,.42),rgba(94,200,252,.42),rgba(169,123,255,.42)),
   linear-gradient(135deg,#F2603F,#C6472A);
 box-shadow:0 0 0 2px #fff,0 5px 14px rgba(198,71,42,.36)}}
.stamp.r2::after{{content:"";position:absolute;inset:0;pointer-events:none;
 background:linear-gradient(100deg,transparent 18%,rgba(255,255,255,.30) 34%,
 rgba(255,255,255,.85) 50%,rgba(255,255,255,.30) 66%,transparent 82%);
 transform:translateX(-160%);animation:sheen2 2.4s ease-in-out infinite}}
@keyframes sheen2{{0%,40%{{transform:translateX(-160%)}}100%{{transform:translateX(160%)}}}}
/* R3 — 전면 무지개 */
.stamp.r3{{transform:rotate(-9deg) translateY(-16px) scale(1.06);color:#fff;border:0;
 font-size:.66rem;padding:3px 9px;overflow:hidden;text-shadow:0 1px 2px rgba(0,0,0,.45);
 background:linear-gradient(105deg,#ff5f6d,#ffc371,#5efc8d,#5ec8fc,#a97bff);
 box-shadow:0 0 0 2px #fff,0 5px 14px rgba(0,0,0,.22)}}
@media (prefers-reduced-motion:reduce){{.stamp.r1::before,.stamp.r2::after{{animation:none;opacity:0}}}}
/* 시안 칸 — 링·후광이 이웃을 침범하지 않게 여유를 준다 */
.vrow{{display:flex;gap:34px;flex-wrap:wrap;align-items:flex-start;padding:30px 26px 36px;
 background:var(--sea);border:1px solid var(--line);border-radius:16px}}
.vcell{{text-align:center;min-width:132px}}
.vcell .vs{{display:flex;align-items:center;justify-content:center;margin:20px 0 14px;height:40px;overflow:visible}}
.vcell .vn{{font-size:.7rem;font-weight:800;color:var(--sub)}}
.vcell .vd{{font-size:.66rem;color:var(--sub);margin-top:3px;line-height:1.45}}
.prow{{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:7px}}
.trtxt{{font-size:.64rem;font-weight:700;color:var(--sub);white-space:nowrap}}
.price{{font-weight:900;font-size:1.18rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums}}
.price small{{font-size:.6em;font-weight:700;color:var(--sub);margin-left:2px}}
.lab{{font-size:.66rem;color:var(--sub);font-weight:500;margin-top:2px}}
.lab .sep{{opacity:.45}}.lab .fr{{color:var(--sub)}}
.hook{{font-size:.72rem;color:var(--sub);margin-top:8px;padding-top:8px;border-top:1px dashed var(--line)}}
.tags{{display:flex;gap:4px;margin-top:8px;flex-wrap:wrap}}
.tag{{font-size:.58rem;background:var(--soft);border-radius:99px;padding:2px 7px;color:var(--sub);font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:.88rem}}
th{{text-align:left;font-weight:700;font-size:.76rem;color:var(--sub);padding:0 10px 9px;border-bottom:1px solid var(--line)}}
td{{padding:11px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
code{{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}}
.bad{{color:var(--accent2);font-weight:800}}.ok{{color:#1E7A50;font-weight:800}}
ul.k{{margin:8px 0 0;padding-left:18px;font-size:.88rem;color:var(--sub)}}ul.k li{{margin:6px 0}}ul.k b{{color:var(--ink)}}
.foot{{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}}
</style></head><body><div class="wrap">

<h1>카드 구조 — <em>확정</em></h1>
<p class="lede">"왜 지금" 훅이 <b>피드의 54%</b>에서 근거 없는 인과를 주장하고 있었다.
문구를 고치는 대신 <b>자리를 없앴다.</b> 서울 출발 실제 딜로 그렸다.</p>

<h2><span class="n">01</span>지금</h2>
<p class="note">훅 줄이 있고, 도장이 <b>모든 카드에</b> 붙는다(할인 0%에도). 직항 여부는 <b>어디에도 없다.</b></p>
<div class="row">{old_html}</div>

<h2><span class="n">02</span>확정</h2>
<p class="note">훅 줄이 사라지고 도장은 <code>≥15%</code>일 때만. 날짜 줄 끝에 <b>직항/경유</b>가 붙고,
<b>중·장거리 직항에만</b> 배지가 올라간다. 태그도 필터로 고를 수 있는 6종만.
<b>네 번째 카드처럼 도장도 배지도 없는 게 정상</b>이다 — 전체의 72%가 그렇다.</p>
<div class="row">{new_html}</div>

<h2><span class="n">03</span>도장 3단계 — 희소할수록 무거워진다</h2>
<p class="note">할인율이 높을수록 도장이 <b>커지고, 채워지고, 떠오른다.</b>
무지개를 쓰지 않는다 — 우리 시그니처는 코랄 하나다(<code>DESIGN.md</code>).
계단은 <b>색을 늘려서가 아니라 채도·크기·무게·레이어로</b> 만든다.</p>
<div class="row">{ladder}</div>
<div class="panel" style="margin-top:16px"><table>
<thead><tr><th style="width:12%">단계</th><th style="width:16%">조건</th><th style="width:14%">오늘</th><th>시각</th></tr></thead>
<tbody>
<tr><td><b>T1</b></td><td><code>15~24%</code></td><td>{t1n}건</td><td>코랄 <b>테두리</b> · 흰 배경 · -7°</td></tr>
<tr><td><b>T2</b></td><td><code>25~34%</code></td><td>{t2n}건</td><td><b>채움</b>(코랄 배경 + 흰 글자) · 더 큼 · -8° · 그림자</td></tr>
<tr><td><b>T3</b></td><td><code>35%+</code></td><td>{t3n}건</td><td><b>그라디언트 + 흰 링 + 후광 + 광택</b> · 가장 큼 · -9° · <b>썸네일 위로 떠오름</b></td></tr>
<tr><td>없음</td><td><code>&lt;15%</code></td><td>{nonen}건</td><td>도장 없음. 카드 우상단이 비는 게 정상</td></tr>
</tbody></table>
<p class="note" style="margin:14px 0 0"><b>T3는 매일 나오지 않는다.</b> 오늘은 서울 36%·부산 43%가 있지만
제주는 최고가 11%라 도장이 하나도 없다. <b>그게 희소성이 작동한다는 뜻</b>이다 —
매일 뜨는 배지는 배지가 아니다.</p></div>

<h2><span class="n">04</span>직항 배지 — 드문 것만 자랑한다</h2>
<p class="note">교통은 모든 딜에 있는 사실이라 전부 배지로 만들면 100%가 배지를 달고 배지가 죽는다.
그래서 <b>드문 경우에만</b> 배지로 올린다.</p>
<div class="panel"><table>
<thead><tr><th style="width:24%">경우</th><th style="width:20%">오늘</th><th>표시</th></tr></thead><tbody>
<tr><td><b>중·장거리 직항</b></td><td>{ml_direct}건 ({ml_pct}%)</td><td><span class="bdg">직항</span> <b>배지</b> — 중거리 36%·장거리 14%만 직항이라 드물다</td></tr>
<tr><td>근거리 직항</td><td>{s_direct}건</td><td>날짜 줄에 <b>직항</b> 텍스트만. <b>근거리는 75%가 직항이라 당연하다</b></td></tr>
<tr><td>경유</td><td>{n_layover}건</td><td>날짜 줄에 <span style="color:var(--sub)">경유 N회</span> — <b>배지 아님.</b> 장점이 아닌 걸 자랑처럼 달지 않는다</td></tr>
</tbody></table>
<p class="note" style="margin:14px 0 0"><b>규칙 한 줄: 배지는 드문 좋은 소식에만. 모두가 가진 것은 배지가 아니다.</b><br>
결과적으로 배지 0개 {b0}% · 1개 {b1}% · 2개 {b2}% — 배지가 붙은 카드가 실제로 눈에 띈다.</p></div>

<h2><span class="n">05</span>무엇이 어디로 갔나</h2>
<div class="panel"><table>
<thead><tr><th style="width:34%">예전 훅이 말하던 것</th><th>지금</th></tr></thead><tbody>
<tr><td><code>평소보다 N%↓</code></td><td><b>도장</b> — <code>discount ≥ 15%</code>일 때만 ({n_stamp}/{tot}건 = {round(100*n_stamp/tot)}%)</td></tr>
<tr><td><code>경유로 확 싸진 특가</code></td><td class="bad">삭제 — 직항 대비 가격이 없어 <b>할 수 없는 주장</b>이었다</td></tr>
<tr><td><code>이번 주말 바로 출발</code></td><td>날짜 줄이 이미 말한다</td></tr>
<tr><td><code>{{when}} 최저가</code></td><td>날짜 줄이 이미 말한다</td></tr>
<tr><td>—</td><td class="ok">＋ <b>직항 / 경유 N회</b>가 날짜 줄에 새로 추가 ({n_direct}/{tot}건이 직항)</td></tr>
</tbody></table></div>

<h2><span class="n">06</span>왜 문구가 아니라 자리를 없앴나</h2>
<div class="panel"><ul class="k">
<li><b>훅의 목적("왜 지금")에 답할 수 있는 건 할인율뿐이고, 딜의 {round(100*n_stamp/tot)}%에만 있다.</b>
    나머지를 위해 자리를 유지하는 한 계속 지어내게 된다.</li>
<li>실제로 대안으로 <code>3시간이면 도착</code>을 떠올렸다가 — <b><code>deals.json</code>에 소요시간 필드가 없다</b>는 걸
    프론트 세션이 잡아냈다. <b>같은 실수를 반복할 뻔했다.</b></li>
<li>임계값만 올리는 안도 버렸다. 근거 약한 딜을 <code>{{when}} 최저가</code>로 몰면
    <b>절반이 같은 문구</b>가 되어 "정보 나열형 회피" 원칙과 충돌한다.</li>
<li><b>부수 효과가 크다</b> — 카드에 <b>직항 여부</b>가 처음 생긴다.
    <code>경유로 확 싸진 특가</code>가 경유를 근거 없이 칭찬하는 동안
    <b>{n_direct}건의 직항이라는 진짜 장점은 한 번도 언급되지 않았다.</b></li>
</ul></div>

<h2><span class="n">07</span>실험 — 무지개 <span style="font-size:.8rem;font-weight:700;color:var(--sub)">(만들어 보고 기각, 2026-08-22)</span></h2>
<p class="note">사용자 요청으로 <b>한 번만</b> 만들었다. 일부러 못생기게 만들지 않았다 —
비교가 되려면 각 안의 가장 좋은 버전이어야 한다. <b>실물을 보고 현행(코랄)을 유지하기로 했다.</b>
기록으로 남긴다. 전부 T3(35%+)에만 적용되던 시안이다.</p>
<div class="vrow">
  <div class="vcell"><span class="vn" style="color:var(--accent)">✅ 현행 · 코랄</span>
    <span class="vs"><span class="stamp t3" style="transform:rotate(-9deg)">평소보다 43%↓</span></span>
    <span class="vd">코랄 그라디언트<br>흰 링 + 흰 광택</span></div>
  <div class="vcell"><span class="vn">기각 · R1 무지개 테두리</span>
    <span class="vs"><span class="stamp r1" style="transform:rotate(-9deg)">평소보다 43%↓</span></span>
    <span class="vd">회전하는 conic 링<br>채움은 코랄 유지</span></div>
  <div class="vcell"><span class="vn">기각 · R2 홀로그램</span>
    <span class="vs"><span class="stamp r2" style="transform:rotate(-9deg)">평소보다 43%↓</span></span>
    <span class="vd">무지개 <b>결이 상시</b> 깔리고<br>그 위로 광택이 흐름</span></div>
  <div class="vcell"><span class="vn">기각 · R3 전면 무지개</span>
    <span class="vs"><span class="stamp r3" style="transform:rotate(-9deg)">평소보다 43%↓</span></span>
    <span class="vd">배경 전체가 무지개<br>코랄이 사라짐</span></div>
</div>
<div class="panel" style="margin-top:16px">
<p class="note" style="margin:0 0 12px"><b>🐛 고침(2026-08-22)</b> — R1에서 무지개 사각형이 통째로 빙글빙글 돌아
모서리가 밖으로 튀어나오고 있었다. <b>요소를 <code>rotate()</code>한 게 원인</b>이었다.
제자리에서 <b>그라디언트의 각도만</b> 도는 방식으로 바꿨다.</p>
<p class="note" style="margin:0 0 14px"><b>밖으로 나가는 게 정상인 것</b>도 있다 —
<b>흰 링·후광</b>은 도장 테두리 바깥에 그려지는 게 맞고, <b>T3가 썸네일 위로 올라타는 것</b>도
의도한 효과다(색을 안 늘리고 "특별함"을 만드는 수단). 도는 사각형만 버그였다.</p>
<ul class="k">
<li><b>R2(홀로그램)가 실물 트레이딩 카드에 가장 가깝다.</b> 진짜 SSR·포일 카드는
    배경이 무지개가 아니라 <b>바탕색 위로 무지개 광택이 흐르는</b> 구조다.
    <b>코랄 시그니처가 살아 있으면서</b> 화려함은 다 얻는다.</li>
<li><b>R1</b>은 눈에 확 띄지만 링이 계속 돌아 <b>시선을 잡아둔다.</b> 카드가 여러 장 있는 피드에서
    T3가 두 장 뜨면 서로 싸운다.</li>
<li><b>R3</b>는 <b>코랄이 완전히 사라진다.</b> 이 도장만 보면 다른 서비스 같다.
    색각이상에서도 무지개는 구분이 안 되므로 <b>계단 정보가 통째로 사라진다</b>(T2와 구별 불가).</li>
<li>어느 안이든 <b>T3에만</b> 쓴다. 오늘 기준 <b>{t3n}건(1.9%)</b>이라 화면 전체가 요란해지지는 않는다.</li>
</ul></div>

<h2><span class="n">08</span>직항 배지 — 더 잘 보이게</h2>
<p class="note">"잘 안 보인다"는 지적으로 후보를 만들었고 <b>B3로 확정</b>했다.
전부 <code>--coast</code>(청록) 계열이라 도장(코랄)과 색이 겹치지 않고 두 번째 강조색도 만들지 않는다.</p>
<div class="vrow">
  <div class="vcell"><span class="vn">기각 · 옛 현행</span>
    <span class="vs"><span class="bdg b0">직항</span></span>
    <span class="vd">연한 배경<br>거의 안 보임</span></div>
  <div class="vcell"><span class="vn">기각 · B2 채움</span>
    <span class="vs"><span class="bdg" style="font-size:.58rem;padding:2px 8px">직항</span></span>
    <span class="vd">청록 채움<br>기호 없음</span></div>
  <div class="vcell"><span class="vn" style="color:var(--accent)">✅ B3 · 채움 + 기호</span>
    <span class="vs"><span class="bdg"><span class="pl">✈</span>직항</span></span>
    <span class="vd"><b>채택</b> — 기호 하나로<br>스캔 속도가 오른다</span></div>
  <div class="vcell"><span class="vn">기각 · B4 테두리</span>
    <span class="vs"><span class="bdg b4">직항</span></span>
    <span class="vd">굵은 테두리<br>도장과 형태가 비슷</span></div>
</div>

<h2><span class="n">09</span>직항/경유를 어디에 둘까 <span style="font-size:.8rem;font-weight:700;color:var(--sub)">(2026-08-22 재배치)</span></h2>
<p class="note">태그 줄에 섞여 있던 걸 옮겼다. <b>정보 종류가 다르다</b> —
태그는 <b>"어떤 곳인가"</b>, 직항/경유는 <b>"어떻게 가는가"</b>다.
게다가 날짜 줄과 태그 줄에 <b>중복으로 두 번</b> 나오고 있었다(내 스펙 오류).</p>
<div class="panel"><table>
<thead><tr><th style="width:14%">후보</th><th style="width:40%">모양</th><th>판단</th></tr></thead><tbody>
<tr><td><b>A</b> 날짜 줄 끝</td>
<td><code>다음 달 9/12(토)~9/15(화) · 3박4일 · 직항</code></td>
<td>여정 정보끼리 묶이는 건 맞지만 <b>줄이 너무 길어진다</b>(카드 폭 340px). 눈에도 안 띈다</td></tr>
<tr><td><b>B</b> 가격 줄 우측 <span class="badge">채택</span></td>
<td><div style="display:flex;align-items:center;justify-content:space-between;max-width:190px">
<span class="price" style="margin:0">218,400<small>원~</small></span>
<span class="bdg"><span class="pl">✈</span>직항</span></div></td>
<td><b>가격과 교통은 실제로 같이 저울질하는 쌍</b>이다 — "이 값에 직항이냐". 그 자리가 비어 있었고, 가격 옆이라 반드시 읽힌다</td></tr>
<tr><td><b>C</b> 태그 줄</td>
<td><div style="display:flex;gap:4px"><span class="bdg"><span class="pl">✈</span>직항</span>
<span class="tag">야경</span><span class="tag">골목</span></div></td>
<td class="bad">기각 — <b>"어떤 곳인가"와 "어떻게 가는가"가 섞인다.</b> 배지가 태그처럼 보여 성격이 흐려진다</td></tr>
</tbody></table>
<p class="note" style="margin:14px 0 0"><b>자리는 하나, 무게는 셋.</b>
같은 위치에 두되 <b>드문 것만 배지</b>로 올린다 —
<span class="bdg" style="vertical-align:middle"><span class="pl">✈</span>직항</span> 중·장거리 직항(드묾) ·
<span class="trtxt">직항</span> 근거리 직항(75%라 당연) ·
<span class="trtxt">경유 1회</span> 경유(장점 아님).</p>
</div>

<h2><span class="n">10</span>날짜 줄 — 읽기 쉽게</h2>
<p class="note">"날짜랑 몇 박 며칠이 다 글로 되어 있어 가독성이 별로"라는 지적.
파 보니 <b>문제가 둘</b>이었다.</p>
<div class="panel">
<p class="note" style="margin:0 0 14px"><b>① 코랄이 카드에 세 곳에서 경쟁한다.</b>
실제 앱은 <code>다음 달</code> 배지가 <b>코랄 배경</b>이고 가격도 <b>코랄 글자</b>다.
여기에 새로 넣은 <b>할인 도장까지 코랄</b>이라 셋이 싸운다.
<b>날짜 배지는 100% 카드에 붙는데 코랄이면 강조가 아니다</b> — 도장을 100%에서 14%로 줄인 것과 같은 논리다.</p>
<p class="note" style="margin:0 0 16px"><b>② 한 줄에 다 밀어 넣었다.</b>
<code>9/12(토)~9/15(화) · 3박4일</code>는 숫자·괄호·물결·가운뎃점이 뒤섞여 시끄럽다.
스캔할 땐 <b>"언제쯤, 며칠"</b>만 필요하고 정확한 날짜는 확인 단계에서 본다.</p>
<div class="vrow" style="gap:40px">
  <div class="vcell" style="min-width:190px"><span class="vn">A · 현행(실제 앱)</span>
    <span class="vs" style="height:auto;display:block;text-align:left">
      <span class="when"><span class="wpill">다음 달</span><span class="dline">9/12(토)~9/15(화) · 3박4일</span></span>
    </span>
    <span class="vd">코랄 배지 + 한 줄<br>가격·도장과 코랄 경쟁</span></div>
  <div class="vcell" style="min-width:190px"><span class="vn" style="color:var(--accent)">B · 두 단 위계</span>
    <span class="vs" style="height:auto;display:block;text-align:left">
      <span class="when"><span class="wpill n">다음 달</span><span class="dmain">3박4일</span>
      <span class="dsub">9/12(토)~9/15(화)</span></span>
    </span>
    <span class="vd"><b>스캔용</b>(언제쯤·며칠)과<br><b>확인용</b>(정확한 날짜)을 분리<br>배지는 중립색</span></div>
  <div class="vcell" style="min-width:190px"><span class="vn">C · 화살표</span>
    <span class="vs" style="height:auto;display:block;text-align:left">
      <span class="when"><span class="wpill n">다음 달</span><span class="dmain">3박4일</span>
      <span class="dsub">9/12 <span class="wk">토</span> → 9/15 <span class="wk">화</span></span></span>
    </span>
    <span class="vd">괄호를 없애고<br>요일을 옅게<br>여정 느낌</span></div>
</div>
<p class="note" style="margin:16px 0 0"><b>B를 권한다.</b> 스캔 단계에서 필요한 건
<code>다음 달 · 3박4일</code>이고, <code>9/12(토)</code>는 마음이 기운 뒤에 본다.
줄이 하나 늘지만 <b>각 줄이 짧아져 실제로는 더 빨리 읽힌다.</b>
C는 더 깔끔하지만 <code>→</code>가 편도로 오해될 여지가 있다.</p>
</div>

<p class="foot">확정 스펙 <b>../SPEC.md</b> §CH3 · 근거·기각안 <b>../DECISIONS.md</b> · 문구 <b>../COPY.md</b><br>
재생성 <code>python design/build_card.py</code> · 커밋된 <code>deals.json</code>의 실제 딜만 사용</p>
</div></body></html>'''

OUT.write_text(HTML, encoding="utf-8")
print(f"생성: {OUT}  (도장 {n_stamp}/{tot} · 직항 {n_direct}/{tot})")
