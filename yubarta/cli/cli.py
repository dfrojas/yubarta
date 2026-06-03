#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Typer CLI - A command-line client for the Yubarta Auto-Remediation API.

This module contains no business logic. It only makes HTTP requests to the API
and displays the results in a user-friendly format.
"""

import json
from datetime import datetime
from typing import Any, List

import requests
import typer

# --- CLI Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"
cli = typer.Typer(help="Yubarta CLI - A client for the Auto-Remediation API.")

# --- Helper Functions ---
def _print_table(headers: List[str], rows: List[List[Any]]):
    """Helper function to print a simple formatted table."""
    if not rows:
        print("No data to display.")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers)))
    print(header_line)
    print("-" * len(header_line))

    for row in rows:
        row_line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
        print(row_line)

# --- CLI Commands ---
@cli.command()
def status(status: str = typer.Option("FIRING", help="Filter alarms by status (e.g., FIRING, RESOLVED).")):
    """
    Shows currently active alarms by calling GET /api/v1/alarms.
    """
    print(f"Fetching alarms with status: {status.upper()}...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/alarms", params={"status": status})
        response.raise_for_status()
        alarms = response.json()

        headers = ["ID", "Status", "Timestamp", "Diagnosis", "Command"]
        rows = []
        for alarm in alarms:
            ts = datetime.fromtimestamp(alarm["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(
                [alarm["event_id"], alarm["status"], ts, alarm["diagnosis"] or "N/A", alarm["remediation_command"] or "N/A"]
            )
        _print_table(headers, rows)

    except requests.RequestException as e:
        print(f"Error: Could not connect to Yubarta API at {API_BASE_URL}. Is the server running?")
        print(f"Details: {e}")

@cli.command()
def history(limit: int = typer.Option(10, "--limit", "-l", help="Number of events to show.")):
    """
    Shows the most recent remediation events from the API.
    """
    print(f"Fetching last {limit} events...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/alarms", params={"limit": limit})
        response.raise_for_status()
        events = response.json()

        headers = ["ID", "Status", "Timestamp", "Diagnosis"]
        rows = []
        for event in events:
            ts = datetime.fromtimestamp(event["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            rows.append([event["event_id"], event["status"], ts, event["diagnosis"] or "N/A"])
        _print_table(headers, rows)

    except requests.RequestException as e:
        print(f"Error: Could not connect to Yubarta API. Details: {e}")

@cli.command()
def diagnose(event_id: int = typer.Option(..., "--event-id", help="The ID of the event to diagnose.")):
    """
    Triggers a re-evaluation of an event by the AI engine.
    """
    print(f"Requesting new diagnosis for event ID: {event_id}...")
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/diagnosis/re-evaluate", params={"event_id": event_id})
        response.raise_for_status()
        result = response.json()
        print("Diagnosis successful!")
        print(json.dumps(result, indent=2))
    except requests.RequestException as e:
        print(f"Error: Could not connect to Yubarta API. Details: {e}")
        if e.response:
            print(f"API Response: {e.response.text}")

if __name__ == "__main__":
    cli()
