"""Call the Skyvern /v1/run/workflows API with the body at /tmp/skyvern_body.json.

Prints a JSON object {code, text} to stdout. Used by .github/workflows/run-skyvern.yml
because repeated attempts with curl returned HTTP 422 with the body parsed as if
raw HTTP headers were embedded in it. urllib sends a clean request.
"""
import json
import os
import sys
import urllib.request
import urllib.error

body = open("/tmp/skyvern_body.json", "rb").read()
req = urllib.request.Request(
    "https://api.skyvern.com/v1/run/workflows",
    data=body,
    method="POST",
    headers={
        "x-api-key": os.environ["SKYVERN_API_KEY"].strip(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        code = r.getcode()
        text = r.read().decode()
except urllib.error.HTTPError as e:
    code = e.code
    text = e.read().decode()
except Exception as e:  # noqa: BLE001
    code = 0
    text = f"client error: {type(e).__name__}: {e}"

json.dump({"code": code, "text": text}, sys.stdout)
