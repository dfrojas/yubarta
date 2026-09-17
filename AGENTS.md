# Yubarta

Autonomous remediation agent for self-hosted infrastructure. Deterministic detection feeds an LLM that diagnoses an incident, picks a remediation from a registered MCP tool set, and executes it under audited, least-privilege control. Reactive (alerts) and proactive (periodic scans).

CRITICAL: DO NOT delegate tasks to subagents. Perform all work, file reading, and coding directly on the main thread.

Skills, rules, etc can be found in /.agents in the root of the repository.

## Chat Interactions
- Do not end our conversations with questions
- Do not add introductions in your responses like "apologies, my bad, you are right", etc. Always straight to the point
- Use ASD-STE100 Simplified Technical English when we talk
