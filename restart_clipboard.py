#!/usr/bin/env python3
"""Restart only this exact script/user/display; explicit command clears history."""
import os, pathlib, signal, sys, subprocess, time

script = pathlib.Path(__file__).with_name("clipboard_history.py").resolve()
display = os.environ.get("DISPLAY")
if not display:
    raise SystemExit("DISPLAY is required")
stopped = []
for proc in pathlib.Path("/proc").iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        args = (proc / "cmdline").read_bytes().split(b"\0")
        if str(script).encode() not in args:
            continue
        env = dict(
            item.split(b"=", 1)
            for item in (proc / "environ").read_bytes().split(b"\0")
            if b"=" in item
        )
        if env.get(b"DISPLAY") != display.encode():
            continue
        os.kill(int(proc.name), signal.SIGTERM)
        stopped.append(proc)
    except (OSError, ValueError):
        continue
deadline = time.monotonic() + 3
while any(proc.exists() for proc in stopped) and time.monotonic() < deadline:
    time.sleep(0.05)
subprocess.run(
    [str(script.parent / "bin/clipboard-history"), "--ensure-running"], check=True
)
