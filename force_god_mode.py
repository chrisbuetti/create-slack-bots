#!/usr/bin/env python3
"""
Force-update a Slack app with ALL available bot scopes ("god mode").

Usage:
  export SLACK_CONFIG_REFRESH_TOKEN="xoxe-..."
  export SLACK_APP_ID="A0123ABCDEF"
  python force_god_mode.py
"""

import json
import os
import sys
import urllib.request
import urllib.parse

SLACK_API_BASE = "https://slack.com/api"
APP_ID = os.environ.get("SLACK_APP_ID", "")

# God mode scopes - every valid bot scope Slack offers (March 2026)
GOD_MODE_SCOPES = [
    "app_mentions:read",
    "bookmarks:read",
    "bookmarks:write",
    "calls:read",
    "calls:write",
    "channels:history",
    "channels:join",
    "channels:manage",
    "channels:read",
    "channels:write.invites",
    "channels:write.topic",
    "chat:write",
    "chat:write.customize",
    "chat:write.public",
    "commands",
    "conversations.connect:manage",
    "conversations.connect:read",
    "conversations.connect:write",
    "dnd:read",
    "emoji:read",
    "files:read",
    "files:write",
    "groups:history",
    "groups:read",
    "groups:write",
    "groups:write.invites",
    "groups:write.topic",
    "im:history",
    "im:read",
    "im:write",
    "incoming-webhook",
    "links:read",
    "links:write",
    "metadata.message:read",
    "mpim:history",
    "mpim:read",
    "mpim:write",
    "mpim:write.topic",
    "pins:read",
    "pins:write",
    "reactions:read",
    "reactions:write",
    "reminders:read",
    "reminders:write",
    "remote_files:read",
    "remote_files:share",
    "remote_files:write",
    "team:read",
    "team.billing:read",
    "team.preferences:read",
    "usergroups:read",
    "usergroups:write",
    "users:read",
    "users:read.email",
    "users:write",
    "users.profile:read",
    "workflow.steps:execute",
]

# Valid bot events (removed deprecated ones)
GOD_MODE_EVENTS = [
    "app_home_opened",
    "app_mention",
    "app_uninstalled",
    "channel_archive",
    "channel_created",
    "channel_deleted",
    "channel_history_changed",
    "channel_id_changed",
    "channel_left",
    "channel_rename",
    "channel_shared",
    "channel_unarchive",
    "channel_unshared",
    "emoji_changed",
    "file_change",
    "file_created",
    "file_deleted",
    "file_public",
    "file_shared",
    "file_unshared",
    "group_archive",
    "group_deleted",
    "group_history_changed",
    "group_left",
    "group_rename",
    "group_unarchive",
    "im_history_changed",
    "link_shared",
    "member_joined_channel",
    "member_left_channel",
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim",
    "pin_added",
    "pin_removed",
    "reaction_added",
    "reaction_removed",
    "team_join",
    "tokens_revoked",
    "user_change",
    "user_profile_changed",
]


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

    print("[1/4] Rotating token...")
    token, new_refresh = rotate_token(refresh_token)
    print(f"  ✅ New refresh token: {new_refresh}")

    print("[2/4] Exporting current manifest...")
    result = slack_api("apps.manifest.export", token, {"app_id": APP_ID})
    if not result.get("ok"):
        print(f"  ❌ Export failed: {result.get('error')}")
        sys.exit(1)
    manifest = result["manifest"]
    print(f"  ✅ Got manifest for: {manifest.get('display_information', {}).get('name')}")

    print("[3/4] Injecting god-mode scopes...")
    manifest.setdefault("oauth_config", {}).setdefault("scopes", {})["bot"] = GOD_MODE_SCOPES
    manifest.setdefault("settings", {}).setdefault("event_subscriptions", {})["bot_events"] = GOD_MODE_EVENTS
    print(f"  • {len(GOD_MODE_SCOPES)} bot scopes")
    print(f"  • {len(GOD_MODE_EVENTS)} event subscriptions")

    print("[4/4] Updating app manifest...")
    result = slack_api("apps.manifest.update", token, {"app_id": APP_ID, "manifest": manifest})
    if not result.get("ok"):
        errors = result.get("errors", [])
        print(f"  ❌ Update failed: {result.get('error')}")
        for e in errors:
            print(f"     • {e.get('message')} (at {e.get('pointer')})")
        sys.exit(1)

    app_name = manifest.get("display_information", {}).get("name", APP_ID)
    print("\n" + "=" * 60)
    print(f"  ✅ {app_name} now has GOD MODE!")
    print("=" * 60)
    print(f"\n  Go to: https://api.slack.com/apps/{APP_ID}/oauth")
    print("  Click 'Reinstall to Workspace' to activate new scopes.\n")


if __name__ == "__main__":
    main()
