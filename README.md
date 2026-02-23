# Customer Service Conversation Generator & Analyzer

## Опис проекту
Система для генерації та аналізу діалогів між клієнтами та агентами підтримки з використанням LLM через OpenRouter. Проект дозволяє створювати реалістичні діалоги з різними типами клієнтів та аналізувати якість обслуговування, виявляючи приховане незадоволення.

## Як запустити проект через Docker

### 1. Підготовка
```bash
git clone https://github.com/MykhailoTymoshenko08/skelar-ai-support-analyser
cd skelar-ai-support-analyser
echo "OPENROUTER_API_KEY=your-api-key-here" > .env
```

### 2. Збірка Docker образу
```bash
docker build -t chat-analyzer .
```

#### Запуск генерації діалогів
```bash
docker run -v $(pwd)/data:/app/data chat-analyzer python src/generate.py
```

#### Запуск аналізу діалогів
```bash
docker run -v $(pwd)/data:/app/data chat-analyzer python src/analyze.py
```

### 3. Або використовувати docker-compose
```bash
docker-compose up app
```
