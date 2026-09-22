#!/usr/bin/env python3
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def alive() -> bool:
    try:
        process = int(Path("/run/tomcat.pid").read_text())
        os.kill(process, 0)
        return Path(f"/proc/{process}/stat").read_text().split()[2] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


def stop() -> None:
    if alive():
        os.kill(int(Path("/run/tomcat.pid").read_text()), signal.SIGKILL)
    time.sleep(0.1)


def main() -> None:
    command = sys.argv[1]
    if command in {"is-active", "status"}:
        print("active" if alive() else "failed")
        raise SystemExit(0 if alive() else 3)
    if command == "is-failed":
        print("active" if alive() else "failed")
        raise SystemExit(1 if alive() else 0)
    if command in {"stop", "fail"}:
        stop()
        if command == "fail":
            with open("/var/log/apache2/error.log", "a") as stream:
                stream.write(f"[{datetime.now(timezone.utc).isoformat()}] [proxy:error] AH00957: AJP: attempt to connect to backend failed: Connection refused\n")
        return
    if command == "restart":
        stop()
        with open("/var/log/tomcat-sandbox.log", "ab") as output:
            process = subprocess.Popen(["python3", "/opt/sandbox/service.py"], stdin=subprocess.DEVNULL,
                                        stdout=output, stderr=output, start_new_session=True)
        Path("/run/tomcat.pid").write_text(str(process.pid))
        return
    if command == "daemon-reload":
        path = Path("/etc/systemd/system/tomcat9.service.d/zz-yubarta.conf")
        Path("/run/effective-policy").write_text(path.read_text() if path.exists() else "")
        return
    if command in {"show", "cat"}:
        path = Path("/run/effective-policy")
        configured = path.exists() and "Restart=on-failure" in path.read_text()
        print("Restart=on-failure\nRestartUSec=10s" if configured else "Restart=no\nRestartUSec=100ms")
        return
    if command == "disconnect-scanners":
        # Kill real SSH sessions whose shell is running tail, not execution sessions.
        for directory in Path("/proc").iterdir():
            if directory.name.isdigit():
                try:
                    if (directory / "comm").read_text().strip() == "tail":
                        parent = int((directory / "stat").read_text().split()[3])
                        while parent > 1:
                            process = Path(f"/proc/{parent}")
                            if (process / "comm").read_text().strip().startswith("sshd"):
                                os.kill(parent, signal.SIGKILL)
                                break
                            parent = int((process / "stat").read_text().split()[3])
                except (FileNotFoundError, ProcessLookupError):
                    continue
        return
    raise SystemExit(f"Unsupported sandbox command: {command}")


if __name__ == "__main__":
    main()
