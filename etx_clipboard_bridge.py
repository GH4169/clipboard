#!/usr/bin/env python3
"""Guarded ETX entry point. Unsupported layouts never touch selections."""
import argparse, json, os, pathlib


def check():
    display = os.environ.get("DISPLAY", "")
    candidates = []
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            exe = (proc / "exe").resolve()
            if "etx" not in exe.name.lower():
                continue
            env = dict(
                x.split(b"=", 1)
                for x in (proc / "environ").read_bytes().split(b"\0")
                if b"=" in x
            )
            if env.get(b"DISPLAY", b"").decode() != display:
                continue
            candidates.append(int(proc.name))
        except (OSError, ValueError):
            continue
    return {
        "etx_present": bool(candidates),
        "enabled": False,
        "reason": "No validated ETX symbol layout exists on this WSL host; clipboard ownership and process memory are untouched.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--ensure-running", action="store_true")
    p.add_argument("--stop", action="store_true")
    a = p.parse_args()
    print(json.dumps(check(), ensure_ascii=False))


if __name__ == "__main__":
    main()
