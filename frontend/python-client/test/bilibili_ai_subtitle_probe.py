"""
Probe Bilibili AI subtitle responses with Playwright.

Install dependencies before running:
    pip install playwright
    python -m playwright install chromium

Run from the repository root:
    python frontend\\python-client\\test\\bilibili_ai_subtitle_probe.py
"""

from __future__ import annotations

import base64
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


AI_SUBTITLE_URL_MARKERS = (
    "aisubtitle.hdslb.com/bfs/ai_subtitle/",
    "aisubtitle.hdslb.com",
    "ai_subtitle",
)
DEFAULT_TIMEOUT_MS = 30_000
CAPTURE_WAIT_SECONDS = 20
DIRECT_FETCH_TIMEOUT_SECONDS = 15
MAX_RETRY_ATTEMPTS = 3


def repo_python_client_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def prompt_url() -> str:
    print("Paste a Bilibili video URL and press Enter.")
    print(
        "Example: https://www.bilibili.com/video/BV1qG41197E4/"
        "?spm_id_from=333.788.videopod.episodes&vd_source=5256fff615db9842220a8db3a337b9db&p=7"
    )
    url = input("> ").strip()
    if not url:
        raise ValueError("Video URL is required.")
    return url


def is_ai_subtitle_url(url: str) -> bool:
    return any(marker in url for marker in AI_SUBTITLE_URL_MARKERS)


def wait_and_click_first(page, selectors: list[str], description: str) -> str:
    last_error: Optional[Exception] = None
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            locator.click(timeout=DEFAULT_TIMEOUT_MS)
            print(f"[click] {description}: {selector}")
            return selector
        except PlaywrightError as exc:
            last_error = exc

    raise RuntimeError(f"Could not click {description}. Last error: {last_error}")


def reveal_player_controls(page) -> None:
    hover_selectors = [
        ".bpx-player-video-area",
        ".bpx-player-container",
        "#bilibili-player",
        "video",
        "body",
    ]
    for selector in hover_selectors:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=5_000)
            locator.hover(timeout=5_000)
            print(f"[hover] {selector}")
            time.sleep(0.5)
            return
        except PlaywrightError:
            continue

    print("[warn] Could not hover a known player area; continuing anyway.")


def click_subtitle_language(page) -> None:
    language_selectors = [
        ".bpx-player-ctrl-subtitle-language-item[data-lan]:not(.bpx-state-active)",
        ".bpx-player-ctrl-subtitle-language-item[data-lan]",
        ".bpx-player-ctrl-subtitle-language-item",
    ]
    wait_and_click_first(page, language_selectors, "subtitle language item")


def open_subtitle_menu_and_select_language(page) -> None:
    reveal_player_controls(page)
    wait_and_click_first(
        page,
        [
            ".bpx-player-ctrl-subtitle",
            "[class*='player'][class*='subtitle']",
            "[aria-label*='subtitle' i]",
        ],
        "subtitle button",
    )
    click_subtitle_language(page)


def wait_for_capture(captured_body: dict[str, Optional[str]]) -> bool:
    deadline = time.time() + CAPTURE_WAIT_SECONDS
    while time.time() < deadline and not captured_body["body"]:
        time.sleep(0.25)
    return bool(captured_body["body"])


def print_capture_help() -> None:
    print()
    print("[miss] No AI subtitle response was captured.")
    print("Possible causes:")
    print("- The current part has no AI subtitle.")
    print("- The browser profile is not logged in to Bilibili.")
    print("- Bilibili changed the player subtitle selectors.")
    print("- The player did not finish loading or the video is blocked.")
    print("- The subtitle was already enabled and no new request was triggered.")
    print("- A service worker or cache served the response before the listener saw it.")
    print()
    print("If the browser is not logged in, log in inside the opened browser window.")
    print("This script uses its own persistent profile, so that login is kept for later runs.")


def load_video_page(page, video_url: str) -> None:
    try:
        print(f"[open] {video_url}")
        page.goto(video_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        print("[warn] Page did not reach networkidle in time; continuing with current page state.")


def print_captured_body(
    url: str,
    body: str,
    captured_body: dict[str, Optional[str]],
    source: str,
) -> None:
    if captured_body["body"]:
        return

    captured_body["url"] = url
    captured_body["body"] = body
    print(f"\n[capture:{source}] {url}")
    print()
    print(body)
    print()
    print("[success] AI subtitle response body printed above.")


def fetch_subtitle_url_directly(url: str, referer: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Referer": referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(request, timeout=DIRECT_FETCH_TIMEOUT_SECONDS) as response:
        raw_body = response.read()

    return raw_body.decode("utf-8", errors="replace")


def install_network_listeners(context, page, captured_body: dict[str, Optional[str]]) -> None:
    fetched_urls: set[str] = set()

    def on_request(request) -> None:
        if is_ai_subtitle_url(request.url):
            print(f"[request] {request.method} {request.url}")
            if captured_body["body"] or request.url in fetched_urls:
                return

            fetched_urls.add(request.url)
            try:
                body = fetch_subtitle_url_directly(request.url, page.url)
            except (urllib.error.URLError, TimeoutError, PlaywrightError, OSError) as exc:
                print(f"[direct-fetch-error] {exc}")
                return

            print_captured_body(request.url, body, captured_body, "direct-fetch")

    def on_response(response) -> None:
        if not is_ai_subtitle_url(response.url):
            return

        print(f"[response] {response.status} {response.url}")
        try:
            body = response.text()
        except PlaywrightError as exc:
            body = f"<failed to read response body through Playwright response: {exc}>"

        print_captured_body(response.url, body, captured_body, "playwright")

    context.on("request", on_request)
    context.on("response", on_response)
    page.on("request", on_request)
    page.on("response", on_response)

    cdp_request_urls: dict[str, str] = {}
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})

    def on_cdp_response_received(params) -> None:
        response = params.get("response", {})
        url = response.get("url", "")
        if not is_ai_subtitle_url(url):
            return

        request_id = params.get("requestId")
        if request_id:
            cdp_request_urls[request_id] = url
        print(f"[cdp-response] {response.get('status')} {url}")

    def on_cdp_loading_finished(params) -> None:
        request_id = params.get("requestId")
        url = cdp_request_urls.pop(request_id, None)
        if not url or captured_body["body"]:
            return

        try:
            result = cdp.send("Network.getResponseBody", {"requestId": request_id})
            body = result.get("body", "")
            if result.get("base64Encoded"):
                body = base64.b64decode(body).decode("utf-8", errors="replace")
        except PlaywrightError as exc:
            body = f"<failed to read response body through CDP: {exc}>"

        print_captured_body(url, body, captured_body, "cdp")

    cdp.on("Network.responseReceived", on_cdp_response_received)
    cdp.on("Network.loadingFinished", on_cdp_loading_finished)


def main() -> int:
    try:
        video_url = prompt_url()
    except ValueError as exc:
        print(f"[error] {exc}")
        return 1

    profile_dir = repo_python_client_dir() / ".playwright-bilibili-profile"
    captured_body: dict[str, Optional[str]] = {"url": None, "body": None}

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            channel="msedge",
            user_data_dir=str(profile_dir),
            headless=False,
            service_workers="block",
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        install_network_listeners(context, page, captured_body)
        load_video_page(page, video_url)

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            if attempt > 1:
                print(f"[retry] Attempt {attempt}/{MAX_RETRY_ATTEMPTS}")
                load_video_page(page, video_url)

            try:
                open_subtitle_menu_and_select_language(page)
            except Exception as exc:
                print(f"[error] Failed to open/select subtitle menu: {exc}")

            if wait_for_capture(captured_body):
                break

            print_capture_help()
            if attempt >= MAX_RETRY_ATTEMPTS:
                break

            answer = input(
                "\nLog in or adjust the page in the opened browser, then press Enter to retry "
                "(type q to stop retrying): "
            ).strip()
            if answer.lower() == "q":
                break

        input("\nPress Enter to close the browser...")
        context.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
