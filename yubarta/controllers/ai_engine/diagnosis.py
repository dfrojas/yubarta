"""
AI Engine for problem diagnosis using the Gemini API.
"""
import json
from typing import Dict, Optional

import requests

from configs.config import config

def get_ai_diagnosis(problem_data: Dict) -> Optional[Dict]:
    """
    Sends data to Gemini and parses the JSON response.
    """
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == "YOUR_API_KEY":
        print("AI ENGINE ERROR: API key not set. Returning mock diagnosis.")
        return {
            "diagnosis": "Mock Diagnosis: High latency detected.",
            "root_cause": "This is a simulated root cause because the API key is missing.",
            "ai_confidence": 0.99,
            "remediation_command": "echo 'Simulated remediation: API key needed for real action.'",
            "notes": "Please configure the GEMINI_API_KEY in configs/config.py or as an environment variable.",
        }

    headers = {"Content-Type": "application/json"}
    prompt = config.GEMINI_PROMPT_TEMPLATE.format(problem_data=json.dumps(problem_data, indent=2))
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        print("Contacting Gemini API for diagnosis...")
        response = requests.post(
            f"{config.GEMINI_API_URL}?key={config.GEMINI_API_KEY}", headers=headers, json=payload, timeout=90
        )
        response.raise_for_status()

        response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Clean potential markdown formatting
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]

        return json.loads(response_text)
    except requests.RequestException as e:
        print(f"AI ENGINE ERROR: API request failed: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        print(f"AI ENGINE ERROR: Failed to parse API response: {e}")
    return None
