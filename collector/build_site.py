# -*- coding: utf-8 -*-
"""prices.db의 특가 판정 결과로 정적 웹 피드(docs/index.html) 생성.

GitHub Pages(main 브랜치 /docs)로 서빙되며, Actions 크론이 매일 재생성해 커밋.
사용: python collector/build_site.py
"""
import html
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import db
from detect_deals import compute_deals

SUBSCRIBE_ADDR = "flightpromokr@gmail.com"

OUT = Path(__file__).resolve().parent.parent / "docs" / "index.html"
KST = timezone(timedelta(hours=9))

CITY = {
    "ICN": "인천", "GMP": "김포", "CJU": "제주",
    "NRT": "도쿄(나리타)", "KIX": "오사카", "FUK": "후쿠오카", "OKA": "오키나와",
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


def city(code):
    return CITY.get(code, code)


def airline_name(code):
    return AIRLINE.get(code, code)


def deal_card(d):
    kind = "직항" if d["is_direct"] else \
        f"경유 {max(d['transfers'], d['return_transfers'])}회"
    kind_cls = "direct" if d["is_direct"] else "transfer"
    return f"""
    <article class="card">
      <div class="card-top">
        <span class="badge discount">-{d['discount_pct']}%</span>
        <span class="badge {kind_cls}">{kind}</span>
      </div>
      <h2>{city(d['origin'])} → {html.escape(city(d['destination']))}</h2>
      <p class="dates">{d['depart_date']} ~ {d['return_date']} 왕복</p>
      <p class="price">{d['price']:,}원
        <span class="median">시세 {d['median']:,}원</span></p>
      <p class="meta">{html.escape(airline_name(d['airline']))}</p>
      <a class="cta" href="{html.escape(d['link'])}" target="_blank" rel="noopener sponsored">
        이 가격 확인하기</a>
    </article>"""


def mail_deal_rows(conn):
    """LLM이 메일에서 추출한 구조화 특가 (최근 20건)."""
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
           ORDER BY id DESC LIMIT 10""").fetchall()
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
    cards = "\n".join(deal_card(d) for d in deals) if deals else \
        "<p class='empty'>오늘은 기준(시세 대비 35% 이상 할인)을 넘는 특가가 없습니다.</p>"
    mail_deals = mail_deal_rows(conn)
    mails = mail_rows(conn)
    conn.close()
    updated = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>오늘의 항공권 특가</title>
<meta name="description" content="한국 출발 항공권 특가를 매일 자동 수집해 시세 대비 할인율로 알려드립니다.">
<style>
  :root {{
    --bg:#f6f7f9; --card:#fff; --text:#1c2733; --sub:#5f6b7a;
    --accent:#0b62d6; --deal:#d6274b; --line:#e4e8ee;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#12161c; --card:#1b222c; --text:#e8edf3; --sub:#98a4b3;
             --accent:#5aa2ff; --deal:#ff6b8b; --line:#2a3441; }}
  }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ background:var(--bg); color:var(--text);
         font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
         line-height:1.5; padding:24px 16px 48px; }}
  main {{ max-width:960px; margin:0 auto; }}
  header h1 {{ font-size:1.6rem; margin-bottom:4px; }}
  header p {{ color:var(--sub); font-size:.9rem; margin-bottom:24px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:16px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
           padding:18px; display:flex; flex-direction:column; gap:6px; }}
  .card-top {{ display:flex; gap:6px; }}
  .badge {{ font-size:.75rem; font-weight:700; padding:2px 8px; border-radius:99px; }}
  .discount {{ background:var(--deal); color:#fff; }}
  .direct {{ background:var(--accent); color:#fff; }}
  .transfer {{ background:var(--line); color:var(--sub); }}
  .card h2 {{ font-size:1.15rem; }}
  .dates, .meta {{ color:var(--sub); font-size:.85rem; }}
  .price {{ font-size:1.35rem; font-weight:800; }}
  .median {{ color:var(--sub); font-size:.8rem; font-weight:400;
             text-decoration:line-through; margin-left:6px; }}
  .cta {{ margin-top:auto; text-align:center; background:var(--accent); color:#fff;
          text-decoration:none; font-weight:700; padding:10px; border-radius:10px; }}
  .empty {{ color:var(--sub); padding:24px 0; }}
  section.mail {{ margin-top:40px; }}
  section.mail h2 {{ font-size:1.2rem; margin-bottom:12px; }}
  section.mail ul {{ list-style:none; display:flex; flex-direction:column; gap:8px; }}
  section.mail li {{ background:var(--card); border:1px solid var(--line);
                     border-radius:10px; padding:10px 14px; font-size:.9rem; }}
  .sender {{ font-weight:700; margin-right:8px; }}
  .until {{ color:var(--deal); font-size:.8rem; }}
  section.mail a {{ color:var(--accent); font-weight:700; text-decoration:none; }}
  footer {{ margin-top:48px; color:var(--sub); font-size:.78rem;
            border-top:1px solid var(--line); padding-top:16px; }}
  footer p {{ margin-bottom:6px; }}
  section.subscribe {{ margin-top:40px; background:var(--card);
    border:1px solid var(--line); border-radius:14px; padding:20px; }}
  section.subscribe h2 {{ font-size:1.2rem; margin-bottom:8px; }}
  section.subscribe p {{ color:var(--sub); font-size:.9rem; margin-bottom:12px; }}
  .sub-form {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .sub-form select {{ flex:1; min-width:220px; padding:10px; border-radius:10px;
    border:1px solid var(--line); background:var(--bg); color:var(--text); font-size:.95rem; }}
  .sub-form button {{ background:var(--accent); color:#fff; border:none; font-weight:700;
    padding:10px 18px; border-radius:10px; cursor:pointer; font-size:.95rem; }}
  .hint {{ font-size:.8rem !important; margin-top:10px; }}
</style>
<script>
function subscribeMail() {{
  var code = document.getElementById('route-sel').value;
  var label = document.getElementById('route-sel').selectedOptions[0].text;
  var subject = encodeURIComponent('구독신청');
  var body = encodeURIComponent('노선: ' + code + ' (' + label + ')\\n\\n이 메일을 그대로 보내주시면 구독이 신청됩니다.');
  location.href = 'mailto:{SUBSCRIBE_ADDR}?subject=' + subject + '&body=' + body;
}}
</script>
</head>
<body>
<main>
  <header>
    <h1>✈️ 오늘의 항공권 특가</h1>
    <p>한국 출발 주요 노선의 가격을 매일 수집해, 평소 시세보다 크게 저렴한 항공권만 골라 보여드립니다.
       마지막 갱신: {updated} (KST)</p>
  </header>

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
    <p>· "이 가격 확인하기" 링크를 통해 예약이 이루어지면 운영자가 수수료를 받을 수 있습니다.</p>
    <p>· 시세는 해당 노선·유형(직항/경유)의 최근 30일 수집 가격 중앙값입니다. 데이터: Travelpayouts(Aviasales)</p>
  </footer>
</main>
</body>
</html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"생성 완료: {OUT} (특가 {len(deals)}건)")


if __name__ == "__main__":
    main()
