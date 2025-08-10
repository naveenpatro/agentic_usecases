# meeting.py
import os
import asyncio
from pyppeteer import launch
from urllib.parse import quote_plus

class JitsiMeeting:
    def __init__(self, jitsi_base: str = "https://meet.jit.si"):
        self.jitsi_base = jitsi_base.rstrip("/")

    def room_url(self, room_name: str) -> str:
        # We add config params to start muted and hidden display name handled later with JS.
        # We'll add a query param so user sees appropriate muted default.
        qp = "?config.startWithAudioMuted=true&config.startWithVideoMuted=true"
        return f"{self.jitsi_base}/{quote_plus(room_name)}{qp}"

    async def start_bot_and_hold(self, room_name: str, display_name: str = "IncidentBot"):
        """
        Launch headless Chromium, join the Jitsi room, keep it running.
        The browser runs headless and mutes audio/video via Jitsi config + page JS.
        """
        url = self.room_url(room_name)
        print(f"[Jitsi] Launching headless browser for {url}")
        # Launch browser
        browser = await launch({
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
            ],
            "ignoreHTTPSErrors": True
        })

        page = await browser.newPage()
        # Increase timeout
        page.setDefaultNavigationTimeout(60000)

        # Intercept console logs from page to our stdout (optional)
        page.on("console", lambda msg: print(f"[Browser Console] {msg.text}"))

        await page.goto(url)

        # Wait for jitsi to load and set display name & mute
        # This script tries to set the display name and mute. It might need small tweaks if Jitsi UI changes.
        await asyncio.sleep(3)
        try:
            # set display name via localStorage and reload (Jitsi stores display name in localStorage)
            await page.evaluate(f"""() => {{
                try {{
                    localStorage.setItem('displayname', "{display_name}");
                    localStorage.setItem('deviceAvailability', JSON.stringify({{'audio':false,'video':false}}));
                }} catch(e) {{ console.log('localstorage set failed', e); }}
            }}""")
            await page.reload()
            await asyncio.sleep(2)
        except Exception as e:
            print("[Jitsi] set display name failed:", e)

        # Ensure audio/video are muted (attempt UI toggle to be safe)
        try:
            # Try to click mute buttons if found (selectors may vary)
            await page.evaluate("""
                () => {
                    // Try to mute audio and video using Jitsi's external API if available
                    if (window.JitsiMeetExternalAPI) {
                        // not in iframe mode on meet.jit.si; skip.
                    }
                    // fallback: click mute buttons by aria-label
                    const btns = document.querySelectorAll('[aria-label]');
                    btns.forEach(b => {
                        const al = b.getAttribute('aria-label') || '';
                        if (/microphone/i.test(al) && /mute/i.test(al)) {
                            b.click();
                        }
                        if (/camera/i.test(al) && /mute/i.test(al)) {
                            b.click();
                        }
                    });
                }
            """)
        except Exception as e:
            print("[Jitsi] mute buttons click attempt failed:", e)

        print(f"[Jitsi] Bot joined room {room_name}. Holding connection...")

        # Hold the browser open until the process is stopped externally
        # Use a very long sleep loop and handle cancellation
        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            print("[Jitsi] Bot task cancelled; closing browser...")
        finally:
            await browser.close()
