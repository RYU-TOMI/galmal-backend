# -*- coding: utf-8 -*-
"""v1 응답 사본을 **받아 적는다.** 손으로 고치는 것을 대신하는 도구다.

    python fixtures/capture.py 05d0de9                  # 이 저장소의 커밋에서
    python fixtures/capture.py https://api.galmal.kr/v1 # 실물 API 에서

분리 후에는 두 번째 형태만 남는다(첫 번째는 `docs/v1/` 이 같은 저장소에 있는
이전 기간에만 쓴다). 어느 쪽이든 **하는 일은 같다** — 받아서 그대로 쓴다.

번거로우면 아무도 안 한다. 그래서 한 단계다.
"""
import io
import json
import os
import subprocess
import sys
import urllib.request

# 윈도우 콘솔이 cp949 라 한글 출력이 깨진다. 결과를 사람이 읽어야 하는 도구다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v1")


def _from_git(ref):
    """커밋에서 docs/v1/** 를 통째로 가져온다."""
    names = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "docs/v1"],
        capture_output=True, cwd=os.path.dirname(HERE)).stdout.decode().split()
    if not names:
        sys.exit("커밋 %s 에 docs/v1/ 이 없다" % ref)
    for n in names:
        blob = subprocess.run(["git", "show", "%s:%s" % (ref, n)],
                              capture_output=True, cwd=os.path.dirname(HERE)).stdout
        yield n[len("docs/"):], blob


def _from_url(base):
    """실물 API 에서. routes/index.json 을 먼저 읽어 노선 목록을 안다 —
    노선 목록을 여기 박아두면 그것도 계약의 사본이 된다."""
    base = base.rstrip("/")

    def get(path):
        with urllib.request.urlopen(base + "/" + path, timeout=30) as r:
            return r.read()

    for p in ("meta.json", "deals.json", "routes/index.json"):
        yield "v1/" + p, get(p)
    idx = json.loads(get("routes/index.json").decode("utf-8"))
    for r in idx["routes"]:
        yield "v1/routes/%s.json" % r["code"], get("routes/%s.json" % r["code"])


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    gen = _from_url(src) if src.startswith("http") else _from_git(src)

    n = 0
    for rel, blob in gen:
        dst = os.path.join(HERE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(blob)
        n += 1

    meta = json.load(io.open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    print("받아 적음 %d개 · schema=%s · generated=%s · 딜 %d건"
          % (n, meta.get("schema"), meta.get("generated"),
             meta.get("counts", {}).get("deals", -1)))
    print("출처: %s" % src)
    print("→ fixtures/README.md 의 「지금 사본의 출처」를 이 값으로 갱신할 것.")


if __name__ == "__main__":
    main()
