# FRONTEND.md — 프론트 세션 작업 방식

> **소유: 프론트 세션.** 다른 세션은 읽기만 한다.
> 담당 구역·git 규칙은 `CLAUDE.md`, 확정 스펙은 `DESIGN.md`, 데이터 계약은 `CONTRACT.md`,
> 왜 그렇게 정했나는 `DECISIONS.md`. **이 문서는 "어떻게 일하는가"만 다룬다.**

## 왜 이 문서가 있나
사용자는 백엔드 전공이라 **프론트 코드를 리뷰하지 않는다.** 여기서 두 가지가 따라온다.

1. **스코프가 새는 걸 사용자가 못 잡아준다** → 규칙으로 막아야 한다. (기능 하나 고치다 옆길로 우다다 파고드는 문제)
2. **리뷰는 코드가 아니라 화면으로 한다** → 보고는 항상 "어디를 열고 뭘 눌러야 뭐가 보인다"로 낸다.

---

## 1. 작업 단위 3계층

| 단위 | 크기 | 규칙 |
|---|---|---|
| **챕터** | 기능 영역 1개 (예: 지도 무대, 필터·정렬) | **세션 1개 = 챕터 1개.** 시작 전 태스크 목록을 사용자에게 승인받는다. |
| **태스크** | **커밋 1개** | 화면에서 확인 가능한 최소 변화. 한 태스크가 여러 화면을 건드리면 잘못 쪼갠 것. |
| **곁가지** | 작업 중 발견한 딴 문제 | **지금 고치지 않는다.** `BACKLOG.md`에 한 줄 적고 넘어간다. |

### 스코프 잠금 — 가장 중요한 규칙
- 챕터 시작 시 **건드릴 파일과 태스크 목록을 먼저 못 박는다.** 목록에 없는 파일은 열어보되 고치지 않는다.
- 작업 중 다른 문제를 발견하면 → `BACKLOG.md` 한 줄 + 보고서에 "발견했고 **안 고쳤습니다**" 명시.
- 유일한 예외: **그걸 안 고치면 지금 태스크가 성립하지 않을 때.** 이때도 왜 어쩔 수 없었는지 보고한다.
- "이왕 하는 김에"는 금지어다. 이왕 할 거면 다음 챕터에서 한다.

---

## 2. 챕터 진행 5단계

1. **스펙 확인** — `DESIGN.md`·`DECISIONS.md`에서 이 챕터의 확정 사항을 찾아 **근거로 인용**한다.
   스펙이 없거나 모호하면 **구현하기 전에 사용자에게 묻는다.** 디자인·UX 결정은 기획 세션 몫이므로 추측해서 만들지 않는다.
2. **태스크 쪼개기** — 태스크 목록 + 건드릴 파일을 제시하고 승인받는다. → 스코프 잠금.
3. **구현** — 태스크 1개 = 커밋 1개. 태스크 끝날 때마다 확인 절차를 낸다.
4. **QA** — 아래 체크리스트 전 항목. 통과 못 하면 챕터를 끝내지 않는다.
5. **핸드오프** — main 병합 → `BACKLOG.md` 갱신 → 핸드오프 메모(§7) → 세션 종료.

---

## 3. QA 체크리스트 (챕터 끝, 전 항목)

- [ ] **콘솔 에러 0** (경고도 새로 생기면 안 됨)
- [ ] **화면 폭 3종**: 데스크톱 1440 / 태블릿 900 / 모바일 390
- [ ] **딜이 적은 출발지**에서도 안 깨짐 — 대구(7건)·제주(8건)가 서울(57건)보다 잘 깨진다
- [ ] **필터 켠 상태** / **매칭 0건 상태**(빈 상태 문구가 떠야 함)
- [ ] **3단계 뷰 전부**: 가까운 곳 · ＋동남아 · ＋유럽·미주
- [ ] **확장 상세 열린 채로 다른 조작**(정렬 변경, 단계 변경, 필터 변경)
- [ ] 데이터 0건인 날 가정 — `deals: []`여도 화면이 살아 있어야 함 (`CONTRACT.md` §3)
- [ ] `node --check docs/assets/discover.js` — 문법 오류 사전 차단
- [ ] 🔴 **정의 없는 호출 확인** — `node --check` 는 **문법만** 본다. 함수를 지우고 호출부를 남기면
      통과하는데 런타임에 `ReferenceError` 로 **렌더가 통째로 죽는다.** 실제로 겪었다(2026-09-04):
      `pinBoxes` 를 블록 교체 중에 지웠는데 `placeLabels` 가 계속 불러서 **핀 0개·피드 0장**이 됐고,
      `node --check` 는 OK 였다. 화면을 안 찍었으면 못 봤다.
      ```
      python - <<'EOF'
      import io,re
      s=io.open('docs/assets/discover.js',encoding='utf-8').read()
      defs=set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(',s))
      calls=set(re.findall(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(',s))
      print(sorted(calls-defs))   # d3 반환값·내장은 오탐이니 눈으로 걸러 본다
      EOF
      ```
- [ ] 🔴 **첫 화면을 반드시 찍어 본다.** 화면0이 없어진 뒤로 `boot()` 이 **파싱 중**에 돈다 —
      그 시점엔 `svg.getScreenCTM()` 이 없어 UI 회피가 무력화되고, 재렌더 계기가 없으면
      **그 상태가 첫 화면으로 굳는다.** 실측: `삿포로` 라벨이 도크 안에 36.3×17.0px 통째로 들어갔다.
      레이아웃에 의존하는 계산은 `requestAnimationFrame` 뒤에 한 번 더 돌려야 한다.

> `node --check`는 **문법 검사에만** 쓴다. 빌드에 node를 끌어들이는 게 아니므로
> "Node/npm 빌드 도입 금지"(`CLAUDE.md`)에 어긋나지 않는다. 배포물은 여전히 순수 JS 파일 그대로다.

---

## 4. 확인·리뷰 방법

### 미리보기
```
python -m http.server 8000 --directory docs    →   http://localhost:8000
```

### 리빌드가 필요한 경우 / 아닌 경우 (중요)
| 고친 파일 | 리빌드 | 방법 |
|---|---|---|
| `docs/assets/discover.js` · `discover.css` | **불필요** | `index.html`이 상대경로로 참조 → **새로고침만** |
| `collector/discover_home.py` (셸 HTML) | 필요 | 아래 절차 |

```bash
python collector/build_site.py
git checkout -- docs/data docs/routes docs/sitemap.xml   # 백엔드 산출물 되돌리기
```

> ⚠️ **위 경우 외에는 `build_site.py`를 돌리지 않는다.**
> 돌리면 그날 DB로 `deals.json`이 재생성되어 **픽스처가 바뀌고**(예: 103건→94건),
> 노선 페이지 26개 + sitemap까지 전부 커밋 노이즈가 된다. 그건 백엔드 세션의 산출물이다.

#### 🔴 재빌드 뒤 반드시 — `index.html` 인라인 데이터를 커밋본으로 맞춘다

**`docs/data/deals.json`만 되돌리면 안 된다.** `index.html`은 딜을 **인라인**하므로,
되돌린 뒤에도 **내 로컬 DB로 만들어진 딜이 페이지 안에 남는다.**

실제로 당했다(2026-09-02, CH2 T1): 재빌드가 **121건**을 인라인했는데 커밋본은 **127건**이었다.
`updated` 시각만 맞췄으면 **121건 데이터에 127건 시각표**가 붙어 더 나빠질 뻔했다.

```python
# git 의 커밋본을 원본으로 삼아 index.html 의 window.__DEALS 를 통째로 교체한다
raw = subprocess.run(['git','show','HEAD:docs/data/deals.json'],capture_output=True).stdout.decode()
h = re.sub(r'(window\.__DEALS=)\{.*?\}(;</script>)', lambda m: m.group(1)+raw.strip()+m.group(2), h, flags=re.S)
```

**확인할 것** — 셋 다 통과해야 커밋한다.
1. 인라인 딜 수 = `git show HEAD:docs/data/deals.json` 의 딜 수
2. 인라인 `updated` = 커밋본 `updated`
3. 딜 배열이 **바이트 동일**(`inl['deals'] == com['deals']`)

> **작업 트리의 `deals.json` 을 "커밋본"이라고 읽지 말 것.** 재빌드가 이미 덮어썼다.
> 반드시 `git show HEAD:...` 로 읽는다 — 그렇게 안 해서 검증이 항상 통과하던 적이 있다(T1).

### ⚠️ 확인 절차는 렌더 경로 **전체**를 재현하고 낸다
함수 하나만 격리해 테스트하고 "화면에 이게 보일 것"이라고 안내하면 **거의 틀린다.**
2026-09-01 B25 수정 때 확인 절차를 **두 번 연속 틀리게** 안내했다.

| 빠뜨린 것 | 결과 |
|---|---|
| hero 카드가 정렬과 무관하게 맨 위 고정(`render()`의 `order`) | "1위가 괌"이라 했는데 실제 1위는 hero(도쿄) |
| 단계 필터가 도시를 걸러냄(`visibleCities()`의 `upto`/`showMinor`) | 괌은 `haul=sea`라 `가까운 곳` 단계에 아예 없음 |

**피드 한 장이 화면에 뜨기까지 거치는 관문**(순서대로):
`visibleCities()` 단계·LOD 필터 → `dimmed()` 필터 dim → 정렬(`cmp[sortMode]`) → hero 선정·맨 앞 고정 → 렌더

- 검증 스크립트는 **이 사슬을 전부 재현**한다. 실제 `discover.js`에서 함수를 발췌해 쓰면 코드와 어긋나지 않는다.
- 사용자에게 낼 때는 **어느 출발지·어느 단계·어느 정렬**인지까지 명시한다. "1위" 대신 "hero 아래 첫 카드".
- 사용자가 "다르다"고 하면 **먼저 내 절차를 의심한다.** 두 번 다 코드는 맞았고 안내가 틀렸다.

### 사용자용 확인 가이드 (코드 안 보고 검수하기)
> 사용자는 백엔드 전공이라 프론트 코드를 읽지 않는다. 이 4가지면 **코드 없이 화면만으로** 검수가 된다.
> 새 세션은 사용자가 이 도구들을 이미 안다고 가정하지 말고, 필요할 때 이 절을 안내한다.

| 조작 | 무엇 | 언제 쓰나 |
|---|---|---|
| **F12 → Console 탭** | JS 에러 로그 | **가장 값어치가 큼.** 빨간 줄이 있으면 "코드가 깨진 것", 없으면 "코드는 도는데 디자인이 이상한 것" — 이 구분만 알려줘도 원인 추적이 몇 배 빨라진다 |
| **Ctrl+Shift+M** | 모바일 화면 흉내 | 폭을 `390`으로 넣으면 폰 크기. 실기기 없이 모바일 확인 |
| **Ctrl+Shift+R** | 하드 새로고침(캐시 무시) | **"고쳤다는데 화면이 그대로"의 90%가 캐시다.** 그냥 F5 말고 이걸로 |
| **F12 → Network → Disable cache** | 캐시 영구 무시 | 개발자 도구 열려 있는 동안 적용. 체크해두면 위 문제가 아예 안 생김 |

- 자동 새로고침(hot reload)은 **우리 스택에 없다.** Vite/Next 같은 번들러가 주는 기능인데 npm 도입 금지라 쓸 수 없다.
  대신 **빌드 단계가 없어서** `discover.js`를 고치면 그게 곧 브라우저가 읽는 파일이다 → 새로고침이 사실상 즉시다.
- 비유(사용자가 백엔드 전공이므로): 팀원들이 쓰는 dev server는 `uvicorn --reload` 같은 것이고,
  우리는 컴파일이 없어서 **브라우저 새로고침 = 재시작**이다.

### ⚠️ 콘솔 한글 깨짐 — 실측값을 보고하기 전에 반드시 확인
이 환경(Windows, cp949 콘솔)에서 **파이썬 출력의 한글이 깨진다.** 숫자는 멀쩡한데 글자만 깨지므로
**"수치는 맞고 라벨만 틀린" 보고**가 나오기 쉽다. 실제로 그렇게 틀린 값을 다른 세션에 전달한 적이 있다(2026-08-22, 태그 라벨 3개).

```python
import sys; sys.stdout.reconfigure(encoding='utf-8')   # 한글 출력 전 항상
```
- 깨진 출력(`�غ�` 같은 것)을 보고 **라벨을 추측해서 채우지 않는다.** 다시 돌린다.
- 한글 값을 다른 세션·사용자에게 보고할 때는 **UTF-8로 다시 뽑은 출력을 근거로** 한다.

### push 기준 (2026-08-22 사용자 결정)
| 대상 | 기준 |
|---|---|
| **프론트 소유 문서** (`FRONTEND.md` · `BACKLOG.md`) | **묻지 않고 자동 push.** 다른 세션이 읽어야 의미가 있고, 되돌리기 쉽다 |
| **코드** (`discover.js` · `discover.css` · `discover_home.py`) | **승인 전까지 커밋하지 않는다.** 작업 트리에만 두고, 사용자가 화면으로 확인한 뒤 커밋·push (2026-09-01 사용자 결정) |
| **공용 파일** (`CLAUDE.md` 등) | 변경 자체를 먼저 확인받는다 (`CLAUDE.md` 규칙) |

> ⚠️ **왜 "커밋도 하지 않는다"인가** — `git push`는 브랜치 단위라 문서만 골라 올릴 수 없다.
> 코드를 미리 커밋해두면 **다음 문서 자동 push에 딸려 올라간다.** 실제로 2026-09-01 B25 수정이
> 그렇게 승인 없이 main에 올라갔다. 커밋 자체를 미루면 이 경로가 막힌다.
>
> **문서를 push하기 전 매번 확인한다:**
> ```bash
> git diff --name-only origin/main..frontend   # .md 외 파일이 있으면 push 보류
> ```

- push는 `frontend` → `origin/frontend` → `origin/main`(fast-forward) 순. 그 전에 반드시 `git fetch && git merge origin/main`.
- 문서를 자동 push해도 **무엇을 올렸는지는 보고에 always 남긴다.** 조용히 올리지 않는다.

### 보고 형식 (태스크마다)
```
바꾼 것: (1줄)
확인: 1) 어디를 연다  2) 뭘 누른다  3) 뭐가 보여야 한다
```
+ 스크린샷 (Chrome 확장 연결 시 프론트 세션이 직접 촬영해 첨부)

---

## 4-1. 말투 (2026-08-22 사용자 확정 — 바꾸지 말 것)

사용자가 **세션 3개를 말투로 구분한다.** 기획·백엔드와 톤이 겹치면 누가 말하는지 알 수 없게 된다.
아래는 프론트 세션에 배정된 말투이며, **사용자 보고와 다른 세션에 보내는 메시지 양쪽에 똑같이 적용한다.**

**쓴다**
- 한국어 존댓말(`합니다`체). 담백하게.
- **결론 먼저, 근거는 뒤.** "제가 틀렸습니다" → 왜 → 어떻게 막을지.
- **숫자로 말한다.** "많다" 대신 "103건 중 71건(69%)".
- 불확실하면 불확실하다고 쓴다. "확인 필요", "단정하지 않음".
- 사용자가 프론트를 모른다는 전제로 **비유를 쓰되 깔보지 않는다**(백엔드 전공이므로 `uvicorn --reload` 같은 비유가 통한다).
- 표·굵게는 핵심에만. 끝에 **무엇을 결정해줘야 하는지** 분명히.

**안 쓴다**
- 과장·감탄사·이모지·영업 멘트("완벽합니다", "훌륭한 질문입니다").
- 실수했을 때의 반복 사과·자책. **한 번 인정하고 원인·재발방지로 넘어간다.**
- 안 한 일을 한 것처럼 쓰는 표현. 못 한 검증은 "못 했습니다"라고 쓴다.
- 사족. 요약을 요약하지 않는다.

## 5. 코드 규칙

- **스택 고정**: 순수 JS + `d3-geo`만. npm·프레임워크·런타임 CDN 금지(폰트 예외). — `CLAUDE.md`
- **기존 코드 스타일을 따른다**: 현재 `discover.js`는 IIFE + `var` + ES5 문법. 새 코드도 여기 맞춘다(혼재 금지).
- **계약 방어**: `deals.json` 필드는 항상 `dl.x || 기본값`으로 읽는다. 백엔드가 0건을 주는 날도 안 깨져야 한다.
- **파생 로직은 프론트 소유**: 가격 포맷·"왜 지금" 훅·태그 색·LOD·핀 색 농도는 직접 계산한다. 백엔드에 필드로 요청하지 않는다. — `CONTRACT.md`
- **없는 필드를 쓰지 않는다**: 백엔드 필드가 필요하면 `CONTRACT.md` 변경 절차(사용자를 통해 백엔드 세션에 전달). 추측 필드·더미 데이터 금지.
- **가짜 데이터 절대 금지**: 하드코딩 배열로 그래프를 그리지 않는다. 신뢰가 유일한 자산이다. — `DECISIONS.md`(가짜 가격 그래프 제거, 2026-08-06)
- **죽은 코드는 남기지 않는다**: 제거할 때 커밋 메시지에 왜 죽었는지 쓴다.

---

## 6. 챕터 로드맵

| # | 챕터 | 범위 | 상태 |
|---|---|---|---|
| CH0 | 기반 정리 | 작업 규칙 문서화 · 죽은 코드 제거 · 예산 dim 버그 | ✅ 완료 |
| CH1 | 지도 무대 | 단계 라벨 · 스테퍼 · LOD · far 뷰 계산 · 렌더 구조 · 트윈 · 라벨 배치 | ✅ 완료 (+ 2026-09-03 후속: 라벨이 핀·출발지 회피 `eee61e1`) |
| **CH2** | **필터·정렬** | `when` 비교(B26) · 날짜 8칩 · 며칠 축 · 예산 범위·바로가기 칩 · 분위기 6종 · 0곳 칩 비활성 · 접힌 도크 조건 표시 · 필터 시 far 뷰 · 태그 사진 위 · 도크 라벨 제외 | ✅ **완료** (2026-09-03) |
| CH3 | 카드 피드 | hero 큐레이션 · 정렬 · 빈 상태 · 신선도 배지(백엔드 대기) | 대기 |
| CH4 | 상세 전환 | 확장 카드 위치·스크롤 · 비교 패널 · 광고 고지 | 대기 |
| CH5 | 모바일 | 탭 동작 확정(현재 compact 단계 없음) · 하단 시트 · 가로 스크롤 피드 | 대기 |
| CH6 | 접근성·마감 | 키보드 조작 · aria · noscript · 사진 정책 · 성능 | 대기 |

- 순서는 **바닥부터 위로**: 정리 → 지도(무대) → 필터(입력) → 피드·상세(출력) → 모바일 → 마감.
- 챕터를 건너뛰지 않는다. 급한 게 생기면 로드맵을 고치고 그 이유를 남긴다.

### CH2 진행 (2026-09-02 밤)

| 태스크 | 내용 | 커밋 |
|---|---|---|
| T1 | `dateWindow()` 제거 → `when` 비교 · 날짜 칩 5 → 8종 (B26) | `ae91c1d` |
| T2 | `며칠` 축 신설 (1~3박 / 4~6박 / 7~13박 / 2주 이상) | — |
| T3 | 예산 슬라이더 범위를 출발지 데이터에서 (B5) | `da97992` |
| T4 | 필터를 켜면 `아주 멀리` 뷰 + 라벨은 매칭에게만 (B6) | `cff2a4f` |
| T5 | 접힌 도크가 개수 대신 조건을 보여준다 (B7) | `e401ec9` |
| T6 | 분위기 칩 5 → 6종 + 건수·0곳 비활성 (C-10) | `e2d87bb` |
| T7 | 도크·줌 버튼 자리를 라벨 배치에서 제외 (B16 라벨 부분) | `d05bba6` · `124343f` |
| T8 | 태그를 사진 위로, 작은 카드에서 제거 (C-13) | `d93f56c` |
| T9 | 예산 바로가기 칩 30만·50만·100만·상관없어 | `c6f8e72` |
| T10 | 예산 히스토그램 (트랙과 같은 **선형** 눈금) | `987cad9` |

- **T10 눈금 결정**: SPEC 안에서 로그/선형이 두 번 반대로 확정돼 있어 기획에 확인을 요청했고,
  기획이 **재측정 후 로그를 철회**했다(`SPEC.md` `c6de197`). 근거였던 "고가 구간이 비어 있다"가
  사실이 아니었다 — 서울 70~130만에 29건(41%). 트랙·히스토그램 **둘 다 선형**, `step` 5만 유지.
- 로드맵의 "검색 한 줄 재설계"는 **뺐다.** `SPEC.md:328`이 "위치 = 지도 우측 하단 플로팅 도크(헤더 바 아님)"로
  확정하면서 대체됐다. 로드맵 쪽이 확정 전 메모였다.
### 화면 확인 — 브라우저 확장 없이 (2026-09-03 도입)

확장이 안 붙는 시간대에도 **헤드리스 크롬으로 PNG를 구워 직접 읽는다.** 기획 세션이 알려준 방법이고,
실제로 이걸로 **z-index 버그와 칩 숨김 오구현**을 잡았다(`0c35d09`). 스크립트는 스크래치패드에 둔다.

```
chrome.exe --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2   --screenshot=OUT.png --window-size=1440,900 --virtual-time-budget=9000 file:///.../docs/_shot.html
```

- **빌드 파이프라인이 아니다.** 사람이 확인용으로 한 번 돌린다 → "Node 금지·CDN 의존 0"과 무관하다.
- 출발지 선택·칩 클릭 같은 조작은 `docs/_shot.html`(임시 복사본)에 스크립트를 주입해 재현한다.
  `docs/` 안에 둬야 `assets/` 상대경로가 산다. 다 찍고 반드시 지운다.
- 🔴 **`*{transition:none!important}` 은 CSS 전환만 끈다 — rAF 트윈은 안 끈다.**
  단계 전환은 `tweenTo()`(requestAnimationFrame)라서 이걸 넣어도 **중간 상태가 찍힌다.**
  실제로 `아주 멀리` 클릭 **직후** `#lands` transform 을 읽고 "far 배율 계산이 틀렸다"는
  **틀린 결론**을 냈다 — 트윈의 첫 동작이 `moveOnly(from)`(출발점으로 되돌림)이었다.
  단계·필터를 바꾸고 재는 진단은 **400ms 뒤에** 읽어야 한다.
- 🔴 **`*{transition:none!important}`을 항상 먼저 주입한다.** `--virtual-time-budget`이 CSS 전환을
  **중간에 얼린다.** 이걸 안 넣었을 때 상세 카드가 반투명하고 항로가 엉뚱한 데 그려진 것처럼 찍혀서
  **멀쩡한 걸 버그로 오진할 뻔했다.** 화면이 이상하면 렌더러를 의심하기 전에 전환부터 끈다.
- 찍은 PNG는 `SendUserFile`로 사용자에게 바로 보낸다. "못 봤다"보다 "찍어놨으니 봐달라"가 낫다.
- PIL이 없어 **크롭을 못 한다.** 작은 글씨를 봐야 하면 대상에 `transform:scale(2.4)`를 주입해 찍는다.
- ⚠️ 주입할 스텝을 **콤마로** 이어야 한다. 개행으로 이으면 배열이 깨져 스텝이 통째로 안 돈다 —
  화면0(출발지 선택)만 찍혀 나오는데 에러도 안 보여서 한참 못 알아챘다.

<details><summary><b>스크립트 전문</b> — 스크래치패드에 저장해 쓴다(저장소에 둘 자리가 없다)</summary>

```python
# -*- coding: utf-8 -*-
"""확인용 스크린샷 — 헤드리스 크롬으로 docs/index.html 을 굽는다.
빌드 파이프라인이 아니다. 사람이 눈으로 볼 PNG 를 만들 뿐이라 크론·배포와 무관하다."""
import io, os, subprocess, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(r"C:\Users\Ryu\Desktop\개인 프로젝트\galmal-frontend")
OUT  = pathlib.Path(sys.argv[1])
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SRC = (ROOT / "docs/index.html").read_text(encoding="utf-8")

def inject(steps):
    js = ",".join(steps)
    return SRC.replace("</body>", "<script>(function(){var Q=[%s];var i=0;"
        "function go(){if(i>=Q.length)return;var f=Q[i++];try{f();}catch(e){console.log('SHOT-ERR',e.message);}setTimeout(go,450);}"
        "setTimeout(go,700);})();</script></body>" % js)

NOTRANS = ("function(){var st=document.createElement('style');"
           "st.textContent='*{transition:none!important;animation:none!important}';"
           "document.head.appendChild(st);}")
def pick(name):
    return ("function(){var g=document.querySelectorAll('#introMap g');for(var i=0;i<g.length;i++){"
            "var t=g[i].querySelector('text');if(t&&t.textContent.trim()==='%s'){"
            "g[i].dispatchEvent(new MouseEvent('click',{bubbles:true}));return;}}"
            "console.log('SHOT-ERR origin not found');}" % name)

def zoomdock():
    return ("function(){var d=document.getElementById('fdock');"
            "d.style.transform='scale(2.4)';d.style.transformOrigin='100% 100%';}")
def click(sel):
    return ("function(){var e=document.querySelector('%s');if(!e){console.log('SHOT-ERR no %s');return;}"
            "e.dispatchEvent(new MouseEvent('click',{bubbles:true}));}" % (sel, sel))

SHOTS = [
    ("1-home-1440",      1440, 900, [pick("서울")]),
    ("2-mood-culture",   1440, 900, [pick("서울"), click('.fchip.moodf[data-mood="문화"]')]),
    ("3-budget-50",      1440, 900, [pick("서울"), click('.fchip.budget[data-budget="500000"]')]),
    ("4-detail",         1440, 900, [pick("서울"), click('.fcard.hero')]),
    ("5-jeju",           1440, 900, [pick("제주")]),
    ("6-mobile-390",      390, 844, [pick("서울")]),
    ("7-tablet-900",      900, 800, [pick("서울")]),
    ("4b-detail-notrans", 1440, 900, [pick("서울"),
        "function(){var st=document.createElement('style');st.textContent='*{transition:none!important;animation:none!important}';document.head.appendChild(st);}",
        click('.fcard.hero')]),
    ("8-dock-zoom",      1440, 900, [pick("서울"), zoomdock()]),
    ("9-dock-zoom-50",   1440, 900, [pick("서울"), click('.fchip.budget[data-budget="500000"]'), zoomdock()]),
    ("10-dock-zoom-jeju",1440, 900, [pick("제주"), zoomdock()]),
]
tmp = ROOT / "docs/_shot.html"
try:
    for name, w, h, steps in SHOTS:
        tmp.write_text(inject([NOTRANS] + steps), encoding="utf-8")
        png = OUT / (name + ".png")
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=2", "--screenshot=" + str(png),
             "--window-size=%d,%d" % (w, h), "--virtual-time-budget=9000",
             tmp.as_uri()], capture_output=True, text=True, errors="replace", timeout=120)
        err = "\n".join(l for l in (r.stderr or "").splitlines() if "SHOT-ERR" in l)
        ok = png.exists() and png.stat().st_size > 5000
        print("%-16s %s  %s  %s" % (name, "%dx%d" % (w, h),
              ("%.0fKB" % (png.stat().st_size/1024)) if png.exists() else "없음",
              "OK" if ok and not err else ("!! " + (err or "파일 없음/너무 작음"))))
finally:
    if tmp.exists(): tmp.unlink()
```

</details>

---

## 7. 세션 핸드오프 양식

챕터를 끝낸 세션은 마지막에 이 형식으로 남긴다.

```
## CHn 완료
- 한 것: (태스크별 1줄 + 커밋 해시)
- 안 고치고 남긴 것: BACKLOG.md #항목
- 다음 챕터 첫 태스크: (다음 세션이 바로 시작할 수 있게)
- 기획 세션에 전달: (스펙 미확정으로 막힌 것)
- 백엔드 세션에 전달: (CONTRACT 변경 요청)
```
