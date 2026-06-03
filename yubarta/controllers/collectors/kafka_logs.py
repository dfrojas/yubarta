"""
Simulates collecting log entries from a Kafka broker.
"""

import time
from typing import Dict, List

from src.collectors._base import create_event

def collect_logs() -> List[Dict]:
    """
    Generates a list of simulated log events.
    """
    print("Simulating Log collection...")
    log_entry = "ERROR [Controller id=1] Controller failed to increase broker epoch for broker 2"
    return [create_event("kafka_logs", "LogError", log_entry, {"broker": "2", "level": "ERROR"})]
