"""
Simulates collecting metrics from a Confluent Cloud-like API.
"""

import time
from typing import Dict, List

from src.collectors._base import create_event

def collect_confluent_api_metrics() -> List[Dict]:
    """
    Shows how the system could be adapted for a SaaS environment.
    """
    print("Simulating Confluent API collection...")
    return [create_event("confluent_api", "ActiveConnections", 500, {"cluster_id": "lkc-xyz"})]
