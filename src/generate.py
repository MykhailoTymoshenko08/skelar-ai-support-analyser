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

import re

def _strip_role_prefix(text: str) -> str:
    """Remove role prefixes like 'Client:', 'User:', 'CLIENT:' that LLMs sometimes prepend."""
    return re.sub(r'^(?:client|user|customer)\s*:\s*["\']?', '', text.strip(), flags=re.IGNORECASE).lstrip('"\'')


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
}

SCENARIOS = {
    intent.payment_problem: [
        "having issues with a payment that was charged twice on their credit card",
        "standing at a checkout in a store right now and their card is being declined despite having funds",
        "noticing an unauthorized charge on their account from yesterday",
        "trying to pay for a subscription but the payment keeps failing at the last step",
    ],
    intent.tech_error: [
        "experiencing a critical technical error where the app crashes every time they try to open it",
        "unable to load anything in the app for the past 2 hours — they have an important meeting in 30 minutes",
        "getting a '500 Internal Server Error' on every page after updating the app",
        "having their session log out every 5 minutes making it impossible to do anything",
    ],
    intent.account_access: [
        "completely locked out of their account and cannot access critical work documents inside",
        "unable to log in — the 2FA code never arrives to their phone",
        "their account seems to have been hacked — they see unfamiliar activity",
        "reset their password three times but still cannot log in",
    ],
    intent.tariff: [
        "confused about which tariff plan to choose before their trial ends tomorrow",
        "just got charged for a premium plan they never knowingly upgraded to",
        "trying to understand why their bill is 40% higher this month than last month",
        "wanting to downgrade their plan but the option is greyed out in the UI",
    ],
    intent.refund: [
        "wanting to request a refund for a service they were charged for but never received",
        "cancelled their subscription 2 weeks ago but is still being charged",
        "received a completely different product/service than what was advertised and wants money back",
        "was promised a refund 10 days ago and it still hasn't appeared on their account",
    ],
    intent.other: [
        "having a general inquiry about the service features",
        "looking for information about data privacy and how their data is stored",
    ],
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


URGENCY_CONTEXTS = {
    intent.payment_problem: [
        "URGENT CONTEXT: The client is physically standing at a store checkout RIGHT NOW. Their card is declining in front of other customers. They are embarrassed and stressed.",
        "URGENT CONTEXT: The client needs to pay for a medical service in the next hour. The failed payment is blocking them.",
        "",
        "",
    ],
    intent.tech_error: [
        "URGENT CONTEXT: The client has a critical work presentation in 45 minutes and the app is broken. Their job may depend on this.",
        "URGENT CONTEXT: The client is a small business owner — they cannot process any customer orders because of this tech error. They are losing money every minute.",
        "",
        "",
    ],
    intent.account_access: [
        "URGENT CONTEXT: The client is locked out right before an important deadline. They need their documents NOW.",
        "",
        "",
    ],
    intent.tariff: [
        "URGENT CONTEXT: The client's trial expires TODAY in a few hours. If they can't decide, they'll lose their data.",
        "",
        "",
    ],
    intent.refund: [
        "URGENT CONTEXT: The client has been waiting 2 weeks for this refund and their rent is due tomorrow.",
        "",
        "",
    ],
    intent.other: ["", ""],
}


async def generate_conversation_async(
    intent_category: str,
    client_persona_name: str,
    client_persona_prompt: str,
    max_turns: int = 6,
    include_mistakes: bool = True,
) -> List[Dict[str, str]]:
    scenario_list = SCENARIOS.get(intent_category, ["needing help with something"])
    scenario = random.choice(scenario_list)

    urgency_list = URGENCY_CONTEXTS.get(intent_category, [""])
    urgency_context = random.choice(urgency_list)

    agent_instruction = AGENT_PROMPT_DEFAULT
    if include_mistakes and random.random() < 0.3:
        agent_instruction += MISTAKE_HINT

    conversation: List[Dict[str, str]] = []

    urgency_instruction = f"\n\n{urgency_context}" if urgency_context else ""

    client_message = await get_llm_response_async(
        f"{client_persona_prompt}\n\nYou are a client {scenario}.{urgency_instruction}\n"
        "Generate your FIRST message to customer support. Be natural, emotional, and in character. Keep it to 1-3 sentences.\n"
        "CRITICAL: Do NOT start your message with 'Client:', 'User:', or any role label. Write only the message itself.",
        temperature=0.8,
    )
    client_message = _strip_role_prefix(client_message)
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

        urgency_line = f"\n{urgency_context}" if urgency_context else ""
        client_response = await get_llm_response_async(
            f"{client_persona_prompt}\n\nYou are the client. Here's the conversation so far:\n{format_conversation(conversation)}\n\n"
            f"Generate your NEXT response as the client. Stay in character and react naturally to what the agent said.\n"
            f"Your issue is about: {scenario}{urgency_line}\n"
            "Keep responding until the issue is resolved or you're satisfied.\n"
            "CRITICAL: Do NOT start your message with 'Client:', 'User:', or any role label. Write only the message itself.",
            temperature=0.8,
        )
        client_response = _strip_role_prefix(client_response)
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
    print(f"Generating {n} conversations (concurrency={concurrency_limit}, turns={max_turns_min}–{max_turns_max})...")

    semaphore = asyncio.Semaphore(concurrency_limit)

    async def _generate(i: int) -> Dict[str, Any]:
        async with semaphore:
            return await generate_single_conversation_async(i)

    start = datetime.now()
    conversations = await asyncio.gather(*[_generate(i) for i in range(n)])
    elapsed = (datetime.now() - start).total_seconds()

    save_all_conversations(list(conversations), output_file)

    print(f"\nGenerated {n} conversations in {elapsed:.1f}s")
    print(f"Saved to: {output_file}")


def generate_dataset(
    n: int = num_conversations,
    output_file: str = chats_file,
    concurrency_limit: int = generation_concurrency,
) -> None:
    asyncio.run(generate_dataset_async(n, output_file, concurrency_limit))


if __name__ == "__main__":
    generate_dataset()