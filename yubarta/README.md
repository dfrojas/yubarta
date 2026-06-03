# Yubarta - AI-Powered Auto-Remediation Engine

Yubarta is a proof-of-concept auto-remediation engine that uses AI to diagnose issues in a Kafka cluster and automatically applies corrective actions.

## Project Structure

```
/yubarta
├── /src
│   ├── /collectors       # Modules to gather data (JMX, logs, etc.)
│   ├── /ai_engine        # Module to interact with a GenAI model for diagnosis
│   ├── /remediators      # Modules to execute corrective actions
│   ├── /database         # Database interface for event logging
│   └── main.py           # Main orchestrator for the workflow
├── /configs
│   └── config.py         # Stores configuration like API keys and prompts
├── /remediations
│   └── scripts           # Contains executable remediation scripts
└── README.md
```

## How It Works

The workflow is orchestrated by `src/main.py`:

1.  **Collect**: Data is gathered from various sources by the `collectors`. Currently, this is simulated for Kafka JMX metrics and logs.
2.  **Diagnose**: The collected data is sent to a Generative AI model (Gemini) using a structured prompt. The AI is asked to identify the root cause and recommend a remediation script in a JSON format.
3.  **Log**: The diagnosis and recommended action are logged to a local SQLite database (`yubarta_events.db`).
4.  **Remediate**: If the AI recommends a script, the `shell_remediator` executes it.

## How to Run

1.  **Configure API Key**:
    *   Open `yubarta/configs/config.py`.
    *   Replace `"YOUR_API_KEY"` with your actual Google Gemini API key.
    *   If you run without a key, the application will use a mock response for demonstration.

2.  **Execute the Workflow**:
    *   Navigate to the project's root directory (`/yubarta`).
    *   Run the main orchestrator:
        ```bash
        python yubarta/src/main.py
        ```

The script will print the steps of the workflow, from data collection to remediation.
