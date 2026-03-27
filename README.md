# create-slack-bots

Create, update, and manage Slack bot apps entirely from the command line — no clicking
through the Slack admin UI.

Uses the [Slack App Manifest API](https://api.slack.com/reference/manifests) to programmatically
create and update fully-configured apps with bot users, OAuth scopes, event subscriptions,
and Socket Mode in a single command.

## Why?

Setting up a Slack app through the web UI means clicking through a dozen pages every time.
This script turns that into one command: define your config, run it, get credentials back.
Need to change something later? Update it the same way — no UI required.

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
python create_bot.py --name "My Bot"
```

That's it. The script rotates your config token, validates the manifest, creates the app,
and prints the credentials you need.

## CLI Options

```
python create_bot.py [options]

Options:
  --app-id ID           Target an existing app to update (omit to create new)
  --export              Export an app's current manifest (use with --app-id)
  --name NAME           App name shown in Slack (default: "My Custom Bot")
  --display-name NAME   Bot @username in conversations
  --description TEXT    Short app description
  --icon PATH           Path to an image file to use as the app icon
  --no-socket-mode      Use HTTP request URLs instead of Socket Mode
  --request-url URL     Events/interactivity URL (with --no-socket-mode)
  --dry-run             Print the manifest JSON and exit — nothing is created/updated
  -h, --help            Show help
```

### Creating Apps

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

### Updating Existing Apps

Pass `--app-id` to target an existing app. The script exports its current manifest,
applies only the fields you specify, and pushes the update — so you don't have to
redefine everything.

```bash
# Rename an app
python create_bot.py --app-id A0123ABCDEF --name "New Name"

# Update the description and icon
python create_bot.py --app-id A0123ABCDEF --description "Does deploys" --icon new_icon.png

# Preview what would change without applying
python create_bot.py --app-id A0123ABCDEF --name "New Name" --dry-run
```

### Exporting Manifests

Dump the current manifest of any app you own — useful for inspection or backup.

```bash
python create_bot.py --app-id A0123ABCDEF --export
```

## How It Works

### Create Flow

1. **Rotates your config token** — Slack config tokens expire every 12 hours; the script
   handles this automatically and prints the new refresh token.
2. **Builds an app manifest** — Declarative JSON that defines scopes, events, features,
   and bot user configuration.
3. **Validates the manifest** — Catches errors before creation via `apps.manifest.validate`.
4. **Creates the app** — Calls `apps.manifest.create` and returns your new app's credentials
   (Client ID, Client Secret, Signing Secret).
5. **Sets the app icon** (optional) — Uploads a profile picture via `apps.icon.set`.

### Update Flow

1. **Rotates your config token**
2. **Exports the current manifest** — Fetches the app's live config via `apps.manifest.export`.
3. **Applies your changes** — Only the fields you specified via CLI flags are patched in;
   everything else stays untouched.
4. **Shows a diff** — Prints exactly what changed before proceeding.
5. **Validates and updates** — Pushes the merged manifest via `apps.manifest.update`.
6. **Sets the app icon** (optional)

## After Creation

The script prints next steps, but in short:

1. Go to your app at `https://api.slack.com/apps/<APP_ID>`
2. If using Socket Mode: generate an **App-Level Token** with `connections:write` scope
3. **Install the app** to your workspace using the OAuth URL printed by the script
4. Grab your **Bot User OAuth Token** (`xoxb-...`) from OAuth & Permissions

## Customization

Edit the `BotConfig` dataclass in `create_bot.py` to change defaults for new apps:

- **`bot_scopes`** — OAuth permission scopes ([full list](https://api.slack.com/scopes))
- **`bot_events`** — Event subscriptions ([full list](https://api.slack.com/events))
- **`slash_commands`** — Register slash commands at creation time
- **`socket_mode`** — Toggle between Socket Mode and HTTP request URLs

## Requirements

- Python 3.10+
- No third-party dependencies — uses only the standard library

## License

MIT
