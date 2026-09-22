from typing import Any

from pydantic import model_validator

from yubarta.config.settings import AppConfig


class ConfigInput(AppConfig):
    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        value = dict(value)
        watches = []
        raw_watches = value.get("watch", [])
        if not isinstance(raw_watches, list):
            raise ValueError("watch must be a list")
        for index, watch in enumerate(raw_watches):
            if isinstance(watch, dict) and len(watch) == 1 and next(iter(watch)) in {"log", "command"}:
                kind, body = next(iter(watch.items()))
                if not isinstance(body, dict):
                    raise ValueError(f"{kind} watch must be a mapping")
                watch = {**body, "kind": kind}
            if isinstance(watch, dict):
                watch = {"name": f"watch-{index + 1}", **watch}
            watches.append(watch)
        value["watch"] = watches
        if not isinstance(value.get("checks", []), list):
            raise ValueError("checks must be a list")
        value["checks"] = [
            {"kind": "http" if "http" in check else "command", **check}
            if isinstance(check, dict) else check
            for check in value.get("checks", [])
        ]
        return value
