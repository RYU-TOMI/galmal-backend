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
GRAD = {"해변": "linear-gradient(135deg,#8fd0e0,#2a6f8f)", "도시": "linear-gradient(135deg,#ff9a76,#c6472a)",
        "미식": "linear-gradient(135deg,#f2603f,#7a2e18)", "자연": "linear-gradient(135deg,#a8e0c0,#2a8f6c)",
        "문화": "linear-gradient(135deg,#ffcf9a,#c6652a)", "온천": "linear-gradient(135deg,#ffc07a,#e0782f)"}
CHIPS = ["해변", "도시", "미식", "자연", "문화", "온천"]


def md(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.month}/{d.day}({WD[d.weekday()]})"


def transit(d):
    return "직항" if d["transfers"] == 0 else f"경유 {d['transfers']}회"


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
    ds = [x for x in D["deals"] if x["o"] == o]
    hi = max(ds, key=lambda x: (x.get("discount", 0), -x["price"]))
    direct0 = next(x for x in ds if x["transfers"] == 0 and x.get("discount", 0) < STAMP_MIN)
    layover0 = next(x for x in ds if x["transfers"] > 0 and x.get("discount", 0) == 0)
    return [("할인 있음 · 직항" if hi["transfers"] == 0 else "할인 있음", hi),
            ("할인 없음 · 직항", direct0),
            ("할인 없음 · 경유", layover0)]


def card(d, new, hero=False):
    tags = [t for t in d.get("tags", []) if t in CHIPS][:2] if new else d.get("tags", [])[:3]
    g = next((GRAD[t] for t in d.get("tags", []) if t in GRAD), "linear-gradient(135deg,#ffb89a,#c6502a)")
    disc = d.get("discount", 0)
    stamp = ""
    if new:
        if disc >= STAMP_MIN:
            stamp = f'<span class="stamp">평소보다 {disc}%↓</span>'
    else:
        stamp = f'<span class="stamp">특가 {disc}%↓</span>'
    date = f'{md(d["dep"])}~{md(d["ret"])}' if d.get("ret") else md(d["dep"])
    line = f'{d["when"]} {date}'
    if d.get("nights"):
        line += f' · {d["nights"]}'
    if new:
        line += f' · <b class="tr">{transit(d)}</b>'
    hook = "" if new else f'<div class="hook">{old_why(d)}</div>'
    badge = '<span class="pick">진짜 갈래말래?</span>' if hero else ""
    return f'''<div class="card">
      <div class="thumb" style="background:{g}">{badge}<span class="ph">사진 준비중</span></div>
      <div class="body">
        <div class="top"><div><div class="city">{d["ko"]}</div>
          <div class="when">{line}</div></div>{stamp}</div>
        <div class="price">{d["price"]:,}<small>원~</small></div>
        <div class="lab">발견가 <span class="sep">·</span> <span class="fr">어제 확인</span></div>
        {hook}
        <div class="tags">{"".join(f'<span class="tag">{t}</span>' for t in tags)}</div>
      </div></div>'''


rows = pick()
old_html = "".join(f'<div class="col"><p class="cap">{n}</p>{card(d, False)}</div>' for n, d in rows)
new_html = "".join(f'<div class="col"><p class="cap">{n}</p>{card(d, True)}</div>' for n, d in rows)

n_stamp = sum(1 for x in D["deals"] if x.get("discount", 0) >= STAMP_MIN)
n_direct = sum(1 for x in D["deals"] if x["transfers"] == 0)
tot = len(D["deals"])

HTML = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>갈래말래 — 카드 구조 확정</title><style>
:root{{--accent:#F2603F;--accent2:#C6472A;--ink:#20353A;--sub:#5E7A7C;--sea:#EDF4F3;
--line:#E6EDEC;--soft:#F0F5F4;--card:#FFF;--bg:#F4F8F7}}
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
@media(min-width:820px){{.row{{grid-template-columns:repeat(3,1fr)}}}}
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
.when{{font-size:.68rem;color:var(--sub);font-weight:700;margin-top:1px}}
.when .tr{{color:var(--ink)}}
.stamp{{flex:none;transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-weight:900;font-size:.54rem;padding:1px 5px;border-radius:4px;white-space:nowrap}}
.price{{font-weight:900;font-size:1.18rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums;margin-top:7px}}
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
<p class="note">훅 줄이 있고, 도장이 <b>모든 카드에</b> 붙는다. 직항 여부는 <b>어디에도 없다.</b></p>
<div class="row">{old_html}</div>

<h2><span class="n">02</span>확정</h2>
<p class="note">훅 줄이 사라지고, 도장은 <code>≥15%</code>일 때만.
날짜 줄 끝에 <b>직항/경유</b>가 새로 붙었다. 태그도 필터로 고를 수 있는 6종만.</p>
<div class="row">{new_html}</div>

<h2><span class="n">03</span>무엇이 어디로 갔나</h2>
<div class="panel"><table>
<thead><tr><th style="width:34%">예전 훅이 말하던 것</th><th>지금</th></tr></thead><tbody>
<tr><td><code>평소보다 N%↓</code></td><td><b>도장</b> — <code>discount ≥ 15%</code>일 때만 ({n_stamp}/{tot}건 = {round(100*n_stamp/tot)}%)</td></tr>
<tr><td><code>경유로 확 싸진 특가</code></td><td class="bad">삭제 — 직항 대비 가격이 없어 <b>할 수 없는 주장</b>이었다</td></tr>
<tr><td><code>이번 주말 바로 출발</code></td><td>날짜 줄이 이미 말한다</td></tr>
<tr><td><code>{{when}} 최저가</code></td><td>날짜 줄이 이미 말한다</td></tr>
<tr><td>—</td><td class="ok">＋ <b>직항 / 경유 N회</b>가 날짜 줄에 새로 추가 ({n_direct}/{tot}건이 직항)</td></tr>
</tbody></table></div>

<h2><span class="n">04</span>왜 문구가 아니라 자리를 없앴나</h2>
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

<p class="foot">확정 스펙 <b>../SPEC.md</b> §CH3 · 근거·기각안 <b>../DECISIONS.md</b> · 문구 <b>../COPY.md</b><br>
재생성 <code>python design/build_card.py</code> · 커밋된 <code>deals.json</code>의 실제 딜만 사용</p>
</div></body></html>'''

OUT.write_text(HTML, encoding="utf-8")
print(f"생성: {OUT}  (도장 {n_stamp}/{tot} · 직항 {n_direct}/{tot})")
