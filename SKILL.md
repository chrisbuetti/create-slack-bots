---
name: create-slack-bot
description: create, configure, install, and connect a slack bot for an openclaw agent with minimal user interruption. use when the user wants a slack bot created or updated in a specific workspace. once the user provides the target workspace, proceed end to end using the logged-in browser session and local scripts without repeatedly asking for approval, tokens, or manual navigation. only ask for input if the workspace is unavailable in the current browser session, slack authentication blocks progress, or permissions prevent completion.
---

# Create Slack Bot for OpenClaw

Create and configure Slack bot apps for OpenClaw with a browser-first, low-interruption workflow.

## Core Rules

- Assume the browser is already logged in unless evidence shows otherwise.
- Once the user provides the target workspace, continue automatically.
- Do not stop after each step to ask whether to continue.
- Do not ask the user to manually retrieve or paste tokens, secrets, app IDs, client IDs, signing secrets, or similar values if they can be obtained through the browser session, local scripts, or local files.

Only ask the user for input when blocked by one of these conditions:

1. The target workspace is not accessible in the logged-in browser session.
2. Slack requires login or re-authentication.
3. The browser session lacks the required permissions.
4. The target workspace is missing from the original request.

## Required Input

The only required upfront input is:

- the Slack workspace where the bot should be created or updated

Use additional details if provided, but do not require them before starting:

- bot name
- display name
- agent id
- agent name
- model
- icon asset
- workspace path
- whether to connect immediately to OpenClaw

If details are missing, infer sensible defaults and continue.

## Default Workflow

Unless the user explicitly requests otherwise, do all of the following automatically:

1. Create or locate the Slack app in the requested workspace.
2. Apply the full approved scopes and events.
3. Ensure socket mode is enabled.
4. Generate or retrieve the app-level token.
5. Install or reinstall the app to the same workspace.
6. Retrieve the bot token.
7. Remove the Home tab.
8. Set the bot icon if an asset is available.
9. Update local OpenClaw config if the task includes bot connection.
10. Report the final status.

## Local Repo and Tools

Primary scripts (in this repo):

- `create_bot.py` — create a new Slack app with manifest
- `force_god_mode.py` — apply full bot scopes and event subscriptions
- `disable_home_tab.py` — disable the Home tab, enable Messages tab
- `set_bot_icon.py` — set bot icon via CDP browser automation
- `set_icon.py` — alternative icon upload method

Prefer browser automation for:

- workspace selection
- generating config tokens
- generating app-level tokens
- installing the app
- retrieving bot tokens
- removing the Home tab
- uploading the bot icon

Prefer local scripts for:

- manifest creation or update
- scope and event setup
- local config edits
- local service restarts
- icon resizing

Choose the path that minimizes interruption and avoids manual token handoff.

## Workflow

### 1. Resolve workspace and defaults

Read the target workspace from the user's request.

If the user does not specify a bot name, infer one from the request context.

Choose reasonable defaults for missing values. Do not ask the user to confirm defaults unless there is real risk of targeting the wrong workspace or bot.

### 2. Create or locate the Slack app

If the request is for a new bot, create the app in the requested workspace.

If the request is for an existing bot, locate it and continue with the requested updates.

Capture or retrieve these values when available:

- App ID
- Client ID
- Client Secret
- Signing Secret

Read them from script output, browser pages, or local config as appropriate.

### 3. Apply scopes, events, and socket mode

Ensure the app has the required bot scopes and event subscriptions.

Use the approved god-mode configuration when the workflow expects a full-permission bot.

If scopes or events change after installation, automatically reinstall the app.

Ensure socket mode is enabled when required.

### 4. Generate or retrieve the app-level token

Generate an app-level token with `connections:write`.

Capture the `xapp-...` token programmatically.

Do not ask the user to generate it manually unless browser automation is blocked.

### 5. Install the app and retrieve the bot token

Install the app into the same target workspace.

Capture the Bot User OAuth Token programmatically from the browser or reliable local output.

Do not ask the user to paste the `xoxb-...` token if it can be retrieved directly.

### 6. Manage config tokens without user handoff

If Slack config tokens are needed:

1. Obtain them through the browser session when possible.
2. Use them immediately.
3. Save the latest refresh token if rotation-aware automation requires it.
4. Regenerate them through the browser if rotation fails.

Do not make manual token retrieval the default path.

### 7. Configure the App Home correctly

Always do ALL of the following on the App Home page for newly created bots:

1. **Disable the Home tab** (uncheck "Display Home tab") unless the user explicitly asks to keep it.
2. **Keep the Messages tab enabled** ("Display Messages tab" should be checked).
3. **CRITICAL: Check "Allow users to send Slash commands and messages from the messages tab"** — this checkbox is UNCHECKED by default. If you skip this, users will see "Sending messages to this app has been turned off" and cannot DM the bot. This is the #1 most-missed step.

Preferred order:

1. Browser automation
2. Manifest update
3. Local script

At the end of the workflow, explicitly verify that:
- Home tab is disabled
- Messages tab is enabled
- "Allow users to send messages" checkbox is checked

### 8. Set the bot icon (profile picture)

If an icon asset is available, set the icon. The image must be:
- **Square** (512×512 to 2000×2000 pixels)
- PNG, JPG, or GIF format

**Resize if needed:**
```bash
# Resize to 1024x1024 using sips (macOS built-in)
sips -z 1024 1024 /path/to/image.png --out /path/to/image_resized.png

# Check dimensions
sips -g pixelWidth -g pixelHeight /path/to/image.png
```

#### ⚠️ API methods do NOT work

These Slack API methods have been tested and do **not** work for setting app icons:

| Method | Token type | Result |
|---|---|---|
| `apps.icon.set` | Config token (`xoxe.xoxp-`) | `unknown_method` |
| `apps.icon.set` | Bot token (`xoxb-`) | `not_allowed_token_type` |
| `apps.icon.set` | App token (`xapp-`) | `not_allowed_token_type` |
| `users.setPhoto` | Bot token (`xoxb-`) | `not_allowed_token_type` |

`apps.icon.set` is undocumented and returns `unknown_method` regardless of token type. `users.setPhoto` requires a User OAuth Token (`xoxp-`) with `users.profile:write` scope, which bots do not have. **Do not waste time retrying these.**

#### Method: CDP `setFileInputFiles` via managed browser (PROVEN, USE THIS)

This is the only reliable programmatic method. It uses the Chrome DevTools Protocol to inject a file into the hidden `<input type="file">` on the Slack app settings page, then triggers the change event which auto-submits the form.

**Prerequisites:**
- OpenClaw managed browser running (default CDP port 18800)
- Browser already logged into `api.slack.com`
- `websocket-client` Python package installed (`pip3 install websocket-client`)
- Image file on disk, square, 512-2000px

**Step 1: Open the app settings page in the managed browser**

Use the `browser` tool:
```
browser(action="open", url=f"https://api.slack.com/apps/{APP_ID}/general")
```
Wait 3 seconds for the page to load. Confirm the page loaded by taking a screenshot or snapshot.

**Step 2: Upload the icon via CDP `DOM.setFileInputFiles`**

The page has a hidden file input: `<input id="app_icon" type="file" name="icon" accept="image/*" data-drop-zone-input="">`

Do NOT use the browser tool's `upload` action — it cannot resolve local file paths in the managed browser sandbox. Instead, connect to CDP directly via WebSocket:

```python
import json, urllib.request, websocket

# CONFIG — replace with your values
APP_ID = "YOUR_APP_ID"
IMAGE_PATH = "/absolute/path/to/icon.png"
CDP_PORT = 18800  # OpenClaw managed browser CDP port

# 1. Find the browser tab for the app settings page
tabs = json.loads(urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json").read().decode())
target = None
for t in tabs:
    if APP_ID in t.get("url", ""):
        target = t
        break
if not target:
    raise Exception(f"No tab found for app {APP_ID}. Open the page first.")

# 2. Connect to the tab's WebSocket debugger
ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=10, suppress_origin=True)

# Helper: send CDP command and wait for the matching response (skip events)
msg_id = 0
def cdp(method, params=None):
    global msg_id
    msg_id += 1
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == msg_id:
            return resp

# 3. Enable DOM domain and find the file input
cdp("DOM.enable")
doc = cdp("DOM.getDocument")
root_id = doc["result"]["root"]["nodeId"]

node = cdp("DOM.querySelector", {"nodeId": root_id, "selector": "#app_icon"})
node_id = node["result"]["nodeId"]
if not node_id:
    raise Exception("#app_icon input not found on page")

# 4. Inject the file into the input element
result = cdp("DOM.setFileInputFiles", {"files": [IMAGE_PATH], "nodeId": node_id})

# 5. Dispatch 'change' event to trigger the form auto-submission
cdp("Runtime.evaluate", {
    "expression": "document.getElementById('app_icon').dispatchEvent(new Event('change', {bubbles: true}))"
})

ws.close()
print(f"Icon uploaded for app {APP_ID}")
```

**How it works:**
1. `DOM.setFileInputFiles` programmatically sets files on an `<input type="file">` element — equivalent to a user selecting a file via the OS file picker
2. The Slack app settings page has a JavaScript `change` event listener on `#app_icon` that auto-submits the form
3. The page reloads and shows the new icon in the "App icon & Preview" section

**Key technical notes:**
- `suppress_origin=True` is required on the WebSocket connection — without it, the managed browser rejects the CDP connection
- You MUST drain CDP event messages in the recv loop — CDP sends async events between command responses
- The file path must be an **absolute path** accessible to the Chromium process
- Changes propagate to Slack clients within ~1 minute

### 9. Connect the bot to OpenClaw

If the task includes OpenClaw integration, update `~/.openclaw/openclaw.json`.

Add the Slack account entry if it does not already exist:

```json
{
  "channels": {
    "slack": {
      "accounts": {
        "<agent-id>": {
          "name": "<Bot Display Name>",
          "botToken": "xoxb-...",
          "appToken": "xapp-1-...",
          "userTokenReadOnly": true,
          "streaming": "partial",
          "nativeStreaming": true
        }
      }
    }
  }
}
```

If needed, also add or update the agent entry and Slack binding.

Restart the gateway or relevant service if required.

### 10. Summarize the final state

When finished, report:

1. Target workspace
2. App name
3. App ID
4. Whether the app-level token was obtained
5. Whether the bot token was obtained
6. Whether the Home tab was removed
7. Whether the icon was set
8. Whether OpenClaw config was updated
9. Any remaining blockers, if any

## Failure Handling

If blocked, try the next recoverable method before asking the user for help.

Use this escalation order:

1. Retry the automated path.
2. Switch from script to browser.
3. Regenerate credentials through the browser.
4. Ask the user for help only if login, permissions, or workspace access truly block the task.

When asking for user input, ask only for the minimum needed to unblock progress.

## Token Handling Policy

Never ask the user to manually retrieve a Slack config token, refresh token, bot token, or app token if the browser session and local environment can obtain them.

If a refresh token becomes invalid, regenerate credentials through the browser and continue.

Treat manual token handoff as a fallback only when browser-based recovery is impossible.

## Constraints and Known Issues

- Slack config tokens rotate and may invalidate older workflows.
- Slack icon APIs are unreliable — browser upload via CDP is the proven method.
- Scope changes may require reinstall before they take effect.
- Slack app installs are workspace-specific.
- App creation should happen in the intended workspace from the start.
- The "Allow users to send messages" checkbox on App Home is OFF by default — always enable it or users cannot DM the bot.
- Agent-to-Slack bindings go in the top-level `bindings[]` array in `openclaw.json` (NOT under `agents.list[].channels` or `agents.defaults.bindings`).
- Binding format: `{ "agentId": "<id>", "match": { "channel": "slack", "accountId": "<id>" } }`
- Agent subagent allowlists go under `agents.list[].subagents.allowAgents`, NOT under `agents.defaults.subagents`.

## What Not to Do

- Do not tell the user to manually grab tokens if the browser can do it.
- Do not stop after each step to ask whether to continue.
- Do not require the user to supervise routine setup actions one by one.
- Do not ask for values that can be inferred or read from the current environment.
- Do not default to manual token handoff.
- Do not leave the Home tab enabled on a newly created bot unless the user explicitly wants it kept or the workflow is blocked by permissions or authentication.

### 11. Set the bot display name (capitalization)

The `create_bot.py` script sets the bot's display name via `--display-name`, but the Slack bot username is always lowercased internally. If the desired name has specific capitalization (e.g., "Gary" not "gary"), verify and correct it via the Manifest API.

**During creation:**

Pass the correctly-capitalized name via `--display-name "Gary"`. Then verify the manifest was created with the right casing by exporting it (see update flow below).

**After creation (updating an existing bot's display name):**

Use the Manifest API programmatically. Requires a config token (see Token Handling Policy).

```python
import json, urllib.request, urllib.parse

# Config — replace with actual values
APP_ID = "YOUR_APP_ID"
REFRESH_TOKEN = "xoxe-1-..."

# Step 1: Rotate config token
rot_req = urllib.request.Request(
    "https://slack.com/api/tooling.tokens.rotate",
    data=urllib.parse.urlencode({"refresh_token": REFRESH_TOKEN}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST"
)
with urllib.request.urlopen(rot_req) as resp:
    rot = json.loads(resp.read().decode())
token = rot["token"]
new_refresh = rot["refresh_token"]  # SAVE THIS — old one is now invalid

# Step 2: Export current manifest
export_req = urllib.request.Request(
    "https://slack.com/api/apps.manifest.export",
    data=json.dumps({"app_id": APP_ID}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    method="POST"
)
with urllib.request.urlopen(export_req) as resp:
    manifest = json.loads(resp.read().decode())["manifest"]

# Step 3: Update both the app name and bot display name
manifest["display_information"]["name"] = "YourBotName"
manifest["features"]["bot_user"]["display_name"] = "YourBotName"

# Step 4: Push updated manifest
update_req = urllib.request.Request(
    "https://slack.com/api/apps.manifest.update",
    data=json.dumps({"app_id": APP_ID, "manifest": manifest}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    method="POST"
)
with urllib.request.urlopen(update_req) as resp:
    result = json.loads(resp.read().decode())
    # result["ok"] should be True
```

**Key points:**
- `display_information.name` = the app name shown in Slack admin and the app directory
- `features.bot_user.display_name` = the name shown next to bot messages and in DMs — this is what users actually see
- Both fields should match and have the correct capitalization
- Changes take effect within ~1 minute in the Slack UI
- Config tokens rotate on every use — always save the new refresh token from the rotation response
- To obtain a config token programmatically, use the browser tool to navigate to `https://api.slack.com/apps`, hook `document.execCommand` to intercept the copy action, click the "Copy refresh token" button, and read `window._copiedTextExec`
