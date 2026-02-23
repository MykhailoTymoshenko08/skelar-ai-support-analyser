import random
import json
import os
from typing import List, Dict, Any
from datetime import datetime

from src.config import intent, intent_choices
from src.prompts import (
    CLIENT_PROMPT_FRIENDLY,
    CLIENT_PROMPT_IMPATIENT,
    CLIENT_PROMPT_CONFUSED,
    CLIENT_PROMPT_DISSATISFIED_HIDDEN,
    AGENT_PROMPT_DEFAULT,
)
from src.llm_utils import get_llm_response
from src.models import Conversation, ConversationTurn, IntentEnum

CLIENT_PERSONAS = {
    "friendly": CLIENT_PROMPT_FRIENDLY,
    "impatient": CLIENT_PROMPT_IMPATIENT,
    "confused": CLIENT_PROMPT_CONFUSED,
    "hidden_dissatisfied": CLIENT_PROMPT_DISSATISFIED_HIDDEN
}

INTENT_MAPPING = {
    intent.payment_problem: IntentEnum.PAYMENT_PROBLEM,
    intent.tech_error: IntentEnum.TECH_ERROR,
    intent.account_access: IntentEnum.ACCOUNT_ACCESS,
    intent.tariff: IntentEnum.TARIFF,
    intent.refund: IntentEnum.REFUND,
    intent.other: IntentEnum.OTHER
}

def generate_conversation(
    intent_category: str,
    client_persona_name: str,
    client_persona_prompt: str,
    max_turns: int = 6,
    include_mistakes: bool = True
) -> List[Dict[str, str]]:
    conversation = []
    scenarios = {
        intent.payment_problem: "having issues with a payment that was charged twice",
        intent.tech_error: "experiencing a technical error where the app crashes",
        intent.account_access: "unable to log into their account",
        intent.tariff: "confused about which tariff plan to choose",
        intent.refund: "wanting to request a refund for a service",
        intent.other: "having a general inquiry about the service"
    }
    
    scenario = scenarios.get(intent_category, "needing help with something")
    
    agent_instruction = AGENT_PROMPT_DEFAULT
    if include_mistakes:
        mistake_probability = random.random()
        if mistake_probability < 0.3:
            agent_instruction += """
            
            IMPORTANT: Sometimes make realistic mistakes like:
            - Being slightly impatient with repetitive questions
            - Giving incomplete information at first
            - Using technical terms without explanation
            - Forgetting to ask for important details
            - Sounding slightly frustrated
            """
    
    client_instruction = f"""{client_persona_prompt}

You are a client {scenario}.

Generate your FIRST message to customer support. Be natural and in character.
Keep it to 1-3 sentences.
"""
    
    client_message = get_llm_response(
        client_instruction,
        temperature=0.7
    )
    
    conversation.append({"role": "client", "content": client_message})
    
    for turn in range(max_turns - 1):
        agent_context = f"""Previous conversation:
{format_conversation(conversation)}

Current issue category: {intent_category}
Client persona: {client_persona_name}

{agent_instruction}

Generate the AGENT's next response. Be helpful and appropriate to the situation."""
        
        agent_response = get_llm_response(
            agent_context,
            temperature=0.5
        )
        
        conversation.append({"role": "agent", "content": agent_response})
        
        if random.random() < 0.2 and turn > 2:
            break
        
        client_context = f"""{client_persona_prompt}

You are the client. Here's the conversation so far:
{format_conversation(conversation)}

Generate your NEXT response as the client. Stay in character and react naturally to what the agent said.
Your issue is about: {scenario}
Keep responding until the issue is resolved or you're satisfied."""
        
        client_response = get_llm_response(
            client_context,
            temperature=0.7
        )
        
        conversation.append({"role": "client", "content": client_response})
        
        if random.random() < 0.15:
            break
    
    return conversation

def format_conversation(conversation: List[Dict[str, str]]) -> str:
    formatted = []
    for msg in conversation:
        role = msg["role"].capitalize()
        content = msg["content"]
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

def save_conversation(conversation_data: dict, filename: str = "data/chats.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    
    existing_data.append(conversation_data)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

def generate_dataset(
    num_conversations: int = 10,
    output_file: str = "data/chats.json"
):
    print(f"Starting generation of {num_conversations} conversations...")
    
    for i in range(num_conversations):
        intent_category = random.choice(intent_choices)
        persona_name = random.choice(list(CLIENT_PERSONAS.keys()))
        client_persona = CLIENT_PERSONAS[persona_name]
        
        print(f"Generating conversation {i+1}/{num_conversations}: {intent_category} - {persona_name}")
        
        raw_conversation = generate_conversation(
            intent_category=intent_category,
            client_persona_name=persona_name,
            client_persona_prompt=client_persona,
            max_turns=random.randint(4, 8),
            include_mistakes=True
        )
        
        turns = [
            ConversationTurn(role=msg["role"], content=msg["content"])
            for msg in raw_conversation
        ]
        
        conversation = Conversation(
            id=i + 1,
            intent=INTENT_MAPPING[intent_category],
            client_persona=persona_name,
            turns=turns,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "model_used": "arcee-ai/trinity-large-preview:free",
                "temperature_client": 0.7,
                "temperature_agent": 0.5
            }
        )
        
        save_conversation(conversation.model_dump(), output_file)
    
    print(f"\n✅ Successfully generated {num_conversations} conversations!")
    print(f"📁 Saved to: {output_file}")

if __name__ == "__main__":
    generate_dataset(num_conversations=5)