"""
Shell Remediator for Yubarta.

Executes shell commands securely and captures their output.
"""

import subprocess
from typing import Any, Dict

def execute_command(command: str) -> Dict[str, Any]:
    """
    Executes a command and captures its output.
    Returns a dictionary with status, stdout, and stderr.
    """
    print(f"Executing command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,  # Use shell=True cautiously. For this use case, it allows simple commands.
            capture_output=True,
            text=True,
            check=False,  # We handle the error manually
            timeout=300,  # 5-minute timeout
        )

        execution_log = f"--- STDOUT ---\n{result.stdout}\n--- STDERR ---\n{result.stderr}"

        if result.returncode == 0:
            print("Command executed successfully.")
            return {"success": True, "log": execution_log}
        else:
            print(f"Command failed with return code {result.returncode}.")
            return {"success": False, "log": execution_log}

    except subprocess.TimeoutExpired:
        return {"success": False, "log": "Execution timed out after 300 seconds."}
    except Exception as e:
        return {"success": False, "log": f"An unexpected error occurred: {e}"}

