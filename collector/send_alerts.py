# -*- coding: utf-8 -*-
"""구독자에게 노선 특가 알림 메일 발송.

흐름: 받은편지함에서 구독자 계산(subscriptions.py) → 오늘의 특가와 매칭 →
같은 특가를 이미 보낸 구독자는 제외(alert_log, 이메일 해시) → Gmail SMTP 발송.

법적 표기: 제휴 링크가 포함되므로 정보통신망법에 따라 제목 '(광고)' 표기와
수신거부 방법을 본문에 포함한다.

사용: python collector/send_alerts.py
"""
import hashlib
import smtplib
import sys
from datetime import date
from email.mime.text import MIMEText
from email.header import Header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
from build_site import CITY, airline_name
from detect_deals import compute_deals
from mail_ingest import load_env
from subscriptions import load_subscribers

SMTP_HOST = "smtp.gmail.com"
SITE_URL = "https://ryu-tomi.github.io/promo-ticket-site/"


def email_hash(addr: str) -> str:
    return hashlib.sha256(addr.strip().lower().encode()).hexdigest()[:16]


def deal_line(d) -> str:
    kind = "직항" if d["is_direct"] else "경유"
    return (f"<li><b>{CITY.get(d['origin'], d['origin'])} → "
            f"{CITY.get(d['destination'], d['destination'])}</b> "
            f"{d['depart_date']}~{d['return_date']} 왕복 "
            f"<b>{d['price']:,}원</b> ({airline_name(d['airline'])}, {kind}) "
            f"— 시세 대비 <b>{d['discount_pct']}% 저렴</b> "
            f"<a href='{d['link']}'>가격 확인</a></li>")


def build_mail(to_addr, deals):
    n = len(deals)
    top = max(d["discount_pct"] for d in deals)
    subject = f"(광고) ✈️ 구독 노선 특가 {n}건 — 최대 {top}% 저렴"
    body = f"""<div style="font-family:sans-serif;line-height:1.6">
<h2>구독하신 노선에 특가가 떴습니다</h2>
<ul>{''.join(deal_line(d) for d in deals)}</ul>
<p>· 가격은 조회 시점 기준이며 실제 예약 가격은 달라질 수 있습니다.<br>
· 링크를 통해 예약 시 운영자가 수수료를 받을 수 있습니다.</p>
<p><a href="{SITE_URL}">전체 특가 보기</a></p>
<hr>
<p style="color:#888;font-size:12px">본 메일은 특가 알림을 구독 신청하신 분께 발송됩니다.<br>
수신거부(구독 해지): 이 메일에 제목 '구독취소'로 회신해 주세요.
특정 노선만 해지하려면 본문에 노선 코드(예: ICN-FUK)를 적어주세요.<br>
발신: 항공권 특가 알림 ({SITE_URL})</p>
</div>"""
    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["To"] = to_addr
    return msg


def main():
    addr, pw = load_env()
    subs = load_subscribers(addr, pw)
    print(f"구독자 {len(subs)}명")
    if not subs:
        return
    conn = db.connect()
    deals = compute_deals(conn)
    today = date.today().isoformat()
    smtp = None
    n_sent = 0
    for to_addr, routes in subs.items():
        matched = [d for d in deals
                   if "ALL" in routes or f"{d['origin']}-{d['destination']}" in routes]
        h = email_hash(to_addr)
        new = [d for d in matched if not conn.execute(
            """SELECT 1 FROM alert_log WHERE email_hash=? AND origin=? AND destination=?
               AND depart_date=? AND return_date=? AND price=?""",
            (h, d["origin"], d["destination"], d["depart_date"],
             d["return_date"], d["price"])).fetchone()]
        if not new:
            print(f"  {to_addr[:3]}***: 새 특가 없음")
            continue
        if smtp is None:
            smtp = smtplib.SMTP_SSL(SMTP_HOST, 465)
            smtp.login(addr, pw)
        msg = build_mail(to_addr, new)
        msg["From"] = addr
        smtp.sendmail(addr, [to_addr], msg.as_string())
        for d in new:
            conn.execute(
                """INSERT INTO alert_log
                   (sent_date, email_hash, origin, destination, depart_date, return_date, price)
                   VALUES (?,?,?,?,?,?,?)""",
                (today, h, d["origin"], d["destination"],
                 d["depart_date"], d["return_date"], d["price"]))
        conn.commit()
        n_sent += 1
        print(f"  {to_addr[:3]}***: 특가 {len(new)}건 발송")
    if smtp:
        smtp.quit()
    conn.close()
    print(f"완료: {n_sent}명에게 발송")


if __name__ == "__main__":
    main()
