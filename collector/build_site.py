# -*- coding: utf-8 -*-
"""갈래말래 정적 사이트 생성 — 메인 피드 + 노선별 페이지 + sitemap/robots.

- docs/index.html          : 오늘의 특가 피드
- docs/routes/ICN-FUK.html : 노선별 가격 분석 (검색 유입용 색인 대상)
- docs/sitemap.xml, robots.txt

사용: python collector/build_site.py
"""
import html
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import json

import affiliates
import config
import db
import publish_v1
import timeutil
from affiliates import booking_link
from charts import bar_chart, line_chart
from detect_deals import compute_deals
from discover_data import build_deals_json
from dests import ORIGIN_COORD, ORIGINS, REGION_NAME
from labels import (SQL_WEEKDAY, airline_name, city, fmt_date, fmt_month,
                    region_of)
from theme import BASE_URL, SITE_NAME, SUBSCRIBE_ADDR, page

# 통계는 `route_stats`로 뗐다(M3 T0). 여기는 옛 HTML을 그리는 쪽이라 **가져다 쓰기만** 한다.
from route_stats import (WINDOW_DAYS, WEEK_ORDER, airline_min, daily_min,
                         month_min, route_summary, weekday_min)

DOCS = Path(__file__).resolve().parent.parent / "docs"


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
        tips.append(f"출발 요일은 <b>{SQL_WEEKDAY[best_wd[0]]}요일</b>이 가장 쌉니다 "
                    f"({best_wd[1]:,}원)")
    tip_html = " · ".join(tips) or "데이터가 쌓이면 저렴한 시기를 분석해 보여드립니다."

    airline_rows = "\n".join(
        f"<tr><td>{html.escape(airline_name(a))}</td><td class='num'>{p:,}원</td>"
        f"<td class='num'>{c:,}건</td></tr>" for a, p, c in airlines)

    others = "\n".join(
        f'<li><a href="{BASE_URL}/routes/{o}-{dd}.html">{city(o)} → {city(dd)}</a></li>'
        for o, dd in config.ROUTES if f"{o}-{dd}" != code)

    # 빵부스러기는 **한 번만 만든다.** 화면과 JSON-LD가 각자 문자열을 들고 있으면
    # 한쪽만 고쳐진다 — 실제로 그랬다(`특가 피드`는 2026-09-01에 `발견`으로 폐기된
    # 이름인데 두 곳에 박혀 있었고, 그 상태로 검색엔진에 발행됐다. `SPEC.md` IA-3).
    # 홈의 이름은 네비에 적힌 대로 **발견**이다.
    crumb = [("발견", f"{BASE_URL}/"),
             (REGION_NAME[region_of(dest)], None),
             (label, None)]
    crumb_html = " › ".join(
        f'<a href="{href}">{html.escape(name)}</a>' if href else html.escape(name)
        for name, href in crumb)

    body = f"""  <div class="topbar">
    <a class="brand" href="{BASE_URL}/">갈래<em>말래</em> ✈️</a>
  </div>
  <p class="crumb">{crumb_html}</p>
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
    <h2>{label} 최저가 추이</h2>
    <p class="lead">매일 아침 수집한 이 노선의 왕복 최저가입니다. 아래로 꺾일수록 지금이 살 때입니다.</p>
    <div class="chart">{line_chart(trend, fmt_date)}</div>
  </section>

  <section>
    <h2>출발 월별 최저가</h2>
    <p class="lead">출발 시기에 따라 {label} 항공권 가격이 얼마나 달라지는지 비교했습니다.</p>
    <div class="chart">{bar_chart([(fmt_month(m), p) for m, p, _ in months])}</div>
  </section>

  <section>
    <h2>출발 요일별 최저가</h2>
    <p class="lead">같은 노선도 무슨 요일에 떠나느냐로 가격이 달라집니다.</p>
    <div class="chart">{bar_chart([(SQL_WEEKDAY[wd], p) for wd, p, _ in weekdays])}</div>
  </section>

  <section>
    <h2>항공사별 최저가</h2>
    <p class="lead">최근 30일간 이 노선에서 수집된 항공사별 최저 왕복 요금입니다.</p>
    <table class="data">
      <thead><tr><th>항공사</th><th class="num">최저가</th><th class="num">수집 건수</th></tr></thead>
      <tbody>
{airline_rows}
      </tbody>
    </table>
  </section>

  <section class="subscribe">
    <h2>{label} 특가 알림 받기</h2>
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
    url = f"{BASE_URL}/routes/{code}.html"

    # 구조화 데이터는 **화면에 실제로 있는 것만** 적는다. 아래 BreadcrumbList는 위
    # `<p class="crumb">`가 쓴 것과 **같은 `crumb` 리스트**라 갈라질 수 없다.
    # 중간 단계(지역)는 페이지가 없으므로 링크도 없이 이름만 넣는다 — 없는 URL을
    # 지어내지 않는다. 상품 스키마(Product/Offer)는 쓰지 않는다. 우리가 파는 게
    # 아니라 남의 가격을 보여줄 뿐이라 사실과 다르고, 잘못 쓰면 스팸으로 판정된다.
    structured = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [
             {"@type": "ListItem", "position": i, "name": name,
              **({"item": href} if href else {})}
             for i, (name, href) in enumerate(crumb, 1)]},
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": title, "description": desc, "url": url, "inLanguage": "ko-KR",
         # 매일 갱신하는 페이지라 크롤러에 신선도를 알린다. `fetched_date`와 같은
         # 기준(UTC)으로 찍어야 로컬 재빌드와 크론이 어긋나지 않는다(BE4 T1).
         "dateModified": timeutil.today_utc().isoformat(),
         "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": f"{BASE_URL}/"}},
    ]

    # 링크 미리보기 문구는 `<title>`과 다르다(`COPY.md` §2c). 카톡 말풍선은 이미 아는
    # 사람이 친구에게 보내는 자리라 `· 시세 추이 | 갈래말래`가 붙으면 어색하다.
    #
    # 🔴 **가격을 넣지 않는다.** `인천 → 도쿄 14만원부터`가 훨씬 잘 눌리지만
    # **카톡은 미리보기를 캐시한다** — 내일 값이 바뀌어도 말풍선은 어제 가격을 계속
    # 보여주고, 들어가 보니 다른 가격이면 그게 우리가 가장 안 하기로 한 것이다.
    # 본문에는 가격이 있다. 본문은 매일 다시 그려지고 캐시되지 않는다.
    og_title = f"{label} 항공권, 지금 얼마?"
    og_desc = (f"최근 30일 수집한 가격으로 본 {label} 왕복 시세. "
               "언제 가면 싼지 월·요일별로 비교했습니다.")

    (DOCS / "routes").mkdir(parents=True, exist_ok=True)
    (DOCS / "routes" / f"{code}.html").write_text(
        page(title, desc, f"/routes/{code}.html", body, jsonld=structured,
             og_title=og_title, og_description=og_desc),
        encoding="utf-8")
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
    """발견 홈(docs/index.html) — deals.json + world.geojson 인라인."""
    from discover_home import render_home
    dj = (DOCS / "data" / "deals.json").read_text(encoding="utf-8")
    wj = (DOCS / "data" / "world.geojson").read_text(encoding="utf-8")
    data = json.loads(dj)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(render_home(data, dj, wj, route_index), encoding="utf-8")
    return len(data.get("deals", []))


# ---------------------------------------------------------------- SEO 파일

def build_seo(route_index):
    # 크롤러가 읽는 기계용 날짜다. `fetched_date`와 같은 기준(UTC)으로 찍어야
    # 로컬 재빌드와 크론이 서로 다른 lastmod를 남기지 않는다(BB17).
    today = timeutil.today_utc().isoformat()
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


def warn_if_unpaid():
    """수익 시크릿이 없으면 **크게** 알린다 (BB30).

    산출물은 바꾸지 않는다 — 경고만이다. 없는 채로 빌드하는 건 정당한 경우가
    있고(프론트가 화면만 볼 때), 막아야 할 건 그 결과물을 **모르고 커밋하는 것**이다.
    그 마지막 방어선은 `tests/test_affiliates.py`의 커밋본 검사다.
    """
    missing = affiliates.missing_secrets()
    if not missing:
        return False
    print("\n" + "!" * 68, file=sys.stderr)
    print("!! 제휴 시크릿이 없습니다: " + ", ".join(missing), file=sys.stderr)
    print("!! 이 빌드의 예약 링크에는 수수료 마커가 빠집니다 —", file=sys.stderr)
    print("!! 사이트는 멀쩡해 보이고 수익 경로만 사라집니다.", file=sys.stderr)
    print("!! docs/ 를 커밋하지 마십시오. (BACKEND.md BB30)", file=sys.stderr)
    print("!" * 68 + "\n", file=sys.stderr)
    return True


def main():
    unpaid = warn_if_unpaid()
    conn = db.connect()
    route_index = []
    for origin, dest in config.ROUTES:
        result = route_page(conn, origin, dest)
        if result:
            route_index.append(result)
    # 실제로 파일이 만들어진 노선만 넘긴다 — route 필드가 404를 가리키지 않게.
    n_disc = build_deals_json(conn, {code for code, _ in route_index})
    n_deals = build_index(conn, route_index)
    build_seo(route_index)
    # v1 API 발행 — 현행 산출물과 **나란히** 나간다(`SPLIT.md` M1 T2).
    # 이전이 끝나면 위의 HTML 생성이 프론트로 가고 이 줄만 남는다.
    n_v1 = publish_v1.publish(conn)
    conn.close()
    # n_disc < 0 = 하한선 미달로 갱신하지 않음(BB1). 기존 산출물이 그대로 인라인되므로
    # 홈은 정상 동작하며, 사이트는 어제 딜을 계속 보여 준다.
    disc = "유지(하한선 미달)" if n_disc < 0 else f"{n_disc}건"
    print(f"생성 완료: 발견 홈({n_deals}딜) + deals.json({disc}) "
          f"+ 노선 페이지 {len(route_index)}개 + sitemap/robots "
          f"+ v1 API(노선 {n_v1}개)")
    if unpaid:
        # 사람은 출력의 **끝**을 읽는다. 시작에서 외친 걸 여기서 한 번 더 말한다.
        print("  ⚠️ 수수료 마커 없이 만들어졌습니다 — docs/ 를 커밋하지 마십시오.",
              file=sys.stderr)
    _report_preserved(n_disc < 0)


def _report_preserved(preserved):
    """산출물 보존 여부를 GitHub Actions에 알린다(BB18).

    빌드는 성공으로 끝나야 한다 — 데이터는 커밋돼야 하니까. 대신 이 신호를
    워크플로 마지막 '상태 점검'이 읽어 잡을 실패로 표시하고, GitHub가 메일을 보낸다.
    로컬 실행에는 `GITHUB_OUTPUT`이 없으므로 아무 일도 하지 않는다.
    """
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    try:
        with open(out, "a", encoding="utf-8") as f:
            print(f"preserved={'true' if preserved else 'false'}", file=f)
    except OSError as e:                       # 신호 실패가 빌드를 죽이면 안 된다
        print(f"  (GITHUB_OUTPUT 기록 실패: {e})")


if __name__ == "__main__":
    main()
