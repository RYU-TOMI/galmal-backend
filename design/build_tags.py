# -*- coding: utf-8 -*-
"""TAGS.md 생성 — 목적지 태그 재배정안 (PH3b, C-13).

기획이 어휘와 배정을 정하고, 백엔드가 `collector/dests.py`에 반영한다.
이 스크립트는 배정을 들고 있으면서 **불변식을 검증**하고 표를 뽑는다.

    python design/build_tags.py
"""
import io
import pathlib
import re
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "TAGS.md"

TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {
    "리조트": "해변", "스노클링": "해변", "서핑": "해변", "섬": "해변",
    "야경": "도시", "쇼핑": "도시", "마천루": "도시", "골목": "도시",
    "야시장": "미식", "길거리음식": "미식",
    "화산": "자연", "트레킹": "자연", "사막": "자연", "폭포": "자연",
    "사원": "문화", "유적": "문화", "고성": "문화", "미술관": "문화",
}

# IATA: [태그...]  — 하위 태그는 반드시 그 상위를 함께 적는다(아래에서 검증)
A = {
    # 일본
    "NRT": ["야경", "미식", "도시", "쇼핑"], "HND": ["야경", "미식", "도시", "쇼핑"],
    "KIX": ["미식", "길거리음식", "도시", "쇼핑"], "ITM": ["미식", "길거리음식", "도시"],
    "FUK": ["길거리음식", "온천", "미식", "도시"],
    "OKA": ["해변", "리조트", "고성", "문화", "자연"],
    "CTS": ["자연", "미식", "온천", "도시"],
    "NGO": ["도시", "쇼핑", "문화", "고성"],
    "HIJ": ["문화", "유적", "미식"],
    "KOJ": ["온천", "자연", "화산"],
    "OIT": ["온천", "자연"],
    "TAK": ["미술관", "자연", "문화", "미식"],
    "KMJ": ["고성", "화산", "온천", "문화", "자연"],
    "MYJ": ["온천", "문화", "고성"],
    "KMQ": ["문화", "미술관", "자연"],
    # 중화권
    "TPE": ["야시장", "온천", "미식", "도시"], "KHH": ["야시장", "미식", "도시"],
    "HKG": ["야경", "골목", "도시", "쇼핑", "미식"],
    "MFM": ["야경", "유적", "도시", "문화"],
    "PVG": ["도시", "마천루", "야경", "쇼핑"], "SHA": ["도시", "마천루", "야경", "쇼핑"],
    "PEK": ["유적", "고성", "문화", "도시"],
    "TAO": ["해변", "미식", "도시"],
    "DLC": ["해변", "도시"],
    "CAN": ["미식", "도시", "쇼핑"],
    "XMN": ["해변", "섬", "문화"],
    "SZX": ["도시", "마천루", "쇼핑"],
    "HGH": ["자연", "문화", "사원"],
    "SYX": ["해변", "리조트"],
    # 국내
    "CJU": ["해변", "자연", "화산"],
    # 동남아
    "BKK": ["도시", "미식", "야시장", "문화", "사원"], "DMK": ["도시", "미식", "야시장", "문화", "사원"],
    "HKT": ["해변", "리조트", "야시장", "미식"],
    "CNX": ["문화", "사원", "자연", "미식", "야시장"],
    "DAD": ["리조트", "미식", "해변"],
    "HAN": ["미식", "길거리음식", "도시", "골목", "문화"],
    "SGN": ["도시", "미식", "길거리음식"],
    "PQC": ["해변", "리조트", "스노클링"],
    "CXR": ["온천", "해변", "리조트"],
    "MNL": ["유적", "쇼핑", "도시", "문화"],
    "CEB": ["스노클링", "리조트", "해변", "섬"],
    "SIN": ["도시", "마천루", "길거리음식", "미식", "쇼핑"],
    "KUL": ["도시", "마천루", "야시장", "미식", "쇼핑"],
    "DPS": ["해변", "서핑", "사원", "문화", "리조트"],
    "JKT": ["도시", "쇼핑"], "CGK": ["도시", "쇼핑"],
    "REP": ["문화", "유적", "사원"],
    "PNH": ["유적", "문화", "도시"],
    "VTE": ["문화", "사원", "자연"],
    "RGN": ["사원", "문화", "유적"],
    # 섬
    "MLE": ["해변", "섬", "리조트", "스노클링"],
    "HNL": ["해변", "서핑", "리조트", "자연", "화산"],
    "GUM": ["해변", "리조트", "도시", "쇼핑"],
    "SPN": ["스노클링", "유적", "해변", "문화", "리조트"],
    "ROR": ["섬", "스노클링", "해변"],
    # 오세아니아
    "SYD": ["도시", "야경", "해변", "서핑"],
    "MEL": ["골목", "미식", "문화", "도시"],
    "BNE": ["해변", "서핑", "자연"],
    "AKL": ["자연", "화산", "트레킹"],
    "NAN": ["해변", "리조트", "섬", "스노클링"],
    # 유럽
    "IST": ["사원", "골목", "유적", "문화", "도시", "미식"],
    "CDG": ["미술관", "미식", "문화", "도시"],
    "LHR": ["도시", "문화", "미술관"],
    "FCO": ["유적", "미식", "문화"],
    "BCN": ["골목", "해변", "도시", "문화"],
    "FRA": ["도시", "마천루"],
    "MUC": ["도시", "문화", "고성"],
    "AMS": ["골목", "미술관", "도시", "문화"],
    "ZRH": ["트레킹", "자연", "도시"],
    "VIE": ["문화", "미술관", "고성", "도시"],
    "PRG": ["문화", "고성", "도시", "골목"],
    "HEL": ["자연", "도시", "문화"],
    # 미주
    "JFK": ["도시", "마천루", "미술관", "문화", "쇼핑"], "EWR": ["도시", "마천루", "미술관", "문화", "쇼핑"],
    "LAX": ["도시", "해변", "서핑"],
    "SFO": ["골목", "자연", "도시", "미식"],
    "SEA": ["도시", "자연", "미식"],
    "YVR": ["트레킹", "해변", "자연", "도시"],
    "YYZ": ["도시", "마천루", "자연", "폭포"],
    # 기타
    "CMB": ["해변", "자연", "문화", "사원"],
    "DXB": ["도시", "사막", "마천루", "자연", "쇼핑"],
    "DOH": ["도시", "쇼핑", "자연", "사막"],
    "DEL": ["유적", "골목", "도시", "문화"],
    "KTM": ["자연", "트레킹", "문화", "사원"],
}

# ---- 현행 dests.py 읽기 (이름·국가·haul, 그리고 옛 태그) ----
src = (ROOT / "collector/dests.py").read_text(encoding="utf-8")
body = src[src.index("DEST = {"):]
CUR = {}
for code, ko, country, region, haul, tags in re.findall(
        r'"([A-Z]{3})"\s*:\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*\[([^\]]*)\]', body):
    CUR[code] = (ko, country, region, haul, re.findall(r'"([가-힣]+)"', tags))

# ---- 검증 ----
errs = []
for code, tags in A.items():
    if code not in CUR:
        errs.append(f"{code}: dests.py에 없는 코드")
        continue
    for t in tags:
        if t not in TOP and t not in SUB:
            errs.append(f"{code} {CUR[code][0]}: 어휘에 없는 태그 '{t}'")
    for t in tags:
        if t in SUB and SUB[t] not in tags:
            errs.append(f"{code} {CUR[code][0]}: 하위 '{t}'인데 상위 '{SUB[t]}'가 없다")
    if not any(t in TOP for t in tags):
        errs.append(f"{code} {CUR[code][0]}: 상위 태그가 하나도 없다")
missing = [c for c in CUR if c not in A]
if missing:
    errs.append("배정 누락: " + ", ".join(f"{c}({CUR[c][0]})" for c in missing))

if errs:
    print("검증 실패:")
    for e in errs:
        print("  -", e)
    raise SystemExit(1)

# ---- 통계 ----
cnt = Counter(t for tags in A.values() for t in tags)
old_cnt = Counter(t for c in A for t in CUR[c][4])


def card_tags(tags):
    """카드 표시: **하위 태그 우선, 최대 2개**. 하위끼리는 배정 목록 순서를 따른다.

    앞 2개를 그대로 쓰는 방식도 시도했으나 `도시`·`해변` 같은 상위가 앞에 와서
    고유 표시가 77% → 50%로 떨어졌다. 상위는 여러 도시가 공유하므로 구별에 쓸모가 없다.
    무엇을 앞세울지는 **하위끼리의 순서**로 통제한다.
    """
    subs = [t for t in tags if t in SUB]
    tops = [t for t in tags if t in TOP]
    return (subs + tops)[:2]


combo_new = Counter(tuple(card_tags(t)) for t in A.values())
combo_old = Counter(tuple([t for t in CUR[c][4] if t in TOP][:2]) for c in A)

by_region = defaultdict(list)
for code, tags in A.items():
    ko, country, region, haul, old = CUR[code]
    by_region[(region, haul)].append((code, ko, country, old, tags))

L = []
L.append("# TAGS.md — 목적지 태그 배정안 (기획 → 백엔드)")
L.append("")
L.append("> **소유: 기획 세션.** 어휘와 배정은 제품 목소리에 속하므로 기획이 정하고,")
L.append("> **백엔드가 `collector/dests.py`에 반영**한다. 어휘 정의는 `CONTRACT.md`가 계약으로 들고 있다.")
L.append("> 재생성·검증: `python design/build_tags.py` (불변식을 어기면 실패한다)")
L.append("")
L.append("## 왜 다시 배정하나")
L.append("")
L.append("어휘 12종으로 목적지 84곳을 구별할 수 없었다. 실측(C-13):")
L.append("")
L.append("- `해변` 하나만 붙은 도시 **10곳** — 괌·나디·**몰디브**·사이판·세부·**싼야**·팔라우·푸꾸옥·푸켓·호놀룰루")
L.append("- `도시` 하나만 붙은 도시 **8곳** — 나고야·**두바이**·상하이·선전·자카르타·쿠알라룸푸르·프랑크푸르트·도하")
L.append("- 태그 1개짜리가 **38%**")
L.append("")
L.append("**몰디브와 싼야가 같은 태그였고, 두바이와 나고야가 같은 태그였다.**")
L.append("표시 규칙만 바꿔서는 안 됐다 — 하위 태그 우선 표시를 시뮬레이션해도")
L.append("제주·다낭·오키나와·푸꾸옥·싼야가 전부 `휴양 · 해변`으로 똑같았다.")
L.append("")
L.append("## 어휘 — 상위 6종(필터) + 하위 18종(표시)")
L.append("")
L.append("**하위 태그는 반드시 자기 상위를 함께 단다.** 그래야 `야시장`을 보고 `미식` 필터를 눌렀을 때 잡힌다")
L.append("(`COPY.md`의 \"화면에 보이는 태그는 고를 수 있어야 한다\" 원칙). 이 스크립트가 매번 검증한다.")
L.append("")
L.append("| 상위 (필터) | 하위 (표시용) |")
L.append("|---|---|")
for t in TOP:
    subs = [s for s, p in SUB.items() if p == t]
    L.append(f"| **{t}** ({cnt[t]}곳) | " + (" · ".join(f"`{s}`({cnt[s]})" for s in subs) or "— (그 자체로 구체적)") + " |")
L.append("")
L.append("- **시즌 표현은 넣지 않았다** — `벚꽃`·`단풍`·`설경`은 계절을 타서 문구가 썩는다(`COPY.md` 보이스 규칙).")
L.append("- **`사찰` 대신 `사원`**을 쓴다. 이스탄불 모스크·델리 힌두사원까지 담아야 한다.")
L.append("- **표시 태그는 희소할수록 좋다.** 필터 어휘가 희소하면 빈 결과가 뜨지만(그래서 상위는 6종),")
L.append("  표시 태그는 드물수록 그 도시를 잘 구별한다 — `폭포`가 토론토 한 곳뿐인 건 결함이 아니라 목적이다.")
L.append("")
L.append("## 효과")
L.append("")
L.append(f"- 카드에 보이는 태그 조합: **{len(combo_old)}가지 → {len(combo_new)}가지**")
L.append(f"- 어휘 종수: **{len(old_cnt)}종 → {len(cnt)}종**")
L.append("")
L.append("| 예시 | 전 | 후 |")
L.append("|---|---|---|")
for code in ["MLE", "SYX", "DXB", "NGO", "CEB", "HKT", "YYZ", "KTM"]:
    ko = CUR[code][0]
    L.append(f"| {ko} | `{' · '.join([t for t in CUR[code][4] if t in TOP][:2])}` | **`{' · '.join(card_tags(A[code]))}`** |")
L.append("")
L.append("## 배정표 (84개)")
L.append("")
L.append("`카드`는 **하위 태그 우선 최대 2개**다. 하위끼리의 순서로 무엇을 앞세울지 정한다.")
L.append("")
REG = {"jp": "일본", "cn": "중화권", "sea": "동남아", "island": "섬", "oc": "오세아니아",
       "eu": "유럽", "am": "미주", "etc": "기타", "dom": "국내"}
for (region, haul) in sorted(by_region, key=lambda k: (k[1], k[0])):
    rows = sorted(by_region[(region, haul)], key=lambda r: r[1])
    L.append(f"### {REG.get(region, region)} · {haul} ({len(rows)})")
    L.append("")
    L.append("| IATA | 도시 | 전 | 후 (dests.py에 넣을 값) | 카드 |")
    L.append("|---|---|---|---|---|")
    for code, ko, country, old, tags in rows:
        L.append(f"| `{code}` | {ko} | {' · '.join(old)} | `{'`, `'.join(tags)}` | **{' · '.join(card_tags(tags))}** |")
    L.append("")

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"생성: {OUT}")
print(f"  검증 통과 · {len(A)}개 배정 · 어휘 {len(old_cnt)}종 → {len(cnt)}종")
print(f"  카드 조합 {len(combo_old)}가지 → {len(combo_new)}가지")
