# -*- coding: utf-8 -*-
"""갈래말래 정적 사이트 생성 — 메인 피드 + 노선별 페이지 + sitemap/robots.

- docs/index.html          : 오늘의 특가 피드
- docs/routes/ICN-FUK.html : 노선별 가격 분석 (검색 유입용 색인 대상)
- docs/sitemap.xml, robots.txt

사용: python collector/build_site.py
"""
import html
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import db
from affiliates import booking_link
from charts import bar_chart, line_chart
from detect_deals import IS_DIRECT_SQL, compute_deals
from labels import (REGION_CHIPS, REGION_NAME, SQL_WEEKDAY, airline_name, city,
                    fmt_date, fmt_month, region_of)
from theme import BASE_URL, SITE_NAME, SUBSCRIBE_ADDR, page

DOCS = Path(__file__).resolve().parent.parent / "docs"
KST = timezone(timedelta(hours=9))


# ---------------------------------------------------------------- 데이터 조회

def daily_min(conn, origin, dest, days=30, direct_only=None):
    since = (date.today() - timedelta(days=days)).isoformat()
    cond = ""
    if direct_only is True:
        cond = f"AND {IS_DIRECT_SQL}"
    elif direct_only is False:
        cond = f"AND NOT {IS_DIRECT_SQL}"
    return conn.execute(
        f"""SELECT fetched_date, MIN(price) FROM offers
            WHERE origin=? AND destination=? AND fetched_date>=? {cond}
            GROUP BY fetched_date ORDER BY fetched_date""",
        (origin, dest, since)).fetchall()


def month_min(conn, origin, dest):
    return conn.execute(
        """SELECT strftime('%Y-%m', depart_date) AS m, MIN(price) FROM offers
           WHERE origin=? AND destination=? AND length(depart_date)=10
           GROUP BY m HAVING COUNT(*)>=3 ORDER BY m LIMIT 10""",
        (origin, dest)).fetchall()


def weekday_min(conn, origin, dest):
    rows = dict(conn.execute(
        """SELECT CAST(strftime('%w', depart_date) AS INTEGER) AS wd, MIN(price)
           FROM offers WHERE origin=? AND destination=? AND length(depart_date)=10
           GROUP BY wd""", (origin, dest)).fetchall())
    # 월요일부터 표시
    out = []
    for wd in (1, 2, 3, 4, 5, 6, 0):
        if wd in rows:
            out.append((SQL_WEEKDAY[wd], rows[wd]))
    return out


def airline_min(conn, origin, dest):
    return conn.execute(
        """SELECT airline, MIN(price), COUNT(*) FROM offers
           WHERE origin=? AND destination=? AND fetched_date>=?
           GROUP BY airline ORDER BY MIN(price) LIMIT 8""",
        (origin, dest, (date.today() - timedelta(days=30)).isoformat())).fetchall()


def route_summary(conn, origin, dest):
    """(최저가, 중앙값, 표본수) — 최근 30일 전체."""
    since = (date.today() - timedelta(days=30)).isoformat()
    prices = [p for (p,) in conn.execute(
        "SELECT price FROM offers WHERE origin=? AND destination=? AND fetched_date>=? ORDER BY price",
        (origin, dest, since))]
    if not prices:
        return None, None, 0
    return prices[0], prices[len(prices) // 2], len(prices)


# ---------------------------------------------------------------- 조각 렌더링

def subscribe_link(code, label):
    subject = urllib.parse.quote("구독신청")
    body = urllib.parse.quote(f"노선: {code} ({label})\n\n이 메일을 그대로 보내주시면 구독이 신청됩니다.")
    return f"mailto:{SUBSCRIBE_ADDR}?subject={subject}&body={body}"


def sparkline(conn, d):
    rows = daily_min(conn, d["origin"], d["destination"], 30, d["is_direct"])
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
    kind = "직항" if d["is_direct"] else f"경유 {max(d['transfers'], d['return_transfers'])}회"
    kind_cls = "direct" if d["is_direct"] else "transfer"
    url, shop = booking_link(d)
    code = f"{d['origin']}-{d['destination']}"
    return f"""
    <article class="card" data-region="{region_of(d['destination'])}">
      <div class="card-main">
        <div class="card-top">
          <span class="badge discount">-{d['discount_pct']}%</span>
          <span class="badge {kind_cls}">{kind}</span>
        </div>
        <div class="route">
          <a href="{BASE_URL}/routes/{code}.html">
            <span class="city">{city(d['origin'])}</span>
            <span class="plane">✈</span>
            <span class="city">{html.escape(city(d['destination']))}</span>
          </a>
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
        <a class="cta" href="{html.escape(url)}" target="_blank" rel="noopener sponsored">{shop} 예약</a>
      </div>
    </article>"""


def mail_deal_rows(conn):
    rows = conn.execute(
        """SELECT airline, origin, destination, price_krw, promo_end, summary, url
           FROM mail_deals ORDER BY id DESC LIMIT 20""").fetchall()
    out = []
    for airline, origin, dest, price, promo_end, summary, url in rows:
        parts = [f"<span class='sender'>{html.escape(airline or '항공사')}</span>", html.escape(summary)]
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
        "SELECT sender, subject FROM emails ORDER BY id DESC LIMIT 8").fetchall()
    return "\n".join(
        f"<li><span class='sender'>{html.escape(s.split('<')[0].strip().strip(chr(34)) or s)}</span>"
        f"{html.escape(subj)}</li>" for s, subj in rows)


# ---------------------------------------------------------------- 노선 페이지

def route_page(conn, origin, dest):
    code = f"{origin}-{dest}"
    o_name, d_name = city(origin), city(dest)
    label = f"{o_name} → {d_name}"
    cheapest, median, n = route_summary(conn, origin, dest)
    if not n:
        return None

    trend = daily_min(conn, origin, dest, 30)
    months = month_min(conn, origin, dest)
    weekdays = weekday_min(conn, origin, dest)
    airlines = airline_min(conn, origin, dest)

    best_month = min(months, key=lambda r: r[1]) if months else None
    best_wd = min(weekdays, key=lambda r: r[1]) if weekdays else None

    tips = []
    if best_month:
        tips.append(f"<b>{fmt_month(best_month[0])} 출발</b>이 가장 저렴합니다 ({best_month[1]:,}원)")
    if best_wd:
        tips.append(f"출발 요일은 <b>{best_wd[0]}요일</b>이 가장 쌉니다 ({best_wd[1]:,}원)")
    tip_html = " · ".join(tips) or "데이터가 쌓이면 저렴한 시기를 분석해 보여드립니다."

    airline_rows = "\n".join(
        f"<tr><td>{html.escape(airline_name(a))}</td><td class='num'>{p:,}원</td>"
        f"<td class='num'>{c:,}건</td></tr>" for a, p, c in airlines)

    others = "\n".join(
        f'<li><a href="{BASE_URL}/routes/{o}-{dd}.html">{city(o)} → {city(dd)}</a></li>'
        for o, dd in config.ROUTES if f"{o}-{dd}" != code)

    body = f"""  <div class="topbar">
    <a class="brand" href="{BASE_URL}/">갈래<em>말래</em> ✈️</a>
  </div>
  <p class="crumb"><a href="{BASE_URL}/">특가 피드</a> › {REGION_NAME[region_of(dest)]} › {label}</p>
  <header>
    <h1>{label} 항공권 최저가</h1>
    <p class="tagline">최근 30일 수집한 가격 {n:,}건으로 분석한 {label} 왕복 항공권 시세입니다.</p>
  </header>

  <div class="hero">
    <div class="col">
      <span class="cap">최근 30일 최저가</span>
      <span class="figure">{cheapest:,}<small>원</small></span>
    </div>
    <div class="col">
      <span class="cap">평소 시세(중앙값)</span>
      <span class="figure" style="font-size:1.6rem">{median:,}<small>원</small></span>
    </div>
    <div class="col" style="flex:1;min-width:220px">
      <span class="cap">언제 가면 싼가</span>
      <span>{tip_html}</span>
    </div>
  </div>

  <section>
    <h2>📈 {label} 최저가 추이</h2>
    <p class="lead">매일 아침 수집한 이 노선의 왕복 최저가입니다. 아래로 꺾일수록 지금이 살 때입니다.</p>
    <div class="chart">{line_chart(trend, fmt_date)}</div>
  </section>

  <section>
    <h2>📅 출발 월별 최저가</h2>
    <p class="lead">출발 시기에 따라 {label} 항공권 가격이 얼마나 달라지는지 비교했습니다.</p>
    <div class="chart">{bar_chart([(fmt_month(m), p) for m, p in months])}</div>
  </section>

  <section>
    <h2>🗓 출발 요일별 최저가</h2>
    <p class="lead">같은 노선도 무슨 요일에 떠나느냐로 가격이 달라집니다.</p>
    <div class="chart">{bar_chart(weekdays)}</div>
  </section>

  <section>
    <h2>✈️ 항공사별 최저가</h2>
    <p class="lead">최근 30일간 이 노선에서 수집된 항공사별 최저 왕복 요금입니다.</p>
    <table class="data">
      <thead><tr><th>항공사</th><th class="num">최저가</th><th class="num">수집 건수</th></tr></thead>
      <tbody>
{airline_rows}
      </tbody>
    </table>
  </section>

  <section class="subscribe">
    <h2>🔔 {label} 특가 알림 받기</h2>
    <p>이 노선에 특가가 뜨면 메일로 알려드립니다. 아래 버튼을 누르면 메일 앱이 열립니다 —
       <b>내용 수정 없이 그대로 보내주시면</b> 구독이 완료됩니다.</p>
    <div class="sub-form">
      <a class="cta" href="{subscribe_link(code, label)}">{label} 알림 신청</a>
    </div>
    <p class="hint">해지: {SUBSCRIBE_ADDR}로 제목 '구독취소' 메일을 보내주세요.</p>
  </section>

  <section>
    <h2>다른 노선 보기</h2>
    <ul class="routelist">
{others}
    </ul>
  </section>"""

    title = f"{label} 항공권 최저가 · 시세 추이 | {SITE_NAME}"
    desc = (f"{label} 왕복 항공권 최저가 {cheapest:,}원. 최근 30일 가격 추이와 "
            f"출발 월·요일별 최저가, 항공사별 요금을 매일 갱신합니다.")
    (DOCS / "routes").mkdir(parents=True, exist_ok=True)
    (DOCS / "routes" / f"{code}.html").write_text(
        page(title, desc, f"/routes/{code}.html", body), encoding="utf-8")
    return code, cheapest


# ---------------------------------------------------------------- 메인 페이지

INDEX_JS = """<script>
document.addEventListener('DOMContentLoaded', function() {
  var chips = document.querySelectorAll('.chip');
  chips.forEach(function(chip) {
    chip.addEventListener('click', function() {
      chips.forEach(function(c) { c.classList.remove('active'); });
      chip.classList.add('active');
      var region = chip.dataset.region;
      document.querySelectorAll('.card').forEach(function(card) {
        card.style.display = (region === 'all' || card.dataset.region === region) ? '' : 'none';
      });
    });
  });
});
function subscribeMail() {
  var sel = document.getElementById('route-sel');
  var subject = encodeURIComponent('구독신청');
  var body = encodeURIComponent('노선: ' + sel.value + ' (' + sel.selectedOptions[0].text + ')\\n\\n이 메일을 그대로 보내주시면 구독이 신청됩니다.');
  location.href = 'mailto:SUBSCRIBE_ADDR?subject=' + subject + '&body=' + body;
}
</script>""".replace("SUBSCRIBE_ADDR", SUBSCRIBE_ADDR)


def build_index(conn, route_index):
    deals = compute_deals(conn)
    cards = "\n".join(deal_card(conn, d) for d in deals) if deals else \
        "<p class='empty'>오늘은 기준(시세 대비 35% 이상 할인)을 넘는 특가가 없습니다. 내일 아침 다시 스캔합니다.</p>"
    chips = "\n".join(
        f'<button class="chip{" active" if c == "all" else ""}" data-region="{c}">{lab}</button>'
        for c, lab in REGION_CHIPS)
    opts = "\n".join(['<option value="ALL">✈️ 전체 노선</option>'] + [
        f'<option value="{o}-{d}">{city(o)} → {city(d)} ({o}-{d})</option>'
        for o, d in config.ROUTES])
    routelist = "\n".join(
        f'<li><a href="{BASE_URL}/routes/{code}.html">{city(code[:3])} → {city(code[4:])}'
        f'<br><span class="rl-price">최저 {price:,}원</span></a></li>'
        for code, price in route_index)
    n_offers = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
    n_days = conn.execute("SELECT COUNT(DISTINCT fetched_date) FROM offers").fetchone()[0]
    updated = datetime.now(KST).strftime("%m.%d %H:%M")

    body = f"""  <header>
    <div class="brand" style="font-size:2rem">갈래<em>말래</em> ✈️</div>
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
{opts}
      </select>
      <button onclick="subscribeMail()">메일로 구독 신청</button>
    </div>
    <p class="hint">해지: 같은 주소로 제목 '구독취소' 메일을 보내주세요.
       특정 노선만 해지하려면 본문에 노선 코드를 적어주세요.</p>
  </section>

  <section>
    <h2>📊 노선별 가격 분석</h2>
    <p class="lead">각 노선의 최저가 추이와 언제 가면 싼지를 매일 갱신합니다.</p>
    <ul class="routelist">
{routelist}
    </ul>
  </section>

  <section class="mail">
    <h2>🎫 항공사 프로모션</h2>
    <ul>
{mail_deal_rows(conn) or "<li class='empty'>수집된 프로모션이 아직 없습니다.</li>"}
    </ul>
  </section>

  <section class="mail">
    <h2>📬 항공사 소식</h2>
    <ul>
{mail_rows(conn)}
    </ul>
  </section>"""

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(
        page(f"{SITE_NAME} — 오늘의 항공권 특가",
             "매일 아침 한국 출발 항공권 가격을 스캔해, 시세보다 진짜 싼 특가만 골라 보여드립니다. "
             "노선별 가격 추이와 이메일 알림도 무료로 제공합니다.",
             "/", body, INDEX_JS), encoding="utf-8")
    return len(deals)


# ---------------------------------------------------------------- SEO 파일

def build_seo(route_index):
    today = date.today().isoformat()
    urls = [(f"{BASE_URL}/", "daily", "1.0")]
    urls += [(f"{BASE_URL}/routes/{code}.html", "daily", "0.8") for code, _ in route_index]
    entries = "\n".join(
        f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for loc, freq, pri in urls)
    (DOCS / "sitemap.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
""", encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n", encoding="utf-8")


def main():
    conn = db.connect()
    route_index = []
    for origin, dest in config.ROUTES:
        result = route_page(conn, origin, dest)
        if result:
            route_index.append(result)
    n_deals = build_index(conn, route_index)
    build_seo(route_index)
    conn.close()
    print(f"생성 완료: index(특가 {n_deals}건) + 노선 페이지 {len(route_index)}개 + sitemap/robots")


if __name__ == "__main__":
    main()
