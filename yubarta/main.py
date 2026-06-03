# """
# Yubarta - Main Orchestrator

# This script coordinates the collection, diagnosis, and remediation workflow.
# """
# import json
# import os
# import sys

# # This allows running the script from the project root (e.g., python src/main.py)
# # and ensures that imports from other directories like 'configs' work correctly.
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from collectors import kafka_jmx, kafka_logs, kafka_ebpf
# from ai_engine import diagnosis
# from remediators import shell_remediator
# from database import sqlite_db

# def run_workflow():
#     """
#     Executes the full auto-remediation workflow.
#     """
#     print("--- Starting Yubarta Auto-Remediation Workflow ---")

#     # 1. Initialize Database
#     print("[Step 1/5] Initializing database...")
#     sqlite_db.init_db()
#     print("Database initialized successfully.")

#     # 2. Collect Data
#     print("[Step 2/5] Collecting data from sources...")
#     jmx_metrics = kafka_jmx.collect_metrics()
#     logs = kafka_logs.read_logs()
#     ebpf_stats = kafka_ebpf.collect_ebpf_stats()
#     print("Data collection complete.")

#     # 3. Consolidate Data for AI
#     print("[Step 3/5] Consolidating data for AI analysis...")
#     problem_context = {
#         "jmx_metrics": jmx_metrics,
#         "logs": logs,
#         "ebpf_stats": ebpf_stats
#     }
#     problem_data_str = json.dumps(problem_context, indent=2)
#     print("Data consolidated.")
#     # print(problem_data_str) # Uncomment for debugging

#     # 4. Get AI Diagnosis
#     print("[Step 4/5] Getting diagnosis from AI Engine...")
#     ai_diagnosis = diagnosis.get_ai_diagnosis(problem_data_str)

#     if not ai_diagnosis:
#         print("Could not get AI diagnosis. Aborting workflow.")
#         return

#     print(f"AI Diagnosis received: {ai_diagnosis.get('diagnosis')}")
#     sqlite_db.save_diagnosis_event(ai_diagnosis, "diagnosis_received")
#     print("Diagnosis event saved to database.")

#     # 5. Execute Remediation
#     print("[Step 5/5] Executing recommended remediation...")
#     remediation_info = ai_diagnosis.get("recommended_remediation")
#     if remediation_info and remediation_info.get("script"):
#         script_path = remediation_info["script"]
#         print(f"Remediation recommended: {remediation_info.get('description')}")
#         shell_remediator.execute_command(script_path)
#         sqlite_db.save_diagnosis_event(ai_diagnosis, "remediation_executed")
#     else:
#         print("No remediation script recommended or specified.")
#         sqlite_db.save_diagnosis_event(ai_diagnosis, "no_remediation_required")

#     print("--- Yubarta Workflow Finished ---")


# if __name__ == "__main__":
#     # Set the working directory to the project root to ensure relative paths work
#     project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
#     os.chdir(project_root)
#     run_workflow()
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from yubarta.drivers.db.initialization import init_database
from yubarta.drivers.messaging.initialization import init_kafka
from yubarta.drivers.messaging.kafka import producer
from yubarta.api_server.router import router as v1_router
from yubarta.controllers.indexer.consumer import indexer_consumer_worker
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize API
    app.include_router(v1_router)

    # Initialize database
    db = await init_database()
    app.state.db = db

    # Initialize Kafka
    kafka_admin = await init_kafka()
    app.state.kafka_admin = kafka_admin

    # Initialize Indexer Consumer
    app.state.stop_event = asyncio.Event()
    app.state.consumer_running = False
    app.state.last_commit_ts = 0
    app.state.consumer_task = asyncio.create_task(indexer_consumer_worker(app))

    yield

    # Cleanup
    app.state.stop_event.set()
    await app.state.consumer_task
    await producer.stop()
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)