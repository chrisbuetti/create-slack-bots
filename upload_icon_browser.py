import sys, json, os, urllib.request, urllib.parse, mimetypes, uuid

# Get cookie from env
cookie = os.environ.get('SLACK_COOKIE', '')
if not cookie:
    print("SLACK_COOKIE not set")
    sys.exit(1)

# We need the boot_data from the page to get the api_token
# But since we have a browser session, maybe we can just make the request from within the browser?
