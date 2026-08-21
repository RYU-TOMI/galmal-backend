# 갈래말래 — 3세션 협업 규칙

이 저장소는 **3개의 Claude 세션**이 나눠 작업한다. 이 파일은 모든 세션이 자동으로 읽는다.

## 먼저 읽을 것
| 문서 | 내용 |
|---|---|
| `PROJECT.md` | 상태·로드맵·작업 규칙·운영 정보 (**전체 지도**) |
| `PRODUCT.md` | 제품 본질(대상·목적·포지셔닝) |
| `DESIGN.md` | 디자인 시스템 + 발견 인터랙션·LOD·가격 정책 (**확정 스펙**) |
| `CONTRACT.md` | **프론트↔백엔드 데이터 계약**(deals.json 스키마) |
| `DECISIONS.md` | **왜 그렇게 정했나 + 기각된 대안** — 이미 폐기된 길을 다시 파기 전에 확인 |

## 세션 3개와 담당 구역

**⚠️ 자기 구역 파일만 수정한다.** 남의 구역이 필요하면 코드를 고치지 말고, 사용자에게 "○○ 세션에 전달해달라"고 요청한다.

### 1) 기획 (plan)
- **소유**: `PRODUCT.md` `DESIGN.md` `PROJECT.md` `CONTRACT.md` `DECISIONS.md` `design/`(목업·스토리보드)
- **역할**: 제품 방향·UX·디자인 확정, 목업 제작, 결정을 문서에 기록. 스키마 변경 중재.
- **결정을 내리면** `DESIGN.md`(무엇을)와 `DECISIONS.md`(왜·무엇을 버렸나) **둘 다** 갱신한다.
- **산출**: 문서 + `design/*.html` 목업. **앱 코드는 건드리지 않는다.**

### 2) 프론트 (frontend) — deals.json **소비자**
- **소유**: `docs/assets/discover.js` · `docs/assets/discover.css` · `collector/discover_home.py`(HTML 셸 템플릿) · `docs/assets/`의 벤더 라이브러리
- **역할**: 지도·카드 피드·필터 도크·확장 상세·반응형·인터랙션.
- **개발 방식**: 커밋된 `docs/data/deals.json`을 **픽스처**로 사용 → 백엔드를 기다리지 않는다.
- **금지**: `collector/`의 데이터 로직(`discover_data.py`, `affiliates.py`, `dests.py`, 수집기), `build_site.py`.

### 3) 백엔드 (backend) — deals.json **생산자**
- **소유**: `collector/*.py` 전부(단 `discover_home.py` 제외) · `build_site.py` · `.github/workflows/` · `data/`
- **역할**: 수집(가격·광역·메일)·특가 판정·`deals.json` 생성·예약/비교 링크·크론·SEO 페이지.
- **금지**: `docs/assets/discover.js|css`, `discover_home.py`.

### 공용 (누구든, 단 조심)
`README.md`, `.gitignore`, 이 파일 — 바꾸기 전 사용자에게 알린다.

## git 규칙 (worktree)
- 브랜치: `plan` / `frontend` / `backend`, 통합은 `main`.
- **작업 시작 전** `git fetch && git merge origin/main` (또는 `git pull`)로 main을 당긴다.
- **작게 자주 커밋**하고, 화면/기능 단위가 끝나면 **main에 병합**한다. 브랜치를 오래 끌지 않는다.
- `main`에는 **크론(github-actions)이 매일 `data/`·`docs/`를 커밋**한다 → push 전 반드시 pull.
  - 충돌 시: 생성물(`docs/index.html`, `docs/data/deals.json`, `docs/routes/`, `data/prices.db`)은 **재빌드로 해결**한다.
    `git checkout --theirs data/prices.db` → `python collector/build_site.py` → `git add -A && git commit`
- 커밋 메시지는 한국어로 무엇을 왜 바꿨는지. `Co-Authored-By: Claude` 라인 포함.

## 계약 변경 절차 (프론트↔백 소통의 핵심)
1. `deals.json` 스키마를 바꿔야 하면 → **`CONTRACT.md`를 먼저 갱신·커밋**한다.
2. 사용자에게 "계약 바뀜, 반대편 세션에 알려달라"고 말한다.
3. 필드 **추가**는 안전(프론트가 무시). **삭제·개명·의미 변경**은 양쪽 합의 후에만.

## 기술 스택 (고정 — 바꾸지 말 것)
- Python 정적 생성 + **순수 JS**(프레임워크 없음) + 지도만 `d3-geo`(벤더링, `docs/assets/`).
- **Node/npm 빌드 도입 금지.** 런타임 CDN 의존 0(폰트 제외).
- 빌드 진입점은 **`python collector/build_site.py` 하나**. 크론도 이것만 호출한다.
- 호스팅 GitHub Pages(`docs/`), 비용 $0 유지.

## 로컬 확인
- `python collector/build_site.py` 로 재생성 후 `docs/index.html` 확인.
- `fetch()`는 `file://`에서 막히지만 **deals.json·world.geojson은 HTML에 인라인**되므로 파일 열기로도 동작한다.
- 폰/실서버 확인: `python -m http.server 8000 --bind 0.0.0.0 --directory docs`

## 법적·보안 (전 세션 공통)
- 타 비교사이트 **DB 크롤링 금지**(링크 연결은 무방). 항공사 공지·공식 API·제휴만.
- 제휴 링크에 **"(광고)"·수수료 고지** 필수. 가격엔 "조회 시점 기준" 문구.
- **PII·시크릿 커밋 금지**: `.env`, 구독자 이메일 원본, 메일 본문 DB는 저장소에 올리지 않는다.
