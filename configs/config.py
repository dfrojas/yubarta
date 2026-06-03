"""
System-wide configurations for Yubarta.
"""

import os

class SystemConfig:
    """
    Stores all system-wide configurations.
    """
    # --- General ---
    DATABASE_PATH = "yubarta_master.db"

    # --- Gemini AI Engine ---
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-preview-0520:generateContent"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY")  # Use environment variable or placeholder

    GEMINI_PROMPT_TEMPLATE = """
    Analyze the following monitoring event data from a Kafka cluster and provide a detailed diagnosis.
    The data may include JMX metrics, logs, eBPF stats, or API metrics.

    Your primary goal is to identify the root cause and recommend a specific, executable remediation action.

    Your response MUST be a single, valid JSON object with the following structure:
    {
      "diagnosis": "A brief, clear summary of the problem. Example: 'Broker is experiencing high produce latency due to memory pressure.'",
      "root_cause": "A detailed explanation of the most likely root cause based on the provided data.",
      "ai_confidence": 0.9,
      "remediation_command": "The exact shell command or script path to execute for remediation. Example: 'remediations/scripts/restart_broker.sh' or 'docker restart kafka-broker-1'",
      "notes": "Any additional important information, warnings, or context for the operator."
    }

    Do not include any text, markdown formatting (like ```json), or explanations outside of this JSON object.

    --- Problem Data ---
    {problem_data}
    """

# Instantiate config for global import
config = SystemConfig()
