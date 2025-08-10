# agents.py
import os
import asyncio
import secrets
from meeting import JitsiMeeting
from email_utils import send_invites_with_ics
from typing import Dict

JITSI_BASE = os.environ.get("JITSI_BASE", "https://meet.jit.si")
DEV_EMAILS = [e.strip() for e in os.environ.get("DEV_EMAILS", "").split(",") if e.strip()]
FROM_NAME = os.environ.get("FROM_NAME", "Incident Bot")
BOT_DISPLAY_NAME = os.environ.get("BOT_DISPLAY_NAME", "IncidentBot")

class IncidentResponderAgent:
    """
    Lightweight agent that responds to Sev-1 tickets.
    Steps:
      - build Jitsi room url
      - start Bot join (headless) in background
      - send invites (email + ics)
    """
    def __init__(self):
        self.jitsi = JitsiMeeting(jitsi_base=JITSI_BASE)
        # track bot tasks by ticket id
        self.bot_tasks: Dict[str, asyncio.Task] = {}

    async def handle_incident(self, payload: dict):
        ticket_id = payload.get("ticket_id")
        summary = payload.get("summary", "")
        reporter = payload.get("reporter_email")
        print(f"[Responder] Handling Sev-1 {ticket_id}: {summary}")

        # 1) create a deterministic but unique room name
        room_name = f"{ticket_id}-{secrets.token_hex(4)}"
        url = self.jitsi.room_url(room_name)

        # 2) start headless bot to join (background)
        print(f"[Responder] Starting bot for room {room_name} -> {url}")
        bot_task = asyncio.create_task(self.jitsi.start_bot_and_hold(room_name, display_name=BOT_DISPLAY_NAME))
        self.bot_tasks[ticket_id] = bot_task

        # 3) send invites via email with a calendar invite (ICS)
        # recipients: developers + optional reporter
        recipients = list(DEV_EMAILS)
        if reporter:
            recipients.append(reporter)

        if not recipients:
            print("[Responder] Warning: no recipients configured; no invites sent.")
        else:
            subject = f"[SEV-1] {ticket_id}: {summary}"
            body = f"A Sev-1 incident was opened: {ticket_id}\n\nJoin meeting: {url}\n\nThe bot has joined the meeting; please click the link to join."
            # Create simple 30-min event starting now
            from datetime import datetime, timedelta, timezone
            start = datetime.now(timezone.utc)
            end = start + timedelta(minutes=30)
            print(f"[Responder] Sending invites to {recipients}")
            send_invites_with_ics(
                subject=subject,
                body=body,
                attendees=recipients,
                start=start,
                end=end,
                location=url,
                organizer_name=FROM_NAME
            )

        # Note: we do not wait for the bot task to finish here; it will hold the meeting open.
        print(f"[Responder] Completed triggering actions for {ticket_id}.")
