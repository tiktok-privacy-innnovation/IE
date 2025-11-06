# ig_check.py
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests

USERNAME = os.getenv("TARGET_USERNAME", "target_username_here")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

OUT_DIR = "snapshots"
os.makedirs(OUT_DIR, exist_ok=True)

def send_discord_file(webhook_url, file_path, message=""):
    if not webhook_url:
        print("No Discord webhook configured, skipping send.")
        return False
    try:
        with open(file_path, "rb") as f:
            # Discord accepts multipart/form-data with 'file' and 'payload_json' or 'content'
            data = {"content": message}
            files = {"file": f}
            resp = requests.post(webhook_url, data=data, files=files, timeout=30)
        print("Discord response:", resp.status_code, resp.text)
        return resp.ok
    except Exception as e:
        print("Failed sending to Discord:", e)
        return False

def check_and_screenshot(username):
    url = f"https://www.instagram.com/{username}/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print("Navigation error:", e)
            browser.close()
            return False
        page.wait_for_timeout(2000)
        text = page.content().lower()
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"{OUT_DIR}/{username}_{timestamp}.png"

        if "this account is private" in text:
            print(f"[{timestamp}] Account is still private.")
            browser.close()
            return False

        # detect simple login wall patterns
        if ("log in to see" in text) or (("to continue" in text) and ("login" in text)):
            print(f"[{timestamp}] Possibly login wall or Instagram blocking - uncertain.")
            browser.close()
            return False

        # otherwise assume public; take screenshot and notify
        page.screenshot(path=filename, full_page=True)
        print(f"[{timestamp}] Account appears public — screenshot saved to {filename}")

        message = f"📣 Instagram @{username} appears **PUBLIC** as of {timestamp} UTC"
        ok = send_discord_file(DISCORD_WEBHOOK, filename, message=message)
        browser.close()
        return ok

if __name__ == "__main__":
    usr = os.getenv("TARGET_USERNAME", USERNAME)
    check_and_screenshot(usr)
