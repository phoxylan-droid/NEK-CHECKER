#!/usr/bin/env python3
"""Local all-in-one server for NEK CHECKER (no Vercel needed)."""
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))

# import handlers
import importlib.util

def load_handler(name):
    path = os.path.join(ROOT, "api", f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler


H_HEALTH = load_handler("health")
H_CHECKERS = load_handler("checkers")
H_CHECK = load_handler("check")


class App(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PUBLIC, **k)

    def log_message(self, fmt, *args):
        sys.stderr.write("[nek] " + (fmt % args) + "\n")

    def _route_api(self, HandlerCls):
        # adapt BaseHTTPRequestHandler subclass instance methods onto self
        h = HandlerCls
        # call do_* on a shim
        class Shim(h):
            def __init__(self, outer):
                self.headers = outer.headers
                self.rfile = outer.rfile
                self.wfile = outer.wfile
                self.command = outer.command
                self.path = outer.path
                self.request_version = outer.request_version
                self.client_address = outer.client_address
                self.connection = outer.connection
                self.server = outer.server
            def send_response(self, code, message=None):
                outer = self
                SimpleHTTPRequestHandler.send_response(App_ref, code, message)
            # bind properly below

        # simpler: monkey-patch by invoking methods with self as fake
        return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/health"):
            return self._run(H_HEALTH, "do_GET")
        if path.startswith("/api/checkers"):
            return self._run(H_CHECKERS, "do_GET")
        if path.startswith("/api/check"):
            return self._run(H_CHECK, "do_GET")
        if path == "/":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/api/check"):
            return self._run(H_CHECK, "do_POST")
        self.send_error(404)

    def _run(self, HandlerCls, method):
        # Instantiate without calling BaseHTTPRequestHandler.__init__
        inst = HandlerCls.__new__(HandlerCls)
        inst.headers = self.headers
        inst.rfile = self.rfile
        inst.wfile = self.wfile
        inst.command = self.command
        inst.path = self.path
        inst.request_version = self.request_version
        inst.client_address = self.client_address
        inst.connection = self.connection
        inst.server = self.server
        inst.send_response = self.send_response
        inst.send_header = self.send_header
        inst.end_headers = self.end_headers
        inst.send_error = self.send_error
        getattr(inst, method)()


App_ref = None

def main():
    port = int(os.environ.get("PORT", "8080"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), App)
    print(f"NEK CHECKER → http://127.0.0.1:{port}")
    print("by @samvir1")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
