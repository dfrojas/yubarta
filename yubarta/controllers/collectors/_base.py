"""
Base utilities for collectors.
"""

import time
from typing import Any, Dict

def create_event(source: str, metric_name: str, value: Any, labels: Dict = {}) -> Dict:
    """
    Factory function to create a standardized event dictionary.
    """
    return {"source": source, "timestamp": time.time(), "metric_name": metric_name, "value": value, "labels": labels}
