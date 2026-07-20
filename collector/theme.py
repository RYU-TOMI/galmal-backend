# -*- coding: utf-8 -*-
"""갈래말래 공용 페이지 셸 — CSS와 <head> 메타를 index/노선 페이지가 공유.

색상은 dataviz 팔레트 검증 통과값:
  라이트 브랜드 #23538F / 특가 #D9482B (surface #FAF6EF)
  다크   브랜드 #5D8FE0 / 특가 #E85D35 (surface #121820)
"""

BASE_URL = "https://ryu-tomi.github.io/promo-ticket-site"
SUBSCRIBE_ADDR = "flightpromokr@gmail.com"
SITE_NAME = "갈래말래"

CSS = """
  :root {
    --bg:#FAF6EF; --card:#FFFFFF; --ink:#1E2B3C; --sub:#5C6878;
    --brand:#23538F; --deal:#D9482B; --line:#E7E1D5; --chip:#F0EAE0;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#121820; --card:#1B2430; --ink:#E8ECF2; --sub:#97A3B2;
            --brand:#5D8FE0; --deal:#E85D35; --line:#2A3442; --chip:#232E3E; }
  }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--bg); color:var(--ink);
         font-family:'Pretendard Variable',Pretendard,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
         line-height:1.55; padding:28px 16px 56px; }
  main { max-width:1000px; margin:0 auto; }
  a { color:var(--brand); }

  .topbar { display:flex; align-items:baseline; gap:12px; margin-bottom:6px; }
  .brand { font-size:1.6rem; font-weight:900; letter-spacing:-0.02em;
           text-decoration:none; color:var(--ink); }
  .brand em { font-style:normal; color:var(--brand); }
  header .tagline { color:var(--sub); }
  header h1 { font-size:1.9rem; font-weight:900; letter-spacing:-0.02em; margin-top:6px; }
  .stats { display:flex; gap:14px; flex-wrap:wrap; margin:14px 0 22px;
           color:var(--sub); font-size:.82rem; }
  .stats span b { color:var(--ink); font-weight:700; }
  .crumb { color:var(--sub); font-size:.85rem; margin-bottom:10px; }
  .crumb a { text-decoration:none; }

  .chips { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px; }
  .chip { background:var(--chip); color:var(--sub); border:none; font-weight:600;
          padding:7px 14px; border-radius:99px; cursor:pointer; font-size:.88rem;
          font-family:inherit; }
  .chip.active { background:var(--brand); color:#fff; }

  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px; }
  .card { background:var(--card); border-radius:16px; overflow:hidden;
          box-shadow:0 1px 3px rgba(20,30,50,.07); display:flex; flex-direction:column; }
  .card-main { padding:18px 18px 10px; }
  .card-top { display:flex; gap:6px; margin-bottom:10px; }
  .badge { font-size:.74rem; font-weight:800; padding:3px 9px; border-radius:99px; }
  .discount { background:var(--deal); color:#fff; }
  .direct { background:var(--brand); color:#fff; }
  .transfer { background:var(--chip); color:var(--sub); }
  .route { display:flex; align-items:baseline; gap:10px; font-size:1.45rem; font-weight:800;
           letter-spacing:-0.01em; }
  .route a { color:inherit; text-decoration:none; }
  .route .plane { color:var(--brand); font-size:1rem; }
  .dates { color:var(--sub); font-size:.85rem; margin-top:4px; }

  .spark { margin-top:12px; }
  .spark-plot { position:relative; }
  .spark svg { width:100%; height:34px; display:block; }
  .spark-line { fill:none; stroke:var(--brand); stroke-width:2;
                stroke-linecap:round; stroke-linejoin:round; }
  .spark-area { fill:var(--brand); opacity:.1; }
  .spark-dot { position:absolute; right:calc(4.2% - 5px); width:8px; height:8px;
               margin-top:-4px; border-radius:50%; background:var(--deal);
               border:2px solid var(--card); }
  .spark-label { color:var(--sub); font-size:.72rem; }

  .tear { border-top:2px dashed var(--line); position:relative; margin:6px 0 0; }
  .tear::before, .tear::after { content:""; position:absolute; top:-9px; width:18px; height:18px;
    background:var(--bg); border-radius:50%; }
  .tear::before { left:-9px; }
  .tear::after { right:-9px; }

  .card-stub { display:flex; align-items:center; gap:10px; padding:12px 18px 16px; }
  .fare { display:flex; flex-direction:column; flex:1; }
  .price { font-size:1.5rem; font-weight:900; letter-spacing:-0.02em; }
  .price small { font-size:.9rem; font-weight:700; }
  .median { color:var(--sub); font-size:.78rem; text-decoration:line-through; }
  .carrier { color:var(--sub); font-size:.82rem; }
  .cta { background:var(--deal); color:#fff; text-decoration:none; font-weight:800;
         padding:10px 18px; border-radius:12px; font-size:.95rem; }
  .empty { color:var(--sub); padding:28px 0; }

  section { margin-top:44px; }
  section h2 { font-size:1.15rem; margin-bottom:6px; }
  section .lead { color:var(--sub); font-size:.88rem; margin-bottom:14px; }
  section.mail ul { list-style:none; padding:0; display:flex; flex-direction:column; gap:8px; }
  section.mail li { background:var(--card); border-radius:12px; padding:11px 15px; font-size:.9rem; }
  .sender { font-weight:800; margin-right:8px; }
  .until { color:var(--deal); font-size:.8rem; }
  section.mail a { color:var(--brand); font-weight:700; text-decoration:none; }

  /* 노선 페이지 */
  .hero { background:var(--card); border-radius:16px; padding:22px; display:flex;
          flex-wrap:wrap; gap:22px; align-items:flex-end; }
  .hero .figure { font-size:2.6rem; font-weight:900; letter-spacing:-0.03em; line-height:1.1; }
  .hero .figure small { font-size:1rem; font-weight:700; }
  .hero .cap { color:var(--sub); font-size:.85rem; }
  .hero .col { display:flex; flex-direction:column; gap:2px; }
  .chart { background:var(--card); border-radius:16px; padding:18px; }
  .chart svg { width:100%; height:auto; display:block; }
  .axis { fill:var(--sub); font-size:11px; font-variant-numeric:tabular-nums; }
  .gridline { stroke:var(--line); stroke-width:1; }
  .plot-line { fill:none; stroke:var(--brand); stroke-width:2;
               stroke-linecap:round; stroke-linejoin:round; }
  .plot-area { fill:var(--brand); opacity:.1; }
  .plot-dot { fill:var(--brand); stroke:var(--card); stroke-width:2; }
  .plot-dot-hi { fill:var(--deal); stroke:var(--card); stroke-width:2; }
  .plot-label { fill:var(--ink); font-size:11px; font-weight:700; }
  .bar { fill:var(--brand); }
  .bar-best { fill:var(--deal); }
  .hit { fill:transparent; }
  table.data { width:100%; border-collapse:collapse; font-size:.9rem; }
  table.data th, table.data td { text-align:left; padding:9px 10px;
    border-bottom:1px solid var(--line); }
  table.data th { color:var(--sub); font-weight:600; font-size:.82rem; }
  table.data td.num { text-align:right; font-variant-numeric:tabular-nums; }
  .routelist { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:8px;
               list-style:none; padding:0; }
  .routelist a { display:block; background:var(--card); border-radius:10px; padding:10px 13px;
    text-decoration:none; color:var(--ink); font-size:.9rem; font-weight:600; }
  .routelist .rl-price { color:var(--sub); font-weight:500; font-size:.82rem; }

  section.subscribe { background:var(--card); border-radius:16px; padding:22px;
    border:2px dashed var(--line); }
  section.subscribe p { color:var(--sub); font-size:.9rem; margin-bottom:12px; }
  .sub-form { display:flex; gap:8px; flex-wrap:wrap; }
  .sub-form select { flex:1; min-width:220px; padding:11px; border-radius:12px;
    border:1px solid var(--line); background:var(--bg); color:var(--ink);
    font-size:.95rem; font-family:inherit; }
  .sub-form button { background:var(--brand); color:#fff; border:none; font-weight:800;
    padding:11px 20px; border-radius:12px; cursor:pointer; font-size:.95rem; font-family:inherit; }
  .hint { font-size:.78rem !important; margin-top:10px; margin-bottom:0 !important; }

  footer { margin-top:48px; color:var(--sub); font-size:.78rem;
           border-top:1px solid var(--line); padding-top:16px; }
  footer p { margin-bottom:6px; }
"""

FOOTER = f"""  <footer>
    <p>· 가격은 조회 시점 기준이며 실제 예약 가격은 예약처에서 달라질 수 있습니다.</p>
    <p>· "예약" 링크를 통해 예약이 이루어지면 운영자가 수수료를 받을 수 있습니다.</p>
    <p>· 시세는 해당 노선·유형(직항/경유)의 최근 30일 수집 가격 중앙값입니다. 데이터: Travelpayouts(Aviasales)</p>
    <p>· {SITE_NAME} · 문의 {SUBSCRIBE_ADDR}</p>
  </footer>"""


def page(title, description, canonical_path, body, extra_script=""):
    """공통 <head>/<body> 셸. canonical_path 예: '/' 또는 '/routes/ICN-FUK.html'"""
    url = BASE_URL + canonical_path
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS}</style>
{extra_script}
</head>
<body>
<main>
{body}
{FOOTER}
</main>
</body>
</html>"""
