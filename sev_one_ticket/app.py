# app.py
import os
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from agents import IncidentResponderAgent
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Sev1 -> Jitsi Agent Simulator")

# instantiate the single responder agent (shared)
responder = IncidentResponderAgent()

class TicketPayload(BaseModel):
    ticket_id: str
    severity: int
    summary: str
    reporter_email: str = None

@app.on_event("startup")
async def startup_event():
    # start any background tasks the agent needs (none for now)
    print("Starting app and agent ready.")

@app.post("/ticket")
async def create_ticket(payload: TicketPayload, background: BackgroundTasks):
    """
    Simulated ticket webhook endpoint.
    POST JSON example:
    {
      "ticket_id": "INC1234",
      "severity": 1,
      "summary": "DB cluster down",
      "reporter_email": "oncall@example.com"
    }
    """
    # For Sev-1 only
    if payload.severity == 1:
        # run incident responder in background
        background.add_task(responder.handle_incident, payload.dict())
        return {"status": "accepted", "message": "Sev-1 received, agent triggered."}
    else:
        return {"status": "ignored", "message": "Only Sev-1 triggers meeting."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
