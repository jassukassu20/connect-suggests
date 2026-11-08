#!/usr/bin/env python3
"""Connect Suggests – live demo server (standard library only).

    python connect_server.py                 # starts the Yext mock in-process + demo UI on http://localhost:8800
    YEXT_BASE_URL=https://sbx-api.yextapis.com YEXT_API_KEY=... python connect_server.py   # real Yext sandbox write path

The UI is the same page as the static demo; here step 5 (Apply) performs a real read-modify-write PUT of the
entity's hours to Yext (mock or sandbox) and reads back listings for the owner confirmation.
Every decision is appended to work/audit.jsonl (date, old, new, basis, confidence, decision).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.environ.get("CONNECT_DATA", "/home/claude/src/Fonecta_SinceAI2026/data/FONECTA_CONNECT_SUGGESTS_2026")
sys.path.insert(0, os.path.join(DATA_ROOT, "examples"))
sys.path.insert(0, os.path.join(DATA_ROOT, "mock_api"))
from yext_client import YextClient  # noqa: E402

PORT = int(os.environ.get("PORT", 8800))
BASE = os.environ.get("YEXT_BASE_URL")
SANDBOX_MAP = os.environ.get("SANDBOX_ENTITY_ID")   # sandbox has its own test entity ids: map every demo write to it


def start_mock():
    os.environ.setdefault("MOCK_QUIET", "1")
    import server  # the dataset's Yext mock
    server.STATE_FILE = os.path.join(tempfile.mkdtemp(), "state.json")
    server.STORE = server.Store()
    srv = ThreadingHTTPServer(("127.0.0.1", 8787), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.2)
    return "http://127.0.0.1:8787"


def page():
    t = open(os.path.join(HERE, "app", "template.html"), encoding="utf-8").read()
    d = open(os.path.join(HERE, "work", "demo_bundle.json"), encoding="utf-8").read().replace("</", "<\\/")
    return t.replace("/*__DATA__*/null", d).replace("<script>\nconst DATA", "<script>window.CONNECT_API='';</script>\n<script>\nconst DATA", 1)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, page(), "text/html")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/apply":
            return self._send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        eid = body["entityId"]
        target = SANDBOX_MAP or eid
        yx = YextClient(base_url=BASE)
        try:
            for w in body.get("writes", []):
                yx.set_holiday_hours(target, w["date"], w["hours"])
                with open(os.path.join(HERE, "work", "audit.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "entity": eid,
                                        "written_to": target, **w}) + "\n")
            after = yx.get_entity(target).get("hours", {}).get("holidayHours", [])
            try:
                lst = yx.listings([target]).get("listings", [])
            except Exception:
                lst = []
            self._send(200, {"status": 200, "base": BASE, "holidayHours": after, "listings": lst})
        except Exception as e:
            self._send(200, {"error": str(e), "base": BASE})


def main():
    global BASE
    if not BASE:
        BASE = start_mock()
        print("Yext mock running at", BASE)
    else:
        print("Writing to", BASE, "(entity override: %s)" % SANDBOX_MAP if SANDBOX_MAP else "")
    print(f"Connect Suggests demo → http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
