"""Check the dashboard's layout at real phone and tablet viewports.

The page is one hand-written file with no rendering test, so a layout
regression is invisible to pytest. This drives headless Chrome over the
DevTools protocol, emulates each device properly, and reports the four
faults that make a page unusable on a phone:

* the page scrolling sideways, or an element sitting off the screen
* a control smaller than 44px, which a thumb misses
* a text input under 16px, which makes iOS Safari zoom the whole page
* a form field with no box at all, which a hidden table column causes

Every tab is measured, and a row editor is opened on the tabs that have
one, because an open editor is the widest the page ever gets.

``--window-size`` alone cannot do this job: Chrome clamps its window to
about 500px, so a 320px phone silently measures as 500px.

Usage, against a server already running on the given URL::

    .venv/bin/python scripts/audit_layout.py http://127.0.0.1:8123/
"""

import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request
from typing import Any, Optional

import websockets

DEBUG_PORT = 9333

# Each tab, with the button that opens a row editor on it, where there is one.
TABS = (
    ("overview", None),
    ("accounts", "add-savings"),
    ("accounts", "add-credit-card"),
    ("pensions", "add-pension"),
    ("income", "add-income"),
    ("expenses", "add-monthly-expense"),
    ("expenses", "add-yearly-expense"),
    ("history", None),
)
TAP_TARGET_MINIMUM_PIXELS = 44
IOS_ZOOM_THRESHOLD_PIXELS = 16
SETTLE_SECONDS = 4.5

DEVICES = (
    ("iPhone SE", 320, 568, 2),
    ("iPhone 12 mini", 360, 780, 3),
    ("iPhone 14", 390, 844, 3),
    ("iPhone 14 Pro Max", 430, 932, 3),
    ("iPhone 14 landscape", 844, 390, 3),
    ("iPad mini", 744, 1133, 2),
)

PROBE = """
(() => {
    const width = window.innerWidth;
    const doc = document.documentElement;
    const faults = [];
    const describe = (node) => {
        const panel = node.closest(".tab-panel");
        const text = (node.textContent || "").trim().slice(0, 20).replace(/\\s+/g, " ");
        return node.tagName.toLowerCase() + (node.id ? "#" + node.id : "")
            + "[" + (panel ? panel.id : "header") + "]"
            + (text ? " '" + text + "'" : "");
    };
    // Only what the reader can actually see: the open tab, the page furniture
    // around it, and any dialog that is open.
    const shown = (node) => node.offsetParent !== null
        || window.getComputedStyle(node).position === "fixed";
    const roots = [document.querySelector(".tab-panel.active"), document.querySelector("header"),
        document.getElementById("summary"), document.querySelector(".tabs"),
        ...document.querySelectorAll("dialog[open]")].filter(Boolean);
    const visible = (selector) => roots
        .flatMap((root) => [...root.querySelectorAll(selector)])
        .filter(shown);
    if (doc.scrollWidth > doc.clientWidth + 1) {
        faults.push("the page scrolls sideways: " + doc.scrollWidth
            + " wide in " + doc.clientWidth);
    }
    visible("*").forEach((node) => {
        const box = node.getBoundingClientRect();
        if (box.width === 0 && box.height === 0) { return; }
        if (box.right > width + 1 || box.left < -1) {
            faults.push("off the screen: " + describe(node));
        }
    });
    visible(".table-wrap").forEach((node) => {
        if (node.scrollWidth > node.clientWidth + 1) {
            faults.push("content wider than its card: " + describe(node)
                + " " + node.scrollWidth + " in " + node.clientWidth);
        }
    });
    visible("button, input, select, summary").forEach((node) => {
        const box = node.getBoundingClientRect();
        const font = parseFloat(window.getComputedStyle(node).fontSize);
        if (box.width === 0 && box.height === 0) {
            faults.push("field with no box at all: " + describe(node));
            return;
        }
        const label = node.type === "checkbox" && node.closest("label")
            ? node.closest("label").getBoundingClientRect() : box;
        if (label.height < %(tap)d || label.width < 30) {
            faults.push("target too small to tap: " + describe(node) + " "
                + label.width.toFixed(0) + "x" + label.height.toFixed(0));
        }
        const typed = ["INPUT", "SELECT", "TEXTAREA"].includes(node.tagName);
        if (typed && node.type !== "checkbox" && font < %(zoom)d) {
            faults.push("iOS will zoom on focus: " + describe(node)
                + " at " + font + "px");
        }
    });
    return faults;
})()
"""


def _start_chrome() -> subprocess.Popen:
    """Launch a headless browser with the DevTools protocol open."""
    result = subprocess.Popen(
        [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--remote-debugging-port={DEBUG_PORT}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result


def _wait_for_page() -> Optional[str]:
    """Give the debugger address of the first page, once it answers."""
    found: Optional[str] = None
    for _ in range(40):
        if found is None:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{DEBUG_PORT}/json/list"
                ) as handle:
                    pages = [
                        page for page in json.load(handle) if page["type"] == "page"
                    ]
                found = pages[0]["webSocketDebuggerUrl"] if pages else None
            except Exception:  # noqa: BLE001 - the browser is still starting
                time.sleep(0.25)
    return found


class Session:
    """One DevTools protocol conversation with the browser."""

    def __init__(self, socket: Any) -> None:
        self._socket = socket
        self._sent = 0

    async def send(self, method: str, params: Optional[dict] = None) -> dict:
        """Send one command and wait for the reply that matches it."""
        self._sent = self._sent + 1
        identifier = self._sent
        await self._socket.send(
            json.dumps({"id": identifier, "method": method, "params": params or {}})
        )
        reply: Optional[dict] = None
        while reply is None:
            message = json.loads(await self._socket.recv())
            if message.get("id") == identifier:
                reply = message
        return reply

    async def evaluate(self, expression: str) -> Any:
        """Run an expression in the page and give back its value."""
        reply = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
        return reply.get("result", {}).get("result", {}).get("value")


def _open_tab_script(tab: str, opener: Optional[str]) -> str:
    """Give the script that shows one tab with its editor open, if it has one."""
    click = f"document.getElementById('{opener}').click();" if opener else ""
    return f"(() => {{ activateTab('{tab}'); {click} return true; }})()"


async def _measure_tab(session: Session, tab: str, opener: Optional[str]) -> list[str]:
    """Report the layout faults on one tab, with its editor open."""
    await session.evaluate(_open_tab_script(tab, opener))
    await asyncio.sleep(0.6)
    faults = await session.evaluate(
        PROBE % {"tap": TAP_TARGET_MINIMUM_PIXELS, "zoom": IOS_ZOOM_THRESHOLD_PIXELS}
    )
    named = [f"{tab}: {fault}" for fault in faults or []]
    await session.evaluate("(() => { location.reload(); return true; })()")
    await asyncio.sleep(SETTLE_SECONDS)
    return named


async def _audit_device(
    session: Session, url: str, device: tuple, shot_directory: Optional[str]
) -> list[str]:
    """Load the page as one device and report what is wrong with it."""
    name, width, height, scale = device
    await session.send(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": scale,
            "mobile": True,
        },
    )
    await session.send(
        "Emulation.setTouchEmulationEnabled",
        {"enabled": True, "maxTouchPoints": 5},
    )
    await session.send("Page.navigate", {"url": url})
    await asyncio.sleep(SETTLE_SECONDS)
    faults: list[str] = []
    for tab, opener in TABS:
        faults = faults + await _measure_tab(session, tab, opener)
    if shot_directory is not None:
        await session.evaluate(_open_tab_script("pensions", "add-pension"))
        await asyncio.sleep(0.6)
        reply = await session.send("Page.captureScreenshot", {"format": "png"})
        path = f"{shot_directory}/{name.replace(' ', '-').lower()}.png"
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(reply["result"]["data"]))
    return faults


async def _audit(url: str, shot_directory: Optional[str]) -> int:
    """Audit every device and report how many faults were found."""
    chrome = _start_chrome()
    total = 0
    try:
        address = _wait_for_page()
        if address is None:
            print("Could not reach the browser's debugger.")
            total = 1
        else:
            async with websockets.connect(address, max_size=60_000_000) as socket:
                session = Session(socket)
                await session.send("Page.enable")
                await session.send("Runtime.enable")
                for device in DEVICES:
                    faults = await _audit_device(session, url, device, shot_directory)
                    label = f"{device[0]} {device[1]}x{device[2]}"
                    if faults:
                        print(f"{label}: {len(faults)} faults")
                        for fault in faults:
                            print(f"  {fault}")
                    else:
                        print(f"{label}: clean")
                    total = total + len(faults)
    finally:
        chrome.kill()
    return total


def main() -> int:
    """Audit the given URL and return a process exit code."""
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8123/"
    shots = sys.argv[2] if len(sys.argv) > 2 else None
    faults = asyncio.run(_audit(url, shots))
    print(f"\n{faults} faults in total.")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
