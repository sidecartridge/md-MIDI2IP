#!/usr/bin/env python3
"""Hatari gateway self-test — EPIC-05.

STORY-01: FIFO lifecycle — create (idempotent), robust open tolerant of Hatari
starting before or after the gateway, and cleanup. Stdlib only; exit 0 = PASS.

The gateway's IN-write open waits for a reader (Hatari's --midi-out); we simulate
that reader with a plain os.open(..., O_RDONLY) on the IN fifo.

Usage:  python3 hatari-gateway/selftest.py
"""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gateway  # noqa: E402

_failures: "list[str]" = []


def check(name: str, ok: bool) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        _failures.append(name)


def main() -> int:
    d = tempfile.mkdtemp(prefix="hatari-gw-test-")
    try:
        print("create:")
        out_path, in_path = gateway.create_fifos(d)
        import stat
        check("midi_out.fifo is a FIFO", stat.S_ISFIFO(os.stat(out_path).st_mode))
        check("midi_in.fifo is a FIFO", stat.S_ISFIFO(os.stat(in_path).st_mode))
        check("create_fifos idempotent", gateway.create_fifos(d) == (out_path, in_path))

        print("open — Hatari after the gateway (open waits for the IN reader):")
        result: dict = {}

        def run_open() -> None:
            result["fds"] = gateway.open_fifos(out_path, in_path, poll=0.02)

        t = threading.Thread(target=run_open, daemon=True)
        t.start()
        time.sleep(0.3)
        check("open blocks until Hatari opens the IN fifo", "fds" not in result)
        in_reader = os.open(in_path, os.O_RDONLY | os.O_NONBLOCK)  # ~ Hatari --midi-out
        t.join(timeout=3)
        check("open returns once the IN reader appears", "fds" in result)
        if "fds" in result:
            ofd, ifd = result["fds"]
            check("valid out_fd (Atari OUT, read)", ofd >= 0)
            check("valid in_fd (Atari IN, write)", ifd >= 0)
            os.close(ofd)
            os.close(ifd)
        os.close(in_reader)

        print("open — Hatari before the gateway (IN reader already present):")
        in_reader = os.open(in_path, os.O_RDONLY | os.O_NONBLOCK)
        start = time.monotonic()
        ofd, ifd = gateway.open_fifos(out_path, in_path, poll=0.02)
        check("open returns promptly when reader is already present",
              (time.monotonic() - start) < 0.5)
        os.close(ofd)
        os.close(ifd)
        os.close(in_reader)

        print("cleanup:")
        gateway.remove_fifos(d)
        check("FIFOs removed",
              not os.path.exists(out_path) and not os.path.exists(in_path))
    finally:
        gateway.remove_fifos(d)
        try:
            os.rmdir(d)
        except OSError:
            pass

    print()
    if _failures:
        print(f"FAIL — {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("PASS — Hatari gateway FIFO lifecycle validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
