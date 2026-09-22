# -*- coding: utf-8 -*-
"""메일 수집이 **메일함을 바꾸지 않는가** (BB33, BE19).

예전 경로: 쓰기로 열고 `fetch(RFC822)` → `\Seen` 이 붙음 → 다음 `UNSEEN` 검색에서 사라짐.
그래서 **파싱이 실패한 메일은 영영 다시 안 왔다** — 본문 DB(`emails_raw.db`)는 러너와 함께
사라지므로 재파싱할 방법도 없었다. 「조용히 통과할 수 있나」에 정확히 걸리는 자리다.

지금: 메일함은 읽기만 하고, 「처리했나」는 **공개 DB 의 `emails.parsed`** 가 안다(매일 커밋되어 남는다).
여기서는 가짜 IMAP 으로 `main()` 을 실제로 돌려 **그 두 가지를 눈으로 확인한다.**
"""
import base64
import email
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import db
import mail_ingest


def b64(text):
    """RFC 2047 — 실제 메일이 한글 헤더를 보내는 방식."""
    return base64.b64encode(text.encode()).decode()


def raw_mail(subject, sender="news@koreanair.com", date="Mon, 22 Sep 2026 09:00:00 +0900",
             dmarc="pass", body="<p>특가</p>"):
    dom = sender.rpartition("@")[2]
    return (f"From: =?UTF-8?B?{b64('대한항공')}?= <{sender}>\r\n"
            f"Subject: =?UTF-8?B?{b64(subject)}?=\r\n"
            f"Date: {date}\r\n"
            f"Authentication-Results: mx.google.com;\r\n"
            f"       spf=pass smtp.mailfrom=bounce@{dom};\r\n"
            f"       dmarc={dmarc} (p=NONE) header.from={dom}\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n\r\n{body}\r\n").encode()


class FakeIMAP:
    """메일함 흉내. **무엇을 어떻게 읽었는지 기록한다** — 그게 이 테스트의 검사 대상이다."""

    def __init__(self, mails):
        self.mails = {str(i + 1).encode(): m for i, m in enumerate(mails)}
        self.readonly = None
        self.fetch_calls = []          # (mid, what)
        self.logged_out = False

    def login(self, addr, pw):
        return "OK", []

    def select(self, box, readonly=False):
        self.readonly = readonly
        return "OK", []

    def search(self, charset, *criteria):
        ids = list(self.mails)
        if "FROM" in criteria:                      # FROM "domain" 검색
            needle = criteria[criteria.index("FROM") + 1].strip('"').encode()
            ids = [i for i, m in self.mails.items() if needle in m.split(b"\r\n\r\n")[0]]
        return "OK", [b" ".join(ids)]

    def fetch(self, mid, what):
        self.fetch_calls.append((mid, what))
        return "OK", [(b"", self.mails[mid])]       # 헤더 요청에도 전문을 준다(상위집합이라 무방)

    def logout(self):
        self.logged_out = True


class IngestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pub = Path(self.tmp.name) / "prices.db"
        self.raw = Path(self.tmp.name) / "emails_raw.db"
        for p, schema in ((self.pub, db.SCHEMA), (self.raw, db.RAW_SCHEMA)):
            with closing(sqlite3.connect(p)) as c:
                c.executescript(schema)
                c.commit()

    def run_ingest(self, mails, argv=("mail_ingest.py",)):
        fake = FakeIMAP(mails)
        with mock.patch.object(mail_ingest, "load_env", lambda: ("a@b.c", "pw")), \
             mock.patch.object(mail_ingest.imaplib, "IMAP4_SSL", lambda host: fake), \
             mock.patch.object(db, "connect", lambda: sqlite3.connect(self.pub)), \
             mock.patch.object(db, "connect_raw", lambda: sqlite3.connect(self.raw)), \
             mock.patch.object(mail_ingest.sys, "argv", list(argv)), \
             mock.patch("builtins.print"):
            try:
                mail_ingest.main()
            except SystemExit as e:                  # 경보는 데이터 커밋 뒤에 난다
                self.alert = str(e)
            else:
                self.alert = None
        return fake

    def emails(self):
        with closing(sqlite3.connect(self.pub)) as c:
            return {(r[2], r[3]): r[4] for r in c.execute("SELECT * FROM emails")}

    def bodies(self):
        with closing(sqlite3.connect(self.raw)) as c:
            return [r[0] for r in c.execute("SELECT subject FROM emails_raw")]

    def mark_parsed(self, subject):
        with closing(sqlite3.connect(self.pub)) as c:
            c.execute("UPDATE emails SET parsed=1 WHERE subject=?", (subject,))
            c.commit()

    # ── 메일함을 바꾸지 않는가 ────────────────────────────────────────
    def test_mailbox_is_opened_read_only(self):
        fake = self.run_ingest([raw_mail("(광고) 특가")])
        self.assertIs(fake.readonly, True)

    def test_every_fetch_is_peek(self):
        """🔴 `RFC822` 나 `BODY[...]`(PEEK 없음)를 쓰면 `\Seen` 이 붙는다 — 그 순간 BB33 이 되돌아온다."""
        fake = self.run_ingest([raw_mail("(광고) 특가 A"), raw_mail("(광고) 특가 B")])
        self.assertTrue(fake.fetch_calls)
        for mid, what in fake.fetch_calls:
            with self.subTest(what=what):
                self.assertIn("PEEK", what)
                self.assertNotIn("RFC822", what)

    def test_it_logs_out(self):
        self.assertTrue(self.run_ingest([raw_mail("(광고) 특가")]).logged_out)

    # ── 처리 표시가 공개 DB 에 남는가 ─────────────────────────────────
    def test_new_mail_is_saved_as_unparsed(self):
        self.run_ingest([raw_mail("(광고) 특가")])
        self.assertEqual(list(self.emails().values()), [0])
        self.assertEqual(self.bodies(), ["(광고) 특가"])

    def test_parsed_mail_is_not_fetched_again(self):
        self.run_ingest([raw_mail("(광고) 특가")])
        self.mark_parsed("(광고) 특가")
        fake = self.run_ingest([raw_mail("(광고) 특가")])
        body_fetches = [w for _, w in fake.fetch_calls if "HEADER" not in w]
        self.assertEqual(body_fetches, [], "이미 파싱한 메일의 본문을 다시 받았다")

    def test_unparsed_mail_comes_back(self):
        """🔴 **BB33 의 핵심** — 파싱이 실패해 `parsed=0` 으로 남은 메일은 다음 실행이 다시 받아 온다.

        예전에는 이 메일이 이미 읽음이라 `UNSEEN` 에서 사라졌고, 본문 DB 도 러너와 함께 없어져
        **되살릴 길이 없었다.**
        """
        mail = raw_mail("(광고) 특가")
        self.run_ingest([mail])                      # 1회차: 저장(parsed=0) — 파싱은 실패했다고 치자
        fake = self.run_ingest([mail])               # 2회차
        body_fetches = [w for _, w in fake.fetch_calls if "HEADER" not in w]
        self.assertEqual(len(body_fetches), 1, "parsed=0 인 메일을 다시 받지 않았다")
        self.assertEqual(list(self.emails().values()), [0])   # 중복 행이 생기지 않는다

    # ── 거르는 규칙은 그대로인가 ──────────────────────────────────────
    def test_unauthenticated_mail_is_neither_saved_nor_read(self):
        fake = self.run_ingest([raw_mail("(광고) 사칭", dmarc="fail")])
        self.assertEqual(self.emails(), {})
        self.assertEqual([w for _, w in fake.fetch_calls if "HEADER" not in w], [])
        self.assertIn("인증", self.alert or "")

    def test_subscription_mail_never_reaches_the_public_db(self):
        """구독 메일은 PII 다 — 공개 DB 에 제목·발신이 남으면 안 된다."""
        self.run_ingest([raw_mail("구독신청")])
        self.assertEqual(self.emails(), {})

    def test_cap_defers_the_rest(self):
        mails = [raw_mail(f"(광고) 특가 {i}", date=f"Mon, {i:02d} Sep 2026 09:00:00 +0900")
                 for i in range(1, 26)]
        self.run_ingest(mails)
        self.assertEqual(len(self.emails()), mail_ingest.mail_guard.MAX_PER_RUN)
        self.assertIn("상한", self.alert or "")


class NeedsBodyTest(unittest.TestCase):
    KEY = ("Mon, 22 Sep 2026 09:00:00 +0900", "대한항공 <news@koreanair.com>", "(광고) 특가")

    def test_matrix(self):
        for known, expected, why in (
                ({}, True, "처음 보는 메일"),
                ({self.KEY: 0}, True, "저장은 됐지만 파싱이 안 끝났다"),
                ({self.KEY: 1}, False, "파싱까지 끝났다"),
        ):
            with self.subTest(why=why):
                self.assertEqual(mail_ingest.needs_body(known, self.KEY), expected)

    def test_all_flag_ignores_the_mark(self):
        """`--all` 은 백필용이라 `parsed` 를 무시한다."""
        self.assertTrue(mail_ingest.needs_body({self.KEY: 1}, self.KEY, fetch_all=True))


if __name__ == "__main__":
    unittest.main()
