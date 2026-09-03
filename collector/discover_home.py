# -*- coding: utf-8 -*-
"""발견 홈(docs/index.html) 렌더러 — 지도+피드+필터 도크 셸.

데이터(deals.json)·지도(world.geojson)를 인라인해 file://에서도 열린다.
스타일은 assets/discover.css, 로직은 assets/discover.js.
"""
import html

from labels import city
from theme import BASE_URL, OG_IMAGE, SITE_NAME

# "말래" 밑 페이드 비행운 + 접힌 종이비행기 (theme.logo와 동일 기하)
LOGO_SVG = (
    '<svg class="lg" viewBox="0 0 170 46" overflow="visible" aria-hidden="true">'
    '<defs><linearGradient id="gmlg" x1="0" x2="1">'
    '<stop offset="0" stop-color="#F2603F" stop-opacity="0"/>'
    '<stop offset="1" stop-color="#F2603F" stop-opacity=".95"/></linearGradient></defs>'
    '<path d="M6,34 Q76,40 114,19" fill="none" stroke="url(#gmlg)" stroke-width="3" stroke-linecap="round"/>'
    '<g transform="translate(120,16) rotate(-28.6) scale(1.02)">'
    '<path class="pl-btm" d="M13,0 L-4,0 L-11,8 Z"/>'
    '<path class="pl-top" d="M13,0 L-11,-8 L-4,0 Z"/>'
    '<path class="pl-crease" d="M13,0 L-4,0"/></g></svg>'
)

FILTER_DOCK = """
    <div class="filterdock" id="fdock">
      <button type="button" class="fdtoggle" id="fdtoggle"><span id="fdsum">필터</span><i>▾</i></button>
      <div class="fdbody">
        <div class="fdrow"><span class="fdlabel">언제 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip date on" data-date="">아무때</button>
            <button type="button" class="fchip date" data-date="이번 주말">이번 주말<i></i></button>
            <button type="button" class="fchip date" data-date="다음 주말">다음 주말<i></i></button>
            <button type="button" class="fchip date" data-date="이번 주">이번 주<i></i></button>
            <button type="button" class="fchip date" data-date="이번 달">이번 달<i></i></button>
            <button type="button" class="fchip date" data-date="다음 달">다음 달<i></i></button>
            <button type="button" class="fchip date" data-date="rest">그 이후<i></i></button>
            <button type="button" class="fchip date" data-date="custom">날짜 지정</button>
          </div>
          <div class="customdates" id="customdates">
            <input type="date" id="cdStart"><span>~</span><input type="date" id="cdEnd">
          </div></div>
        <div class="fdrow"><span class="fdlabel">며칠 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip nights on" data-nights="">상관없어</button>
            <button type="button" class="fchip nights" data-nights="1-3">1~3박<i></i></button>
            <button type="button" class="fchip nights" data-nights="4-6">4~6박<i></i></button>
            <button type="button" class="fchip nights" data-nights="7-13">7~13박<i></i></button>
            <button type="button" class="fchip nights" data-nights="14+">2주 이상<i></i></button>
          </div></div>
        <div class="fdrow"><span class="fdlabel">분위기</span>
          <div class="chips">
            <button type="button" class="fchip moodf" data-mood="해변">해변<i></i></button>
            <button type="button" class="fchip moodf" data-mood="도시">도시<i></i></button>
            <button type="button" class="fchip moodf" data-mood="미식">미식<i></i></button>
            <button type="button" class="fchip moodf" data-mood="자연">자연<i></i></button>
            <button type="button" class="fchip moodf" data-mood="문화">문화<i></i></button>
            <button type="button" class="fchip moodf" data-mood="온천">온천<i></i></button>
          </div></div>
        <div class="fdrow"><span class="fdlabel">예산</span>
          <div class="budgetwrap">
            <div class="btrack"><div class="bhist" id="bhist" aria-hidden="true"></div><input id="budget" type="range" min="100000" max="1000000" step="50000" value="1000000"></div>
            <b id="budgetVal">제한 없음</b></div>
          <div class="chips">
            <button type="button" class="fchip budget" data-budget="300000">30만<i></i></button>
            <button type="button" class="fchip budget" data-budget="500000">50만<i></i></button>
            <button type="button" class="fchip budget" data-budget="1000000">100만<i></i></button>
            <button type="button" class="fchip budget on" data-budget="">상관없어</button>
          </div></div>
      </div>
    </div>"""


def render_home(data, deals_json, world_json, route_index):
    updated = html.escape(data.get("updated", ""))
    deals = data.get("deals", [])
    top = sorted(deals, key=lambda x: x["price"])[:30]
    ns_deals = "\n".join(
        f"      <li>{html.escape(d['ko'])} · {d['price']:,}원~ · {html.escape(d['when'])} 출발</li>"
        for d in top) or "      <li>수집된 특가가 아직 없습니다.</li>"
    ns_routes = "\n".join(
        f'      <li><a href="{BASE_URL}/routes/{code}.html">{html.escape(city(code[:3]))} → '
        f'{html.escape(city(code[4:]))} 최저가 분석</a></li>'
        for code, _ in route_index)

    title = f"{SITE_NAME} — 어디, 갈까? 항공권 특가 발견 지도"
    desc = ("시간 남는데 어디 싸게 갈까? 한국 출발 항공권을 매일 스캔해 지도에서 "
            "오늘 싼 여행지를 골라줍니다. 목적지를 정해주는 발견 서비스.")
    # 공유 카드(OG) — `<title>`·`description`을 재사용하지 않는다. 자리가 다르다. (COPY.md §2c)
    #   `<title>`은 **검색 결과**에 뜬다 → 검색어가 들어간다.
    #   `og:title`은 **카톡 말풍선**이다 → 이미 아는 사람이 친구에게 보내는 자리라 태그라인만 쓴다.
    #   `og:description`은 위 74자를 그대로 못 쓴다 — 카톡이 두 줄쯤에서 자른다.
    og_title = f"{SITE_NAME} — 어디, 갈까?"
    og_desc = ("시간 남는데 싸게 다녀올 곳. 한국 출발 항공권을 매일 스캔해 "
               "오늘 싼 여행지를 지도에 펼칩니다.")

    scripts = (
        f"<script>window.__DEALS={deals_json};</script>\n"
        f"<script>window.__WORLD={world_json};</script>\n"
        '<script src="assets/d3-array.min.js"></script>\n'
        '<script src="assets/d3-geo.min.js"></script>\n'
        '<script src="assets/discover.js"></script>'
    )

    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{BASE_URL}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{BASE_URL}/">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME} — 어디, 갈까? 세계 지도에 오늘 싼 여행지가 찍혀 있다">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/discover.css">
</head><body>
<div class="hdr">
  <span class="gm-logo">갈래<em>말래</em>{LOGO_SVG}</span>
  <span class="nav"><span class="on">발견</span><span class="muted">노선별</span></span>
  <span class="tools"><span class="originwrap">
    <button type="button" class="pill origin" id="originPill" aria-haspopup="listbox" aria-expanded="false">출발지 ▾</button>
    <div class="origindrop" id="originDrop" role="listbox" hidden></div>
  </span></span>
</div>
<div class="firstnote" id="firstnote" hidden>
  <span id="fnText"></span>
  <button type="button" class="fn-go" id="fnChange">바꾸기</button>
  <button type="button" class="fn-x" id="fnClose" aria-label="이 안내 닫기">×</button>
</div>
<div class="layout">
  <div class="feed" id="feed"></div>
  <div class="stage">
    <svg class="map" id="map" preserveAspectRatio="xMidYMid slice" role="img" aria-label="여행지 발견 지도">
      <g id="lands"></g><path id="arc" class="arc" d=""/><g id="origin"></g><g id="pins"></g>
    </svg>
    <div class="prompt"><b>카드에 올리면</b> 지도에 항로가 · <b>핀 클릭</b>하면 상세가 열려요</div>
    <div class="stagebar"><span class="pill on">가까운 곳</span><span class="pill">조금 더 멀리</span><span class="pill">아주 멀리</span></div>
    <div class="stepper" id="stepper">
      <button type="button" data-step="out" aria-label="더 멀리" title="더 멀리"><i>＋</i><em>더 멀리</em></button>
      <button type="button" data-step="in" aria-label="가까이" title="가까이"><i>－</i><em>가까이</em></button>
    </div>{FILTER_DOCK}
    <div class="hovercard" id="hc"></div>
  </div>
</div>
<noscript>
  <div class="noscript-fallback">
    <p class="ns-note">JavaScript가 꺼져 있어 지도를 표시하지 못했습니다. 오늘의 특가와 노선별 분석은 아래에서 볼 수 있어요. (갱신 {updated})</p>
    <h2>오늘의 특가</h2>
    <ul>
{ns_deals}
    </ul>
    <h2>노선별 최저가 분석</h2>
    <ul>
{ns_routes}
    </ul>
  </div>
</noscript>
{scripts}
</body></html>"""
