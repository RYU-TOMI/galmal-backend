# -*- coding: utf-8 -*-
"""발견 피드용 광역 수집: 한국 전 공항 → 모든 목적지 최저가 (공항당 1회 호출).

기존 fetch_prices.py(노선별 상세, 30일 히스토리)와 역할이 다르다:
- fetch_prices : 소수 노선을 '깊게' (날짜별) — 노선 상세 페이지·특가 판정용
- fetch_breadth: 전 목적지를 '넓게' (목적지당 최저가 1건) — "어디 갈까" 발견용

v2/prices/latest는 origin 하나로 수백 목적지를 한 번에 준다. 5개 공항 = 5회 호출.
결과는 broad_offers 테이블에 (수집일, 출발, 목적지, 최저가, 신선도...) 저장.

⚠️ 응답의 destination은 공항 코드가 아니라 **IATA 도시 코드**다(TYO·OSA·PAR).
   `dests.canonical()`로 대표 공항 코드로 정규화한 뒤 사전과 대조한다. 이걸 빠뜨리면
   도쿄·오사카·파리·런던·뉴욕이 조용히 버려진다(2026-08-28까지 실제로 그랬다, BB15).

사용: python collector/fetch_breadth.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
import timeutil
from dests import ORIGINS, canonical, is_destination

API = "https://api.travelpayouts.com/v2/prices/latest"

# 발견 피드 신선도 기준. **시간 단위**로 둔다 — 예전엔 `MAX_AGE_DAYS = 3`에
# `timedelta.days`(내림)를 써서 이름은 3일인데 실제로는 95시간59분까지 통과했다(BB10).
# 96h를 유지하는 건 의도된 선택이다: 72h로 조이면 딜 26%와 소도시 롱테일이 먼저
# 잘린다(`DECISIONS.md` 2026-08-06). 이름과 동작을 일치시킨 것이지 정책 변경이 아니다.
MAX_AGE_HOURS = 96


def load_token():
    token = os.environ.get("TP_TOKEN")
    if token:
        return token
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("TP_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("TP_TOKEN이 없습니다.")


def fetch_origin(token, origin):
    params = urllib.parse.urlencode(dict(
        origin=origin, currency="krw", limit=1000, period_type="year"))
    req = urllib.request.Request(f"{API}?{params}", headers={"X-Access-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("data", [])


def main():
    token = load_token()
    conn = db.connect()
    today = date.today().isoformat()
    now = timeutil.now_kst()      # aware — naive와 섞어 빼지 않는다
    kept = 0
    failed = []
    for origin in ORIGINS:
        try:
            rows = fetch_origin(token, origin)
        except Exception as e:
            print(f"  {origin}: 수집 실패 ({e})")
            failed.append(origin)
            continue
        n_origin = 0
        for r in rows:
            # 응답은 공항이 아니라 **도시 코드**로 온다(TYO=도쿄, OSA=오사카).
            # 정규화 없이 사전과 대조하면 도쿄·오사카·파리가 통째로 버려진다(BB15).
            dest = canonical(r.get("destination"))
            if not is_destination(dest):        # 품질 필터: 사전에 있는 목적지만
                continue
            found = r.get("found_at", "")
            # found_at은 오프셋 없는 **UTC** 문자열이다. timeutil이 그 사실을 아는
            # 유일한 곳이며, 여기서 직접 파싱하면 또 9시간이 어긋난다(BB11).
            age = timeutil.age_hours(found, now)
            if age is None or age > MAX_AGE_HOURS:   # 신선도 필터
                continue
            conn.execute(
                """INSERT OR REPLACE INTO broad_offers
                   (fetched_date, origin, destination, price, transfers,
                    depart_date, return_date, found_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (today, origin, dest, r.get("value"), r.get("number_of_changes"),
                 r.get("depart_date"), r.get("return_date"), found))
            n_origin += 1
            kept += 1
        print(f"  {origin}: {n_origin}건 (신선·인기 목적지)")
        time.sleep(0.5)
    conn.commit()
    conn.close()
    print(f"완료: {kept}건 저장 ({today})"
          + (f" · 실패 {len(failed)}/{len(ORIGINS)} 공항 {failed}" if failed else ""))

    # 일부 실패는 넘어간다 — 나머지 공항 데이터는 그대로 쓸모가 있다.
    # 전부 실패했거나 한 건도 못 건졌으면 **종료 코드를 1로 낸다**(BB2).
    #
    # 왜 중요한가: 예전엔 5개 공항이 다 죽어도 exit 0으로 끝나서, 워크플로가
    # 그대로 진행돼 빈 산출물을 커밋·배포했다. 스텝이 제대로 실패하면 잡이 멈춰
    # 커밋 자체가 안 되고 **사이트는 어제 상태로 남는다** — 그게 안전한 쪽이다.
    if len(failed) == len(ORIGINS):
        raise SystemExit(
            f"광역 수집 실패: {len(ORIGINS)}개 공항이 모두 실패했다. "
            "토큰 만료·API 장애·응답 형식 변경을 의심할 것.")
    if kept == 0:
        raise SystemExit(
            "광역 수집 실패: 호출은 됐으나 저장한 행이 0건이다. "
            "목적지 코드 체계 변경(BB15 참조)이나 신선도 컷을 의심할 것.")


if __name__ == "__main__":
    main()
