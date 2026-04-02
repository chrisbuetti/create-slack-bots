#!/usr/bin/env python3
"""Disable the Home Tab for a Slack app via manifest update."""

import json
import os
import sys
import urllib.request
import urllib.parse

SLACK_API_BASE = "https://slack.com/api"
APP_ID = os.environ.get("SLACK_APP_ID", "")


def rotate_token(refresh_token: str):
    url = f"{SLACK_API_BASE}/tooling.tokens.rotate"
    data = urllib.parse.urlencode({"refresh_token": refresh_token}).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if not result.get("ok"):
        print(f"Token rotation failed: {result.get('error')}")
        sys.exit(1)
    return result["token"], result["refresh_token"]


def slack_api(method: str, token: str, payload: dict):
    url = f"{SLACK_API_BASE}/{method}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    refresh_token = os.environ.get("SLACK_CONFIG_REFRESH_TOKEN")
    if not refresh_token:
        print("Set SLACK_CONFIG_REFRESH_TOKEN env var")
        sys.exit(1)

    if not APP_ID:
        print("Set SLACK_APP_ID env var (e.g. A0123ABCDEF)")
        sys.exit(1)

    print(f"[1/4] Rotating token...")
    token, new_refresh = rotate_token(refresh_token)
    print(f"  ✅ New refresh token: {new_refresh}")

    print(f"[2/4] Exporting manifest for app {APP_ID}...")
    result = slack_api("apps.manifest.export", token, {"app_id": APP_ID})
    if not result.get("ok"):
        print(f"  ❌ Export failed: {result.get('error')}")
        sys.exit(1)
    manifest = result["manifest"]
    app_name = manifest.get("display_information", {}).get("name", "Unknown")
    print(f"  ✅ Got manifest for: {app_name}")

    # Check current home tab state
    features = manifest.get("features", {})
    app_home = features.get("app_home", {})
    current_state = app_home.get("home_tab_enabled", "not set")
    print(f"  Current home_tab_enabled: {current_state}")

    print("[3/4] Disabling home tab...")
    manifest.setdefault("features", {}).setdefault("app_home", {})["home_tab_enabled"] = False
    print("  • home_tab_enabled → False")

    print("[4/4] Updating app manifest...")
    result = slack_api("apps.manifest.update", token, {"app_id": APP_ID, "manifest": manifest})
    if not result.get("ok"):
        errors = result.get("errors", [])
        print(f"  ❌ Update failed: {result.get('error')}")
        for e in errors:
            print(f"     • {e.get('message')} (at {e.get('pointer')})")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"  ✅ Home tab disabled for {app_name} ({APP_ID})")
    print(f"\n  Save this refresh token for next time:")
    print(f"  {new_refresh}")


if __name__ == "__main__":
    main()
