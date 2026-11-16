#!/usr/bin/env python3
"""Run on an isolated X server; synthetic text never reaches the user's clipboard."""
import os, pathlib, subprocess, time, unittest, concurrent.futures
from clipboard_history import X11

ROOT = pathlib.Path(__file__).resolve().parent


class X11Tests(unittest.TestCase):
    def test_single_instance_and_display_alias(self):
        if os.environ.get("DISPLAY") in {None, ":0", ":97"}:
            self.skipTest("Dedicated test display required")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(
                pool.map(
                    lambda _: subprocess.run(
                        [str(ROOT / "bin/clipboard-history"), "--ensure-running"],
                        check=True,
                    ),
                    range(6),
                )
            )
        time.sleep(0.5)
        x = X11()
        owner = x.owner()
        self.assertTrue(owner)
        alias = dict(os.environ)
        alias["DISPLAY"] = alias["DISPLAY"].split(".")[0] + ".0"
        subprocess.run(
            [str(ROOT / "bin/clipboard-history"), "--ensure-running"],
            env=alias,
            check=True,
        )
        self.assertEqual(X11().owner(), owner)


if __name__ == "__main__":
    unittest.main()
