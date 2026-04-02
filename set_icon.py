#!/usr/bin/env python3
"""
Set a Slack app icon via the Manifest API.

Usage:
  export SLACK_CONFIG_REFRESH_TOKEN="xoxe-..."
  export SLACK_APP_ID="A0123ABCDEF"
  python set_icon.py --image icon.png
"""

import argparse
import urllib.request
import urllib.parse
import mimetypes
import uuid
import json
import os
import sys

SLACK_API_BASE = "https://slack.com/api"


def main():
    parser = argparse.ArgumentParser(description="Set a Slack app icon")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--app-id", help="Slack App ID (or set SLACK_APP_ID env var)")
    args = parser.parse_args()

    app_id = args.app_id or os.environ.get("SLACK_APP_ID", "")
    refresh = os.environ.get("SLACK_CONFIG_REFRESH_TOKEN", "")

    if not app_id:
        print("Set SLACK_APP_ID env var or pass --app-id")
        sys.exit(1)
    if not refresh:
        print("Set SLACK_CONFIG_REFRESH_TOKEN env var")
        sys.exit(1)

    image_path = args.image

    # Rotate token
    rot_req = urllib.request.Request(
        f"{SLACK_API_BASE}/tooling.tokens.rotate",
        data=urllib.parse.urlencode({"refresh_token": refresh}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(rot_req) as resp:
        rot_res = json.loads(resp.read().decode())
        if not rot_res.get("ok"):
            print(f"Token rotation failed: {rot_res.get('error')}")
            sys.exit(1)
        token = rot_res["token"]
        print(f"New refresh token: {rot_res['refresh_token']}")

    # Upload icon
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    boundary = uuid.uuid4().hex

    with open(image_path, "rb") as f:
        image_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="app_id"\r\n\r\n'
        f"{app_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{os.path.basename(image_path)}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + image_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{SLACK_API_BASE}/apps.icon.set",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print(f"✅ Icon set for app {app_id}")
            else:
                print(f"❌ Failed: {result.get('error')}")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
