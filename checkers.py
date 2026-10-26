from http.server import BaseHTTPRequestHandler
import json

CHECKERS = [
    {"id": "netflix", "name": "Netflix", "cat": "stream", "icon": "🎬"},
    {"id": "disney", "name": "Disney+", "cat": "stream", "icon": "🏰"},
    {"id": "crunchyroll", "name": "Crunchyroll", "cat": "stream", "icon": "🍙"},
    {"id": "paramount", "name": "Paramount+", "cat": "stream", "icon": "⭐"},
    {"id": "peacock", "name": "Peacock", "cat": "stream", "icon": "🦚"},
    {"id": "pluto", "name": "Pluto TV", "cat": "stream", "icon": "📺"},
    {"id": "plex", "name": "Plex", "cat": "stream", "icon": "▶️"},
    {"id": "dazn", "name": "DAZN", "cat": "stream", "icon": "⚽"},
    {"id": "nba", "name": "NBA", "cat": "stream", "icon": "🏀"},
    {"id": "tabii", "name": "Tabii", "cat": "stream", "icon": "📡"},
    {"id": "playabl", "name": "Playabl", "cat": "stream", "icon": "🎮"},
    {"id": "makemusic", "name": "MakeMusic", "cat": "stream", "icon": "🎵"},
    {"id": "steam", "name": "Steam", "cat": "gaming", "icon": "🎮"},
    {"id": "xbox", "name": "Xbox", "cat": "gaming", "icon": "🟢"},
    {"id": "roblox", "name": "Roblox", "cat": "gaming", "icon": "🧱"},
    {"id": "nordvpn", "name": "NordVPN", "cat": "vpn", "icon": "🛡"},
    {"id": "expressvpn", "name": "ExpressVPN", "cat": "vpn", "icon": "🔒"},
    {"id": "cyberghost", "name": "CyberGhost", "cat": "vpn", "icon": "👻"},
    {"id": "hotspotshield", "name": "Hotspot Shield", "cat": "vpn", "icon": "🔥"},
    {"id": "hma", "name": "HMA VPN", "cat": "vpn", "icon": "🛡"},
    {"id": "strongvpn", "name": "StrongVPN", "cat": "vpn", "icon": "💪"},
    {"id": "deezer", "name": "Deezer", "cat": "music", "icon": "🎧"},
    {"id": "pandora", "name": "Pandora", "cat": "music", "icon": "📻"},
    {"id": "hotmail", "name": "Hotmail Inbox", "cat": "mail", "icon": "📧"},
    {"id": "rewards", "name": "Bing Rewards", "cat": "mail", "icon": "🎁"},
    {"id": "lovable", "name": "Lovable.dev", "cat": "ai", "icon": "💜"},
    {"id": "nvidia", "name": "NVIDIA / GFN", "cat": "ai", "icon": "🖥"},
    {"id": "duolingo", "name": "Duolingo", "cat": "other", "icon": "🦉"},
    {"id": "aha", "name": "Aha Video", "cat": "stream", "icon": "🇮🇳"},
    {"id": "pixverse", "name": "Pixverse", "cat": "ai", "icon": "🎥"},
    {"id": "melbet", "name": "Melbet", "cat": "other", "icon": "🎰"},
    {"id": "rdphostings", "name": "RDP Hostings", "cat": "vps", "icon": "🖥"},
    {"id": "terabox", "name": "TeraBox", "cat": "other", "icon": "☁"},
    {"id": "hidive", "name": "HIDIVE", "cat": "stream", "icon": "🎌"},
    {"id": "exxen", "name": "Exxen", "cat": "stream", "icon": "🇹🇷"},
    {"id": "bilibili", "name": "Bilibili", "cat": "stream", "icon": "📺"},
    {"id": "vidio", "name": "Vidio", "cat": "stream", "icon": "🇮🇩"},
    {"id": "multi", "name": "MULTI (all)", "cat": "multi", "icon": "⚡"},
]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"ok": True, "count": len(CHECKERS), "checkers": CHECKERS}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
