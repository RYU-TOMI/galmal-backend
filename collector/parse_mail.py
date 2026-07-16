# -*- coding: utf-8 -*-
"""프로모션 메일 본문을 Claude API(Haiku)로 파싱해 구조화된 특가 정보를 추출.

- 입력: data/emails_raw.db 의 미처리(processed=0) 메일
- 출력: data/prices.db 의 mail_deals 테이블 (요약 + 공식 링크만, 개인화 링크 제외)
- 인증: 환경변수 또는 .env 의 ANTHROPIC_API_KEY
- 비용 절감: 제목에 광고/특가 신호가 없으면 LLM 호출 없이 건너뜀.
  Haiku 기준 통당 ~$0.01 이하, 월 지출 한도는 Console Limits에서 설정.

사용: python collector/parse_mail.py
의존성: pip install anthropic
"""
import os
import re
import sys
from pathlib import Path

import anthropic
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

MODEL = "claude-haiku-4-5"

# 제목 사전 필터: 이 신호가 없으면 특가 메일이 아니라고 보고 LLM 호출 생략
PROMO_SUBJECT = re.compile(r"\(광고\)|특가|할인|프로모션|세일|이벤트|얼리버드", re.I)


class MailDeal(BaseModel):
    origin: str | None = Field(None, description="출발 도시 한글명 (예: 인천, 부산). 명시 없으면 null")
    destination: str | None = Field(None, description="도착 도시 한글명. 노선 특정이 안 되면 null")
    price_krw: int | None = Field(None, description="광고된 대표 가격(원). 없으면 null")
    promo_end: str | None = Field(None, description="프로모션/판매 종료일 YYYY-MM-DD. 없으면 null")
    summary: str = Field(description="특가 내용 한 줄 요약 (예: '부산-방콕 편도 총액 12만원대')")


class MailParseResult(BaseModel):
    is_deal: bool = Field(description="항공권 특가/프로모션 정보가 실제로 포함된 메일인지")
    airline: str | None = Field(None, description="항공사 한글명 (예: 티웨이항공)")
    official_url: str | None = Field(
        None,
        description="항공사 공식 프로모션/이벤트 페이지 URL. 반드시 항공사 도메인의 일반 URL만. "
                    "수신자 식별자가 포함된 추적 링크나 구독해지 링크는 절대 넣지 말 것")
    deals: list[MailDeal] = Field(default_factory=list, description="추출된 특가 항목들 (최대 10개)")


def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("ANTHROPIC_API_KEY가 없습니다. .env 또는 환경변수로 설정하세요.")


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


def parse_one(client, sender, subject, body_html):
    prompt = (
        "다음은 항공사에서 온 마케팅 메일입니다. 항공권 특가/프로모션 정보를 추출하세요.\n"
        "- 단순 회원가입 안내, 본인 인증, 보안 알림 등 특가와 무관하면 is_deal=false\n"
        "- price_krw는 항공권 판매 가격만 (예: '129,000원~' -> 129000). "
        "'최대 N원 할인'처럼 할인 금액은 가격이 아니므로 null로 둘 것\n"
        "- official_url은 항공사 공식 도메인의 프로모션 페이지만. 수신자 추적 파라미터가 "
        "붙은 링크는 파라미터를 제거하거나 제외할 것\n\n"
        f"보낸사람: {sender}\n제목: {subject}\n본문:\n{html_to_text(body_html)}"
    )
    response = client.messages.parse(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        output_format=MailParseResult,
    )
    return response.parsed_output


def main():
    client = anthropic.Anthropic(api_key=load_api_key())
    raw = db.connect_raw()
    conn = db.connect()
    rows = raw.execute(
        "SELECT id, received_at, sender, subject, body_html FROM emails_raw WHERE processed=0"
    ).fetchall()
    print(f"미처리 메일 {len(rows)}건")
    n_deals = 0
    for row_id, received, sender, subject, body in rows:
        if not PROMO_SUBJECT.search(subject or ""):
            print(f"  건너뜀(특가 신호 없음): {subject[:50]}")
            raw.execute("UPDATE emails_raw SET processed=1 WHERE id=?", (row_id,))
            raw.commit()
            continue
        try:
            result = parse_one(client, sender, subject, body or "")
        except anthropic.APIStatusError as e:
            print(f"  파싱 실패({subject[:40]}): {e.status_code} {e.message}")
            continue
        if result and result.is_deal:
            for d in result.deals[:10]:
                conn.execute(
                    """INSERT OR IGNORE INTO mail_deals
                       (received_at, airline, origin, destination, price_krw,
                        promo_end, summary, url)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (received, result.airline, d.origin, d.destination,
                     d.price_krw, d.promo_end, d.summary, result.official_url))
                n_deals += 1
            print(f"  특가 {len(result.deals)}건: {subject[:50]}")
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
