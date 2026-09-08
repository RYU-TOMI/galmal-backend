# -*- coding: utf-8 -*-
"""노선 페이지 36장 — v1 응답만 읽어서 만든다. DB 를 모른다.

**`collector/build_site.py:route_page()` 180줄에서 인수했다**(레포 분리, SPLIT.md M2 T5).
현행은 sqlite 에 직접 질의해 HTML 을 짰다. P1(백엔드는 HTML 을 만들지 않는다)과
P3(프론트는 DB 를 모른다)를 동시에 어기던 자리다.

🔴 **이전 중에는 동작을 바꾸지 않는다.** 화면이 달라지면 M2 T5 동등성 증명
(「같은 입력 → 같은 출력」)이 성립하지 않는다. 개선하고 싶은 것이 보여도 M3 이후다.

## 백엔드가 조용히 걸어주던 필터를 여기서 재현한다

현행 SQL 이 `HAVING`·`LIMIT` 으로 걸던 것을 v1 은 걷어내고 **전 버킷을 `n` 과 함께** 준다.
자를지 말지는 프론트가 정한다는 게 계약의 핵심 규칙이다(창은 백엔드, 임계는 프론트).
**그래서 아래 셋을 빠뜨리면 화면이 조용히 달라진다.**

| 블록 | 현행 SQL | 여기서 재현 |
|---|---|---|
| `months` | `HAVING COUNT(*)>=3` | `n >= 3` |
| `months` | `ORDER BY m LIMIT 10` | 월 오름차순 앞에서 10개 |
| `airlines` | `ORDER BY MIN(price) LIMIT 8` | 최저가 오름차순 상위 8개 |
| `weekdays` | (필터 없음) | **아무것도 안 건다** |

`weekdays` 에 `n>=3` 을 걸지 않는 이유: 계약 초안에 있었으나 기획 착오였고 빼갔다.
현행에 건수 필터가 없다. 걸면 `ICN-RMQ`(타이중)가 5개 → 3개로 줄어 화면이 달라진다.

## 임계는 차트가 아니라 「버킷 비교로 만든 모든 주장」에 건다 (BB28)

현행 `build_site.py:207` 은 `if best_month:` 라 **버킷이 하나뿐이어도
「9월 출발이 가장 저렴합니다」라고 쓴다.** 하나는 비교가 아니다.
지금 안 터지는 건 `HAVING COUNT(*)>=3` 이 우연히 가려주기 때문이고,
새 노선을 넣으면 그날 재현된다(타이중이 지난 길이다).

차트(`charts.py`)는 이미 `len(rows) < 2` 로 막혀 있는데 **문장은 아무도 안 막고 있었다.**
그래서 `usable()` 을 **하나만** 만들어 차트와 문장에 **같이** 건다.
"""
import html
import json
import os
import urllib.parse
import urllib.request

from charts import bar_chart, line_chart
from fmt import fmt_date, fmt_month, weekday_name
from shell import BASE_URL, SITE_NAME, page

# 지역 표시명. 백엔드는 `region` 코드만 주고 이름은 화면이 붙인다(`COPY.md` §2b).
REGION_NAME = {"dom": "국내", "jp": "일본", "cn": "중화권", "sea": "동남아",
               "island": "섬", "oc": "대양주", "eu": "유럽", "am": "미주",
               "etc": "그 외"}

# 프론트가 가진 임계 두 개. 값(2·3)은 현행 코드에서 가져왔다 —
# 바꾸려면 `DESIGN.md`/`COPY.md` 에 근거와 함께 남긴다(`CONTRACT.md` §v1).
MIN_BUCKETS = 2      # 하나는 비교가 아니다
MIN_SAMPLES = 3      # 얇은 버킷은 주장의 근거가 못 된다
MONTH_CAP = 10       # 현행 `LIMIT 10` 재현. 창인지 임계인지의 판정은 이전 후로 미룸
AIRLINE_CAP = 8      # 현행 `LIMIT 8` 재현


def usable(buckets):
    """이 버킷들로 **주장을 해도 되는가.** 차트와 문장에 같이 건다(BB28)."""
    return len(buckets) >= MIN_BUCKETS


def months_shown(months):
    """`n >= 3` 인 것만, 월 오름차순 앞에서 10개 — 현행 SQL 재현."""
    return [m for m in months if m["n"] >= MIN_SAMPLES][:MONTH_CAP]


def airlines_shown(airlines):
    """최저가 오름차순 상위 8개 — 현행 `ORDER BY MIN(price) LIMIT 8` 재현."""
    return sorted(airlines, key=lambda a: a["min"])[:AIRLINE_CAP]


def fetch(api, path):
    """v1 응답 하나를 읽는다. `api` 는 URL 이거나 로컬 폴더다.

    **빌드 타임에** 부른다 — 브라우저가 아니라 빌드 서버다. 그래서 CORS 는 관심사가
    아니고, 방문자는 이 요청을 보지 못한다(`CONTRACT.md` §v1).
    """
    if api.startswith("http"):
        with urllib.request.urlopen(api.rstrip("/") + "/" + path, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    with open(os.path.join(api, *path.split("/")), encoding="utf-8") as f:
        return json.load(f)


def subscribe_link(sub, code, label):
    """구독 `mailto:`.

    🔴 **주소·제목·본문의 노선 표기는 표시가 아니라 전선(wire) 규약이다.**
    IMAP 파서가 이 메일을 읽어 어느 노선인지 뽑는다. 형식이 어긋나면 구독이
    **실패하는 게 아니라 「전 노선 구독」이 된다** — `subscriptions.py:61` 이
    `add(route or "ALL")` 라서다. 도쿄만 신청한 사람이 36노선 메일을 받는다.
    실패는 사용자가 알려주기라도 하는데 이건 스팸 신고로 돌아온다.

    **그래서 지어내지 않고 `meta.json` 의 `subscribe` 블록에서 받는다.**
    문구(「이 메일을 그대로 보내주시면…」)는 `COPY.md` 소관이라 여기서 만든다.
    """
    subject = urllib.parse.quote(sub["subject_subscribe"])
    token = sub["route_token"].replace("{code}", code)
    body = urllib.parse.quote(
        f"노선: {token} ({label})\n\n이 메일을 그대로 보내주시면 구독이 신청됩니다.")
    return f"mailto:{sub['address']}?subject={subject}&body={body}"


def render(r, index, meta, generated_date):
    """노선 1개 → (파일명, HTML). `r` 은 `/v1/routes/{code}.json` 응답."""
    code = r["code"]
    label = f'{r["o_name"]} → {r["d_name"]}'
    s = r["summary"]
    cheapest, median, n = s["cheapest"], s["median"], s["n"]

    months = months_shown(r["months"])
    weekdays = r["weekdays"]                      # 필터 없음 — 현행 그대로
    airlines = airlines_shown(r["airlines"])
    trend = r["trend"]

    # 🔴 문장에도 차트와 **같은** 임계를 건다(BB28). 현행은 `if best_month:` 였다.
    tips = []
    if usable(months):
        b = min(months, key=lambda m: m["price"])
        tips.append(f'<b>{fmt_month(b["m"])} 출발</b>이 가장 저렴합니다 ({b["price"]:,}원)')
    if usable(weekdays):
        b = min(weekdays, key=lambda w: w["price"])
        tips.append(f'출발 요일은 <b>{weekday_name(b["wd"])}요일</b>이 가장 쌉니다 ({b["price"]:,}원)')
    tip_html = " · ".join(tips) or "데이터가 쌓이면 저렴한 시기를 분석해 보여드립니다."

    airline_rows = "\n".join(
        f'<tr><td>{html.escape(a["name"])}</td><td class=\'num\'>{a["min"]:,}원</td>'
        f'<td class=\'num\'>{a["n"]:,}건</td></tr>' for a in airlines)

    others = "\n".join(
        f'<li><a href="{BASE_URL}/routes/{o["code"]}.html">{o["o_name"]} → {o["d_name"]}</a></li>'
        for o in index["routes"] if o["code"] != code)

    # 빵부스러기는 **한 번만 만든다.** 화면과 JSON-LD 가 각자 문자열을 들고 있으면
    # 한쪽만 고쳐진다 — 실제로 그랬다(`특가 피드`는 2026-09-01에 `발견`으로 폐기된
    # 이름인데 두 곳에 박혀 있었고, 그 상태로 검색엔진에 발행됐다. `SPEC.md` IA-3).
    crumb = [("발견", f"{BASE_URL}/"),
             (REGION_NAME.get(r["region"], "그 외"), None),
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
    <div class="chart">{line_chart([(t["date"], t["price"]) for t in trend], fmt_date)}</div>
  </section>

  <section>
    <h2>출발 월별 최저가</h2>
    <p class="lead">출발 시기에 따라 {label} 항공권 가격이 얼마나 달라지는지 비교했습니다.</p>
    <div class="chart">{bar_chart([(fmt_month(m["m"]), m["price"]) for m in months])}</div>
  </section>

  <section>
    <h2>출발 요일별 최저가</h2>
    <p class="lead">같은 노선도 무슨 요일에 떠나느냐로 가격이 달라집니다.</p>
    <div class="chart">{bar_chart([(weekday_name(w["wd"]), w["price"]) for w in weekdays])}</div>
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
      <a class="cta" href="{subscribe_link(meta['subscribe'], code, label)}">{label} 알림 신청</a>
    </div>
    <p class="hint">해지: {meta['subscribe']['address']}로 제목 '{meta['subscribe']['subject_unsubscribe']}' 메일을 보내주세요.</p>
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

    # 구조화 데이터는 **화면에 실제로 있는 것만** 적는다. 아래 BreadcrumbList 는 위
    # `<p class="crumb">`가 쓴 것과 **같은 `crumb` 리스트**라 갈라질 수 없다.
    # 상품 스키마(Product/Offer)는 쓰지 않는다 — 우리가 파는 게 아니라 남의 가격을
    # 보여줄 뿐이라 사실과 다르고, 잘못 쓰면 스팸으로 판정된다.
    structured = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList",
         "itemListElement": [
             {"@type": "ListItem", "position": i, "name": name,
              **({"item": href} if href else {})}
             for i, (name, href) in enumerate(crumb, 1)]},
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": title, "description": desc, "url": url, "inLanguage": "ko-KR",
         # 현행은 `timeutil.today_utc()`(빌드 시각)였다. 이제 `generated`(데이터 생성
         # 시각)에서 뽑는다 — 페이지가 주장하는 건 "이 데이터가 언제 것인가"지
         # "우리가 언제 빌드했나"가 아니다. 기획 확정(`CONTRACT.md` 파생 목록).
         "dateModified": generated_date,
         "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": f"{BASE_URL}/"}},
    ]

    # 링크 미리보기 문구는 `<title>`과 다르다(`COPY.md` §2c). 카톡 말풍선은 이미 아는
    # 사람이 친구에게 보내는 자리라 `· 시세 추이 | 갈래말래`가 붙으면 어색하다.
    #
    # 🔴 **가격을 넣지 않는다.** **카톡은 미리보기를 캐시한다** — 내일 값이 바뀌어도
    # 말풍선은 어제 가격을 계속 보여주고, 들어가 보니 다른 가격이면 그게 우리가
    # 가장 안 하기로 한 것이다. 본문에는 가격이 있다. 본문은 캐시되지 않는다.
    og_title = f"{label} 항공권, 지금 얼마?"
    og_desc = (f"최근 30일 수집한 가격으로 본 {label} 왕복 시세. "
               "언제 가면 싼지 월·요일별로 비교했습니다.")

    return f"{code}.html", page(title, desc, f"/routes/{code}.html", body,
                                jsonld=structured, og_title=og_title,
                                og_description=og_desc)


def build_all(api):
    """36장을 만들어 {파일명: HTML} 로 돌려준다. 파일 쓰기는 `build.py` 가 한다."""
    meta = fetch(api, "meta.json")
    index = fetch(api, "routes/index.json")
    # `generated` 는 오프셋이 붙은 ISO 8601 이다. 날짜만 쓴다.
    generated_date = meta["generated"][:10]

    out = {}
    for r in index["routes"]:
        detail = fetch(api, "routes/%s.json" % r["code"])
        name, html_text = render(detail, index, meta, generated_date)
        out[name] = html_text
    return out
