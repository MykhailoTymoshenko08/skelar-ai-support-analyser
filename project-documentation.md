# Customer Service Conversation Generator & Analyzer
### Повна технічна документація

---

## Зміст

1. [Огляд проєкту](#1-огляд-проєкту)
2. [Архітектура системи](#2-архітектура-системи)
3. [Структура файлів](#3-структура-файлів)
4. [Встановлення та налаштування](#4-встановлення-та-налаштування)
5. [Запуск: Docker (рекомендовано)](#5-запуск-docker-рекомендовано)
6. [Запуск: без Docker](#6-запуск-без-docker)
7. [Конфігурація (`config.py`)](#7-конфігурація-configpy)
8. [Модуль генерації (`generate.py`)](#8-модуль-генерації-generatepy)
9. [Модуль аналізу (`analyze.py`)](#9-модуль-аналізу-analyzepy)
10. [Промпти (`prompts.py`)](#10-промпти-promptspy)
11. [Моделі даних (`models.py`)](#11-моделі-даних-modelspy)
12. [LLM-утиліти (`llm_utils.py`)](#12-llm-утиліти-llm_utilspy)
13. [Формати вхідних і вихідних даних](#13-формати-вхідних-і-вихідних-даних)
14. [Логіка класифікації intent](#14-логіка-класифікації-intent)
15. [Логіка виявлення прихованого незадоволення](#15-логіка-виявлення-прихованого-незадоволення)
16. [Business Logic Guardrails](#16-business-logic-guardrails)
17. [Доступні моделі](#17-доступні-моделі)
18. [Типові помилки та їх вирішення](#18-типові-помилки-та-їх-вирішення)
19. [Розширення та кастомізація](#19-розширення-та-кастомізація)

---

## 1. Огляд проєкту

Ця система вирішує дві незалежні задачі, які можна запускати разом або окремо:

**Генерація** — створення синтетичних діалогів між клієнтом і агентом підтримки. Кожен діалог має визначену тему (`intent`), персону клієнта і, за бажанням, контекст терміновості (клієнт стоїть на касі, у нього важлива зустріч тощо).

**Аналіз** — автоматична оцінка якості цих діалогів за допомогою LLM. Система визначає тему звернення, рівень задоволеності клієнта, помилки агента, ступінь прихованого незадоволення і статус вирішення проблеми.

Обидва модулі працюють **асинхронно** з налаштованим рівнем конкурентності, що дозволяє генерувати і аналізувати сотні діалогів за лічені хвилини.

### Ключові метрики аналізу

| Метрика | Тип | Опис |
|---|---|---|
| `intent` | enum | Тема звернення (5 категорій) |
| `satisfaction` | enum | Задоволеність клієнта (4 стани) |
| `quality_score` | int 1–5 | Загальна оцінка якості обслуговування |
| `hidden_dissatisfaction_score` | float 0.0–1.0 | Ступінь прихованого незадоволення |
| `agent_mistakes` | list | Конкретні помилки агента (8 типів) |
| `resolution_status` | string | Статус вирішення проблеми |
| `agent_performance` | string | Загальна оцінка роботи агента |
| `detected_persona` | string | Виявлена персона клієнта |

---

## 2. Архітектура системи

```
┌─────────────────────────────────────────────────────────┐
│                      PIPELINE                           │
│                                                         │
│  ┌─────────────┐   chats.json   ┌──────────────────┐   │
│  │  generate.py │ ────────────▶  │   analyze.py     │   │
│  │             │                │                  │   │
│  │ LLM × N    │                │ LLM × N (async)  │   │
│  │ (async)    │                │ + guardrails     │   │
│  └─────────────┘                └──────────────────┘   │
│         │                               │               │
│         ▼                               ▼               │
│   data/chats.json            data/analysis_results.json │
└─────────────────────────────────────────────────────────┘

Спільні залежності:
  config.py    ← параметри для обох модулів
  prompts.py   ← всі промпти
  models.py    ← Pydantic-схеми даних
  llm_utils.py ← HTTP-клієнт до OpenRouter API
```

### Потік даних під час генерації

```
intent_category + client_persona
         │
         ▼
generate_conversation_async()
         │
         ├── [Turn 0] client initial message  ← LLM call (temp=0.8)
         ├── [Turn 1] agent response          ← LLM call (temp=0.5)
         ├── [Turn 2] client response         ← LLM call (temp=0.8)
         ├── ... (до max_turns або random break)
         │
         ▼
Conversation (Pydantic) → .model_dump() → JSON
```

### Потік даних під час аналізу

```
conversation (dict з chats.json)
         │
         ▼
analyze_single_conversation_async()
         │
         ├── format conversation as text
         ├── LLM call → raw JSON  (temp=0.0)
         │
         ▼
validate_and_create_result()
         │
         ├── [Guardrail 1] resolve intent → 5 allowed values
         ├── [Guardrail 2] hidden_score > 0.5 + neutral → force hidden_dissatisfaction
         ├── [Guardrail 3] filter agent_mistakes → whitelist only
         │
         ▼
AnalysisResult (Pydantic) → .model_dump() → JSON
```

---

## 3. Структура файлів

```
project/
├── src/
│   ├── generate.py          # Генерація синтетичних діалогів
│   ├── analyze.py           # Аналіз якості діалогів
│   ├── prompts.py           # Всі промпти для LLM
│   ├── models.py            # Pydantic-моделі (схеми даних)
│   ├── llm_utils.py         # Клієнт до OpenRouter API
│   └── config.py            # Глобальна конфігурація
├── data/
│   ├── chats.json           # Згенеровані діалоги (авто)
│   └── analysis_results.json # Результати аналізу (авто)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                     # API-ключ (створити вручну!)
```

> **Важливо:** Папка `data/` і файли в ній створюються автоматично при першому запуску. Не потрібно створювати їх вручну.

---

## 4. Встановлення та налаштування

### Крок 1. Клонувати репозиторій

```bash
git clone https://github.com/MykhailoTymoshenko08/skelar-ai-support-analyser
cd skelar-ai-support-analyser
```

### Крок 2. Створити файл `.env`

```bash
echo "OPENROUTER_API_KEY=your-api-key-here" > .env
```

Отримати безкоштовний ключ: [openrouter.ai/keys](https://openrouter.ai/keys)

> **Чому OpenRouter?** Сервіс надає єдиний API-endpoint для десятків LLM-моделей, включаючи безкоштовні. Проєкт за замовчуванням використовує `arcee-ai/trinity-large-preview:free`.

### Крок 3. Перевірити `.gitignore`

Переконайтеся, що `.env` і `data/` не потрапляють у git:

```
.env
data/
```

---

## 5. Запуск: Docker (рекомендовано)

Docker гарантує однакове середовище виконання незалежно від ОС.

### Збірка образу

```bash
docker compose build
```

Виконується **один раз** (або після зміни `requirements.txt` / `Dockerfile`).

### Запустити повний пайплайн (генерація + аналіз)

```bash
docker compose run all
```

Що відбувається:
1. Видаляються старі файли `data/chats.json` і `data/analysis_results.json`
2. Запускається `generate.py` → створює `data/chats.json`
3. Запускається `analyze.py` → читає `chats.json`, створює `analysis_results.json`

### Запустити тільки генерацію

```bash
docker compose run generate
```

Видаляє старий `chats.json` і генерує новий. Корисно, якщо потрібно перегенерувати датасет без повторного аналізу.

### Запустити тільки аналіз

```bash
docker compose run analyze
```

> **Увага:** `data/chats.json` має існувати до запуску. Якщо файлу нема — аналіз завершиться з помилкою `❌ File data/chats.json not found!`

### Переглянути результати

Файли зберігаються у папці `data/` поруч із проєктом (через volume mount):

```bash
cat data/analysis_results.json | python3 -m json.tool | head -100
```

---

## 6. Запуск: без Docker

### Встановити залежності

```bash
pip install -r requirements.txt
```

### Генерація

```bash
PYTHONPATH=. python src/generate.py
```

### Аналіз

```bash
PYTHONPATH=. python src/analyze.py
```

> **Чому `PYTHONPATH=.`?** Файли в `src/` імпортують один одного як `from src.config import ...`. Щоб Python знайшов модуль `src`, коренева директорія проєкту має бути у `PYTHONPATH`.

---

## 7. Конфігурація (`config.py`)

Всі ключові параметри зосереджені в одному місці.

### Параметри генерації

| Параметр | Тип | За замовчуванням | Опис |
|---|---|---|---|
| `num_conversations` | int | 10 | Кількість діалогів для генерації |
| `max_turns_min` | int | 3 | Мінімальна кількість реплік у діалозі |
| `max_turns_max` | int | 10 | Максимальна кількість реплік у діалозі |
| `generation_concurrency` | int | 10 | Паралельних запитів при генерації |
| `analysis_concurrency` | int | 40 | Паралельних запитів при аналізі |

### Параметри моделі

```python
default_model = arcee_ai  # "arcee-ai/trinity-large-preview:free"
```

Щоб змінити модель, достатньо перевизначити `default_model`:

```python
default_model = google_gemini  # "google/gemini-2.0-flash-exp:free"
```

### Параметри класифікації

```python
dissatisfaction_threshold = 0.7  # поріг для позначення у звіті
```

> **Увага:** У `analyze.py` використовується окремий `HIDDEN_DISSATISFACTION_THRESHOLD = 0.5` для guardrail-логіки. Ці два пороги незалежні.

### Файли виводу

```python
chats_file    = "data/chats.json"
analysis_file = "data/analysis_results.json"
```

---

## 8. Модуль генерації (`generate.py`)

### Загальний принцип

Кожен діалог генерується незалежно і паралельно. Система поперемінно викликає LLM від імені клієнта (висока температура = варіативність) і агента (нижча температура = стабільність).

### Клієнтські персони

| Ключ | Поведінка |
|---|---|
| `friendly` | Ввічливий, терплячий, детально пояснює проблему |
| `impatient` | Нетерплячий, короткі речення, показує роздратування при затримках |
| `confused` | Не розуміє технічних термінів, ставить багато уточнювальних питань |
| `hidden_dissatisfied` | Зовні ввічливий, використовує пасивно-агресивні фрази ("fine I guess", "whatever") |

### Сценарії та контексти терміновості

Кожна категорія `intent` має список із 4 різних сценаріїв (`SCENARIOS`) і список контекстів терміновості (`URGENCY_CONTEXTS`). При кожній генерації обирається випадковий сценарій та з ~50% шансом — контекст терміновості.

**Приклади контекстів терміновості:**
- `payment_problem`: "Клієнт стоїть на касі прямо зараз, картка відхилена перед іншими покупцями"
- `tech_error`: "Клієнт має критичну презентацію через 45 хвилин, додаток не працює"
- `refund`: "Клієнт чекає на повернення 2 тижні, завтра платити за оренду"

Контексти терміновості підвищують емоційну інтенсивність діалогів і роблять тренувальні дані реалістичнішими.

### Помилки агента (30% діалогів)

З ймовірністю 0.3 до промпту агента додається `MISTAKE_HINT`, який спонукає модель робити реалістичні помилки:
- Нетерплячість при повторних питаннях
- Неповна інформація з першого разу
- Технічний жаргон без пояснень
- Забуває уточнити важливі деталі

### Параметри температури

| Хто генерує | Температура | Причина |
|---|---|---|
| Клієнт (перше повідомлення) | 0.8 | Емоційна варіативність, реалізм |
| Клієнт (наступні репліки) | 0.8 | Підтримання емоційного стану |
| Агент | 0.5 | Стабільні, передбачувані відповіді |

### Логіка завершення діалогу

```
for turn in range(max_turns - 1):
    [агент відповідає]
    
    if turn > 2 and random() < 0.2:
        break  # ранній вихід після репліки агента
    
    [клієнт відповідає]
    
    if random() < 0.15:
        break  # ранній вихід після репліки клієнта
```

Після виходу з циклу перевіряється остання репліка. Якщо остання говорить клієнт — система генерує фінальне закриваюче повідомлення агента. **Діалог завжди закінчується репліком агента** — це стандарт якісного обслуговування.

---

## 9. Модуль аналізу (`analyze.py`)

### Загальний принцип

Кожен діалог з `chats.json` перетворюється на текст, передається LLM з детальним промптом і отримується JSON з метриками. Після цього результат проходить через **business logic guardrails** — детерміновані правила, які виправляють логічні суперечності у відповіді моделі.

### Функція `analyze_single_conversation_async`

Формує промпт із трьох частин:
1. Текст діалогу (всі репліки у форматі `Role: Content`)
2. `ANALYZER_PROMPT_SUMMARY` (правила аналізу з `prompts.py`)
3. Специфікація JSON-відповіді з нагадуванням заборон

Виклик до LLM з `temperature=0.0` — максимальна детермінованість аналізу.

### Функція `validate_and_create_result`

Отримує сирий JSON від LLM і виконує три послідовні перевірки:

#### Guardrail 1: Резолюція intent

```python
intent_mapping = {
    "payment_problem": IntentEnum.PAYMENT_PROBLEM,
    "tech_error":      IntentEnum.TECH_ERROR,
    "account_access":  IntentEnum.ACCOUNT_ACCESS,
    "tariff":          IntentEnum.TARIFF,
    "refund":          IntentEnum.REFUND,
}
# Якщо модель повернула щось невідоме — fallback_map → найближча категорія
```

Навіть якщо модель з якоїсь причини повернула `"other"` або власний варіант, код автоматично перетворить це на найближчий дозволений intent.

#### Guardrail 2: Консистентність hidden_dissatisfaction

```python
if hidden_score > HIDDEN_DISSATISFACTION_THRESHOLD:  # 0.5
    if resolved_satisfaction not in (HIDDEN_DISSATISFACTION, DISSATISFIED):
        # Модель виявила сарказм (score=0.8), але поставила "neutral"
        # → примусово перевизначаємо на "hidden_dissatisfaction"
        resolved_satisfaction = SatisfactionEnum.HIDDEN_DISSATISFACTION
```

Це найважливіший guardrail: модель часто правильно оцінює рівень прихованого незадоволення (числом), але помиляється з текстовою міткою.

#### Guardrail 3: Фільтрація помилок агента

```python
ALLOWED_AGENT_MISTAKES = {
    "ignored_question", "incorrect_info", "rude_tone", "no_resolution",
    "unnecessary_escalation", "incomplete_info", "tech_jargon", "impatient"
}
filtered_mistakes = [m for m in raw_mistakes if m in ALLOWED_AGENT_MISTAKES]
```

Іноді модель вигадує власні назви помилок (наприклад, `"bad_attitude"`). Всі невалідні значення видаляються.

### Конкурентний аналіз

```python
semaphore = asyncio.Semaphore(concurrency_limit)  # за замовчуванням 40

async def analyze_with_semaphore(conv):
    async with semaphore:
        # не більше 40 паралельних запитів одночасно
        analysis_data = await analyze_single_conversation_async(conv)
        ...

tasks = [analyze_with_semaphore(conv) for conv in conversations]
await asyncio.gather(*tasks)  # всі задачі запускаються одночасно
```

---

## 10. Промпти (`prompts.py`)

### Клієнтські промпти

Чотири промпти визначають поведінку клієнта під час генерації. Кожен містить:
- Опис характеру та стилю спілкування
- Критичне правило: не додавати префікс ролі ("Client:", "User:")

### Агентські промпти

| Змінна | Призначення |
|---|---|
| `AGENT_PROMPT_DEFAULT` | Основний промпт агента для всіх генерацій |
| `AGENT_PROMPT_TECH` | Спеціаліст технічної підтримки (не використовується в поточній генерації, доступний для розширення) |
| `AGENT_PROMPT_BILLING` | Спеціаліст з оплати (доступний для розширення) |

### `ANALYZER_PROMPT_SUMMARY` — найважливіший промпт

Містить 4 блоки правил, які передаються разом із кожним діалогом на аналіз.

**Блок 1 — INTENT CLASSIFICATION RULES**

Використовує підхід "decision flowchart": модель повинна послідовно перевіряти кожен крок і зупинитися на першому збігу. Для кожної категорії є:
- Опис суті (що хоче клієнт)
- Приклади ✅ правильних класифікацій
- Попередження ❌ про типові помилки
- Таблиця disambiguation з конкретними фразами

Детальніше — у [розділі 14](#14-логіка-класифікації-intent).

**Блок 2 — RESOLUTION STATUS RULES**

Чіткі умови для кожного зі статусів. `resolved` вимагає одночасного виконання трьох умов (агент підтвердив, клієнт погодився, немає відкритих питань).

**Блок 3 — AGENT MISTAKES RULES**

Перелік рівно 8 допустимих значень із поясненням кожного. Явна заборона вигадувати нові назви.

**Блок 4 — HIDDEN DISSATISFACTION RULES**

Детальніше — у [розділі 15](#15-логіка-виявлення-прихованого-незадоволення).

---

## 11. Моделі даних (`models.py`)

### Enums

```python
class IntentEnum(str, Enum):
    PAYMENT_PROBLEM = "payment_problem"
    TECH_ERROR      = "tech_error"
    ACCOUNT_ACCESS  = "account_access"
    TARIFF          = "tariff"
    REFUND          = "refund"

class SatisfactionEnum(str, Enum):
    SATISFIED              = "satisfied"
    NEUTRAL                = "neutral"
    DISSATISFIED           = "dissatisfied"
    HIDDEN_DISSATISFACTION = "hidden_dissatisfaction"
```

### `Conversation` — модель згенерованого діалогу

```python
class Conversation(BaseModel):
    id: int                          # унікальний ID (1, 2, 3...)
    intent: IntentEnum               # тема звернення
    client_persona: str              # персона клієнта
    turns: List[ConversationTurn]    # репліки діалогу
    metadata: dict                   # дата генерації, модель тощо
```

### `AnalysisResult` — модель результату аналізу

```python
class AnalysisResult(BaseModel):
    conversation_id: int
    intent: IntentEnum
    satisfaction: SatisfactionEnum
    quality_score: int               # Field(ge=1, le=5) — Pydantic валідує діапазон
    agent_mistakes: List[str]
    resolution_status: str
    hidden_dissatisfaction_score: float  # Field(ge=0.0, le=1.0)
    key_action_items: List[str]
    agent_performance: str
    detected_persona: str
```

### Валідація

Pydantic автоматично перевіряє:
- `quality_score` завжди між 1 і 5 (інакше `ValueError`)
- `hidden_dissatisfaction_score` завжди між 0.0 і 1.0
- `intent` і `satisfaction` — тільки значення з enum (інакше `ValidationError`)

---

## 12. LLM-утиліти (`llm_utils.py`)

### Основна функція `get_llm_response_async`

Обгортає LangChain `ChatOpenAI` з підтримкою retry-логіки:

```
Спроба 1 → помилка 429 (rate limit) → чекаємо 5 сек
Спроба 2 → помилка 429             → чекаємо 10 сек
Спроба 3 → помилка будь-яка        → fallback_llm_call_async()
Fallback  → пряме звернення через openai.AsyncOpenAI
```

### Функція `get_llm_response_json_async`

Надбудова над `get_llm_response_async` для отримання JSON:
1. Передає `response_format={"type": "json_object"}` (якщо модель підтримує)
2. Парсить відповідь через `parse_json_response()`
3. При невдачі пробує витягнути JSON за допомогою regex `r'\{[^{}]*\}'`
4. Повертає `{}` якщо нічого не вдалось розпарсити

### Налаштування заголовків

```python
default_headers={
    "HTTP-Referer": "http://localhost",
    "X-Title": "Chat Analyzer"
}
```

OpenRouter використовує ці заголовки для ідентифікації. `HTTP-Referer` обов'язковий для деяких безкоштовних моделей.

---

## 13. Формати вхідних і вихідних даних

### `data/chats.json`

Масив об'єктів `Conversation`. Кожен об'єкт:

```json
{
  "id": 1,
  "intent": "payment_problem",
  "client_persona": "impatient",
  "turns": [
    {
      "role": "client",
      "content": "I'm standing at the checkout and my card is being declined! This is embarrassing!",
      "timestamp": null
    },
    {
      "role": "agent",
      "content": "I'm sorry to hear that! Let me check your account right away. Can you confirm the last 4 digits of your card?",
      "timestamp": null
    }
  ],
  "metadata": {
    "generated_at": "2025-01-15T14:23:01.123456",
    "model_used": "arcee-ai/trinity-large-preview:free",
    "temperature_client": 0.7,
    "temperature_agent": 0.5
  }
}
```

### `data/analysis_results.json`

Об'єкт із масивом результатів і метаданими:

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
      "hidden_dissatisfaction_score": 0.25,
      "key_action_items": ["Escalate to billing team", "Follow up within 24h"],
      "agent_performance": "adequate",
      "detected_persona": "impatient"
    }
  ],
  "metadata": {
    "analyzed_at": "2025-01-15T14:35:22.654321",
    "total_conversations": 200,
    "failed_conversations": [],
    "input_file": "data/chats.json",
    "analysis_temperature": 0.0,
    "concurrency_limit": 40
  }
}
```

---

## 14. Логіка класифікації intent

### Проблема, яку вирішує поточна реалізація

Слова "billing", "charged", "money", "payment" зустрічаються в **усіх п'яти категоріях**. Слабкі моделі реагують на ці слова-тригери і скочуються в `payment_problem`. Щоб цього уникнути, промпт використовує підхід **decision flowchart**: питання задаються в певному порядку, і модель зупиняється на першому збігу.

### Дерево рішень

```
Що хоче зробити клієнт?
│
├─ Увійти в акаунт / скинути пароль / розблокувати?
│    └─▶ account_access
│
├─ Отримати гроші НАЗАД за минулу транзакцію?
│    └─▶ refund
│
├─ Змінити / зрозуміти / оскаржити ПЛАН або ТАРИФ?
│    └─▶ tariff
│
├─ Виправити конкретну ТРАНЗАКЦІЮ, що не пройшла?
│    └─▶ payment_problem
│
└─ Виправити ТЕХНІЧНИЙ БАҐ у продукті?
     └─▶ tech_error
```

### Типові точки плутанини та їх вирішення

| Фраза клієнта | ❌ Помилкова класифікація | ✅ Правильна | Причина |
|---|---|---|---|
| "Why is my bill higher this month?" | payment_problem | **tariff** | Клієнт оскаржує структуру плану, не транзакцію |
| "I was charged for premium I didn't choose" | payment_problem | **tariff** | Питання про те, який план застосовано |
| "I cancelled but you charged me again" | payment_problem | **refund** | Клієнт хоче повернення, транзакція вже відбулась |
| "I can't access my paid account" | payment_problem | **account_access** | Мета — доступ, не гроші |
| "I want a refund for last month" | payment_problem | **refund** | Явний запит повернення коштів |

---

## 15. Логіка виявлення прихованого незадоволення

### Ключова концепція

`hidden_dissatisfaction_score` вимірює **наскільки приховане** незадоволення, а не **наскільки сильне**. Це критично важливе розрізнення:

- Клієнт, який кричить "Fix it NOW! I'm calling my lawyer!" — **відкрито** незадоволений → score: 0.1, satisfaction: `dissatisfied`
- Клієнт, який каже "Fine, I guess that works..." після нерозв'язаної проблеми — **приховано** незадоволений → score: 0.8, satisfaction: `hidden_dissatisfaction`

### Індикатори прихованого незадоволення

**Сарказм та іронія (score 0.7–1.0):**
- Перебільшена ввічливість: "Oh please, don't rush on my account!"
- Іронічна похвала за провал: "Great commitment to your 'overnight' promise"
- Риторичні питання: "I assume my refund is just enjoying the scenery?"
- Лапки навколо обіцянок: "'quick' fix", "'same day' delivery"

**Пасивна агресія (score 0.5–0.8):**
- "fine I guess", "whatever", "ok I suppose", "if you say so"
- Дуже короткі відповіді після тривалої нерозв'язаної проблеми
- "never mind", "forget it", "doesn't matter anymore"

**Не є hidden_dissatisfaction:**
- Ввічливе перенаправлення до іншого відділу (агент, не клієнт)
- Прийнятий розв'язок без скарг
- Формально-нейтральна мова без емоцій
- Поодиноке нейтральне слово ("okay", "I see") без паттерну

### Консистентність між score і satisfaction

| Score | Satisfaction | Пояснення |
|---|---|---|
| > 0.5 | `hidden_dissatisfaction` | Паттерн прихованої фрустрації |
| 0.0–0.3 | `dissatisfied` | Відкрите незадоволення |
| 0.0–0.3 | `neutral` | Жодних емоційних сигналів |
| < 0.15 | `satisfied` | Клієнт задоволений, підтвердив розв'язок |

---

## 16. Business Logic Guardrails

Guardrails — це детерміновані правила в коді, які виправляють відповідь LLM **після** її отримання. Вони не залежать від якості моделі і завжди виконуються.

### Guardrail 1: Резолюція забороненого intent

```python
# Якщо модель повернула "other", "billing", "login" тощо
fallback_map = {
    "other":        IntentEnum.TECH_ERROR,      # найнейтральніший fallback
    "billing":      IntentEnum.PAYMENT_PROBLEM,
    "subscription": IntentEnum.TARIFF,
    "login":        IntentEnum.ACCOUNT_ACCESS,
    "cancellation": IntentEnum.REFUND,
}
```

### Guardrail 2: Hidden dissatisfaction override

```python
HIDDEN_DISSATISFACTION_THRESHOLD = 0.5

if hidden_score > HIDDEN_DISSATISFACTION_THRESHOLD:
    if resolved_satisfaction not in (HIDDEN_DISSATISFACTION, DISSATISFIED):
        # Виявлено: модель бачила сарказм (score=0.75), але злякалась і написала "neutral"
        # Виправлення: примусово → "hidden_dissatisfaction"
        resolved_satisfaction = SatisfactionEnum.HIDDEN_DISSATISFACTION
        print(f"  🔍 Business rule: score={hidden_score:.2f} → overriding to hidden_dissatisfaction")
```

### Guardrail 3: Whitelist помилок агента

```python
ALLOWED_AGENT_MISTAKES = {
    "ignored_question", "incorrect_info", "rude_tone", "no_resolution",
    "unnecessary_escalation", "incomplete_info", "tech_jargon", "impatient"
}
# Все що не входить у список — видаляється з попередженням
filtered_mistakes = [m for m in raw_mistakes if m in ALLOWED_AGENT_MISTAKES]
```

---

## 17. Доступні моделі

Всі моделі доступні безкоштовно через OpenRouter.

| Змінна в config.py | Model ID | Характеристики |
|---|---|---|
| `arcee_ai` (default) | `arcee-ai/trinity-large-preview:free` | Збалансована якість та швидкість |
| `google_gemini` | `google/gemini-2.0-flash-exp:free` | Висока якість, можливі ліміти |
| `glm_45_air` | `z-ai/glm-4.5-air:free` | Швидка, добре для генерації |
| `trinity_mini` | `arcee-ai/trinity-mini:free` | Найшвидша, для прототипування |
| `step_fun` | `stepfun/step-3.5-flash:free` | Альтернатива |
| `open_ai` | `openai/gpt-oss-20b:free` | OpenAI-сумісна |

### Як змінити модель

У `config.py`:

```python
default_model = google_gemini  # змінити цей рядок
```

Або використати різні моделі для генерації та аналізу, передавши `model=` явно у виклику `get_llm_response_async()`.

---

## 18. Типові помилки та їх вирішення

### `❌ File data/chats.json not found!`

**Причина:** Запускається `analyze.py` без попередньої генерації.

**Рішення:**
```bash
docker compose run generate  # спочатку генерація
docker compose run analyze   # потім аналіз
# або відразу:
docker compose run all
```

### `Error getting LLM response: 429`

**Причина:** Перевищено rate limit безкоштовної моделі.

**Рішення 1:** Зменшити конкурентність у `config.py`:
```python
generation_concurrency = 5  # замість 10
analysis_concurrency   = 10
```

**Рішення 2:** Перейти на іншу модель:
```python
default_model = trinity_mini  # менше навантажує API
```

**Рішення 3:** Система автоматично робить 3 спроби з паузами 5/10 секунд, потім перемикається на fallback через пряме звернення.

### `ValidationError: quality_score`

**Причина:** LLM повернула `quality_score` поза межами 1–5 (наприклад, `0` або `6`).

**Де обробляється:** Pydantic кине `ValueError` → `validate_and_create_result` впіймає `Exception` → діалог потрапить у `failed_conversations`.

**Рішення:** Зазвичай це поодинокий випадок. Якщо трапляється часто — перевірте промпт або змініть модель.

### `json.JSONDecodeError` під час завантаження chats.json

**Причина:** Файл пошкоджений або порожній (переривання під час запису).

**Рішення:**
```bash
# Видалити пошкоджений файл і перегенерувати
docker compose run generate
```

### Модель повертає текст замість JSON

**Причина:** Деякі безкоштовні моделі ігнорують `response_format={"type": "json_object"}`.

**Де обробляється:** `parse_json_response()` використовує regex для витягування JSON із тексту. Якщо це не допоможе — повертається `{}`, і діалог отримає дефолтні значення.

---

## 19. Розширення та кастомізація

### Додати нову персону клієнта

1. Додати промпт у `prompts.py`:
```python
CLIENT_PROMPT_AGGRESSIVE = """You are an aggressive client who immediately threatens legal action..."""
```

2. Додати в `CLIENT_PERSONAS` у `generate.py`:
```python
CLIENT_PERSONAS = {
    ...
    "aggressive": CLIENT_PROMPT_AGGRESSIVE,
}
```

### Додати новий сценарій

У `generate.py` додати у відповідний список `SCENARIOS`:
```python
intent.payment_problem: [
    ...
    "disputing a charge that appeared on their statement 3 months ago",
]
```

### Збільшити датасет

У `config.py`:
```python
num_conversations      = 500   # скільки генерувати
generation_concurrency = 40    # паралельних потоків (обмежено API)
analysis_concurrency   = 40
```

### Аналізувати власні діалоги

Підготуйте `data/chats.json` у форматі:
```json
[
  {
    "id": 1,
    "intent": "payment_problem",
    "client_persona": "unknown",
    "turns": [
      {"role": "client", "content": "..."},
      {"role": "agent", "content": "..."}
    ],
    "metadata": {}
  }
]
```
Потім запустіть тільки аналіз: `docker compose run analyze`

### Змінити поріг guardrail

У `analyze.py`:
```python
HIDDEN_DISSATISFACTION_THRESHOLD = 0.6  # підвищити → менше спрацювань
HIDDEN_DISSATISFACTION_THRESHOLD = 0.4  # знизити → більше спрацювань
```

---

*Документація актуальна для поточної версії проєкту.*