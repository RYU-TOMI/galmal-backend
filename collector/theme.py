# -*- coding: utf-8 -*-
"""갈래말래 공용 페이지 셸 — CSS와 <head> 메타를 index/노선 페이지가 공유.

색상은 dataviz 팔레트 검증 통과값:
  라이트 브랜드 #23538F / 특가 #D9482B (surface #FAF6EF)
  다크   브랜드 #5D8FE0 / 특가 #E85D35 (surface #121820)
"""
import html
import json

# 사이트 정본 주소. canonical · og:url · sitemap · JSON-LD · 알림 메일이 전부
# 여기서 파생된다. **도메인 문자열은 이 저장소에서 여기 한 곳뿐이다** — 갈라지면
# 어떤 화면은 옛 주소를, 어떤 화면은 새 주소를 가리키게 된다.
#
# 2026-09-05 `galmal.kr`로 전환. 커스텀 도메인 파일은 `docs/CNAME`에 있고 GitHub이
# Pages 설정에서 만든다. `build_site.py`는 `docs/`를 지우지 않으므로(덮어쓰기만)
# 크론 재빌드가 그 파일을 날리지 않는다 — 날아가면 사이트가 죽는 게 아니라 404가 된다.
BASE_URL = "https://galmal.kr"
SUBSCRIBE_ADDR = "flightpromokr@gmail.com"
SITE_NAME = "갈래말래"

# 링크 미리보기(카카오톡·슬랙·X) 썸네일. **절대 URL이어야 한다** — 상대 경로면
# 크롤러가 못 읽어 미리보기가 백지가 된다. 한국에서 링크는 카톡으로 도니 유입에
# 직접 영향이 있다.
#
# 노선별로 다르게 굽지 않는다. OG는 래스터(PNG)여야 하는데 Pillow도 Node도 없고,
# 넣으면 "런타임 의존 0 / Node 금지"와 부딪힌다(`CLAUDE.md`). 정적 1장으로 간다.
# 원본과 재생성 스크립트는 기획 구역이다 — `design/og.png` · `python design/build_og.py`.
# 크론은 `build_site.py`만 부르므로 이 파일은 빌드 의존이 아니다.
OG_IMAGE = BASE_URL + "/assets/og.png"


# 검색엔진 소유확인 메타 태그. 서치콘솔·서치어드바이저가 주는 값을 여기 넣으면
# 모든 페이지 <head>에 나간다.
#
# **비밀이 아니다.** 서비스가 우리 HTML을 읽어 확인하는 공개값이라 커밋해도 된다.
# (시크릿은 `TP_TOKEN`·메일 비밀번호 쪽이고 그건 `.env`에 있다.)
#
# ⚠️ 구글은 이게 **필요 없을 수 있다.** 서치콘솔에 **도메인 속성**(`galmal.kr`)으로
#    등록하면 DNS TXT 레코드로 확인하고, 서브도메인과 http/https 변형을 전부 덮는다.
#    HTML 태그는 **URL 접두어 속성**일 때만 쓴다. 도메인을 우리가 소유하고 DNS도
#    직접 만지므로 도메인 속성 쪽이 낫다 — 그 경우 여기는 비워 둔다.
SITE_VERIFICATION = {
    # 구글은 **도메인 속성**으로 등록해 DNS TXT로 확인한다 — 여기 태그가 필요 없다.
    # URL 접두어 속성으로 바꿀 일이 생기면 그때 아래 줄을 살린다.
    # "google-site-verification": "…",
    "naver-site-verification": "bebd1abc617405ec549b1d6d94eca8da36df8d6a",
}


def verification_meta():
    """소유확인 태그들.

    설정된 게 없으면 **빈 문자열**이라 `<head>`에 빈 줄도 안 남고, 있으면 끝에
    줄바꿈을 붙여 다음 태그가 같은 줄에 붙지 않게 한다. 둘 다 안 하면 하나는
    깨진다 — 빈 줄이 남거나, `<link rel="canonical">`이 메타 태그에 들러붙는다.
    """
    tags = "\n".join(
        f'<meta name="{html.escape(k)}" content="{html.escape(v)}">'
        for k, v in SITE_VERIFICATION.items() if v)
    return tags + "\n" if tags else ""


ACCENT = "#F2603F"

# 로고 항적/비행기 기하 (DESIGN.md). "말래" 밑 페이드 비행운 + 접힌 종이비행기.
import math as _math
_P0, _P1, _P2 = (6, 34), (76, 40), (120, 16)
_ANG = _math.degrees(_math.atan2(2 * (_P2[1] - _P1[1]), 2 * (_P2[0] - _P1[0])))
_PLANE = (f'<g transform="translate({_P2[0]},{_P2[1]}) rotate({_ANG:.1f}) scale(1.02)">'
          '<path class="pl-btm" d="M13,0 L-4,0 L-11,8 Z"/>'
          '<path class="pl-top" d="M13,0 L-11,-8 L-4,0 Z"/>'
          '<path class="pl-crease" d="M13,0 L-4,0"/></g>')


def logo(gid="gm", href=None):
    """워드마크 갈래말래 + 비행운 + 종이비행기. gid는 그라디언트 id 충돌 방지용."""
    svg = (f'<svg class="lg" viewBox="0 0 170 46" overflow="visible" aria-hidden="true">'
           f'<defs><linearGradient id="{gid}" x1="0" x2="1">'
           f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>'
           f'<stop offset="1" stop-color="{ACCENT}" stop-opacity=".95"/></linearGradient></defs>'
           f'<path d="M{_P0[0]},{_P0[1]} Q{_P1[0]},{_P1[1]} {_P2[0]-6},{_P2[1]+3}" '
           f'fill="none" stroke="url(#{gid})" stroke-width="3" stroke-linecap="round"/>{_PLANE}</svg>')
    inner = f'갈래<em>말래</em>{svg}'
    if href:
        return f'<a class="gm-logo" href="{href}" aria-label="{SITE_NAME}">{inner}</a>'
    return f'<span class="gm-logo">{inner}</span>'

CSS = """
  :root {
    /* 디자인 시스템 (DESIGN.md) — 시그니처 코랄 */
    --accent:#F2603F; --accent2:#C6472A;
    --sea:#EDF4F3; --land:#D2E7DE; --coast:#33534F; --soft:#F0F5F4;
    --bg:#F4F8F7; --card:#FFFFFF; --ink:#20353A; --sub:#5E7A7C; --line:#E6EDEC;
    /* 하위호환 별칭(기존 클래스용): brand=청록(차트라인), deal=코랄(강조/CTA) */
    --brand:#33534F; --deal:#F2603F; --chip:#F0F5F4; --ocean:#EDF4F3;
    --serif:'Pretendard Variable',Pretendard,sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --accent:#FF7A57; --accent2:#D65A38;
            --sea:#0F2A29; --land:#16403C; --coast:#2A625C; --soft:#1D3634;
            --bg:#0F2A29; --card:#16302E; --ink:#EAF3F0; --sub:#8FB2AD; --line:#26403C;
            --brand:#5FB0B8; --deal:#FF7A57; --chip:#1D3634; --ocean:#0F2A29; }
  }
  * { box-sizing:border-box; margin:0; }
  body { background-color:var(--bg); color:var(--ink);
         background-image:radial-gradient(var(--line) 0.6px, transparent 0.6px);
         background-size:24px 24px;
         font-family:'Pretendard Variable',Pretendard,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
         line-height:1.6; padding:28px 16px 56px; }
  main { max-width:1000px; margin:0 auto; }
  a { color:var(--brand); }

  .topbar { display:flex; align-items:baseline; gap:12px; margin-bottom:6px; }
  .brand { font-family:var(--serif); font-size:1.7rem; font-weight:700;
           letter-spacing:-0.01em; text-decoration:none; color:var(--ink); }
  .brand em { font-style:normal; color:var(--brand); }
  header .tagline { color:var(--sub); font-family:var(--serif); font-size:1.02rem; }
  header h1 { font-family:var(--serif); font-size:2rem; font-weight:700;
              letter-spacing:-0.01em; margin-top:6px; }
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

  section { margin-top:46px; }
  section h2 { font-family:var(--serif); font-size:1.3rem; font-weight:700;
               margin-bottom:8px; display:flex; align-items:center; gap:12px; }
  section h2::after { content:""; flex:1; height:1px; background:var(--line); }
  section .lead { color:var(--sub); font-size:.88rem; margin-bottom:14px; margin-top:-2px; }
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

  /* 발견 지도 */
  .map-stage { margin:10px 0 8px; }
  .map-prompt { font-family:var(--serif); font-size:1.3rem; font-weight:700; margin-bottom:12px; }
  #map { width:100%; height:auto; aspect-ratio:4/3; display:block;
         background:var(--ocean); border:1px solid var(--line); border-radius:18px;
         box-shadow:inset 0 1px 6px rgba(0,0,0,.05); }
  #map .land { fill:var(--land); stroke:#00000018; stroke-width:0.5; }
  #map .halo { fill:var(--deal); opacity:.14; }
  #map .air-dot { fill:var(--deal); stroke:var(--card); stroke-width:2.5;
                  cursor:pointer; transition:r .12s; }
  #map .airport:hover .air-dot { r:11; }
  #map .air-label { fill:var(--ink); font-size:13px; font-weight:700;
                    font-family:inherit; pointer-events:none;
                    paint-order:stroke; stroke:var(--ocean); stroke-width:3px; }
  .map-note { margin-top:8px; }

  /* ===== 디자인 시스템 컴포넌트 (DESIGN.md) ===== */
  /* 로고 */
  .gm-logo { position:relative; display:inline-block; font-weight:900;
             letter-spacing:-.03em; color:var(--ink); line-height:1; }
  .gm-logo em { font-style:normal; color:var(--accent); }
  .gm-logo .lg { position:absolute; left:46%; right:0; bottom:-24%;
                 height:1.1em; overflow:visible; }
  .gm-logo .pl-top { fill:var(--accent); }
  .gm-logo .pl-btm { fill:var(--accent2); }
  .gm-logo .pl-crease { stroke:#ffffff88; stroke-width:.8; fill:none; }
  /* 헤더 */
  .gm-hdr { display:flex; align-items:center; height:60px; padding:0 22px;
            background:var(--card); border-bottom:1px solid var(--line); }
  .gm-hdr .gm-logo { font-size:1.5rem; margin-right:44px; }
  .gm-nav { display:flex; gap:2px; margin-right:auto; }
  .gm-nav a { font-weight:600; font-size:.92rem; color:var(--sub);
              text-decoration:none; padding:8px 12px; border-radius:9px; }
  .gm-nav a.on { color:var(--ink); font-weight:800; }
  .gm-util { display:flex; align-items:center; gap:8px; }
  .gm-util .icon { width:38px; height:38px; border-radius:10px; display:flex;
                   align-items:center; justify-content:center; font-size:1.05rem; }
  .gm-login { font-weight:700; font-size:.88rem; color:var(--ink);
              border:1.5px solid var(--line); padding:8px 15px; border-radius:10px;
              background:none; cursor:pointer; }
  /* 지도 위 검색 패널 */
  .gm-panel { background:var(--card); border-radius:16px; padding:16px;
              box-shadow:0 8px 26px rgba(20,40,40,.14); }
  .gm-panel h2 { font-size:1.35rem; font-weight:900; letter-spacing:-.02em; color:var(--ink); }
  .gm-panel .desc { font-size:.82rem; color:var(--sub); margin:3px 0 12px; }
  .gm-field { display:flex; justify-content:space-between; align-items:center;
              border:1.5px solid var(--line); border-radius:11px; padding:11px 13px;
              font-weight:700; color:var(--ink); font-size:.95rem; margin-bottom:10px; }
  .gm-field .cur { color:var(--sub); font-weight:600; }
  .gm-filterlabel { font-size:.78rem; color:var(--sub); font-weight:700; margin:2px 0 7px; }
  .gm-chips { display:flex; gap:6px; flex-wrap:wrap; }
  .gm-chip { font-size:.82rem; font-weight:700; padding:7px 12px; border-radius:99px;
             background:var(--soft); color:var(--sub); border:none; cursor:pointer; }
  .gm-chip.on { background:var(--accent); color:#fff; }
  /* 줌 컨트롤 */
  .gm-zoom { background:var(--card); border-radius:12px; overflow:hidden;
             box-shadow:0 4px 14px rgba(20,40,40,.14); }
  .gm-zoom button { display:block; width:42px; height:42px; border:none; background:none;
                    font-size:1.3rem; color:var(--ink); cursor:pointer; }
  .gm-zoom button + button { border-top:1px solid var(--line); }
  /* 특가 도장 */
  .gm-stamp { display:inline-block; transform:rotate(-9deg); border:2px solid var(--accent);
              color:var(--accent); font-weight:900; font-size:.72rem; padding:3px 8px; border-radius:6px; }
"""

FOOTER = f"""  <footer>
    <p>· 가격은 조회 시점 기준이며 실제 예약 가격은 예약처에서 달라질 수 있습니다.</p>
    <p>· "예약" 링크를 통해 예약이 이루어지면 운영자가 수수료를 받을 수 있습니다.</p>
    <p>· 시세는 해당 노선·유형(직항/경유)의 최근 30일 수집 가격 중앙값입니다. 데이터: Travelpayouts(Aviasales)</p>
    <p>· {SITE_NAME} · 문의 {SUBSCRIBE_ADDR}</p>
  </footer>"""


def jsonld_block(payload):
    """구조화 데이터 <script> 한 덩이. `payload`가 비면 빈 문자열.

    `</`를 이스케이프하는 게 중요하다 — 문자열 값 안에 `</script>`가 들어오면
    브라우저가 거기서 스크립트를 끝내 버려 페이지가 깨진다. 지금은 우리가 값을
    다 만들지만, 나중에 도시 이름 같은 외부 유래 문자열이 섞이면 터진다.
    """
    if not payload:
        return ""
    body = json.dumps(payload, ensure_ascii=False,
                      separators=(",", ":")).replace("</", "<\/")
    return f'<script type="application/ld+json">{body}</script>'


def page(title, description, canonical_path, body, extra_script="", jsonld=None,
         og_title=None, og_description=None):
    """공통 <head>/<body> 셸. canonical_path 예: '/' 또는 '/routes/ICN-FUK.html'

    `jsonld` — schema.org 구조화 데이터(dict 또는 list). **화면에 실제로 있는 것만
    적는다** — 보이지 않는 내용을 마크업하면 구글이 스팸으로 본다.

    `og_title`·`og_description` — 생략하면 `title`·`description`을 쓴다. **자리가
    다르면 문구도 다르다**: `<title>`은 검색 결과라 검색어가 들어가고, `og:title`은
    카톡 말풍선이라 이미 아는 사람이 친구에게 보내는 자리다. 검색어를 그대로 넣으면
    광고처럼 읽힌다(`COPY.md` §2c).
    """
    url = BASE_URL + canonical_path
    og_title = og_title or title
    og_description = og_description or description
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
{verification_meta()}<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_description}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME} — 어디, 갈까? 세계 지도에 오늘 싼 여행지가 찍혀 있다">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS}</style>
{jsonld_block(jsonld)}
{extra_script}
</head>
<body>
<main>
{body}
{FOOTER}
</main>
</body>
</html>"""
