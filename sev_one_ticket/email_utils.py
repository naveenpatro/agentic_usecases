# email_utils.py
import smtplib
import os
from email.message import EmailMessage
from email.utils import formataddr
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime
import pytz
import uuid

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
FROM_NAME = os.environ.get("FROM_NAME", "Incident Bot")

def create_ics(subject, start_dt, end_dt, organizer_name, organizer_email, attendees_emails, location, uid=None):
    """
    Build an ICS calendar invite as bytes. Uses UTC times.
    """
    cal = Calendar()
    cal.add('prodid', '-//Incident Bot//example.com//')
    cal.add('version', '2.0')
    event = Event()
    event.add('summary', subject)
    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)
    event.add('dtstamp', datetime.utcnow())
    event.add('location', vText(location))
    uid = uid or str(uuid.uuid4())
    event.add('uid', uid)
    # organizer
    organizer = vCalAddress(f"MAILTO:{organizer_email}")
    organizer.params['cn'] = vText(organizer_name)
    organizer.params['role'] = vText('CHAIR')
    event['organizer'] = organizer

    for a in attendees_emails:
        attendee = vCalAddress(f"MAILTO:{a}")
        attendee.params['cn'] = vText(a)
        attendee.params['ROLE'] = vText('REQ-PARTICIPANT')
        event.add('attendee', attendee, encode=0)
    cal.add_component(event)
    return cal.to_ical()

def send_email(subject, body, recipients, attachments=None, from_name=None):
    """
    Send a simple email with optional attachments (list of tuples (filename, bytes))
    via SMTP.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[Email] SMTP credentials not set. Skipping send.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = formataddr((from_name or FROM_NAME, SMTP_USER))
    msg['To'] = ", ".join(recipients)
    msg.set_content(body)

    # Attach files
    if attachments:
        for fn, content, mimetype in attachments:
            maintype, subtype = mimetype.split("/", 1)
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=fn)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    print(f"[Email] Sent to {recipients} via {SMTP_HOST}:{SMTP_PORT}")

def send_invites_with_ics(subject, body, attendees, start, end, location, organizer_name):
    """
    Build ICS and send to attendees. start/end are timezone-aware datetimes.
    We'll use SMTP to send invite with ICS attachment; recipients can add to calendar.
    """
    organizer_email = SMTP_USER
    ics = create_ics(
        subject=subject,
        start_dt=start,
        end_dt=end,
        organizer_name=organizer_name,
        organizer_email=organizer_email,
        attendees_emails=attendees,
        location=location
    )
    attachments = [("invite.ics", ics, "text/calendar")]
    send_email(subject=subject, body=body, recipients=attendees, attachments=attachments, from_name=organizer_name)
