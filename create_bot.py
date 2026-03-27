#!/usr/bin/env python3
"""
Slack Bot Creator — Programmatic app creation via the Slack App Manifest API.

Creates fully-configured Slack apps without ever touching the Slack admin UI.
Handles config token rotation, manifest validation, and app creation in one shot.

Prerequisites:
  1. Go to https://api.slack.com/apps
  2. Scroll to "Your App Configuration Tokens"
  3. Click "Generate Token" → select your workspace
  4. Copy both the Access Token (xoxe.xoxp-...) and Refresh Token (xoxe-...)
  5. Store them as environment variables or in a .env file

Usage:
  # Via environment variables:
  export SLACK_CONFIG_TOKEN="xoxe.xoxp-..."
  export SLACK_CONFIG_REFRESH_TOKEN="xoxe-..."
  python create_bot.py

  # Override bot name and display name:
  python create_bot.py --name "Deploy Bot" --display-name "deploy-bot"

  # Set a custom app icon:
  python create_bot.py --icon bot_avatar.png

  # Preview the manifest without creating anything:
  python create_bot.py --dry-run

  # Use a .env file (auto-detected in current directory):
  python create_bot.py
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


SLACK_API_BASE = "https://slack.com/api"


# ──────────────────────────────────────────────────────────────────────────────
# Bot Configuration
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BotConfig:
    """Declarative configuration for a Slack bot app."""

    name: str = "My Custom Bot"
    description: str = "A bot created programmatically via the Manifest API"
    display_name: str = "my-custom-bot"
    background_color: str = "#4A154B"

    bot_scopes: list = field(default_factory=lambda: [
        "app_mentions:read",
        "channels:history",
        "channels:read",
        "chat:write",
        "chat:write.public",
        "commands",
        "im:history",
        "im:read",
        "im:write",
        "users:read",
    ])

    bot_events: list = field(default_factory=lambda: [
        "app_mention",
        "message.im",
    ])

    socket_mode: bool = True
    request_url: str = "https://your-server.com/slack/events"
    interactivity_url: str = "https://your-server.com/slack/interactions"

    slash_commands: list = field(default_factory=list)

    home_tab_enabled: bool = True
    messages_tab_enabled: bool = True


# ──────────────────────────────────────────────────────────────────────────────
# Manifest Builder
# ──────────────────────────────────────────────────────────────────────────────

def build_manifest(config: BotConfig) -> dict:
    """Build a Slack app manifest dict from a BotConfig."""

    manifest = {
        "_metadata": {
            "major_version": 2,
            "minor_version": 1,
        },
        "display_information": {
            "name": config.name,
            "description": config.description,
            "background_color": config.background_color,
        },
        "features": {
            "app_home": {
                "home_tab_enabled": config.home_tab_enabled,
                "messages_tab_enabled": config.messages_tab_enabled,
                "messages_tab_read_only_enabled": False,
            },
            "bot_user": {
                "display_name": config.display_name,
                "always_online": True,
            },
        },
        "oauth_config": {
            "scopes": {
                "bot": config.bot_scopes,
            },
        },
        "settings": {
            "socket_mode_enabled": config.socket_mode,
            "org_deploy_enabled": False,
            "token_rotation_enabled": False,
        },
    }

    if config.bot_events:
        event_config = {"bot_events": config.bot_events}
        if not config.socket_mode:
            event_config["request_url"] = config.request_url
        manifest["settings"]["event_subscriptions"] = event_config

    if not config.socket_mode:
        manifest["settings"]["interactivity"] = {
            "is_enabled": True,
            "request_url": config.interactivity_url,
        }

    if config.slash_commands:
        manifest["features"]["slash_commands"] = []
        for cmd in config.slash_commands:
            slash = {
                "command": cmd["command"],
                "description": cmd["description"],
                "usage_hint": cmd.get("usage_hint", ""),
            }
            if not config.socket_mode and "url" in cmd:
                slash["url"] = cmd["url"]
            manifest["features"]["slash_commands"].append(slash)

    return manifest


# ──────────────────────────────────────────────────────────────────────────────
# Slack API Client
# ──────────────────────────────────────────────────────────────────────────────

def slack_api_call(method: str, token: str, payload: Optional[dict] = None) -> dict:
    """Make a Slack API call using only the stdlib (no third-party deps)."""

    url = f"{SLACK_API_BASE}/{method}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def rotate_token(refresh_token: str) -> tuple[str, str]:
    """Rotate a Slack config token. Returns (new_access_token, new_refresh_token)."""

    url = f"{SLACK_API_BASE}/tooling.tokens.rotate"
    data = urllib.parse.urlencode({"refresh_token": refresh_token}).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if not result.get("ok"):
        print(f"  Token rotation failed: {result.get('error', 'unknown error')}")
        print("  → Re-generate your config token at https://api.slack.com/apps")
        sys.exit(1)

    return result["token"], result["refresh_token"]


def set_app_icon(token: str, app_id: str, image_path: Path) -> dict:
    """Upload an app icon via multipart form POST to apps.icon.set."""

    if not image_path.is_file():
        print(f"  ❌ Icon file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    boundary = uuid.uuid4().hex

    image_data = image_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="app_id"\r\n\r\n'
        f"{app_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
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
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader — no dependencies required."""
    if not path.is_file():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Slack bot app programmatically via the Manifest API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                                  # create with defaults
  %(prog)s --name "Deploy Bot"              # custom name
  %(prog)s --icon avatar.png                # set a profile picture
  %(prog)s --dry-run                        # preview manifest only
  %(prog)s --no-socket-mode                 # use HTTP request URLs instead
""",
    )
    parser.add_argument(
        "--name",
        help="app name shown in Slack (default: 'My Custom Bot')",
    )
    parser.add_argument(
        "--display-name",
        help="bot username in conversations (default: derived from --name)",
    )
    parser.add_argument(
        "--description",
        help="short app description",
    )
    parser.add_argument(
        "--no-socket-mode",
        action="store_true",
        help="use HTTP request URLs instead of Socket Mode",
    )
    parser.add_argument(
        "--request-url",
        help="events request URL (only with --no-socket-mode)",
    )
    parser.add_argument(
        "--icon",
        type=Path,
        help="path to an image file to use as the app icon (PNG, JPG, or GIF)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the manifest JSON and exit without creating the app",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    load_dotenv()

    print("=" * 60)
    print("  Slack Bot Creator — Manifest API")
    print("=" * 60)

    config = BotConfig()
    if args.name:
        config.name = args.name
    if args.display_name:
        config.display_name = args.display_name
    elif args.name:
        config.display_name = args.name.lower().replace(" ", "-")
    if args.description:
        config.description = args.description
    if args.no_socket_mode:
        config.socket_mode = False
    if args.request_url:
        config.request_url = args.request_url
        config.interactivity_url = args.request_url

    manifest = build_manifest(config)

    # --dry-run: just dump the manifest and exit
    if args.dry_run:
        print("\n[dry-run] Generated manifest:\n")
        print(json.dumps(manifest, indent=2))
        return

    # Load credentials from env
    config_token = os.environ.get("SLACK_CONFIG_TOKEN", "")
    refresh_token = os.environ.get("SLACK_CONFIG_REFRESH_TOKEN", "")

    if not config_token or not refresh_token:
        print("\n❌ Missing credentials.")
        print("   Set SLACK_CONFIG_TOKEN and SLACK_CONFIG_REFRESH_TOKEN")
        print("   as environment variables or in a .env file.")
        print("   Generate them at: https://api.slack.com/apps")
        print("   (scroll to 'Your App Configuration Tokens')")
        sys.exit(1)

    total_steps = 5 if args.icon else 4

    # Step 1 — Rotate token (config tokens expire every 12 hours)
    print(f"\n[1/{total_steps}] Rotating config token...")
    config_token, refresh_token = rotate_token(refresh_token)
    print("  ✅ Token rotated.")
    print(f"  💡 Save your new refresh token for next time:")
    print(f"     {refresh_token}")

    # Step 2 — Show manifest summary
    print(f"\n[2/{total_steps}] Building app manifest...")
    print(f"  App name:    {config.name}")
    print(f"  Bot user:    @{config.display_name}")
    print(f"  Scopes:      {len(config.bot_scopes)}")
    print(f"  Events:      {len(config.bot_events)}")
    print(f"  Socket Mode: {config.socket_mode}")

    # Step 3 — Validate
    print(f"\n[3/{total_steps}] Validating manifest...")
    validation = slack_api_call("apps.manifest.validate", config_token, {
        "manifest": manifest,
    })

    if not validation.get("ok"):
        print("  ❌ Manifest validation failed:")
        for err in validation.get("errors", []):
            print(f"     • {err.get('message', '')} (at {err.get('pointer', '')})")
        sys.exit(1)
    print("  ✅ Manifest is valid.")

    # Step 4 — Create the app
    print(f"\n[4/{total_steps}] Creating Slack app...")
    result = slack_api_call("apps.manifest.create", config_token, {
        "manifest": manifest,
    })

    if not result.get("ok"):
        print(f"  ❌ App creation failed: {result.get('error', 'unknown')}")
        for err in result.get("errors", []):
            print(f"     • {err.get('message', '')} (at {err.get('pointer', '')})")
        sys.exit(1)

    # Step 5 (optional) — Upload app icon
    if args.icon:
        print(f"\n[5/{total_steps}] Uploading app icon ({args.icon.name})...")
        icon_result = set_app_icon(config_token, result["app_id"], args.icon)
        if not icon_result.get("ok"):
            print(f"  ⚠️  Icon upload failed: {icon_result.get('error', 'unknown')}")
            print("  The app was still created — you can set the icon manually.")
        else:
            print("  ✅ App icon set.")

    # Done — print credentials
    creds = result.get("credentials", {})
    app_id = result.get("app_id", "???")
    oauth_url = result.get("oauth_authorize_url", "")

    print("  ✅ App created successfully!")
    print()
    print("=" * 60)
    print("  YOUR NEW SLACK APP")
    print("=" * 60)
    print(f"  App ID:            {app_id}")
    print(f"  Client ID:         {creds.get('client_id', 'N/A')}")
    print(f"  Client Secret:     {creds.get('client_secret', 'N/A')}")
    print(f"  Signing Secret:    {creds.get('signing_secret', 'N/A')}")
    print(f"  Verification Token:{creds.get('verification_token', 'N/A')}")
    print()
    print("  NEXT STEPS:")
    print(f"  1. Go to: https://api.slack.com/apps/{app_id}")

    if config.socket_mode:
        print(f"  2. Under 'Basic Information' → 'App-Level Tokens'")
        print(f"     → Generate a token with 'connections:write' scope")
        print(f"     → This gives you your SLACK_APP_TOKEN (xapp-...)")

    print(f"  3. Install to workspace: {oauth_url}")
    print(f"  4. After install, grab your Bot Token (xoxb-...) from")
    print(f"     'OAuth & Permissions' → 'Bot User OAuth Token'")
    print()
    print("  ⚠️  Store these credentials securely — they won't be shown again!")
    print("=" * 60)


if __name__ == "__main__":
    main()
