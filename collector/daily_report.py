# -*- coding: utf-8 -*-
"""운영자에게 보내는 **일일 보고 메일** — 크론이 끝날 때 한 통 (BE22).

왜: 크론이 잘 돈 날엔 아무 소식이 없었다. 실패하면 GitHub 가 메일을 주지만 「무엇이 얼마나 발행됐나」는
    저장소를 열어야 알고, **소식이 없는 것**이 「정상」과 「아예 안 돌았다」 둘 다를 뜻했다.
    매일 한 통이 오면 **안 온 날이 곧 경보**다.

무엇을 담나: 잡 결과 · 실행 시각과 지연 · 상태 점검이 적은 줄 **그대로** · 발행 수치 · 수집량 · 메일 · 노선 후보.
    아침마다 손으로 보던 대조(딜 수 == 제휴 링크 수 · route/oa · 수집일 구멍 · 이번 실행이 발행했나)를 같이 본다.

🔴 **본문을 로그에 찍지 않는다.** 이 저장소는 공개라 Actions 로그도 공개다. 구독 알림 수처럼
   「우리에게 사람이 얼마나 오는가」(`SESSIONS.md` 🔒)가 본문에 있고, 방문자 수도 여기로 들어올 것이다.
   로컬에서 볼 땐 `--dry-run`.
🔴 **제목에 `구독신청`·`구독취소`를 넣지 않는다.** 받는 주소가 서비스 메일함이면 `subscriptions`가 구독 메일로 읽는다.
🔴 **실 DB는 읽기 전용으로 연다.** 이 스텝은 커밋 **뒤**에 돈다 — 여기서 바뀐 것은 어디에도 안 남는다.

사용: python collector/daily_report.py [--dry-run]
"""
import json
import os
import smtplib
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
import env
import probe_routes
import timeutil
from mail_ingest import load_env
from send_alerts import SMTP_HOST

V1 = Path(__file__).resolve().parent.parent / "docs" / "v1"

# 예약 실행이 UTC 이 시각 이후에 시작하면 자정까지 여유가 2시간이 안 된다(BB36).
# 23·00시는 상태 점검이 이미 실패로 만든다 — 여기는 **그 전에** 알리는 자리다.
LATE_HOUR_UTC = 22
GAP_DAYS = 7      # 수집일 구멍을 찾는 창


def _when(dt):
    """사람이 읽는 시각 — **KST 먼저**, UTC 는 괄호. 운영자는 한국 시간으로 산다."""
    k, u = dt.astimezone(timeutil.KST), dt.astimezone(timezone.utc)
    return f"{k:%m-%d %H:%M} KST ({u:%m-%d %H:%M} UTC)"


def _span(td):
    minutes = int(td.total_seconds()) // 60
    h, m = divmod(minutes, 60)
    return f"{h}시간 {m}분" if h else f"{m}분"


def parse_started(raw):
    """가드 스텝이 남긴 시작 시각(`2026-10-03T19:20:28Z`) → aware datetime. 없거나 못 읽으면 None."""
    try:
        return datetime.fromisoformat((raw or "").strip().replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def scheduled_for(started, cron):
    """`started` 를 깨운 예약 시각 — cron(`"10 14 * * *"`, UTC)의 **시작 이전 가장 가까운** 발생.

    지연이 자정을 넘으면(18:10 예약이 다음 날 00:30 에 시작) 하루 전 것을 집는다.
    매일 한 번짜리 cron 만 안다. 다른 모양이면 None — 지어내지 않는다.
    """
    parts = (cron or "").split()
    if len(parts) != 5 or parts[2:] != ["*", "*", "*"] or not (parts[0].isdigit() and parts[1].isdigit()):
        return None
    at = started.replace(hour=int(parts[1]), minute=int(parts[0]), second=0, microsecond=0)
    return at if at <= started else at - timedelta(days=1)


def read_health(path):
    """상태 점검 스텝이 적은 줄들. 제목 줄과 마크다운 굵게 표시는 뺀다. 파일이 없으면 `[]`."""
    try:
        text = Path(path).read_text(encoding="utf-8") if path else ""
    except OSError:
        return []
    return [line.replace("**", "") for line in text.splitlines()
            if line.strip() and not line.startswith("#")]


def open_db():
    return sqlite3.connect(f"file:{db.DB_PATH.as_posix()}?mode=ro", uri=True)


def _load(rel):
    return json.loads((V1 / rel).read_text(encoding="utf-8"))


def publish_lines(started, warns):
    """발행물(`docs/v1/`)에서 읽은 수치. 대조가 어긋나면 `warns` 에 적는다."""
    meta, deals, routes = _load("meta.json"), _load("deals.json")["deals"], _load("routes/index.json")["routes"]
    gen = datetime.fromisoformat(meta["generated"])
    mine = started is None or gen >= started
    lines = [f"- 발행 시각 {_when(gen)}" + ("" if started is None else " — 이번 실행이 만들었다" if mine else "")]
    if not mine:
        warns.append(f"이번 실행은 발행하지 못했다 — 서빙 중인 것은 {_when(gen)} 발행분이다")
    if meta.get("preserved"):
        warns.append("딜 보존일 — 하한선 미달로 deals.json 을 갱신하지 않았다(사이트는 이전 딜)")
    lines.append(f"- 노선 {len(routes)} · 딜 {len(deals)}")
    ads = sum(any(l.get("ad") for l in d["links"]) for d in deals)
    lines.append(f"- 제휴 링크가 붙은 딜 {ads}/{len(deals)}")
    if ads != len(deals):
        warns.append(f"제휴 링크가 빠진 딜 {len(deals) - ads}건 — 시크릿 없이 발행됐을 수 있다(BB30)")
    bad = sum(1 for d in deals if d.get("route") and d["route"].split("-")[0] != d.get("oa"))
    if bad:
        warns.append(f"route 와 oa 가 어긋난 딜 {bad}건 — 프론트 빌드가 멈춘다")
    return lines, len(deals), len(routes)


def _day_count(conn, table, today):
    """`(오늘 행 수, (직전 수집일, 행 수) | None)`"""
    n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE fetched_date=?", (today,)).fetchone()[0]
    prev = conn.execute(f"SELECT fetched_date, COUNT(*) FROM {table} WHERE fetched_date<? "
                        "GROUP BY 1 ORDER BY 1 DESC LIMIT 1", (today,)).fetchone()
    return n, prev


def collect_lines(conn, today, warns):
    """수집량 — 오늘(UTC `fetched_date`)과 직전 수집일. 최근 `GAP_DAYS`일에 빈 날이 있으면 알린다."""
    lines = []
    for label, table in (("노선 수집", "offers"), ("광역 수집", "broad_offers")):
        n, prev = _day_count(conn, table, today.isoformat())
        lines.append(f"- {label} {n:,}행" + (f" (직전 {prev[0][5:]}: {prev[1]:,}행)" if prev else ""))
        if n == 0:
            warns.append(f"{label} 0행 — 오늘({today.isoformat()} UTC) 치가 없다")
    have = {r[0] for r in conn.execute("SELECT DISTINCT fetched_date FROM offers WHERE fetched_date>=?",
                                       ((today - timedelta(days=GAP_DAYS - 1)).isoformat(),))}
    holes = [d.isoformat() for d in (today - timedelta(days=i) for i in range(1, GAP_DAYS))
             if d.isoformat() not in have]
    if holes:
        warns.append(f"수집일 구멍 {', '.join(sorted(holes))} (최근 {GAP_DAYS}일, UTC)")
    return lines


def mail_lines(conn, today, now):
    """메일 파이프라인과 구독 알림. 🔴 알림 수는 유입 수치다 — 이 줄이 본문을 로그에 못 찍는 이유다."""
    total, pending = conn.execute("SELECT COUNT(*), COALESCE(SUM(parsed=0), 0) FROM emails").fetchone()
    recent = 0
    for (raw,) in conn.execute("SELECT received_at FROM emails"):
        try:
            recent += timedelta(0) <= now - parsedate_to_datetime(raw) <= timedelta(hours=24)
        except (TypeError, ValueError):
            continue          # 날짜를 못 읽는 메일은 세지 않는다 — 틀리게 세느니
    deals = conn.execute("SELECT COUNT(*) FROM mail_deals").fetchone()[0]
    rows, people = conn.execute("SELECT COUNT(*), COUNT(DISTINCT email_hash) FROM alert_log WHERE sent_date=?",
                                (today.isoformat(),)).fetchone()
    return [f"- 항공사 메일 최근 24시간 {recent}통 · 누적 {total}통 · 파싱 대기 {pending}통",
            f"- 메일 특가 누적 {deals}건",
            f"- 구독 알림 오늘 {people}명에게 {rows}건" if rows else "- 구독 알림 오늘 발송 없음"]


def probe_lines(today):
    """노선 후보의 연속 측정과 판정(`probe_routes`). 후보가 없으면 `[]`."""
    data = probe_routes.load()
    lines = []
    for o, d in probe_routes.CANDIDATES:
        route = f"{o}-{d}"
        counts = probe_routes.streak(data, route, today)
        lines.append(f"- {route} 연속 {len(counts)}일 {counts[:probe_routes.WINDOW]} → {probe_routes.verdict(counts)}"
                     if counts else f"- {route} 오늘 측정 없음 — 연속이 끊겼다")
    return lines


def _goat(site, token, path, **query):
    """GoatCounter REST API 한 번(`https://<site>.goatcounter.com/api/v0`, Bearer 토큰, 초당 4회 제한)."""
    req = urllib.request.Request(f"https://{site}.goatcounter.com/api/v0{path}?{urllib.parse.urlencode(query)}",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def visit_lines(now):
    """방문 집계(GoatCounter, 기획 결정 2026-10-05 (2)) — **어제 하루(KST)** 와 최근 7일.

    🔴 여기 숫자는 「우리에게 사람이 얼마나 오는가」다. 메일 본문에만 싣는다 — 로그·저장소·커밋 메시지 금지.
    시크릿이 없으면 「연결 안 됨」으로 적고 넘어간다. 있는데 못 받으면 예외를 올려 `_section` 이 적게 한다.
    """
    site, token = env.get("GOATCOUNTER_SITE"), env.get("GOATCOUNTER_TOKEN")
    if not (site and token):
        return ["- 아직 연결 안 됨 (변수 GOATCOUNTER_SITE · 시크릿 GOATCOUNTER_TOKEN)"]
    today0 = now.astimezone(timeutil.KST).replace(hour=0, minute=0, second=0, microsecond=0)
    z = lambda dt: dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end = z(today0 - timedelta(seconds=1))                          # 어제 23:59:59 KST
    try:
        day = _goat(site, token, "/stats/hits", start=z(today0 - timedelta(days=1)), end=end, limit=5)
        week = _goat(site, token, "/stats/total", start=z(today0 - timedelta(days=7)), end=end)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        # 집계된 방문이 한 건도 없으면 통계 조회가 404 다(2026-10-07 실측: 사이트·토큰은 맞고 대시보드는 「No data received」).
        # 매일 뜨는 경고는 안 읽게 된다 — 경고로 올리지 않되 **코드는 적는다.** 스크립트가 나간 뒤에도 이 줄이면 그때는 고장이다.
        return ["- 아직 집계된 방문이 없다 (404) — 프론트가 집계 스크립트를 배포하기 전이면 정상"]
    lines = [f"- 어제({today0 - timedelta(days=1):%m-%d} KST) 방문 {day['total']} · 최근 7일 {week['total']}"]
    lines += [f"  · {h['count']:>4}  {h['path']}" for h in day.get("hits", []) if h.get("count")]
    return lines


def _section(title, fn, *args):
    """한 구역이 죽어도 **보고는 나간다.** 못 읽은 것은 못 읽었다고 적는다."""
    try:
        lines = fn(*args)
    except Exception as e:                      # 보고 메일이 통계 하나 때문에 통째로 안 오면 안 된다
        lines = [f"- ⚠️ 읽지 못했다: {type(e).__name__}: {e}"]
    return ([f"[{title}]"] + lines + [""]) if lines else []


def build(environ, now):
    """`(제목, 본문)`. `environ` 은 워크플로가 넣는 값들, `now` 는 aware datetime."""
    status = (environ.get("JOB_STATUS") or "").strip()
    event = (environ.get("GITHUB_EVENT_NAME") or "").strip()
    cron = (environ.get("SCHEDULE") or "").strip()
    started = parse_started(environ.get("STARTED"))
    today = (started or now).astimezone(timezone.utc).date()      # 수집 라벨과 같은 축(UTC)
    warns = []

    head = []
    if event == "schedule":
        backup = bool(cron) and cron == (environ.get("BACKUP_CRON") or "").strip()
        head.append("예약 실행 (예비)" if backup else "예약 실행 (주)")
        if backup:
            warns.append("예비 실행이 일했다 — 주 실행이 버려졌거나 발행까지 못 갔다")
    elif event:
        head.append("수동 실행" if event == "workflow_dispatch" else event)
    if started:
        head.append(f"시작 {_when(started)}")
        sched = scheduled_for(started, cron) if event == "schedule" else None
        if sched:
            head.append(f"예약 {_when(sched)} → {_span(started - sched)} 늦게 시작")
        if event == "schedule" and started.hour >= LATE_HOUR_UTC:
            warns.append(f"시작이 {started:%H:%M} UTC — 자정까지 2시간이 안 남았다. cron 을 당길 때다(BB36)")
    if environ.get("GITHUB_RUN_ID"):
        head.append("기록 {}/{}/actions/runs/{}".format(environ.get("GITHUB_SERVER_URL", "https://github.com"),
                                                      environ.get("GITHUB_REPOSITORY", ""), environ["GITHUB_RUN_ID"]))

    health = read_health(environ.get("HEALTH_NOTES"))
    body = []
    body += ["[상태 점검]"] + (health or ["- 기록이 없다 — 점검 스텝이 돌지 못했거나 건너뛰었다"]) + [""]
    n_deals = n_routes = None
    try:
        pub, n_deals, n_routes = publish_lines(started, warns)
    except Exception as e:
        pub = [f"- ⚠️ 발행물을 읽지 못했다: {type(e).__name__}: {e}"]
        warns.append("발행물(docs/v1)을 읽지 못했다")
    body += ["[발행]"] + pub + [""]
    try:
        conn = open_db()
    except sqlite3.Error as e:
        body += ["[수집]", f"- ⚠️ DB 를 열지 못했다: {e}", ""]
    else:
        try:
            body += _section("수집", collect_lines, conn, today, warns)
            body += _section("메일 · 구독", mail_lines, conn, today, now)
        finally:
            conn.close()
    body += _section("노선 후보 — 7일 연속 중앙값 10건 이상이면 넣는다", probe_lines, today)
    visits = _section("방문 (GoatCounter)", visit_lines, now)
    if any("읽지 못했다" in line for line in visits):
        warns.append("방문 통계를 읽지 못했다 — 토큰 권한·사이트 코드를 볼 것")
    body += visits

    day = f"{now.astimezone(timeutil.KST):%m-%d}"
    if status == "success" and not warns:
        mark, verdict = "✅", "크론 정상"
    elif status == "success":
        mark, verdict = "⚠️", f"크론 완료 · 주의 {len(warns)}건"
    elif status in ("failure", "cancelled"):
        mark, verdict = "❌", "크론 실패" if status == "failure" else "크론 취소됨"
    else:
        mark, verdict = "❔", "잡 결과 모름(로컬 실행)"
    subject = f"[갈래말래] {mark} {day} {verdict}"
    if status == "success" and n_deals is not None:
        subject += f" · 딜 {n_deals} · 노선 {n_routes}"

    top = [f"{mark} {verdict}"] + head + [""]
    if warns:
        top += ["[주의]"] + [f"- ⚠️ {w}" for w in warns] + [""]
    return subject, "\n".join(top + body).rstrip() + "\n"


def send(subject, body):
    """보고를 보낸다 → 받는 주소 수. 실패는 **그대로 올린다** — 조용히 안 오는 보고는 보고가 아니다."""
    to = [a.strip() for a in env.require(
        "REPORT_TO", "production 환경 시크릿 REPORT_TO(보고 받을 주소)를 확인할 것.").split(",") if a.strip()]
    addr, pw = load_env()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = addr
    msg["To"] = ", ".join(to)
    with smtplib.SMTP_SSL(SMTP_HOST, 465) as smtp:
        smtp.login(addr, pw)
        smtp.sendmail(addr, to, msg.as_string())
    return len(to)


def main():
    subject, body = build(os.environ, datetime.now(timezone.utc))
    if "--dry-run" in sys.argv:
        print(subject, "", body, sep="\n")
        return
    n = send(subject, body)
    print(f"보고 메일 발송: 받는 주소 {n}곳 · 본문 {body.count(chr(10))}줄 (내용은 로그에 찍지 않는다)")
    # 못 읽은 구역은 **이름과 오류 종류만** 찍는다 — 본문을 못 보는 로그에서 「방문 통계가 붙었나」를 알 길이 이것뿐이다.
    lines = body.splitlines()
    for title, nxt in zip(lines, lines[1:]):
        if title.startswith("[") and nxt.startswith("- ⚠️ 읽지 못했다:"):
            print(f"  못 읽은 구역 — {title.strip('[]')}: {nxt.split(':')[1].strip()}")


if __name__ == "__main__":
    main()
