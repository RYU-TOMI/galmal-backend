# promo-ticket-site

항공권 특가 정보를 자동 수집·판정하는 사이트 (프로토타입 단계).

## 구조

```
collector/
  config.py        # 수집 노선 목록, 특가 판정 기준
  fetch_prices.py  # Travelpayouts API에서 가격 수집 → data/prices.db
  detect_deals.py  # 가격 히스토리 중앙값 대비 급락 판정 → 특가 리포트
  mail_ingest.py   # 전용 메일함(IMAP)에서 항공사 프로모션 메일 수집
data/prices.db     # SQLite (git 제외)
.env               # TP_TOKEN, MAIL_ADDRESS, MAIL_APP_PASSWORD (git 제외)
```

## 실행

```powershell
python collector/fetch_prices.py   # 하루 1회 실행 (추후 GitHub Actions 크론)
python collector/detect_deals.py   # 특가 판정 리포트
python collector/mail_ingest.py    # 메일 계정 설정 후 사용
```

외부 라이브러리 불필요 (Python 표준 라이브러리만 사용).

## 특가 판정 로직

노선을 직항/경유로 나눠 각각 최근 30일 수집 가격의 중앙값을 시세로 보고,
같은 유형 시세의 65% 이하 가격을 특가로 판정. 데이터가 쌓일수록 기준선이 정확해짐.

## 자동 수집 (GitHub Actions)

`.github/workflows/collect.yml` — 매일 KST 07:10에 수집·판정 실행 후
`data/prices.db`와 `data/deals_latest.txt`를 저장소에 커밋해 히스토리를 축적.
저장소 Secrets에 `TP_TOKEN` 필요. Actions 탭에서 수동 실행(workflow_dispatch)도 가능.

## 주의

- Travelpayouts 캐시 데이터는 2~7일 지연될 수 있음 → 표시 시 "조회 시점 기준" 면책 필요
- 타 비교사이트(네이버/스카이스캐너 등) 크롤링 금지 (법적 리스크)
