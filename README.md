# create-slack-bots

Create Slack bot apps entirely from the command line — no clicking through the Slack admin UI.

Uses the [Slack App Manifest API](https://api.slack.com/reference/manifests) to programmatically
create fully-configured apps with bot users, OAuth scopes, event subscriptions, and Socket Mode
in a single command.

## Why?

Setting up a Slack app through the web UI means clicking through a dozen pages every time.
This script turns that into one command: define your config, run it, get credentials back.

## Quick Start

**1. Get your config tokens**

Go to [api.slack.com/apps](https://api.slack.com/apps), scroll to **"Your App Configuration Tokens"**,
click **"Generate Token"**, and select your workspace. You'll get an Access Token and a Refresh Token.

**2. Set credentials**

```bash
# Option A: environment variables
export SLACK_CONFIG_TOKEN="xoxe.xoxp-..."
export SLACK_CONFIG_REFRESH_TOKEN="xoxe-..."

# Option B: .env file (auto-loaded)
cp .env.example .env
# edit .env with your tokens
```

**3. Create a bot**

```bash
python create_bot.py
```

That's it. The script rotates your config token, validates the manifest, creates the app,
and prints the credentials you need.

## CLI Options

```
python create_bot.py [options]

Options:
  --name NAME           App name shown in Slack (default: "My Custom Bot")
  --display-name NAME   Bot @username in conversations
  --description TEXT    Short app description
  --icon PATH           Path to an image file to use as the app icon
  --no-socket-mode      Use HTTP request URLs instead of Socket Mode
  --request-url URL     Events/interactivity URL (with --no-socket-mode)
  --dry-run             Print the manifest JSON and exit — nothing is created
  -h, --help            Show help
```

### Examples

```bash
# Create with a custom name
python create_bot.py --name "Deploy Bot"

# Set a profile picture
python create_bot.py --name "Deploy Bot" --icon avatar.png

# Preview the manifest without creating anything
python create_bot.py --name "Test Bot" --dry-run

# Create an HTTP-mode bot (no Socket Mode)
python create_bot.py --name "Webhook Bot" --no-socket-mode --request-url "https://example.com/slack/events"
```

## What It Does

1. **Rotates your config token** — Slack config tokens expire every 12 hours; the script
   handles this automatically and prints the new refresh token.
2. **Builds an app manifest** — Declarative JSON that defines scopes, events, features,
   and bot user configuration.
3. **Validates the manifest** — Catches errors before creation via `apps.manifest.validate`.
4. **Creates the app** — Calls `apps.manifest.create` and returns your new app's credentials
   (Client ID, Client Secret, Signing Secret).
5. **Sets the app icon** (optional) — Uploads a profile picture via `apps.icon.set`.

## After Creation

The script prints next steps, but in short:

1. Go to your app at `https://api.slack.com/apps/<APP_ID>`
2. If using Socket Mode: generate an **App-Level Token** with `connections:write` scope
3. **Install the app** to your workspace using the OAuth URL printed by the script
4. Grab your **Bot User OAuth Token** (`xoxb-...`) from OAuth & Permissions

## Customization

Edit the `BotConfig` dataclass in `create_bot.py` to change defaults:

- **`bot_scopes`** — OAuth permission scopes ([full list](https://api.slack.com/scopes))
- **`bot_events`** — Event subscriptions ([full list](https://api.slack.com/events))
- **`slash_commands`** — Register slash commands at creation time
- **`socket_mode`** — Toggle between Socket Mode and HTTP request URLs

## Requirements

- Python 3.10+
- No third-party dependencies — uses only the standard library

## License

MIT
