# -*- coding: utf-8 -*-
"""prices.db의 특가 판정 결과로 정적 웹 피드(docs/index.html) 생성.

브랜드: 갈래말래 — 보딩패스 스타일 카드 + 노선별 30일 가격 스파크라인 + 지역 필터.
GitHub Pages(main 브랜치 /docs)로 서빙되며, Actions 크론이 매일 재생성해 커밋.
사용: python collector/build_site.py
"""
import html
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import db
from detect_deals import IS_DIRECT_SQL, compute_deals

SUBSCRIBE_ADDR = "flightpromokr@gmail.com"
OUT = Path(__file__).resolve().parent.parent / "docs" / "index.html"
KST = timezone(timedelta(hours=9))
WEEKDAY = "월화수목금토일"

CITY = {
    "ICN": "인천", "GMP": "김포", "CJU": "제주",
    "NRT": "도쿄", "KIX": "오사카", "FUK": "후쿠오카", "OKA": "오키나와",
    "CTS": "삿포로", "NGO": "나고야", "TPE": "타이베이", "HKG": "홍콩",
    "BKK": "방콕", "DAD": "다낭", "SGN": "호치민", "HAN": "하노이",
    "MNL": "마닐라", "CEB": "세부", "SIN": "싱가포르", "KUL": "쿠알라룸푸르",
    "DPS": "발리", "GUM": "괌", "CDG": "파리", "LHR": "런던", "FCO": "로마",
    "BCN": "바르셀로나", "JFK": "뉴욕", "LAX": "로스앤젤레스", "SYD": "시드니",
}
AIRLINE = {
    "7C": "제주항공", "LJ": "진에어", "TW": "티웨이항공", "BX": "에어부산",
    "RS": "에어서울", "ZE": "이스타항공", "YP": "에어프레미아",
    "KE": "대한항공", "OZ": "아시아나항공", "VN": "베트남항공",
    "VJ": "비엣젯", "5J": "세부퍼시픽", "CA": "에어차이나", "MU": "중국동방항공",
    "CI": "중화항공", "BR": "에바항공", "CX": "캐세이퍼시픽", "TG": "타이항공",
    "SQ": "싱가포르항공", "MH": "말레이시아항공", "PR": "필리핀항공",
    "NH": "전일본공수", "JL": "일본항공", "ZG": "집에어",
}
REGION = {
    "NRT": "jp", "KIX": "jp", "FUK": "jp", "OKA": "jp", "CTS": "jp", "NGO": "jp",
    "TPE": "cn", "HKG": "cn",
    "BKK": "sea", "DAD": "sea", "SGN": "sea", "HAN": "sea", "MNL": "sea",
    "CEB": "sea", "SIN": "sea", "KUL": "sea", "DPS": "sea",
    "CDG": "eu", "LHR": "eu", "FCO": "eu", "BCN": "eu",
    "JFK": "am", "LAX": "am", "SYD": "am",
    "GUM": "dom", "CJU": "dom",
}
REGION_CHIPS = [("all", "전체"), ("jp", "일본"), ("sea", "동남아"), ("cn", "중화권"),
                ("eu", "유럽"), ("am", "미주·대양주"), ("dom", "국내·괌")]


def city(code):
    return CITY.get(code, code)


def airline_name(code):
    return AIRLINE.get(code, code)


def fmt_date(iso):
    """'2026-07-18' -> '7.18(토)'"""
    try:
        d = date.fromisoformat(iso)
        return f"{d.month}.{d.day}({WEEKDAY[d.weekday()]})"
    except (ValueError, TypeError):
        return iso or ""


def sparkline(conn, d):
    """딜과 같은 노선·유형의 최근 30일 일별 최저가 스파크라인 SVG.

    dataviz 규격: 2px 라인, 10% 영역 채움, 끝점 r4 + 2px 서피스 링, 단일 시리즈.
    """
    cond = IS_DIRECT_SQL if d["is_direct"] else f"NOT {IS_DIRECT_SQL}"
    since = (date.today() - timedelta(days=30)).isoformat()
    rows = conn.execute(
        f"""SELECT fetched_date, MIN(price) FROM offers
            WHERE origin=? AND destination=? AND fetched_date>=? AND {cond}
            GROUP BY fetched_date ORDER BY fetched_date""",
        (d["origin"], d["destination"], since)).fetchall()
    if len(rows) < 2:
        return ""
    prices = [p for _, p in rows]
    pmin, pmax = min(prices), max(prices)
    w, h, pad = 120, 34, 5
    span = (pmax - pmin) or 1
    pts = []
    for i, p in enumerate(prices):
        x = pad + i * (w - 2 * pad) / (len(prices) - 1)
        y = h - pad - (p - pmin) / span * (h - 2 * pad)
        pts.append((round(x, 1), round(y, 1)))
    line = " ".join(f"{x},{y}" for x, y in pts)
    area = f"{pad},{h - pad} {line} {pts[-1][0]},{h - pad}"
    ey = pts[-1][1]
    # 끝점은 SVG 밖 HTML 오버레이로 — preserveAspectRatio=none의 가로 늘어남에 왜곡되지 않게
    return f"""
      <div class="spark">
        <div class="spark-plot">
          <svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">
            <polygon points="{area}" class="spark-area"/>
            <polyline points="{line}" class="spark-line" vector-effect="non-scaling-stroke"/>
          </svg>
          <span class="spark-dot" style="top:{ey / h * 100:.1f}%"></span>
        </div>
        <span class="spark-label">최근 {len(prices)}일 최저 {pmin:,}원 ~ {pmax:,}원</span>
      </div>"""


def deal_card(conn, d):
    kind = "직항" if d["is_direct"] else \
        f"경유 {max(d['transfers'], d['return_transfers'])}회"
    kind_cls = "direct" if d["is_direct"] else "transfer"
    region = REGION.get(d["destination"], "etc")
    return f"""
    <article class="card" data-region="{region}">
      <div class="card-main">
        <div class="card-top">
          <span class="badge discount">-{d['discount_pct']}%</span>
          <span class="badge {kind_cls}">{kind}</span>
        </div>
        <div class="route">
          <span class="city">{city(d['origin'])}</span>
          <span class="plane">✈</span>
          <span class="city">{html.escape(city(d['destination']))}</span>
        </div>
        <p class="dates">{fmt_date(d['depart_date'])} 출발 · {fmt_date(d['return_date'])} 귀국 · 왕복</p>
        {sparkline(conn, d)}
      </div>
      <div class="tear"></div>
      <div class="card-stub">
        <div class="fare">
          <span class="price">{d['price']:,}<small>원</small></span>
          <span class="median">시세 {d['median']:,}원</span>
        </div>
        <span class="carrier">{html.escape(airline_name(d['airline']))}</span>
        <a class="cta" href="{html.escape(d['link'])}" target="_blank" rel="noopener sponsored">Aviasales 예약</a>
      </div>
    </article>"""


def mail_deal_rows(conn):
    rows = conn.execute(
        """SELECT airline, origin, destination, price_krw, promo_end, summary, url
           FROM mail_deals ORDER BY id DESC LIMIT 20""").fetchall()
    out = []
    for airline, origin, dest, price, promo_end, summary, url in rows:
        parts = [f"<span class='sender'>{html.escape(airline or '항공사')}</span>",
                 html.escape(summary)]
        if price:
            parts.append(f"<strong>{price:,}원~</strong>")
        if promo_end:
            parts.append(f"<span class='until'>~{html.escape(promo_end)}</span>")
        body = " ".join(parts)
        if url:
            body += f" <a href='{html.escape(url)}' target='_blank' rel='noopener'>공식 이벤트 →</a>"
        out.append(f"<li>{body}</li>")
    return "\n".join(out)


def mail_rows(conn):
    rows = conn.execute(
        """SELECT received_at, sender, subject FROM emails
           ORDER BY id DESC LIMIT 8""").fetchall()
    out = []
    for received, sender, subject in rows:
        name = sender.split("<")[0].strip().strip('"') or sender
        out.append(f"<li><span class='sender'>{html.escape(name)}</span> "
                   f"{html.escape(subject)}</li>")
    return "\n".join(out)


def route_options():
    opts = ['<option value="ALL">✈️ 전체 노선</option>']
    for origin, dest in config.ROUTES:
        code = f"{origin}-{dest}"
        opts.append(f'<option value="{code}">{city(origin)} → {city(dest)} ({code})</option>')
    return "\n".join(opts)


def main():
    conn = db.connect()
    deals = compute_deals(conn)
    cards = "\n".join(deal_card(conn, d) for d in deals) if deals else \
        "<p class='empty'>오늘은 기준(시세 대비 35% 이상 할인)을 넘는 특가가 없습니다. 내일 아침 다시 스캔합니다.</p>"
    chips = "\n".join(
        f'<button class="chip{" active" if code == "all" else ""}" data-region="{code}">{label}</button>'
        for code, label in REGION_CHIPS)
    mail_deals = mail_deal_rows(conn)
    mails = mail_rows(conn)
    n_offers = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    n_days = conn.execute("SELECT COUNT(DISTINCT fetched_date) FROM offers").fetchone()[0]
    conn.close()
    updated = datetime.now(KST).strftime("%m.%d %H:%M")

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>갈래말래 — 오늘의 항공권 특가</title>
<meta name="description" content="매일 아침 한국 출발 항공권 가격을 스캔해, 시세보다 진짜 싼 특가만 골라 보여드립니다.">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
  :root {{
    --bg:#FAF6EF; --card:#FFFFFF; --ink:#1E2B3C; --sub:#5C6878;
    --brand:#23538F; --deal:#D9482B; --line:#E7E1D5; --chip:#F0EAE0;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#121820; --card:#1B2430; --ink:#E8ECF2; --sub:#97A3B2;
             --brand:#5D8FE0; --deal:#E85D35; --line:#2A3442; --chip:#232E3E; }}
  }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ background:var(--bg); color:var(--ink);
         font-family:'Pretendard Variable',Pretendard,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
         line-height:1.55; padding:28px 16px 56px; }}
  main {{ max-width:1000px; margin:0 auto; }}

  header .brand {{ font-size:2rem; font-weight:900; letter-spacing:-0.02em; }}
  header .brand em {{ font-style:normal; color:var(--brand); }}
  header .tagline {{ color:var(--sub); margin-top:2px; }}
  .stats {{ display:flex; gap:14px; flex-wrap:wrap; margin:14px 0 22px;
            color:var(--sub); font-size:.82rem; }}
  .stats span b {{ color:var(--ink); font-weight:700; }}

  .chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px; }}
  .chip {{ background:var(--chip); color:var(--sub); border:none; font-weight:600;
           padding:7px 14px; border-radius:99px; cursor:pointer; font-size:.88rem;
           font-family:inherit; }}
  .chip.active {{ background:var(--brand); color:#fff; }}

  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px; }}
  .card {{ background:var(--card); border-radius:16px; overflow:hidden;
           box-shadow:0 1px 3px rgba(20,30,50,.07); display:flex; flex-direction:column; }}
  .card-main {{ padding:18px 18px 10px; }}
  .card-top {{ display:flex; gap:6px; margin-bottom:10px; }}
  .badge {{ font-size:.74rem; font-weight:800; padding:3px 9px; border-radius:99px; }}
  .discount {{ background:var(--deal); color:#fff; }}
  .direct {{ background:var(--brand); color:#fff; }}
  .transfer {{ background:var(--chip); color:var(--sub); }}
  .route {{ display:flex; align-items:baseline; gap:10px; font-size:1.45rem; font-weight:800;
            letter-spacing:-0.01em; }}
  .route .plane {{ color:var(--brand); font-size:1rem; }}
  .dates {{ color:var(--sub); font-size:.85rem; margin-top:4px; }}

  .spark {{ margin-top:12px; }}
  .spark-plot {{ position:relative; }}
  .spark svg {{ width:100%; height:34px; display:block; }}
  .spark-line {{ fill:none; stroke:var(--brand); stroke-width:2;
                 stroke-linecap:round; stroke-linejoin:round; }}
  .spark-area {{ fill:var(--brand); opacity:.1; }}
  .spark-dot {{ position:absolute; right:calc(4.2% - 5px); width:8px; height:8px;
                margin-top:-4px; border-radius:50%; background:var(--deal);
                border:2px solid var(--card); }}
  .spark-label {{ color:var(--sub); font-size:.72rem; }}

  .tear {{ border-top:2px dashed var(--line); position:relative; margin:6px 0 0; }}
  .tear::before, .tear::after {{ content:""; position:absolute; top:-9px; width:18px; height:18px;
    background:var(--bg); border-radius:50%; }}
  .tear::before {{ left:-9px; }}
  .tear::after {{ right:-9px; }}

  .card-stub {{ display:flex; align-items:center; gap:10px; padding:12px 18px 16px; }}
  .fare {{ display:flex; flex-direction:column; flex:1; }}
  .price {{ font-size:1.5rem; font-weight:900; letter-spacing:-0.02em; }}
  .price small {{ font-size:.9rem; font-weight:700; }}
  .median {{ color:var(--sub); font-size:.78rem; text-decoration:line-through; }}
  .carrier {{ color:var(--sub); font-size:.82rem; }}
  .cta {{ background:var(--deal); color:#fff; text-decoration:none; font-weight:800;
          padding:10px 18px; border-radius:12px; font-size:.95rem; }}
  .empty {{ color:var(--sub); padding:28px 0; }}

  section {{ margin-top:44px; }}
  section h2 {{ font-size:1.15rem; margin-bottom:12px; }}
  section.mail ul {{ list-style:none; padding:0; display:flex; flex-direction:column; gap:8px; }}
  section.mail li {{ background:var(--card); border-radius:12px; padding:11px 15px; font-size:.9rem; }}
  .sender {{ font-weight:800; margin-right:8px; }}
  .until {{ color:var(--deal); font-size:.8rem; }}
  section.mail a {{ color:var(--brand); font-weight:700; text-decoration:none; }}

  section.subscribe {{ background:var(--card); border-radius:16px; padding:22px;
    border:2px dashed var(--line); }}
  section.subscribe p {{ color:var(--sub); font-size:.9rem; margin-bottom:12px; }}
  .sub-form {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .sub-form select {{ flex:1; min-width:220px; padding:11px; border-radius:12px;
    border:1px solid var(--line); background:var(--bg); color:var(--ink);
    font-size:.95rem; font-family:inherit; }}
  .sub-form button {{ background:var(--brand); color:#fff; border:none; font-weight:800;
    padding:11px 20px; border-radius:12px; cursor:pointer; font-size:.95rem; font-family:inherit; }}
  .hint {{ font-size:.78rem !important; margin-top:10px; margin-bottom:0 !important; }}

  footer {{ margin-top:48px; color:var(--sub); font-size:.78rem;
            border-top:1px solid var(--line); padding-top:16px; }}
  footer p {{ margin-bottom:6px; }}
</style>
<script>
function subscribeMail() {{
  var sel = document.getElementById('route-sel');
  var subject = encodeURIComponent('구독신청');
  var body = encodeURIComponent('노선: ' + sel.value + ' (' + sel.selectedOptions[0].text + ')\\n\\n이 메일을 그대로 보내주시면 구독이 신청됩니다.');
  location.href = 'mailto:{SUBSCRIBE_ADDR}?subject=' + subject + '&body=' + body;
}}
document.addEventListener('DOMContentLoaded', function() {{
  var chips = document.querySelectorAll('.chip');
  chips.forEach(function(chip) {{
    chip.addEventListener('click', function() {{
      chips.forEach(function(c) {{ c.classList.remove('active'); }});
      chip.classList.add('active');
      var region = chip.dataset.region;
      document.querySelectorAll('.card').forEach(function(card) {{
        card.style.display = (region === 'all' || card.dataset.region === region) ? '' : 'none';
      }});
    }});
  }});
}});
</script>
</head>
<body>
<main>
  <header>
    <div class="brand">갈래<em>말래</em> ✈️</div>
    <p class="tagline">매일 아침 항공권 가격을 스캔해, 시세보다 진짜 싼 특가만.</p>
    <div class="stats">
      <span><b>{len(config.ROUTES)}개</b> 노선 감시</span>
      <span>가격 데이터 <b>{n_offers:,}건</b> ({n_days}일치)</span>
      <span>매일 아침 자동 갱신 · 마지막 {updated}</span>
    </div>
  </header>

  <div class="chips">
{chips}
  </div>

  <div class="grid">
{cards}
  </div>

  <section class="subscribe">
    <h2>🔔 노선 특가 알림 받기</h2>
    <p>원하는 노선에 특가가 뜨면 메일로 알려드립니다. 노선을 고르고 버튼을 누르면
       메일 앱이 열립니다 — <b>내용 수정 없이 그대로 보내주시면</b> 다음 수집부터 적용됩니다.</p>
    <div class="sub-form">
      <select id="route-sel">
{route_options()}
      </select>
      <button onclick="subscribeMail()">메일로 구독 신청</button>
    </div>
    <p class="hint">해지: 같은 주소로 제목 '구독취소' 메일을 보내주세요.
       특정 노선만 해지하려면 본문에 노선 코드를 적어주세요.</p>
  </section>

  <section class="mail">
    <h2>🎫 항공사 프로모션</h2>
    <ul>
{mail_deals if mail_deals else "<li class='empty'>수집된 프로모션이 아직 없습니다.</li>"}
    </ul>
  </section>

  <section class="mail">
    <h2>📬 항공사 소식</h2>
    <ul>
{mails}
    </ul>
  </section>

  <footer>
    <p>· 가격은 조회 시점 기준이며 실제 예약 가격은 예약처에서 달라질 수 있습니다.</p>
    <p>· "Aviasales 예약" 링크를 통해 예약이 이루어지면 운영자가 수수료를 받을 수 있습니다.</p>
    <p>· 시세는 해당 노선·유형(직항/경유)의 최근 30일 수집 가격 중앙값입니다. 데이터: Travelpayouts(Aviasales)</p>
    <p>· 갈래말래 · 문의 {SUBSCRIBE_ADDR}</p>
  </footer>
</main>
</body>
</html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"생성 완료: {OUT} (특가 {len(deals)}건)")


if __name__ == "__main__":
    main()
