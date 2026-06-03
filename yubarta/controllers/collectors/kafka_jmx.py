"""
Simulates collecting JMX metrics from a Kafka broker.
"""

import time
from typing import Dict, List

from src.collectors._base import create_event

def collect_jmx_metrics() -> List[Dict]:
    """
    Generates a list of simulated JMX metric events.
    """
    print("Simulating JMX collection...")
    return [
        create_event("kafka_jmx", "HeapMemoryUsage", 0.85, {"broker": "1", "node": "kafka-node-1"}),
        create_event("kafka_jmx", "ProduceRequestLatency", 250, {"broker": "1", "node": "kafka-node-1"}),
    ]
