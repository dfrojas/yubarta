# from yubarta.core.models import Alert
# from abc import ABC, abstractmethod
# from datetime import datetime
# import uuid

# from yubarta.adapters.alarms.datadog import DatadogImpl
# from yubarta.core.interfaces import AlarmInterface


# class AlarmIdentificator:
#     def __init__(self, alarm: dict):
#         self.alarm = alarm

#     def identify(self) -> AlarmInterface:
#         """Identify the provider and return the appropriate normalizer."""
#         provider = self._identify_provider()

#         identificators = {
#             "datadog": DatadogImpl,
#             # Add more identificators here as they are implemented
#             # "newrelic": NewRelicAlarmIdentificator,
#         }

#         if provider not in identificators:
#             raise ValueError(f"Unknown alarm provider: {provider}")

#         identificator = identificators[provider](self.alarm)

#         # I'm not very friend of runtime checks but I wanted to
#         # give a try. Maybe I'll remove it later and leave this
#         # task to MyPy during the development cycle.
#         if not isinstance(identificator, AlarmInterface):
#             raise TypeError(f"Adapter for '{provider}' doesn't implement AlarmInterface protocol")

#         return identificator.process()

#     def _identify_provider(self) -> str:
#         """
#         Identify the provider based on the alarm payload.
#         In a real implementation, this would examine the payload structure
#         to determine the source.
#         """
#         # Explicit provider field (for testing)
#         if "provider" in self.alarm:
#             return self.alarm["provider"]

#         # Datadog specific fields
#         if "alert_type" in self.alarm and ("host" in self.alarm or "org_id" in self.alarm):
#             return "datadog"

#         # In a real implementation, add more provider detection logic here

#         raise ValueError("Could not identify alarm provider from payload")
