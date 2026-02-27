# Customer Service Conversation Generator & Analyzer

A system for **generating and analyzing** dialogues between customers and support agents using LLM via [OpenRouter](https://openrouter.ai/). The project allows you to:

- Generate realistic dialogues with different client types (friendly, impatient, confused, hidden_dissatisfied)
- Analyze the quality of agent service
- Detect hidden dissatisfaction and sarcasm in client messages
- Obtain metrics: intent, satisfaction, quality score, agent mistakes, and more

---

## Project Structure

```
.
├── src/
│   ├── generate.py        # Dialogue generation
│   ├── analyze.py         # Dialogue analysis
│   ├── llm_utils.py       # LLM utility functions
│   ├── models.py          # Pydantic models
│   ├── prompts.py         # System prompts
│   └── config.py          # Configuration
├── data/
│   ├── chats.json         # Generated dialogues (created automatically)
│   └── analysis_results.json  # Analysis results (created automatically)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                   # Your API key (must be created manually)
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/MykhailoTymoshenko08/skelar-ai-support-analyser
cd skelar-ai-support-analyser
```

### 2. Configure the API key

Create a `.env` file in the project root:

```bash
echo "OPENROUTER_API_KEY=your-api-key-here" > .env
```

> Get a free key at [openrouter.ai](https://openrouter.ai/keys).

---

## Running with Docker Compose (recommended)

### Build the image

```bash
docker compose build
```

### Run the full pipeline (generation + analysis)

```bash
docker compose run all
```

### Generation only

```bash
docker compose run generate
```

### Analysis only

```bash
docker compose run analyze
```

> Make sure `data/chats.json` exists before running analysis separately.

---

## Running without Docker

### Install dependencies

```bash
pip install -r requirements.txt
```

### Generate dialogues

```bash
PYTHONPATH=. python src/generate.py
```

### Analyze dialogues

```bash
PYTHONPATH=. python src/analyze.py
```

---

## Configuration

The main parameters are located in `src/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `num_conversations` | `10` | Number of dialogues to generate |
| `max_turns_min` | `3` | Minimum number of turns per dialogue |
| `max_turns_max` | `10` | Maximum number of turns per dialogue |
| `generation_concurrency` | `40` | Parallel requests during generation |
| `analysis_concurrency` | `10` | Parallel requests during analysis |
| `default_model` | `arcee-ai/trinity-large-preview:free` | Default model |

### Available models (via OpenRouter, free)

```python
arcee_ai      = "arcee-ai/trinity-large-preview:free"
google_gemini = "google/gemini-2.0-flash-exp:free"
glm_45_air    = "z-ai/glm-4.5-air:free"
trinity_mini  = "arcee-ai/trinity-mini:free"
```

---

## Output Data Formats

### `data/chats.json` — generated dialogues

```json
[
  {
    "id": 1,
    "intent": "payment_problem",
    "client_persona": "impatient",
    "turns": [
      { "role": "client", "content": "I was charged twice for my subscription!" },
      { "role": "agent",  "content": "I'm sorry to hear that. Let me check your account..." }
    ],
    "metadata": { "generated_at": "2024-01-01T12:00:00" }
  }
]
```

### `data/analysis_results.json` — analysis results

```json
{
  "results": [
    {
      "conversation_id": 1,
      "intent": "payment_problem",
      "satisfaction": "dissatisfied",
      "quality_score": 3,
      "agent_mistakes": ["incomplete_info", "tech_jargon"],
      "resolution_status": "partially_resolved",
      "hidden_dissatisfaction_score": 0.75,
      "key_action_items": ["Refund pending confirmation"],
      "agent_performance": "adequate",
      "detected_persona": "impatient"
    }
  ],
  "metadata": {
    "analyzed_at": "2024-01-01T12:05:00",
    "total_conversations": 10,
    "failed_conversations": []
  }
}
```

---

## Client Personas

| Persona | Description |
|---|---|
| `friendly` | Patient and polite, explains the problem in detail |
| `impatient` | Impatient, wants a quick resolution |
| `confused` | Does not understand technical terms, asks many questions |
| `hidden_dissatisfied` | Outwardly polite but covertly dissatisfied |

## Intent Types

`payment_problem` · `tech_error` · `account_access` · `tariff` · `refund` · `other`