# -*- coding: utf-8 -*-
"""일일 보고 메일 (BE22) — 크론이 끝날 때 운영자에게 한 통.

조용히 틀릴 수 있는 자리:
  · 잡은 실패했는데 점검 줄이 전부 ✅ 라 「정상」으로 읽힌다 → 머리말은 **잡 결과**를 따른다
  · 통계 하나를 못 읽어 보고가 통째로 안 온다 → 구역 하나가 죽어도 나머지는 나간다
  · 발송이 실패했는데 스텝은 초록불이다 → 예외를 삼키지 않는다
  · 본문(구독 알림 수 같은 유입 수치)이 **공개 로그**에 찍힌다 → 발송 경로는 내용을 print 하지 않는다
  · 제목에 `구독신청`·`구독취소`가 들어가 서비스 메일함에서 구독 메일로 읽힌다
  · 지연이 자정을 넘은 날 예약 시각을 「오늘」로 잡아 지연이 음수가 된다
네트워크·실 DB·실 `.env`·실 `docs/v1`은 건드리지 않는다.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from email import message_from_string
from email.header import decode_header
from pathlib import Path
from unittest import mock

import daily_report
import db
import env
import probe_routes
import subscriptions
from daily_report import build, parse_started, read_health, scheduled_for

UTC = timezone.utc
STARTED = "2026-10-03T17:53:31Z"                       # 주 실행(14:10Z)이 3시간 43분 늦게 시작한 날
NOW = datetime(2026, 10, 3, 18, 5, tzinfo=UTC)
TODAY = date(2026, 10, 3)
SECRET_TO = "owner@example.com"


def deal(route="ICN-NRT", oa="ICN", ad=True):
    return {"route": route, "oa": oa, "links": [{"name": "a", "url": "u", "ad": ad}]}


class Fixture(unittest.TestCase):
    """임시 `docs/v1` · DB · 후보 측정 파일 · 점검 기록. 실물은 하나도 안 연다."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.v1 = self.root / "v1"
        (self.v1 / "routes").mkdir(parents=True)
        self.write_v1()
        self.db = self.root / "prices.db"
        with closing(sqlite3.connect(self.db)) as c:
            c.executescript(db.SCHEMA)
            for i in range(7):                                   # 오늘 포함 7일 — 구멍 없음
                day = (TODAY - timedelta(days=i)).isoformat()
                for k in range(3 if i else 5):                   # 오늘 5행, 그 전은 3행
                    c.execute("INSERT INTO offers (fetched_date, origin, destination, depart_date, price) "
                              "VALUES (?,?,?,?,?)", (day, "ICN", "NRT", f"2026-11-{k + 1:02d}", 100 + k))
                c.execute("INSERT INTO broad_offers (fetched_date, origin, destination, price) VALUES (?,?,?,?)",
                          (day, "ICN", "NRT", 100))
            c.execute("INSERT INTO emails (received_at, sender, subject, parsed) VALUES (?,?,?,1)",
                      ("Sat, 3 Oct 2026 20:00:00 +0900", "a", "s1"))      # 11:00Z — 24시간 안
            c.execute("INSERT INTO emails (received_at, sender, subject, parsed) VALUES (?,?,?,0)",
                      ("Mon, 28 Sep 2026 09:00:00 +0900", "a", "s2"))     # 오래됨 · 파싱 대기
            c.execute("INSERT INTO emails (received_at, sender, subject, parsed) VALUES (?,?,?,1)",
                      ("날짜 아님", "a", "s3"))
            for price in (1, 2):
                c.execute("INSERT INTO alert_log (sent_date, email_hash, origin, destination, price) "
                          "VALUES (?,?,?,?,?)", (TODAY.isoformat(), "h1", "ICN", "NRT", price))
            c.commit()
        self.probe = self.root / "route_probe.json"
        self.probe.write_text(json.dumps({"ICN-CNX": {
            (TODAY - timedelta(days=i)).isoformat(): {"n": 14, "direct": 6} for i in range(7)}}), encoding="utf-8")
        self.health = self.root / "health.md"
        self.health.write_text("## 수집 결과 (2026-10-04 02:58 KST)\n- ✅ 노선 수집 (success)\n"
                               "- ❌ 사이트 점검: 사이트가 **2026-09-30** 에 멈춰 있다\n", encoding="utf-8")
        for target, name, value in ((daily_report, "V1", self.v1), (db, "DB_PATH", self.db),
                                    (probe_routes, "PATH", self.probe),
                                    (probe_routes, "CANDIDATES", [("ICN", "CNX")]),
                                    (env, "ENV_FILE", self.root / "no.env")):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)

    def write_v1(self, deals=None, generated="2026-10-04T02:54:26+09:00", preserved=False):
        deals = [deal(), deal("PUS-BKK", "PUS")] if deals is None else deals
        (self.v1 / "meta.json").write_text(json.dumps({"generated": generated, "preserved": preserved}), encoding="utf-8")
        (self.v1 / "deals.json").write_text(json.dumps({"deals": deals}), encoding="utf-8")
        (self.v1 / "routes" / "index.json").write_text(
            json.dumps({"routes": [{"code": "ICN-NRT"}, {"code": "PUS-BKK"}, {"code": "ICN-CJU"}]}), encoding="utf-8")

    def environ(self, **over):
        e = {"JOB_STATUS": "success", "GITHUB_EVENT_NAME": "schedule", "SCHEDULE": "10 14 * * *",
             "BACKUP_CRON": "10 18 * * *", "STARTED": STARTED, "HEALTH_NOTES": str(self.health),
             "GITHUB_RUN_ID": "77", "GITHUB_REPOSITORY": "o/r", "GITHUB_SERVER_URL": "https://github.com"}
        e.update(over)
        return e

    def build(self, now=NOW, **over):
        return build(self.environ(**over), now)


class ScheduleTest(unittest.TestCase):
    def test_same_day(self):
        at = scheduled_for(parse_started(STARTED), "10 14 * * *")
        self.assertEqual(at, datetime(2026, 10, 3, 14, 10, tzinfo=UTC))

    def test_delay_across_midnight_picks_yesterday(self):
        """18:10 예약이 다음 날 00:30 에 시작 — 「오늘 18:10」으로 잡으면 지연이 음수다."""
        started = datetime(2026, 10, 4, 0, 30, tzinfo=UTC)
        self.assertEqual(scheduled_for(started, "10 18 * * *"), datetime(2026, 10, 3, 18, 10, tzinfo=UTC))

    def test_unknown_cron_shapes_are_not_guessed(self):
        for cron in ("", None, "*/5 * * * *", "10 14 * * 1", "10 14 1 * *", "x y * * *"):
            with self.subTest(cron=cron):
                self.assertIsNone(scheduled_for(parse_started(STARTED), cron))

    def test_started_is_optional(self):
        for raw in (None, "", "어제"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_started(raw))

    def test_the_workflow_crons_and_backup_marker_agree(self):
        """`collect.yml` 의 예약 둘째 줄과 `BACKUP_CRON` 은 **같은 문자열**이어야 한다.

        갈리면 예비 실행이 자기가 예비인 줄 모른다 — 가드가 안 걸려 매일 두 번 전부 돌고, 보고는 「(주)」라고 적는다.
        예외도 경고도 없다. 예약 시각을 옮길 때 한쪽만 고치기 쉬운 자리다(2026-10-06 에 옮겼다).
        """
        import re
        text = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "collect.yml").read_text(encoding="utf-8")
        crons = re.findall(r'^\s*- cron: "([^"]+)"', text, re.M)
        backup = re.findall(r'^\s*BACKUP_CRON: "([^"]+)"', text, re.M)
        self.assertEqual(len(crons), 2, crons)
        self.assertEqual(backup, [crons[1]])
        for cron in crons:                                   # 보고가 지연을 계산할 수 있는 모양인가
            self.assertIsNotNone(scheduled_for(parse_started(STARTED), cron), cron)


class HeadlineTest(Fixture):
    def test_clean_run(self):
        subject, body = self.build()
        self.assertEqual(subject, "[갈래말래] ✅ 10-04 크론 정상 · 딜 2 · 노선 3")
        self.assertIn("예약 실행 (주)", body)
        self.assertIn("시작 10-04 02:53 KST (10-03 17:53 UTC)", body)       # KST 먼저
        self.assertIn("예약 10-03 23:10 KST (10-03 14:10 UTC) → 3시간 43분 늦게 시작", body)
        self.assertIn("기록 https://github.com/o/r/actions/runs/77", body)
        self.assertNotIn("[주의]", body)

    def test_job_failure_wins_over_green_checks(self):
        """🔴 커밋 실패처럼 점검 줄에 없는 실패도 있다. 머리말은 점검 줄이 아니라 **잡 결과**다."""
        self.health.write_text("- ✅ 노선 수집 (success)\n", encoding="utf-8")
        subject, body = self.build(JOB_STATUS="failure")
        self.assertTrue(subject.startswith("[갈래말래] ❌ 10-04 크론 실패"), subject)
        self.assertTrue(body.startswith("❌ 크론 실패\n"))
        self.assertNotIn("딜", subject)                         # 실패한 날 제목은 수치로 안심시키지 않는다

    def test_cancelled_and_unknown(self):
        self.assertIn("❌", self.build(JOB_STATUS="cancelled")[0])
        self.assertIn("❔", self.build(JOB_STATUS="")[0])

    def test_subject_is_never_a_subscription_mail(self):
        """받는 주소가 서비스 메일함이면 `subscriptions`가 제목으로 구독·해지를 판정한다."""
        for status in ("success", "failure", "cancelled", ""):
            subject = self.build(JOB_STATUS=status)[0]
            with self.subTest(status=status):
                self.assertNotIn(subscriptions.SUBSCRIBE, subject)
                self.assertNotIn(subscriptions.UNSUBSCRIBE, subject)
                subs = {}
                subscriptions.apply_message(subs, "x@y.z", subject, self.build(JOB_STATUS=status)[1])
                self.assertEqual(subs, {})

    def test_manual_run_has_no_schedule_line(self):
        _, body = self.build(GITHUB_EVENT_NAME="workflow_dispatch", SCHEDULE="")
        self.assertIn("수동 실행", body)
        self.assertNotIn("늦게 시작", body)

    def test_backup_run_doing_the_work_is_a_warning(self):
        subject, body = self.build(SCHEDULE="10 18 * * *")
        self.assertIn("예약 실행 (예비)", body)
        self.assertIn("⚠️ 예비 실행이 일했다", body)
        self.assertIn("주의 1건", subject)

    def test_late_start_warns_before_the_midnight_check_fails(self):
        _, body = self.build(STARTED="2026-10-03T22:05:00Z")
        self.assertIn("자정까지 2시간이 안 남았다", body)
        self.assertNotIn("자정까지", self.build(STARTED="2026-10-03T21:59:00Z")[1])
        self.assertNotIn("자정까지", self.build(GITHUB_EVENT_NAME="workflow_dispatch", STARTED="2026-10-03T22:05:00Z")[1])


class HealthNotesTest(Fixture):
    def test_lines_are_copied_without_markdown(self):
        _, body = self.build()
        self.assertIn("- ✅ 노선 수집 (success)", body)
        self.assertIn("- ❌ 사이트 점검: 사이트가 2026-09-30 에 멈춰 있다", body)
        self.assertNotIn("## 수집 결과", body)

    def test_missing_notes_are_said_out_loud(self):
        for path in ("", str(self.root / "none.md")):
            with self.subTest(path=path):
                self.assertIn("기록이 없다", self.build(HEALTH_NOTES=path)[1])
        self.assertEqual(read_health(None), [])


class PublishTest(Fixture):
    def test_numbers(self):
        _, body = self.build()
        self.assertIn("- 발행 시각 10-04 02:54 KST (10-03 17:54 UTC) — 이번 실행이 만들었다", body)
        self.assertIn("- 노선 3 · 딜 2", body)
        self.assertIn("- 제휴 링크가 붙은 딜 2/2", body)

    def test_stale_publish_is_named(self):
        """「결론이 맞은 것과 근거가 맞은 것은 다르다」 — 수치가 멀쩡해도 **이번 실행이 만든 게 아니면** 말한다."""
        self.write_v1(generated="2026-10-03T02:54:26+09:00")
        subject, body = self.build()
        self.assertIn("⚠️ 이번 실행은 발행하지 못했다", body)
        self.assertNotIn("이번 실행이 만들었다", body)
        self.assertIn("⚠️", subject)

    def test_missing_affiliate_links(self):
        self.write_v1(deals=[deal(), deal(ad=False)])
        _, body = self.build()
        self.assertIn("- 제휴 링크가 붙은 딜 1/2", body)
        self.assertIn("⚠️ 제휴 링크가 빠진 딜 1건", body)

    def test_route_and_oa_disagree(self):
        self.write_v1(deals=[deal("ICN-CJU", "GMP"), deal(None, "GMP")])     # route 없는 딜은 대상이 아니다
        self.assertIn("⚠️ route 와 oa 가 어긋난 딜 1건", self.build()[1])

    def test_preserved_day(self):
        self.write_v1(preserved=True)
        self.assertIn("⚠️ 딜 보존일", self.build()[1])

    def test_unreadable_publish_does_not_kill_the_report(self):
        (self.v1 / "deals.json").write_text("{", encoding="utf-8")
        subject, body = self.build()
        self.assertIn("발행물을 읽지 못했다", body)
        self.assertIn("[수집]", body)                             # 나머지 구역은 나간다
        self.assertIn("⚠️", subject)
        self.assertNotIn("딜", subject)


class CollectTest(Fixture):
    def test_today_and_previous_day(self):
        _, body = self.build()
        self.assertIn("- 노선 수집 5행 (직전 10-02: 3행)", body)
        self.assertIn("- 광역 수집 1행 (직전 10-02: 1행)", body)

    def test_today_is_the_day_the_run_started(self):
        """수집 라벨(`fetched_date`)은 시작한 날의 UTC 날짜다. 보고가 자정을 넘겨 나가도 그날 치를 센다."""
        _, body = self.build(now=datetime(2026, 10, 4, 0, 20, tzinfo=UTC))
        self.assertIn("- 노선 수집 5행", body)
        self.assertNotIn("0행", body)

    def test_nothing_collected_today(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("DELETE FROM offers WHERE fetched_date=?", (TODAY.isoformat(),))
            c.commit()
        subject, body = self.build()
        self.assertIn("⚠️ 노선 수집 0행 — 오늘(2026-10-03 UTC) 치가 없다", body)
        self.assertIn("⚠️", subject)

    def test_a_hole_in_the_last_week(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("DELETE FROM offers WHERE fetched_date='2026-09-30'")
            c.commit()
        self.assertIn("⚠️ 수집일 구멍 2026-09-30", self.build()[1])

    def test_a_dead_section_does_not_kill_the_report(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("DROP TABLE broad_offers")
            c.commit()
        _, body = self.build()
        self.assertIn("[수집]\n- ⚠️ 읽지 못했다: OperationalError", body)
        self.assertIn("[메일 · 구독]\n- 항공사 메일", body)

    def test_db_is_opened_read_only(self):
        with closing(daily_report.open_db()) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("CREATE TABLE be22_probe (x)")


class MailAndProbeTest(Fixture):
    def test_mail_lines(self):
        _, body = self.build()
        self.assertIn("- 항공사 메일 최근 24시간 1통 · 누적 3통 · 파싱 대기 1통", body)
        self.assertIn("- 구독 알림 오늘 1명에게 2건", body)

    def test_no_alerts_today(self):
        with closing(sqlite3.connect(self.db)) as c:
            c.execute("DELETE FROM alert_log")
            c.commit()
        self.assertIn("- 구독 알림 오늘 발송 없음", self.build()[1])

    def test_probe_verdict_is_shown(self):
        self.assertIn("- ICN-CNX 연속 7일 [14, 14, 14, 14, 14, 14, 14] → ✅ 넣을 조건 충족", self.build()[1])

    def test_probe_missing_today(self):
        data = json.loads(self.probe.read_text(encoding="utf-8"))
        del data["ICN-CNX"][TODAY.isoformat()]
        self.probe.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("- ICN-CNX 오늘 측정 없음 — 연속이 끊겼다", self.build()[1])

    def test_no_candidates_no_section(self):
        with mock.patch.object(probe_routes, "CANDIDATES", []):
            self.assertNotIn("노선 후보", self.build()[1])


class VisitsTest(Fixture):
    """방문 집계(GoatCounter) — 숫자는 메일 본문에만. 네트워크는 `_goat` 를 갈아끼운다."""
    GOAT = {"GOATCOUNTER_SITE": "site", "GOATCOUNTER_TOKEN": "tok"}

    def fake(self, calls):
        def _goat(site, token, path, **q):
            calls.append((site, token, path, q))
            return ({"total": 4321, "hits": [{"path": "/routes/ICN-NRT.html", "count": 987}, {"path": "/x", "count": 0}]}
                    if path == "/stats/hits" else {"total": 87654})
        return _goat

    def build_with(self, goat, environ=None):
        with mock.patch.dict(os.environ, self.GOAT if environ is None else environ, clear=True), \
             mock.patch.object(daily_report, "_goat", goat):
            return self.build()

    def test_not_connected_is_said_and_is_not_a_warning(self):
        goat = mock.Mock()
        subject, body = self.build_with(goat, environ={"GOATCOUNTER_SITE": "site"})      # 토큰 없음
        goat.assert_not_called()
        self.assertIn("[방문 (GoatCounter)]\n- 아직 연결 안 됨", body)
        self.assertIn("✅", subject)

    def test_yesterday_in_kst_and_the_week(self):
        calls = []
        _, body = self.build_with(self.fake(calls))
        self.assertIn("- 어제(10-03 KST) 방문 4321 · 최근 7일 87654", body)      # NOW = 10-04 03:05 KST
        self.assertIn(" 987  /routes/ICN-NRT.html", body)
        self.assertNotIn("/x", body)                                              # 0건 경로는 안 싣는다
        (s1, t1, p1, q1), (_, _, p2, q2) = calls
        self.assertEqual((s1, t1, p1, p2), ("site", "tok", "/stats/hits", "/stats/total"))
        # 어제 = KST 10-03 00:00 ~ 23:59:59 → UTC 로는 10-02 15:00 ~ 10-03 14:59:59. UTC 날짜로 자르면 9시간 어긋난다.
        self.assertEqual((q1["start"], q1["end"]), ("2026-10-02T15:00:00Z", "2026-10-03T14:59:59Z"))
        self.assertEqual((q2["start"], q2["end"]), ("2026-09-26T15:00:00Z", "2026-10-03T14:59:59Z"))

    def test_api_failure_is_a_warning_and_the_report_still_goes(self):
        subject, body = self.build_with(mock.Mock(side_effect=OSError("HTTP Error 403: Forbidden")))
        self.assertIn("[방문 (GoatCounter)]\n- ⚠️ 읽지 못했다: OSError", body)
        self.assertIn("⚠️ 방문 통계를 읽지 못했다", body)
        self.assertIn("주의 1건", subject)
        self.assertIn("[발행]", body)

    def run_main(self, goat):
        env_ = dict(self.environ(), MAIL_ADDRESS="svc@example.com", MAIL_APP_PASSWORD="pw", REPORT_TO=SECRET_TO, **self.GOAT)
        with mock.patch.dict(os.environ, env_, clear=True), \
             mock.patch.object(daily_report, "_goat", goat), \
             mock.patch.object(daily_report.smtplib, "SMTP_SSL", mock.MagicMock()), \
             mock.patch.object(daily_report.sys, "argv", ["daily_report.py"]), \
             mock.patch("builtins.print") as out:
            daily_report.main()
        return "\n".join(" ".join(map(str, c.args)) for c in out.call_args_list)

    def test_visit_numbers_never_reach_the_log(self):
        """🔴 방문 수는 유입 수치다 — 공개 Actions 로그에 한 글자도 안 나간다."""
        printed = self.run_main(self.fake([]))
        for secret in ("4321", "87654", "987", "/routes/ICN-NRT.html", "tok"):
            self.assertNotIn(secret, printed)

    def test_a_failed_section_is_named_in_the_log_without_content(self):
        printed = self.run_main(mock.Mock(side_effect=OSError("HTTP Error 403: Forbidden")))
        self.assertIn("못 읽은 구역 — 방문 (GoatCounter): OSError", printed)
        self.assertNotIn("403", printed)


class SendTest(Fixture):
    ENV = {"MAIL_ADDRESS": "svc@example.com", "MAIL_APP_PASSWORD": "pw", "REPORT_TO": SECRET_TO}

    def run_main(self, argv=("daily_report.py",), environ=None, smtp_cls=None):
        environ = dict(self.environ(), **(self.ENV if environ is None else environ))
        smtp_cls = smtp_cls or mock.MagicMock()
        with mock.patch.dict(os.environ, environ, clear=True), \
             mock.patch.object(daily_report.smtplib, "SMTP_SSL", smtp_cls), \
             mock.patch.object(daily_report.sys, "argv", list(argv)), \
             mock.patch("builtins.print") as out:
            daily_report.main()
        printed = "\n".join(" ".join(map(str, c.args)) for c in out.call_args_list)
        return smtp_cls, printed

    def test_it_is_sent_to_the_secret_address(self):
        cls, _ = self.run_main()
        smtp = cls.return_value.__enter__.return_value
        smtp.login.assert_called_once_with("svc@example.com", "pw")
        sender, to, raw = smtp.sendmail.call_args.args
        self.assertEqual((sender, to), ("svc@example.com", [SECRET_TO]))
        msg = message_from_string(raw)
        subject = "".join(p.decode(enc) if isinstance(p, bytes) else p for p, enc in decode_header(msg["Subject"]))
        self.assertTrue(subject.startswith("[갈래말래] "), subject)
        self.assertIn("구독 알림 오늘 1명에게 2건", msg.get_payload(decode=True).decode("utf-8"))

    def test_several_recipients(self):
        cls, _ = self.run_main(environ=dict(self.ENV, REPORT_TO=" a@x.com , b@y.com,"))
        self.assertEqual(cls.return_value.__enter__.return_value.sendmail.call_args.args[1], ["a@x.com", "b@y.com"])

    def test_the_log_never_carries_the_content(self):
        """🔴 공개 저장소는 Actions 로그도 공개다. 본문엔 구독 알림 수가 있고 방문자 수도 들어올 자리다."""
        _, printed = self.run_main()
        subject, body = self.build()
        self.assertTrue(printed)                                           # 전제 — 뭔가는 찍는다
        for line in [subject] + [l for l in body.splitlines() if l.strip()]:
            self.assertNotIn(line, printed)
        self.assertNotIn(SECRET_TO, printed)
        self.assertNotIn("구독 알림", printed)

    def test_dry_run_prints_and_does_not_connect(self):
        cls, printed = self.run_main(argv=("daily_report.py", "--dry-run"), environ={})
        cls.assert_not_called()
        self.assertIn("[발행]", printed)

    def test_no_recipient_is_loud_and_sends_nothing(self):
        cls = mock.MagicMock()
        with self.assertRaises(SystemExit) as cm:
            self.run_main(environ={k: v for k, v in self.ENV.items() if k != "REPORT_TO"}, smtp_cls=cls)
        self.assertIn("REPORT_TO", str(cm.exception))
        cls.assert_not_called()

    def test_a_failed_send_is_not_swallowed(self):
        """조용히 안 오는 보고는 보고가 아니다 — 스텝이 실패해야 GitHub 가 대신 알린다."""
        with self.assertRaises(OSError):
            self.run_main(smtp_cls=mock.MagicMock(side_effect=OSError("연결 거부")))
        cls = mock.MagicMock()
        cls.return_value.__enter__.return_value.sendmail.side_effect = daily_report.smtplib.SMTPException("거절")
        with self.assertRaises(daily_report.smtplib.SMTPException):
            self.run_main(smtp_cls=cls)


if __name__ == "__main__":
    unittest.main()
