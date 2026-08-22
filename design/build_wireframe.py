# -*- coding: utf-8 -*-
"""design/wireframe.html 생성 — 구조 재설계 (PH5).

색·사진 없이 **구조만** 본다. 다만 지도는 실제 해안선을 회색조로 그린다 —
우리 제품은 지도가 주인공이라 지도 없는 와이어프레임은 의미가 없다.
딜은 커밋된 deals.json 실데이터를 쓴다(밀도가 구조 판단에 영향을 주므로).

    python design/build_wireframe.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "design" / "wireframe.html"
d3a = (ROOT / "docs/assets/d3-array.min.js").read_text(encoding="utf-8")
d3g = (ROOT / "docs/assets/d3-geo.min.js").read_text(encoding="utf-8")
world = (ROOT / "docs/data/world.geojson").read_text(encoding="utf-8")
D = json.loads((ROOT / "docs/data/deals.json").read_text(encoding="utf-8"))

sel = [x for x in D["deals"] if x["o"] == "SEL"]
n_sel = len(sel)

# 상속 vs 확정 — T1 산출물
AUDIT = [
    ("지도 + 카드 피드 병행", "확정", "2026-08-01",
     "지도만 두면 검색 UI가 되어 lean-back 사용자가 이탈한다"),
    ("피드가 <b>왼쪽</b>", "상속", "—",
     "결정한 적이 없다. 오른쪽·아래도 후보였다"),
    ("피드 폭 <b>340px 고정</b>", "상속", "—",
     "근거 없는 숫자다. <b>오늘 카드 정보가 늘어(도장·직항·2단 날짜·태그 4개) 좁을 수 있다</b>"),
    ("확장 상세 = 지도 위 <b>플로팅</b>", "확정", "2026-08-01",
     "다만 '인라인 확장'이라는 결정이 곧 '지도 위'는 아니었다. 피드에서 펼치는 것도 인라인이다"),
    ("확장 상세가 <b>무대 안에 갇힘</b>", "상속", "—",
     "무대를 벗어나지 못해 도크·단계바와 자리를 다툰다"),
    ("필터 도크 = 우측 하단", "확정", "2026-08-01", "지도앱 관행. 헤더 바는 결과와 멀다"),
    ("단계바 = <b>하단 중앙</b>", "상속", "—", "위치를 정한 적이 없다"),
    ("줌 컨트롤 = 우측 상단", "상속→변경", "2026-08-22",
     "단계 스테퍼(<code>＋/－</code>)로 바뀌었다. 자리도 다시 볼 것"),
    ("안내 문구 = 좌측 상단", "상속", "—", "지도 위에 늘 떠 있어야 하는지도 의문"),
    ("화면0 = <b>전체 화면 오버레이</b>", "상속", "—",
     "'한국 지도 + 5핀'만 정했고 전체를 덮는지는 안 정했다"),
    ("헤더 56px · 로고/네비/출발지", "일부 확정", "2026-08-01",
     "네비 구성(발견·노선별)은 확정. 출발지 pill 위치는 상속"),
    ("모바일 전부", "미정", "—", "<b>DESIGN.md가 '구현하며 확정'으로 미뤄둔 유일한 영역</b>"),
]

HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>갈래말래 — 와이어프레임</title><style>
:root{--ink:#20353A;--sub:#5E7A7C;--line:#E6EDEC;--bg:#F4F8F7;--card:#FFF;--accent:#F2603F;
 --w1:#E9EEEE;--w2:#D6DEDE;--w3:#BAC6C6;--w4:#94A5A5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:Pretendard,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;line-height:1.6}
.wrap{max-width:1180px;margin:0 auto;padding:44px 22px 90px}
h1{font-weight:900;letter-spacing:-.035em;font-size:2.2rem;margin:0 0 8px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);max-width:66ch;margin:0 0 10px}
h2{font-weight:900;font-size:1.24rem;margin:52px 0 6px;letter-spacing:-.02em}
h2 .n{color:var(--accent);margin-right:8px}
.note{color:var(--sub);font-size:.9rem;margin:0 0 16px;max-width:74ch}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:0 9px 8px;border-bottom:1px solid var(--line)}
td{padding:9px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:#EEF3F3;padding:1px 5px;border-radius:4px}
.k{font-size:.66rem;font-weight:900;padding:2px 7px;border-radius:99px;white-space:nowrap}
.k.fix{background:#DDE9E4;color:#2A6B52}
.k.inh{background:#F3E6DF;color:#A0522D}
.k.non{background:#EDE3EF;color:#6B3A78}

/* ── 와이어 공통 ── */
.wf{background:#fff;border:1.5px solid var(--w3);border-radius:10px;overflow:hidden;
 font-size:.7rem;color:var(--w4)}
.wf .bar{background:var(--w1);border-bottom:1.5px solid var(--w3);display:flex;align-items:center;
 gap:8px;padding:0 12px;height:38px;font-weight:800;color:var(--sub)}
.wf .box{border:1.5px dashed var(--w3);border-radius:7px;background:#FBFCFC;
 display:flex;align-items:center;justify-content:center;color:var(--w4);font-weight:700}
.lbl{position:absolute;font-size:.6rem;font-weight:900;color:#fff;background:var(--w4);
 padding:1px 6px;border-radius:4px;letter-spacing:-.01em;z-index:5}
.stage{position:relative;background:#F7FAFA;flex:1;overflow:hidden}
.stage svg{display:block;width:100%;height:100%}
.land{fill:var(--w2);stroke:var(--w4);stroke-width:.4}
.pin{fill:var(--w4)}
.pin.hi{fill:var(--ink)}
.chipbar{position:absolute;left:50%;transform:translateX(-50%);bottom:12px;display:flex;gap:6px}
.chip{background:#fff;border:1.5px solid var(--w3);border-radius:99px;padding:4px 11px;
 font-size:.66rem;font-weight:800;color:var(--sub)}
.chip.on{background:var(--w4);color:#fff;border-color:var(--w4)}
.dock{position:absolute;right:12px;bottom:12px;width:190px;background:#fff;border:1.5px solid var(--w3);
 border-radius:11px;padding:9px 10px}
.dock .row{height:9px;background:var(--w1);border-radius:5px;margin:6px 0}
.step{position:absolute;right:12px;top:12px;width:30px;background:#fff;border:1.5px solid var(--w3);
 border-radius:8px;text-align:center;font-weight:900;color:var(--sub);font-size:.72rem}
.step div{padding:4px 0}
.step div+div{border-top:1.5px solid var(--w3)}
.detail{position:absolute;left:40%;top:22%;width:180px;background:#fff;border:1.5px solid var(--ink);
 border-radius:10px;padding:8px;box-shadow:0 8px 20px #0002}
.feed{width:300px;border-right:1.5px solid var(--w3);background:#FCFDFD;padding:10px;overflow:hidden}
.fcard{border:1.5px solid var(--w3);border-radius:8px;padding:7px;margin-bottom:8px;background:#fff}
.fcard.hero{border-color:var(--ink);border-width:2px}
.thumb{height:34px;background:var(--w1);border-radius:5px;margin-bottom:6px}
.ln{height:7px;background:var(--w2);border-radius:4px;margin:4px 0}
.ln.s{width:45%}.ln.m{width:70%}.ln.l{width:88%}
.tagrow{display:flex;gap:3px;margin-top:6px}
.tg{height:11px;border:1px solid var(--w3);border-radius:3px;width:26px}
.row2{display:flex;justify-content:space-between;align-items:center;margin-top:5px}
.bdg{height:12px;width:34px;background:var(--w4);border-radius:99px}
.stamp{height:12px;width:44px;border:1.5px solid var(--w4);border-radius:3px;transform:rotate(-7deg)}
.mob{width:300px;height:600px}
.mob .stage{height:44%;flex:none}
.sheet{border-top:1.5px solid var(--w3);background:#fff;position:relative}
.grab{width:34px;height:4px;background:var(--w3);border-radius:99px;margin:7px auto}
.hscroll{display:flex;gap:8px;padding:0 10px 10px;overflow:hidden}
.hscroll .fcard{flex:0 0 132px;margin:0}
.tabbar{border-top:1.5px solid var(--w3);height:44px;display:flex;align-items:center;
 justify-content:center;gap:8px;background:var(--w1);font-weight:800;color:var(--sub);font-size:.68rem}
.two{display:grid;gap:20px}
@media(min-width:900px){.two{grid-template-columns:1fr 1fr}}
ul.q{margin:8px 0 0;padding-left:18px;font-size:.88rem;color:var(--sub)}
ul.q li{margin:7px 0}ul.q b{color:var(--ink)}
.foot{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
</style></head><body><div class="wrap">

<h1>와이어프레임 — <em>구조부터 다시</em></h1>
<p class="lede">색·사진 없이 <b>구조만</b> 본다. 다만 <b>지도는 실제 해안선을 회색조로</b> 그렸다 —
우리 제품은 지도가 주인공이라 지도 없는 와이어프레임은 의미가 없다.
카드 수·태그 수는 <b>커밋된 실데이터</b>(서울 출발 __N__건)를 쓴다. 밀도가 구조 판단에 영향을 주기 때문이다.</p>

<h2><span class="n">01</span>먼저 — 무엇이 결정이고 무엇이 상속인가</h2>
<p class="note">지금 화면의 구조 중 상당수는 <b>결정된 적이 없다.</b> 그냥 처음 구현이 그랬고 아무도 되묻지 않았다.
와이어프레임을 다시 그리는 진짜 이유가 이것이다 — <b>상속을 결정으로 바꾸는 것.</b></p>
<div class="panel"><table>
<thead><tr><th style="width:26%">구조 요소</th><th style="width:10%">상태</th><th style="width:10%">언제</th><th>메모</th></tr></thead>
<tbody>__AUDIT__</tbody></table></div>

<h2><span class="n">02</span>데스크톱 — 지금 구조 그대로 그리면</h2>
<p class="note">1440 기준. <b>바꾸자는 안이 아니라 현재 구조를 회색조로 옮긴 것</b>이다. 여기서 무엇이 어색한지 본다.</p>
__DESKTOP__
<div class="panel" style="margin-top:16px">
<p class="note" style="margin:0 0 8px"><b>이렇게 그려 보니 걸리는 것</b></p>
<ul class="q">
<li><b>피드 폭 340px에 정보가 너무 많아졌다.</b> 오늘 도장·직항 배지·2단 날짜·태그 4개가 들어갔다.
    카드 한 장이 세로로 길어져 <b>한 화면에 3장도 안 들어간다.</b></li>
<li><b>지도 아래쪽이 붐빈다.</b> 단계바(하단 중앙)·필터 도크(우하단)·확장 상세가 <b>같은 영역</b>을 놓고 다툰다.
    확장 상세는 무대를 벗어날 수 없어 더 그렇다.</li>
<li><b>지도 위쪽은 거의 비어 있다.</b> 스테퍼만 있다. 핀도 대체로 아래쪽에 몰린다(딜이 북반구 중위도에 많다).</li>
<li><b>화면0이 전체를 덮을 이유가 있나.</b> 출발지는 헤더 pill로도 바꿀 수 있다.</li>
</ul></div>

<h2><span class="n">03</span>모바일 — 처음 그린다</h2>
<p class="note">390 기준. <b>스펙이 없던 유일한 영역</b>이라 후보를 두 개 그렸다.</p>
<div class="two">
  <div><p class="note" style="margin:0 0 8px"><b>M1 · 고정 분할</b> — 지도 44% + 하단 피드 가로 스크롤</p>__MOB1__</div>
  <div><p class="note" style="margin:0 0 8px"><b>M2 · 드래그 시트</b> — 지도 위, 시트를 끌어 3단계로</p>__MOB2__</div>
</div>
<div class="panel" style="margin-top:16px">
<ul class="q">
<li><b>M1</b>은 단순하다. 다만 <b>가로 스크롤 카드는 정보가 적게 들어간다</b> — 오늘 카드에 넣은
    도장·직항·2단 날짜·태그가 132px 폭에 다 들어가지 않는다. 카드를 모바일용으로 따로 설계해야 한다.</li>
<li><b>M2</b>는 지도앱 관행이고 <b>세로 카드를 그대로 쓸 수 있다.</b>
    시트를 내리면 지도가 커지고, 올리면 목록이 된다 — <b>lean-back(목록)과 lean-forward(지도)를 사용자가 고른다.</b>
    대신 제스처가 하나 늘고, 지도 드래그와 충돌하지 않게 해야 한다(자유 줌이 없어 충돌 여지는 작다).</li>
<li>둘 다 <b>필터는 하단 시트</b>, <b>확장 상세도 하단 시트</b>다. 데스크톱의 플로팅 카드가 모바일에선 시트가 된다.</li>
</ul></div>

<h2><span class="n">04</span>이 와이어에서 정해야 할 것</h2>
<div class="panel"><table>
<thead><tr><th style="width:30%">질문</th><th>선택지</th></tr></thead><tbody>
<tr><td><b>피드 폭</b></td><td>340px 유지 / 넓히기(380~400) / 카드를 낮추기</td></tr>
<tr><td><b>확장 상세 위치</b></td><td>지도 위 플로팅(현행) / <b>피드 카드가 그 자리에서 펼쳐지기</b> / 우측 패널</td></tr>
<tr><td><b>단계바 위치</b></td><td>하단 중앙(현행) / 상단 / 피드 헤더로 이동</td></tr>
<tr><td><b>화면0</b></td><td>전체 오버레이(현행) / 지도 위 작은 카드 / 헤더 pill만</td></tr>
<tr><td><b>모바일 구조</b></td><td>M1 고정 분할 / M2 드래그 시트</td></tr>
</tbody></table></div>

<p class="foot">구조 재검토·와이어프레임 — PH5. 확정되면 <b>../SPEC.md</b>와 <b>../DECISIONS.md</b>에 기록한다.<br>
재생성 <code>python design/build_wireframe.py</code> · 지도는 실제 <code>world.geojson</code>(50m), 딜은 커밋된 <code>deals.json</code></p>
</div>
<script>__D3A__</script><script>__D3G__</script>
<script>
var WORLD=__WORLD__, DEALS=__DEALS__;
var SEL=DEALS.deals.filter(function(d){return d.o==="SEL";});
var NS="http://www.w3.org/2000/svg";
function el(n,a){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);return e;}
function drawMap(host,W,H,lon,lat,scale,hi){
  var p=d3.geoEquirectangular().rotate([-lon,0]).center([0,lat]).scale(scale).translate([W/2,H/2]);
  var path=d3.geoPath(p);
  var svg=el("svg",{viewBox:"0 0 "+W+" "+H,preserveAspectRatio:"xMidYMid slice"});
  svg.appendChild(el("path",{class:"land",d:path(WORLD)}));
  SEL.forEach(function(d,i){
    var q=p([d.lon,d.lat]); if(!q) return;
    if(q[0]<0||q[0]>W||q[1]<0||q[1]>H) return;
    svg.appendChild(el("circle",{class:"pin"+(i===hi?" hi":""),cx:q[0],cy:q[1],r:i===hi?4:2.6}));
  });
  host.appendChild(svg);
}
document.querySelectorAll("[data-map]").forEach(function(h){
  var a=h.dataset.map.split(",");
  drawMap(h,+a[0],+a[1],+a[2],+a[3],+a[4],+a[5]);
});
</script>
</body></html>"""


def card(hero=False, stamp=False, badge=True):
    return (f'<div class="fcard{" hero" if hero else ""}">'
            '<div class="thumb"></div>'
            f'<div class="row2"><div class="ln m" style="height:9px"></div>{"<div class=stamp></div>" if stamp else ""}</div>'
            '<div class="ln s"></div><div class="ln s" style="width:38%"></div>'
            f'<div class="row2"><div class="ln" style="width:44%;height:10px"></div>{"<div class=bdg></div>" if badge else ""}</div>'
            '<div class="tagrow"><div class="tg"></div><div class="tg"></div><div class="tg"></div></div>'
            '</div>')


desktop = f'''<div class="wf" style="height:520px;display:flex;flex-direction:column;position:relative">
  <span class="lbl" style="left:8px;top:8px">헤더 56</span>
  <div class="bar"><b style="color:var(--ink)">갈래말래</b><span>발견 · 노선별</span>
    <span style="margin-left:auto;border:1.5px solid var(--w3);border-radius:99px;padding:2px 10px">서울 출발 ▾</span></div>
  <div style="display:flex;flex:1;min-height:0">
    <div class="feed" style="position:relative">
      <span class="lbl" style="left:8px;top:6px">피드 340</span>
      <div style="margin-top:20px"><div class="ln m" style="height:10px"></div>
      <div style="display:flex;gap:5px;margin:8px 0 10px">
        <span class="chip on" style="font-size:.6rem;padding:3px 8px">가성비순</span>
        <span class="chip" style="font-size:.6rem;padding:3px 8px">임박순</span>
        <span class="chip" style="font-size:.6rem;padding:3px 8px">할인율순</span></div></div>
      {card(hero=True, stamp=True)}{card(stamp=False)}{card(stamp=True, badge=False)}
    </div>
    <div class="stage" data-map="620,420,122,14,180,3" style="position:relative">
      <span class="lbl" style="left:8px;top:8px">지도 무대</span>
      <div class="step"><div>＋</div><div>－</div></div>
      <div class="chipbar"><span class="chip on">가까운 곳</span><span class="chip">조금 더 멀리</span><span class="chip">아주 멀리</span></div>
      <div class="dock"><div style="font-weight:800;color:var(--sub);font-size:.66rem">필터</div>
        <div class="row"></div><div class="row" style="width:70%"></div><div class="row" style="width:85%"></div></div>
      <div class="detail"><div class="thumb" style="height:44px"></div>
        <div class="ln m" style="height:9px"></div><div class="ln s"></div>
        <div class="ln l" style="margin-top:7px"></div><div class="ln l"></div>
        <div class="ln" style="height:13px;background:var(--w4);margin-top:8px"></div>
        <span class="lbl" style="right:6px;top:-9px">확장 상세</span></div>
    </div>
  </div>
</div>'''

mob1 = f'''<div class="wf mob" style="display:flex;flex-direction:column;position:relative">
  <div class="bar" style="height:34px"><b style="color:var(--ink)">갈래말래</b>
    <span style="margin-left:auto;border:1.5px solid var(--w3);border-radius:99px;padding:1px 8px;font-size:.62rem">서울 ▾</span></div>
  <div class="stage" data-map="300,264,122,14,120,3" style="position:relative">
    <div class="chipbar" style="bottom:8px"><span class="chip on" style="font-size:.58rem;padding:3px 8px">가까운 곳</span>
      <span class="chip" style="font-size:.58rem;padding:3px 8px">＋</span><span class="chip" style="font-size:.58rem;padding:3px 8px">＋＋</span></div>
    <span class="lbl" style="left:8px;top:8px">지도 44%</span>
  </div>
  <div class="sheet" style="flex:1;position:relative">
    <span class="lbl" style="left:8px;top:6px">피드 (가로 스크롤)</span>
    <div style="padding:20px 10px 6px"><div class="ln m" style="height:9px"></div></div>
    <div class="hscroll">{card(hero=True, stamp=True)}{card()}</div>
  </div>
  <div class="tabbar">필터 · 2</div>
</div>'''

mob2 = f'''<div class="wf mob" style="display:flex;flex-direction:column;position:relative">
  <div class="bar" style="height:34px"><b style="color:var(--ink)">갈래말래</b>
    <span style="margin-left:auto;border:1.5px solid var(--w3);border-radius:99px;padding:1px 8px;font-size:.62rem">서울 ▾</span></div>
  <div class="stage" data-map="300,320,122,14,120,3" style="position:relative;height:auto;flex:1">
    <div class="chipbar" style="bottom:8px"><span class="chip on" style="font-size:.58rem;padding:3px 8px">가까운 곳</span>
      <span class="chip" style="font-size:.58rem;padding:3px 8px">＋</span><span class="chip" style="font-size:.58rem;padding:3px 8px">＋＋</span></div>
    <span class="lbl" style="left:8px;top:8px">지도 (시트 아래로 계속)</span>
  </div>
  <div class="sheet" style="flex:0 0 250px;position:relative;border-radius:14px 14px 0 0;margin-top:-14px;
    box-shadow:0 -6px 18px #0001">
    <div class="grab"></div>
    <span class="lbl" style="right:8px;top:8px">↕ 3단</span>
    <div style="padding:2px 10px 6px"><div class="ln m" style="height:9px"></div></div>
    <div style="padding:0 10px">{card(hero=True, stamp=True)}{card()}</div>
  </div>
</div>'''

rows = "".join(
    f'<tr><td>{a}</td><td><span class="k {"fix" if b=="확정" else ("non" if b=="미정" else "inh")}">{b}</span></td>'
    f'<td style="color:var(--sub);font-size:.8rem">{c}</td><td style="color:var(--sub)">{d}</td></tr>'
    for a, b, c, d in AUDIT)

out = (HTML.replace("__AUDIT__", rows).replace("__DESKTOP__", desktop)
       .replace("__MOB1__", mob1).replace("__MOB2__", mob2)
       .replace("__N__", str(n_sel))
       .replace("__D3A__", d3a).replace("__D3G__", d3g)
       .replace("__WORLD__", world).replace("__DEALS__", json.dumps(D, ensure_ascii=False)))
OUT.write_text(out, encoding="utf-8")
print(f"생성: {OUT}  ({len(out)/1024:.0f}KB) · 서울 딜 {n_sel}건")
