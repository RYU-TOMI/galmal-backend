# -*- coding: utf-8 -*-
"""프로모션 메일 본문을 Claude Code 헤드리스(claude -p)로 파싱해 특가 정보를 추출.

- 입력: data/emails_raw.db 의 미처리(processed=0) 메일
- 출력: data/prices.db 의 mail_deals 테이블 (요약 + 공식 링크만, 개인화 링크 제외)
- 인증: 로컬은 claude 로그인 세션, CI는 CLAUDE_CODE_OAUTH_TOKEN (claude setup-token으로 발급)
  → 별도 API 키 불필요, 구독 사용량으로 처리됨

사용: python collector/parse_mail.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

SCHEMA_GUIDE = """{
  "is_deal": true|false,        // 항공권 특가/프로모션 정보가 실제로 포함됐는지
  "airline": "항공사 한글명" | null,
  "official_url": "URL" | null, // 항공사 공식 도메인의 이벤트 페이지만. 수신자 추적 파라미터가
                                // 붙었으면 파라미터 제거, 구독해지/개인화 링크는 절대 금지
  "deals": [                    // 최대 10개
    {
      "origin": "출발 도시 한글명" | null,
      "destination": "도착 도시 한글명" | null,
      "price_krw": 129000 | null,   // 광고된 대표 가격, 원화 숫자만
      "promo_end": "YYYY-MM-DD" | null,
      "summary": "특가 한 줄 요약 (예: '부산-방콕 편도 총액 12만원대')"
    }
  ]
}"""


def html_to_text(html: str, limit: int = 12000) -> str:
    """토큰 절약용 간이 HTML→텍스트. 링크는 [텍스트](URL) 형태로 보존."""
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                  lambda m: f" [{re.sub('<[^>]+>', '', m.group(2)).strip()}]({m.group(1)}) ",
                  html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;?", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html[:limit]


def call_claude(prompt: str) -> dict:
    """claude -p 헤드리스 호출. 결과 텍스트에서 JSON을 파싱해 반환."""
    proc = subprocess.run(
        "claude -p --output-format json",
        input=prompt, capture_output=True, text=True, encoding="utf-8",
        shell=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"claude 실행 실패: {proc.stderr[:300]}")
    result = json.loads(proc.stdout)["result"]
    result = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.strip())
    return json.loads(result)


def parse_one(sender, subject, body_html) -> dict:
    prompt = (
        "다음은 항공사에서 온 마케팅 메일입니다. 항공권 특가/프로모션 정보를 추출해 "
        "아래 스키마의 JSON만 출력하세요. 설명·코드펜스 없이 JSON 객체 하나만.\n"
        "- 회원가입 안내, 본인 인증, 보안 알림 등 특가와 무관하면 is_deal=false\n"
        f"스키마:\n{SCHEMA_GUIDE}\n\n"
        f"보낸사람: {sender}\n제목: {subject}\n본문:\n{html_to_text(body_html)}"
    )
    return call_claude(prompt)


def main():
    raw = db.connect_raw()
    conn = db.connect()
    rows = raw.execute(
        "SELECT id, received_at, sender, subject, body_html FROM emails_raw WHERE processed=0"
    ).fetchall()
    print(f"미처리 메일 {len(rows)}건")
    n_deals = 0
    for row_id, received, sender, subject, body in rows:
        try:
            result = parse_one(sender, subject, body or "")
        except Exception as e:
            print(f"  파싱 실패({subject[:40]}): {e}")
            continue
        if result.get("is_deal"):
            for d in (result.get("deals") or [])[:10]:
                conn.execute(
                    """INSERT OR IGNORE INTO mail_deals
                       (received_at, airline, origin, destination, price_krw,
                        promo_end, summary, url)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (received, result.get("airline"), d.get("origin"),
                     d.get("destination"), d.get("price_krw"),
                     d.get("promo_end"), d.get("summary") or subject[:80],
                     result.get("official_url")))
                n_deals += 1
            print(f"  특가 {len(result.get('deals') or [])}건: {subject[:50]}")
        else:
            print(f"  특가 아님: {subject[:50]}")
        raw.execute("UPDATE emails_raw SET processed=1 WHERE id=?", (row_id,))
        raw.commit()
        conn.commit()
    conn.close()
    raw.close()
    print(f"완료: 특가 {n_deals}건 저장")


if __name__ == "__main__":
    main()
