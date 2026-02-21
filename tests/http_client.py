"""Minimal HTTP client using stdlib only (no requests dependency)."""

import json
import urllib.error
import urllib.request


def _request(method, url, json_body=None):
    data = json.dumps(json_body).encode() if json_body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode()
            return r.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"detail": body}


def get(url):
    code, body = _request("GET", url)
    return _Response(code, body)


def post(url, json_body):
    code, body = _request("POST", url, json_body)
    return _Response(code, body)


def delete(url):
    code, body = _request("DELETE", url)
    return _Response(code, body)


class _Response:
    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self._json = json_body

    def json(self):
        return self._json
