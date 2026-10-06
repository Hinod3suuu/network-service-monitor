import json
import os
import platform
import subprocess
from datetime import datetime

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv


# Initialize terminal colors and load environment variables
init(autoreset=True)
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def load_targets():
    with open("targets.json", "r", encoding="utf-8") as file:
        return json.load(file)


def check_ping(host):
    # Windows uses -n, while Linux/macOS use -c.
    flag = "-n" if platform.system().lower() == "windows" else "-c"

    result = subprocess.run(
        ["ping", flag, "1", host],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        # Extract latency from the ping output.
        for line in result.stdout.splitlines():
            if "time=" in line.lower() or "time<" in line.lower():
                latency_part = line.lower().split("time")[1].split()[0]
                latency = latency_part.replace("=", "").replace("<", "<")
                return True, latency

        return True, "N/A"

    return False, None


def check_http(url):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def print_status(name, target, success, latency=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if success:
        status = f"{Fore.GREEN}[PASS]{Style.RESET_ALL}"

        if latency:
            print(
                f"[{timestamp}] {status} {name} ({target}) "
                f"is reachable (latency: {latency})."
            )
        else:
            print(
                f"[{timestamp}] {status} {name} ({target}) "
                f"is reachable."
            )

    else:
        status = f"{Fore.RED}[FAIL]{Style.RESET_ALL}"

        print(
            f"[{timestamp}] {status} {name} ({target}) "
            f"is unreachable!"
        )


def send_alert(name, message):
    if not DISCORD_WEBHOOK_URL:
        print(
            f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} "
            "Discord webhook URL is not configured."
        )
        return

    payload = {
        "content": (
            f"🚨 **CRITICAL ALERT**\n"
            f"Service `{name}` is DOWN!\n"
            f"Details: {message}"
        )
    }

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(
            f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} "
            f"Failed to send Discord alert: {error}"
        )


def main():
    targets = load_targets()

    print(
        f"\n{Style.BRIGHT}"
        "=== Network Service Monitor ==="
        f"{Style.RESET_ALL}\n"
    )

    for target in targets:

        if target["type"] == "ping":
            success, latency = check_ping(target["host"])

            print_status(
                target["name"],
                target["host"],
                success,
                latency
            )

            if not success:
                send_alert(
                    target["name"],
                    f"{target['host']} is unreachable."
                )

        elif target["type"] == "http":
            success = check_http(target["url"])

            print_status(
                target["name"],
                target["url"],
                success
            )

            if not success:
                send_alert(
                    target["name"],
                    f"{target['url']} failed the HTTP health check."
                )

    print()


if __name__ == "__main__":
    main()