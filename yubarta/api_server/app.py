# """
# FastAPI Application - Yubarta's main API server.

# This file defines all the API endpoints for receiving events, querying alarms,
# and executing remediations.
# """

# import json
# from typing import List, Optional

# import uvicorn
# from fastapi import FastAPI, HTTPException, Query
# from pydantic import BaseModel, Field

# # Modular Imports
# from src.ai_engine.diagnosis import get_ai_diagnosis
# from src.database.sqlite_db import db_manager
# from src.remediators.shell_remediator import execute_command

# # --- Pydantic Models for API requests/responses ---
# class EventModel(BaseModel):
#     source: str
#     timestamp: float
#     metric_name: str
#     value: str or float
#     labels: dict = {}

# class RemediationRequestModel(BaseModel):
#     event_id: int
#     command: str

# # --- FastAPI App Instance ---
# app = FastAPI(
#     title="Yubarta Auto-Remediation API",
#     description="API for managing monitoring events and executing remediations.",
#     version="1.0.0",
# )

# @app.on_event("startup")
# def on_startup():
#     """Initialize the database when the API starts."""
#     db_manager.initialize()

# # --- API Endpoints ---
# @app.post("/api/v1/events/new", status_code=202, summary="Submit a new monitoring event")
# async def submit_new_event(events: List[EventModel]):
#     """
#     Receives one or more monitoring events from collectors, validates them,
#     and stores them in the database for later evaluation.
#     """
#     try:
#         event_ids = [db_manager.add_event(event.dict()) for event in events]
#         return {"message": "Events accepted", "event_ids": event_ids}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to process events: {e}")

# @app.get("/api/v1/alarms", summary="Get a list of active alarms")
# async def get_active_alarms(
#     status: Optional[str] = Query(None, description="Filter by status (e.g., FIRING, RESOLVED)"),
#     limit: int = Query(100, description="Maximum number of results"),
# ):
#     """
#     Retrieves a list of alarms, which can be filtered by their current status.
#     """
#     try:
#         alarms = db_manager.get_alarms(status=status, limit=limit)
#         return alarms
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to retrieve alarms: {e}")

# @app.post("/api/v1/remediations/execute", summary="Manually execute a remediation")
# async def execute_remediation(request: RemediationRequestModel):
#     """
#     Executes a given command for a specific event and updates the event's
#     status and execution log accordingly.
#     """
#     event = db_manager.get_event_by_id(request.event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail=f"Event with ID {request.event_id} not found.")

#     db_manager.update_event(request.event_id, {"status": "EXECUTING", "remediation_command": request.command})

#     result = execute_command(request.command)

#     final_status = "RESOLVED" if result["success"] else "FAILED"
#     db_manager.update_event(request.event_id, {"status": final_status, "execution_log": result["log"]})

#     return {"event_id": request.event_id, "status": final_status, "details": result["log"]}

# @app.get("/api/v1/history/events/{event_id}", summary="Get the full history of an event")
# async def get_event_history(event_id: int):
#     """
#     Provides all stored details for a single event, including its trigger data
#     and execution log if available.
#     """
#     event = db_manager.get_event_by_id(event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail=f"Event with ID {event_id} not found.")
#     return event

# @app.post("/api/v1/diagnosis/re-evaluate", summary="Trigger a new AI diagnosis for an event")
# async def re_evaluate_diagnosis(event_id: int):
#     """
#     Fetches an event's trigger data, sends it to the AI engine for a new
#     diagnosis, and updates the event in the database with the new information.
#     """
#     event = db_manager.get_event_by_id(event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail=f"Event with ID {event_id} not found.")

#     trigger_data = json.loads(event["trigger_metrics"])
#     ai_response = get_ai_diagnosis(trigger_data)

#     if not ai_response:
#         raise HTTPException(status_code=502, detail="Failed to get a valid diagnosis from the AI engine.")

#     updates = {
#         "diagnosis": ai_response.get("diagnosis"),
#         "remediation_command": ai_response.get("remediation_command"),
#         "ai_confidence": ai_response.get("ai_confidence"),
#         "notes": ai_response.get("notes"),
#         "status": "ALERTING",  # Update status to show it has been diagnosed
#     }
#     db_manager.update_event(event_id, updates)

#     return {"message": "Diagnosis complete", "event_id": event_id, "diagnosis": updates}

# if __name__ == "__main__":
#     print("Starting Yubarta API server...")
#     uvicorn.run(app, host="127.0.0.1", port=8000)
