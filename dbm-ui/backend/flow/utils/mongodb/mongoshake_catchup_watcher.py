# -*- coding: utf-8 -*-
"""MongoShake catch-up watcher (stdlib only). Used by wait_and_stop_script and e2e.

Compatible with Python 3.6+ (avoid postponed annotation syntax).
"""

import json
import os
import signal
import sys
import time
import urllib.request


def pid_alive(work):
    try:
        pid = int(open(os.path.join(work, "collector.pid")).read().strip())
    except Exception:
        return False, 0
    try:
        os.kill(pid, 0)
    except OSError:
        return False, pid
    return True, pid


def get_json(port, path):
    with urllib.request.urlopen("http://127.0.0.1:{}{}".format(port, path), timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def full_done(full_port):
    try:
        progress = str(get_json(full_port, "/progress").get("progress") or "")
    except Exception:
        return False
    return progress.startswith("100")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    work, full_port, incr_port = argv[0], int(argv[1]), int(argv[2])
    lag_seconds, stable_need, poll_seconds = int(argv[3]), int(argv[4]), int(argv[5])
    deadline = time.time() + int(argv[6])

    stable = 0
    seen_full = False
    full_done_at = 0
    while time.time() < deadline:
        alive, pid = pid_alive(work)
        if not alive:
            sys.stderr.write("collector exited before catch-up\n")
            return 1
        if not seen_full:
            seen_full = full_done(full_port)
            if seen_full:
                full_done_at = int(time.time())
            print("full_done={}".format(seen_full), flush=True)
            time.sleep(poll_seconds)
            continue
        try:
            repl = get_json(incr_port, "/repl")
        except Exception as err:
            print("repl not ready: {}".format(err), flush=True)
            stable = 0
            time.sleep(poll_seconds)
            continue
        ack = int((repl.get("lsn_ack") or {}).get("unix") or 0)
        now = int((repl.get("now") or {}).get("unix") or 0)
        # Require a real incr ack at/after full sync; never treat ack==0 as caught-up.
        caught = ack > 0 and ack >= full_done_at and now >= ack and now - ack <= lag_seconds
        stable = stable + 1 if caught else 0
        print("lag={} stable={}/{}".format(now - ack if ack else -1, stable, stable_need), flush=True)
        if stable >= stable_need:
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):
                try:
                    os.kill(pid, 0)
                except OSError:
                    print("collector stopped", flush=True)
                    break
                time.sleep(1)
            else:
                os.kill(pid, signal.SIGKILL)
                print("collector killed", flush=True)
            # Keep logs for triage; only drop plaintext conf.
            conf = os.path.join(work, "collector.conf")
            try:
                os.remove(conf)
            except OSError:
                pass
            return 0
        time.sleep(poll_seconds)
    sys.stderr.write("catch-up timeout\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
