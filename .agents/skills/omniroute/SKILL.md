---
name: omniroute
description: Local-first AI Gateway and model routing proxy by Diego Souza. Use to aggregate multiple AI providers (OpenAI, Anthropic, Gemini, DeepSeek, Local Ollama), enable intelligent automatic failover, and apply token compression.
---

# OmniRoute AI Gateway Skill

**OmniRoute** is an open-source, local-first AI gateway designed to unify disparate AI model providers behind a single, resilient OpenAI-compatible API endpoint.

Repository: `https://github.com/diegosouzapw/OmniRoute`

---

## 1. Key Capabilities

- **Single Universal Endpoint:** All models (Claude 3.5 Sonnet, GPT-4o, Gemini 2.0 Flash, DeepSeek-R1, Llama 3) accessed via `http://localhost:8080/v1/chat/completions`.
- **Automatic Fallback & Failover:** If an API provider experiences rate limits (HTTP 429) or downtime (HTTP 500/503), OmniRoute instantly shifts requests to backup providers or local models.
- **Token Compression:** Supports token reduction techniques (RTK + Caveman) to save costs and stay within tight context window budgets.
- **Cost & Latency Routing:** Route simple classification tasks to faster/cheaper models, routing complex reasoning to frontier models.

---

## 2. Configuration & Usage

### Running OmniRoute Locally
```bash
# Clone and run via Docker
docker run -d -p 8080:8080 \
  -e OPENAI_API_KEY="your-openai-key" \
  -e ANTHROPIC_API_KEY="your-anthropic-key" \
  -e GEMINI_API_KEY="your-gemini-key" \
  diegosouzapw/omniroute:latest
```

### Routing Requests in Applications
To point any OpenAI SDK client (Python or TypeScript) to OmniRoute:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="omniroute-local",
)

response = client.chat.completions.create(
    model="smart-router", # Automatically routes with failover
    messages=[{"role": "user", "content": "Explain binary search"}],
)
```

---

## 3. Best Practices for Coding Agents

1. **Fallback Priority:** Configure primary = Fast Frontier (e.g. Claude 3.5 / GPT-4o), secondary = Cost Efficient (Gemini 2.0 Flash / DeepSeek-V3), tertiary = Local Ollama.
2. **Health Probing:** Regularly monitor `/health` on the local OmniRoute instance before sending high-volume batch requests.
