# Customer Service Conversation Generator & Analyzer

Система для **генерації та аналізу** діалогів між клієнтами та агентами підтримки з використанням LLM через [OpenRouter](https://openrouter.ai/). Проєкт дозволяє:

- Генерувати реалістичні діалоги з різними типами клієнтів (friendly, impatient, confused, hidden_dissatisfied)
- Аналізувати якість обслуговування агентів
- Виявляти приховане незадоволення та сарказм клієнтів
- Отримувати метрики: intent, satisfaction, quality score, помилки агента тощо

---

## Структура проєкту

```
.
├── src/
│   ├── generate.py        # Генерація діалогів
│   ├── analyze.py         # Аналіз діалогів
│   ├── llm_utils.py       # Утиліти для роботи з LLM
│   ├── models.py          # Pydantic-моделі
│   ├── prompts.py         # Системні промпти
│   └── config.py          # Конфігурація
├── data/
│   ├── chats.json         # Згенеровані діалоги (створюється автоматично)
│   └── analysis_results.json  # Результати аналізу (створюється автоматично)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                   # Ваш API-ключ (треба створити вручну)
```

---

## Швидкий старт

### 1. Клонування репозиторію

```bash
git clone https://github.com/MykhailoTymoshenko08/skelar-ai-support-analyser
cd skelar-ai-support-analyser
```

### 2. Налаштування API-ключа

Створіть файл `.env` у корені проєкту:

```bash
echo "OPENROUTER_API_KEY=your-api-key-here" > .env
```

> Отримати безкоштовний ключ можна на [openrouter.ai](https://openrouter.ai/keys).

---

## Запуск через Docker Compose (рекомендовано)

### Збірка образу

```bash
docker compose build
```

### Запуск усього пайплайну (генерація + аналіз)

```bash
docker compose run all
```

### Тільки генерація діалогів

```bash
docker compose run generate
```

### Тільки аналіз діалогів

```bash
docker compose run analyze
```

> Переконайтесь, що `data/chats.json` існує перед запуском аналізу окремо.

---

## Запуск без Docker — macOS

### Вимоги

Перевірте, що встановлено Python 3.8+:

```bash
python3 --version
```

Якщо не встановлено — завантажте з [python.org](https://www.python.org/downloads/) або через Homebrew:

```bash
brew install python
```

### Встановлення залежностей

```bash
pip3 install -r requirements.txt
```

### Генерація діалогів

```bash
PYTHONPATH=. python3 src/generate.py
```

### Аналіз діалогів

```bash
PYTHONPATH=. python3 src/analyze.py
```

> **Важливо:** На Mac не використовуйте `python` або `pip` без суфікса `3` — починаючи з macOS Catalina вони або вказують на Python 2, або взагалі відсутні.

---

## Запуск без Docker — Windows

### Вимоги

Встановіть Python 3.8+ з [python.org](https://www.python.org/downloads/).

Під час встановлення обов'язково поставте галочку **"Add Python to PATH"** — без цього команди нижче не працюватимуть.

Перевірте після встановлення (у Command Prompt або PowerShell):

```cmd
python --version
```

### Встановлення залежностей

```cmd
pip install -r requirements.txt
```

### Встановлення PYTHONPATH та генерація діалогів

**Command Prompt:**
```cmd
set PYTHONPATH=. && python src/generate.py
```

**PowerShell:**
```powershell
$env:PYTHONPATH="."; python src/generate.py
```

### Встановлення PYTHONPATH та аналіз діалогів

**Command Prompt:**
```cmd
set PYTHONPATH=. && python src/analyze.py
```

**PowerShell:**
```powershell
$env:PYTHONPATH="."; python src/analyze.py
```

> **Важливо:** Windows не підтримує синтаксис `PYTHONPATH=. python ...`, який використовується на Mac/Linux. Змінну середовища потрібно задавати окремо — через `set` у CMD або `$env:` у PowerShell, як показано вище.

---

## Конфігурація

Основні параметри знаходяться у `src/config.py`:

| Параметр | За замовчуванням | Опис |
|---|---|---|
| `num_conversations` | `10` | Кількість діалогів для генерації |
| `max_turns_min` | `3` | Мінімальна кількість реплік у діалозі |
| `max_turns_max` | `10` | Максимальна кількість реплік у діалозі |
| `generation_concurrency` | `10` | Паралельних запитів при генерації |
| `analysis_concurrency` | `10` | Паралельних запитів при аналізі |
| `default_model` | `arcee-ai/trinity-large-preview:free` | Модель за замовчуванням |

### Доступні моделі (через OpenRouter, безкоштовні)

```python
arcee_ai      = "arcee-ai/trinity-large-preview:free"
google_gemini = "google/gemini-2.0-flash-exp:free"
glm_45_air    = "z-ai/glm-4.5-air:free"
trinity_mini  = "arcee-ai/trinity-mini:free"
```

---

## Формат вихідних даних

### `data/chats.json` — згенеровані діалоги

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

### `data/analysis_results.json` — результати аналізу

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

## Клієнтські персони

| Персона | Опис |
|---|---|
| `friendly` | Терплячий і ввічливий, детально пояснює проблему |
| `impatient` | Нетерплячий, хоче швидкого вирішення |
| `confused` | Не розуміє технічних термінів, ставить багато запитань |
| `hidden_dissatisfied` | Зовні ввічливий, але приховано незадоволений |

## Типи звернень (Intent)

`payment_problem` · `tech_error` · `account_access` · `tariff` · `refund`