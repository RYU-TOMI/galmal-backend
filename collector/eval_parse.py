# -*- coding: utf-8 -*-
"""메일 파싱 평가 (BE28) — 운영 모델이 항공사 메일을 제대로 읽는지 상위 모델과 견준다.

**로컬 전용. 크론에서 돌지 않는다.**
- 메일함을 **읽기 전용**으로 받는다. 허용 도메인·Gmail 인증 검사·구독 메일 제외는 `mail_ingest` 와 같다.
- 같은 메일을 `MODELS` 각각에 **운영과 같은 프롬프트**(`parse_mail.request`)로 태운다.
  운영의 제목 거름망(`PROMO_SUBJECT`)과 상관없이 **전부** 태운다 — 거름망이 놓친 특가도 센다.
- 🔴 결과는 `data/eval/` 에만 둔다(.gitignore). **메일 본문이 들어 있다** — 저장소에 올리지 않는다.
- 이어 돌리기: 받아 둔 메일·받아 둔 응답은 다시 부르지 않는다(오류난 것만 다시). `--refetch` 면 메일함을 다시 받는다.

사용: python -X utf8 collector/eval_parse.py           # 받기 + 부르기 + 보고
      python -X utf8 collector/eval_parse.py --report  # 부르지 않고 보고만 (받아 둔 메일이 없으면 받기는 한다)
"""
import concurrent.futures as cf
import email
import hashlib
import imaplib
import json
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mail_guard
import mail_ingest
import parse_mail

OUT = Path(__file__).resolve().parent.parent / "data" / "eval"
REF = "opus-5-5"
# 이름 → 요청 옵션. **운영 모델은 운영 값 그대로**(max_tokens 2048) — 운영을 재는 것이다.
# 생각하는 모델은 생각이 max_tokens 를 먹으므로 넉넉히 준다(잘리면 `stop` 에 남는다).
# 기준(REF)에는 거절 대비 `fallbacks` 를 달지 않는다 — 다른 모델이 조용히 대신 답하면 기준이 흐려진다. 거절은 거절로 남긴다.
MODELS = {
    "haiku-4-5": {"model": "claude-haiku-4-5"},
    "haiku-5-5": {"model": "claude-haiku-5-5", "max_tokens": 16000},
    REF: {"model": "claude-opus-5-5", "max_tokens": 16000, "output_config": {"effort": "high"}},
}
PRICE = {"haiku-4-5": (1.00, 5.00), "haiku-5-5": (0.10, 0.50), REF: (4.00, 20.00)}  # $/1M 토큰 (입력, 출력)
LIMIT = 12000   # parse_mail.html_to_text 의 기본 자르기 — 넘는 메일은 뒷부분을 어느 모델도 못 본다


def fetch_mails():
    addr, pw = mail_ingest.load_env()
    imap = imaplib.IMAP4_SSL(mail_ingest.IMAP_HOST)
    imap.login(addr, pw)
    imap.select("INBOX", readonly=True)          # 🔴 메일함을 바꾸지 않는다 (BB33)
    mails = []
    for mid in mail_ingest._candidates(imap, True):
        _, hdr = imap.fetch(mid, mail_ingest.HEADERS)
        head = email.message_from_bytes(hdr[0][1])
        if mail_guard.verdict(head.get("From"), head.get_all("Authentication-Results")) != mail_guard.OK:
            continue
        _, data = imap.fetch(mid, "(BODY.PEEK[])")
        msg = email.message_from_bytes(data[0][1])
        received = msg.get("Date", "")
        sender, subject = mail_ingest.decode(msg.get("From")), mail_ingest.decode(msg.get("Subject"))
        if "구독신청" in subject or "구독취소" in subject:     # PII — mail_ingest 와 같은 규칙
            continue
        mails.append({"id": hashlib.sha1(f"{received}|{sender}|{subject}".encode()).hexdigest()[:10],
                      "received": received, "sender": sender, "subject": subject,
                      "body": mail_ingest.html_body(msg)})
    imap.logout()
    return mails


def call(client, m, opts):
    try:
        r = parse_mail.request(client, m["sender"], m["subject"], m["body"], **opts)
    except (anthropic.APIError, ValueError) as e:     # ValueError: 잘리거나 거절된 응답의 스키마 검증 실패
        return {"error": f"{type(e).__name__}: {e}"[:300]}
    p = r.parsed_output
    return {"stop": r.stop_reason, "in": r.usage.input_tokens, "out": r.usage.output_tokens,
            "parsed": p.model_dump() if p else None}


def run(mails, results, save):
    client = anthropic.Anthropic(api_key=parse_mail.load_api_key())
    parse_mail.check_key(client)
    for name, opts in MODELS.items():
        done = results.setdefault(name, {})
        todo = [m for m in mails if "error" in done.get(m["id"], {"error": 1})]
        print(f"{name}: {len(todo)}통 요청 (받아 둔 것 {len(mails) - len(todo)}통)")
        with cf.ThreadPoolExecutor(4) as pool:
            futs = {pool.submit(call, client, m, opts): m["id"] for m in todo}
            for f in cf.as_completed(futs):
                done[futs[f]] = f.result()
                save()


def norm(rec):
    """비교용 모양. 요약(summary)은 자유 문장이라 뺀다. 특가가 아니면 운영처럼 항목을 버린다. 오류는 None."""
    p = (rec or {}).get("parsed")
    if not p:
        return None
    deals = sorted({(d["origin"], d["destination"], d["price_krw"], d["promo_end"]) for d in p["deals"]}, key=str) \
        if p["is_deal"] else []
    return {"is_deal": p["is_deal"], "airline": p["airline"], "url": p["official_url"], "deals": deals}


def report(mails, results):
    lines, flags = [], {}
    for m in mails:
        flags[m["id"]] = {"filter": bool(parse_mail.PROMO_SUBJECT.search(m["subject"] or "")),
                          "cut": len(parse_mail.html_to_text(m["body"], limit=10**9)) > LIMIT}
    n = len(mails)
    print(f"\n메일 {n}통 · 제목 거름망 통과 {sum(f['filter'] for f in flags.values())} · "
          f"본문 {LIMIT}자 넘어 잘림 {sum(f['cut'] for f in flags.values())}")
    for name in MODELS:
        recs = [results.get(name, {}).get(m["id"]) for m in mails]
        err = sum(1 for r in recs if r is None or "error" in r)
        odd = sum(1 for r in recs if r and r.get("stop") not in (None, "end_turn"))
        tin = sum(r.get("in", 0) for r in recs if r)
        tout = sum(r.get("out", 0) for r in recs if r)
        cost = (tin * PRICE[name][0] + tout * PRICE[name][1]) / 1e6
        print(f"  {name}: 응답 없음·오류 {err} · end_turn 아님 {odd} · 토큰 {tin:,}/{tout:,} · 약 ${cost:.2f}")
    for name in MODELS:
        if name == REF:
            continue
        same = {k: 0 for k in ("is_deal", "airline", "url", "deals")}
        both = 0
        for m in mails:
            a, b = norm(results.get(name, {}).get(m["id"])), norm(results.get(REF, {}).get(m["id"]))
            if a and b:
                both += 1
                for k in same:
                    same[k] += a[k] == b[k]
        print(f"  {name} vs {REF} (둘 다 응답 {both}통): " + " · ".join(f"{k} {v}/{both}" for k, v in same.items()))
    missed = [m for m in mails if not flags[m["id"]]["filter"]
              and (norm(results.get(REF, {}).get(m["id"])) or {}).get("is_deal")]
    print(f"  거름망이 막았는데 {REF} 는 특가라고 본 메일: {len(missed)}통")

    for m in mails:
        outs = {name: norm(results.get(name, {}).get(m["id"])) for name in MODELS}
        if len({json.dumps(o, ensure_ascii=False, sort_keys=True) for o in outs.values()}) == 1:
            continue
        f = flags[m["id"]]
        lines.append(f"\n## [{m['id']}] {m['subject']}\n{m['sender']} · {m['received']} · "
                     f"거름망 {'통과' if f['filter'] else '막힘'}{' · 본문 잘림' if f['cut'] else ''}")
        for name, o in outs.items():
            if o is None:
                lines.append(f"- **{name}**: (응답 없음) {results.get(name, {}).get(m['id'])}")
                continue
            lines.append(f"- **{name}**: 특가 {o['is_deal']} · {o['airline']} · {o['url']}")
            lines.extend(f"    - {d}" for d in o["deals"])
    (OUT / "diff.md").write_text("# 모델 간 차이\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n갈린 메일 {sum(1 for l in lines if l.startswith(chr(10) + '## '))}통 → {OUT / 'diff.md'}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mpath, rpath = OUT / "mails.json", OUT / "results.json"
    if "--refetch" in sys.argv or not mpath.exists():
        mpath.write_text(json.dumps(fetch_mails(), ensure_ascii=False, indent=1), encoding="utf-8")
    mails = json.loads(mpath.read_text(encoding="utf-8"))
    results = json.loads(rpath.read_text(encoding="utf-8")) if rpath.exists() else {}

    def save():
        rpath.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    if "--report" not in sys.argv:
        run(mails, results, save)
    report(mails, results)


if __name__ == "__main__":
    main()
