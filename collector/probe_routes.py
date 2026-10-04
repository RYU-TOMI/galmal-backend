# -*- coding: utf-8 -*-
"""노선 후보를 **매일 한 번** v3로 재서 쌓는다 — 넣을지 말지는 7일 중앙값으로 (BE8 2차).

기획 결정 `decisions/2026-09.md` 2026-09-28 (2):
  · 결정 2 — `ICN-CNX`·`ICN-HIJ`는 **7일 연속 v3 실측 중앙값 ≥ 10** 이면 기획 재결정 없이 넣는다.
  · 결정 3 — 「넣을 때 하루 10건」은 하루치가 아니라 **7일 중앙값**이다. 하루치는 흔들린다
    (CNX가 09-20 23건 → 09-28 9건).

손으로 재면 하루만 빠져도 「연속 7일」을 처음부터 다시 센다. 그래서 크론이 잰다.

🔴 **`offers`(노선 수집 테이블)에는 쓰지 않는다.** 거기 들어가면 노선 페이지·특가 판정의 입력이 된다 —
   아직 넣지 않은 노선이다. 건수만 `data/route_probe.json`에 남긴다(크론이 `data/`를 커밋한다).

**판정만 한다 — 노선을 넣지는 않는다.** `config.ROUTES`에 넣는 건 사람이 결정을 인용해 커밋한다.

사용: python collector/probe_routes.py
"""
import json
import statistics
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_prices
import timeutil

# (출발, 도착). 판정이 끝나면(넣었든 뺐든) 여기서 지운다 — 기록은 파일에 남는다.
# 비어 있으면 크론 스텝은 아무것도 재지 않고 끝난다. 다음 후보가 생기면 여기에 적기만 하면 된다.
#   2026-10-04 판정 끝: ICN-CNX 중앙 16 → `config.ROUTES` 에 넣음 · ICN-HIJ 중앙 2 → 넣지 않음.
CANDIDATES = []
WINDOW = 7        # 연속 일수
THRESHOLD = 10    # 중앙값 기준(건/일) — 노선을 넣을 때의 기준과 같은 수

PATH = Path(__file__).resolve().parent.parent / "data" / "route_probe.json"


def load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def record(data, route, day, rows):
    """그날 잰 값을 넣는다. 같은 날 두 번 돌면(주·예비·손) **덮어쓴다** — 하루는 한 점이다."""
    data.setdefault(route, {})[day] = {
        "n": len(rows),
        "direct": sum(1 for r in rows if r.get("transfers") == 0),
    }
    return data


def streak(data, route, today):
    """`today`에서 거꾸로 **끊기지 않고** 이어진 날들의 건수(최신이 앞). 오늘 값이 없으면 빈 목록."""
    days = data.get(route, {})
    out, d = [], today
    while d.isoformat() in days:
        out.append(days[d.isoformat()]["n"])
        d -= timedelta(days=1)
    return out


def verdict(counts):
    """연속 일수가 `WINDOW`에 못 미치면 판정 보류. 차면 **최근 `WINDOW`일**의 중앙값으로 가른다."""
    if len(counts) < WINDOW:
        return f"측정 중 {len(counts)}/{WINDOW}일"
    med = statistics.median(counts[:WINDOW])
    return (f"✅ 넣을 조건 충족 — 7일 중앙값 {med:g} ≥ {THRESHOLD}" if med >= THRESHOLD
            else f"❌ 기준 미달 — 7일 중앙값 {med:g} < {THRESHOLD}")


def main():
    token = fetch_prices.load_token()
    today = timeutil.today_utc()
    data = load()
    failed = []
    for o, d in CANDIDATES:
        route = f"{o}-{d}"
        try:
            rows = fetch_prices.fetch_route(token, o, d)
        except Exception as e:
            print(f"  {route}: 측정 실패 ({e}) — 오늘이 빠지면 연속 일수가 끊긴다")
            failed.append(route)
            continue
        record(data, route, today.isoformat(), rows)
        counts = streak(data, route, today)
        print(f"  {route}: 오늘 {counts[0]}건 · 연속 {len(counts)}일 {counts[:WINDOW]} → {verdict(counts)}")
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")   # 윈도우에서 돌려도 LF
    if failed:
        raise SystemExit(f"후보 측정 실패: {', '.join(failed)}")


if __name__ == "__main__":
    main()
