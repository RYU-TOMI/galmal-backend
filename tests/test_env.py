# -*- coding: utf-8 -*-
"""`.env`·환경변수를 읽는 한 곳 (BB41 → BE18).

다섯 벌을 하나로 합쳤으므로, **그 하나가 틀리면 다섯 군데가 같이 틀린다.** 합치기 전에
각 구현이 실제로 어떻게 행동했는지를 여기 고정해 둔다 — 「합쳤더니 조용히 달라졌다」를 막는다.

🔴 실제 `.env` 는 건드리지 않는다. 전부 임시 파일로 본다.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import env


class EnvFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env._cache.clear()
        self.addCleanup(env._cache.clear)

    def write(self, text):
        p = Path(self.tmp.name) / ".env"
        p.write_text(text, encoding="utf-8")
        return p

    def get(self, name, text=None, environ=None):
        path = self.write(text) if text is not None else Path(self.tmp.name) / "없는파일.env"
        with mock.patch.object(env, "ENV_FILE", path), \
             mock.patch.dict(os.environ, environ or {}, clear=True):
            return env.get(name)

    def test_environment_wins_over_file(self):
        """크론은 시크릿을 환경변수로 넣는다. 둘 다 있으면 손으로 덮어쓸 수 있어야 한다."""
        self.assertEqual(self.get("K", "K=파일값", {"K": "환경값"}), "환경값")

    def test_file_is_used_when_the_variable_is_missing(self):
        self.assertEqual(self.get("K", "K=파일값"), "파일값")

    def test_empty_is_the_same_as_absent(self):
        """🔴 빈 값이 시크릿 행세를 하면 안 된다 — 다섯 구현 모두 `if val:` 로 그렇게 다뤘다.

        빈 환경변수는 파일로 넘어가고, 파일의 빈 값은 `None` 이다.
        """
        self.assertEqual(self.get("K", "K=파일값", {"K": ""}), "파일값")
        self.assertEqual(self.get("K", "K=", {"K": "   "}), None)
        self.assertIsNone(self.get("K", "K="))

    def test_missing_file_and_missing_key_are_none(self):
        self.assertIsNone(self.get("K"))
        self.assertIsNone(self.get("없는키", "K=v"))

    def test_values_are_stripped(self):
        self.assertEqual(self.get("K", "  K = 값  "), "값")
        self.assertEqual(self.get("K", "K=v", {"K": "  환경  "}), "환경")

    def test_comments_and_junk_lines_are_ignored(self):
        self.assertIsNone(self.get("K", "# K=주석\n\n키만있는줄\n"))

    def test_first_wins_when_a_key_repeats(self):
        """예전 구현들은 `startswith(f"{name}=")` 로 **첫 매치**를 가져갔다. 그 동작을 지킨다."""
        self.assertEqual(self.get("K", "K=처음\nK=나중"), "처음")

    def test_value_may_contain_equals(self):
        """토큰에 `=` 가 들어갈 수 있다(base64 패딩 등). 첫 `=` 에서만 가른다."""
        self.assertEqual(self.get("K", "K=a=b=c"), "a=b=c")

    def test_cache_follows_the_file(self):
        """캐시가 파일보다 오래 살면 안 된다 — 키에 mtime·크기가 들어 있다."""
        path = self.write("K=처음")
        with mock.patch.object(env, "ENV_FILE", path), \
             mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env.get("K"), "처음")
            path.write_text("K=바뀐값이라길이도다르다", encoding="utf-8")
            self.assertEqual(env.get("K"), "바뀐값이라길이도다르다")

    def test_file_is_read_once_per_version(self):
        """예전 `affiliates._env` 는 **호출마다** 파일을 다시 읽었다(링크 하나 만들 때마다 여러 번)."""
        path = self.write("K=v")
        with mock.patch.object(env, "ENV_FILE", path), \
             mock.patch.dict(os.environ, {}, clear=True):
            env.get("K")
            before = len(env._cache)
            for _ in range(5):
                env.get("K")
            self.assertEqual(len(env._cache), before)
            self.assertEqual(before, 1)


class RequireTest(unittest.TestCase):
    """없으면 **멈춘다.** 조용히 빈 값으로 계속 가면 빈 산출물이 배포된다(BB30·BB2)."""

    def setUp(self):
        env._cache.clear()
        self.addCleanup(env._cache.clear)

    def test_returns_the_value(self):
        with mock.patch.dict(os.environ, {"K": "v"}, clear=True):
            self.assertEqual(env.require("K"), "v")

    def test_exits_with_the_name_in_the_message(self):
        missing = Path(tempfile.gettempdir()) / "없는파일.env"
        with mock.patch.object(env, "ENV_FILE", missing), \
             mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                env.require("TP_TOKEN")
        self.assertIn("TP_TOKEN", str(cm.exception))


class CallersUseTheSharedModuleTest(unittest.TestCase):
    """🔎 여집합 — **`.env` 를 직접 읽는 모듈이 더 생기지 않는다.**

    다시 흩어지면 합친 의미가 없다. 새 코드가 파일을 직접 열면 여기서 걸린다.
    """

    COLLECTOR = Path(__file__).resolve().parent.parent / "collector"

    def test_only_env_module_touches_the_dotenv_file(self):
        offenders = sorted(
            f.name for f in self.COLLECTOR.glob("*.py")
            if f.name != "env.py" and '".env"' in f.read_text(encoding="utf-8"))
        self.assertEqual(offenders, [], f"`.env` 를 직접 읽지 말고 `env.get()` 을 쓸 것: {offenders}")


if __name__ == "__main__":
    unittest.main()
