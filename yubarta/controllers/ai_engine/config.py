"""
Configuration file for Yubarta.

Stores API keys, endpoints, and prompt templates.
"""

# Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-preview-0520:generateContent"
GEMINI_API_KEY = "YOUR_API_KEY"  # IMPORTANT: Replace with your actual API key

# AI Engine Prompt Template
GEMINI_PROMPT = """
Analyze the following Kafka monitoring data and provide a diagnosis.
The data includes JMX metrics and recent log entries.
Based on the data, identify the most likely root cause of the problem.

Your response MUST be a valid JSON object with the following structure:
{
  "diagnosis": "A brief summary of the problem.",
  "root_cause": "The most likely root cause of the issue.",
  "confidence_score": 0.9,
  "recommended_remediation": {
    "description": "A brief description of the recommended action.",
    "script": "The path to the shell script to execute for remediation, relative to the project root."
  }
}

Do not include any other text or formatting outside of the JSON object.

Problem Data:
{problem_data}
"""
