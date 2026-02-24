import random
import json
import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from src.config import (
    intent, intent_choices,
    num_conversations, max_turns_min, max_turns_max,
    generation_concurrency, chats_file,
)
from src.prompts import (
    CLIENT_PROMPT_FRIENDLY,
    CLIENT_PROMPT_IMPATIENT,
    CLIENT_PROMPT_CONFUSED,
    CLIENT_PROMPT_DISSATISFIED_HIDDEN,
    AGENT_PROMPT_DEFAULT,
)
from src.llm_utils import get_llm_response_async
from src.models import Conversation, ConversationTurn, IntentEnum

CLIENT_PERSONAS = {
    "friendly": CLIENT_PROMPT_FRIENDLY,
    "impatient": CLIENT_PROMPT_IMPATIENT,
    "confused": CLIENT_PROMPT_CONFUSED,
    "hidden_dissatisfied": CLIENT_PROMPT_DISSATISFIED_HIDDEN,
}

INTENT_MAPPING = {
    intent.payment_problem: IntentEnum.PAYMENT_PROBLEM,
    intent.tech_error: IntentEnum.TECH_ERROR,
    intent.account_access: IntentEnum.ACCOUNT_ACCESS,
    intent.tariff: IntentEnum.TARIFF,
    intent.refund: IntentEnum.REFUND,
    intent.other: IntentEnum.OTHER,
}

SCENARIOS = {
    intent.payment_problem: "having issues with a payment that was charged twice",
    intent.tech_error: "experiencing a technical error where the app crashes",
    intent.account_access: "unable to log into their account",
    intent.tariff: "confused about which tariff plan to choose",
    intent.refund: "wanting to request a refund for a service",
    intent.other: "having a general inquiry about the service",
}

MISTAKE_HINT = """
IMPORTANT: Sometimes make realistic mistakes like:
- Being slightly impatient with repetitive questions
- Giving incomplete information at first
- Using technical terms without explanation
- Forgetting to ask for important details
- Sounding slightly frustrated
"""


def format_conversation(conversation: List[Dict[str, str]]) -> str:
    return "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" for msg in conversation
    )


async def generate_conversation_async(
    intent_category: str,
    client_persona_name: str,
    client_persona_prompt: str,
    max_turns: int = 6,
    include_mistakes: bool = True,
) -> List[Dict[str, str]]:
    scenario = SCENARIOS.get(intent_category, "needing help with something")

    agent_instruction = AGENT_PROMPT_DEFAULT
    if include_mistakes and random.random() < 0.3:
        agent_instruction += MISTAKE_HINT

    conversation: List[Dict[str, str]] = []

    client_message = await get_llm_response_async(
        f"{client_persona_prompt}\n\nYou are a client {scenario}.\n"
        "Generate your FIRST message to customer support. Be natural and in character. Keep it to 1-3 sentences.",
        temperature=0.7,
    )
    conversation.append({"role": "client", "content": client_message})

    for turn in range(max_turns - 1):
        history = format_conversation(conversation)

        agent_response = await get_llm_response_async(
            f"Previous conversation:\n{history}\n\n"
            f"Current issue category: {intent_category}\n"
            f"Client persona: {client_persona_name}\n\n"
            f"{agent_instruction}\n\n"
            "Generate the AGENT's next response. Be helpful and appropriate to the situation.",
            temperature=0.5,
        )
        conversation.append({"role": "agent", "content": agent_response})

        if turn > 2 and random.random() < 0.2:
            break

        client_response = await get_llm_response_async(
            f"{client_persona_prompt}\n\nYou are the client. Here's the conversation so far:\n{format_conversation(conversation)}\n\n"
            f"Generate your NEXT response as the client. Stay in character and react naturally to what the agent said.\n"
            f"Your issue is about: {scenario}\n"
            "Keep responding until the issue is resolved or you're satisfied.",
            temperature=0.7,
        )
        conversation.append({"role": "client", "content": client_response})

        if random.random() < 0.15:
            break

    return conversation


async def generate_single_conversation_async(i: int) -> Dict[str, Any]:
    intent_category = random.choice(intent_choices)
    persona_name = random.choice(list(CLIENT_PERSONAS.keys()))
    client_persona = CLIENT_PERSONAS[persona_name]

    print(f"  Generating conversation {i + 1}: {intent_category} – {persona_name}")

    raw_conversation = await generate_conversation_async(
        intent_category=intent_category,
        client_persona_name=persona_name,
        client_persona_prompt=client_persona,
        max_turns=random.randint(max_turns_min, max_turns_max),
        include_mistakes=True,
    )

    turns = [ConversationTurn(role=msg["role"], content=msg["content"]) for msg in raw_conversation]

    conversation = Conversation(
        id=i + 1,
        intent=INTENT_MAPPING[intent_category],
        client_persona=persona_name,
        turns=turns,
        metadata={
            "generated_at": datetime.now().isoformat(),
            "model_used": "arcee-ai/trinity-large-preview:free",
            "temperature_client": 0.7,
            "temperature_agent": 0.5,
        },
    )

    return conversation.model_dump()


def save_all_conversations(conversations: List[Dict[str, Any]], filename: str) -> None:
    """Зберігає всі розмови за один запис — без повторного читання файлу."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    existing: List[Dict[str, Any]] = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = []

    existing.extend(conversations)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


async def generate_dataset_async(
    n: int = num_conversations,
    output_file: str = chats_file,
    concurrency_limit: int = generation_concurrency,
) -> None:
    print(f"🚀 Generating {n} conversations (concurrency={concurrency_limit}, turns={max_turns_min}–{max_turns_max})...")

    semaphore = asyncio.Semaphore(concurrency_limit)

    async def _generate(i: int) -> Dict[str, Any]:
        async with semaphore:
            return await generate_single_conversation_async(i)

    start = datetime.now()
    conversations = await asyncio.gather(*[_generate(i) for i in range(n)])
    elapsed = (datetime.now() - start).total_seconds()

    # Single write instead of N read-modify-write cycles
    save_all_conversations(list(conversations), output_file)

    print(f"\n✅ Generated {n} conversations in {elapsed:.1f}s")
    print(f"📁 Saved to: {output_file}")


def generate_dataset(
    n: int = num_conversations,
    output_file: str = chats_file,
    concurrency_limit: int = generation_concurrency,
) -> None:
    asyncio.run(generate_dataset_async(n, output_file, concurrency_limit))


if __name__ == "__main__":
    generate_dataset()