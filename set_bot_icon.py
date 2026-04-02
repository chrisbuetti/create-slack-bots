#!/usr/bin/env python3
"""
Set a Slack bot's profile picture using users.setPhoto.

This requires a User OAuth Token (xoxp-...) with users.profile:write scope.
The token must belong to or act as the bot user.

Usage:
  export SLACK_BOT_TOKEN="xoxb-..."  # Bot token (to get bot user ID)
  export SLACK_USER_TOKEN="xoxp-..." # User token with users.profile:write
  python set_bot_icon.py --image avatar.jpg
  
  Or with just user token:
  python set_bot_icon.py --token xoxp-... --image avatar.jpg
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.request
import urllib.error
import uuid
from pathlib import Path

SLACK_API_BASE = "https://slack.com/api"


def set_photo(token: str, image_path: Path) -> dict:
    """
    Upload a profile photo using users.setPhoto.
    
    Requires a user token (xoxp-) with users.profile:write scope.
    This sets the photo for the user associated with that token.
    """
    if not image_path.is_file():
        print(f"❌ Image file not found: {image_path}")
        sys.exit(1)

    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    boundary = uuid.uuid4().hex
    image_data = image_path.read_bytes()

    # Build multipart form data
    body_parts = []
    
    # Image field
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"'.encode())
    body_parts.append(f"Content-Type: {mime_type}".encode())
    body_parts.append(b"")
    body_parts.append(image_data)
    
    # End boundary
    body_parts.append(f"--{boundary}--".encode())
    
    body = b"\r\n".join(body_parts)

    req = urllib.request.Request(
        f"{SLACK_API_BASE}/users.setPhoto",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        print(f"HTTP {e.code}: {body_text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Set Slack bot profile picture")
    parser.add_argument("--token", help="User OAuth token (xoxp-...) with users.profile:write")
    parser.add_argument("--image", required=True, help="Path to image file (JPG, PNG, GIF)")
    args = parser.parse_args()

    token = args.token or os.environ.get("SLACK_USER_TOKEN")
    
    if not token:
        print("❌ No token provided.")
        print("   Pass --token xoxp-... or set SLACK_USER_TOKEN env var.")
        print("")
        print("   To get a user token for your bot:")
        print("   1. Go to https://api.slack.com/apps/<APP_ID>/oauth")
        print("   2. Add 'users.profile:write' to User Token Scopes")
        print("   3. Reinstall app to workspace")
        print("   4. Copy the 'User OAuth Token' (xoxp-...)")
        sys.exit(1)

    if not token.startswith("xoxp-"):
        print("⚠️  Warning: Token doesn't start with 'xoxp-'")
        print("   users.setPhoto requires a User OAuth Token, not a bot token.")
        print("   Bot tokens (xoxb-) cannot set profile photos.")
        print("")

    image_path = Path(args.image)
    
    print(f"📸 Setting profile photo from: {image_path.name}")
    result = set_photo(token, image_path)
    
    if result.get("ok"):
        print("✅ Profile photo updated successfully!")
        if "profile" in result:
            urls = result["profile"]
            if "image_512" in urls:
                print(f"   Preview: {urls['image_512']}")
    else:
        error = result.get("error", "unknown")
        print(f"❌ Failed: {error}")
        
        if error == "missing_scope":
            print("")
            print("   The token is missing the 'users.profile:write' scope.")
            print("   Add it at: https://api.slack.com/apps/<APP_ID>/oauth")
        elif error == "not_authed":
            print("")
            print("   The token is invalid or expired.")
        elif error == "invalid_auth":
            print("")
            print("   Authentication failed. Check your token.")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
