import json
import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from src.models import AnalysisResult, AnalysisResults, IntentEnum, SatisfactionEnum
from src.llm_utils import get_llm_response_json_async
from src.prompts import ANALYZER_PROMPT_SUMMARY

async def load_conversations_async(filename: str = "data/chats.json") -> List[Dict[str, Any]]:
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found!")
        return []
    
    loop = asyncio.get_event_loop()
    with open(filename, 'r', encoding='utf-8') as f:
        try:
            data = await loop.run_in_executor(None, json.load, f)
            print(f"✅ Loaded {len(data)} conversations from {filename}")
            return data
        except json.JSONDecodeError as e:
            print(f"❌ Error loading JSON: {e}")
            return []

def format_conversation_for_analysis(conversation: Dict[str, Any]) -> str:
    formatted = []
    for turn in conversation['turns']:
        role = turn['role'].capitalize()
        content = turn['content']
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

async def analyze_single_conversation_async(conversation: Dict[str, Any]) -> Dict[str, Any]:
    conversation_text = format_conversation_for_analysis(conversation)
    
    analysis_prompt = f"""Analyze this customer service conversation:

{conversation_text}

{ANALYZER_PROMPT_SUMMARY}

Return your analysis as JSON with these fields:
- intent: string (payment_problem/tech_error/account_access/tariff/refund/other)
- satisfaction: string (satisfied/neutral/dissatisfied/hidden_dissatisfaction)
- quality_score: integer (1-5, where 5 is best)
- agent_mistakes: list of strings from: ignored_question, incorrect_info, rude_tone, no_resolution, unnecessary_escalation, incomplete_info, tech_jargon, impatient
- resolution_status: string (resolved/partially_resolved/unresolved)
- hidden_dissatisfaction_score: float (0.0 to 1.0)
- key_action_items: list of strings
- agent_performance: string (good/adequate/poor)
- detected_persona: string (friendly/impatient/confused/hidden_dissatisfied)

Be precise and objective in your analysis."""
    
    result = await get_llm_response_json_async(
        analysis_prompt,
        temperature=0.0
    )
    
    return result

def validate_and_create_result(conversation_id: int, analysis_data: Dict[str, Any]) -> AnalysisResult:
    intent_mapping = {
        "payment_problem": IntentEnum.PAYMENT_PROBLEM,
        "tech_error": IntentEnum.TECH_ERROR,
        "account_access": IntentEnum.ACCOUNT_ACCESS,
        "tariff": IntentEnum.TARIFF,
        "refund": IntentEnum.REFUND,
        "other": IntentEnum.OTHER
    }
    
    satisfaction_mapping = {
        "satisfied": SatisfactionEnum.SATISFIED,
        "neutral": SatisfactionEnum.NEUTRAL,
        "dissatisfied": SatisfactionEnum.DISSATISFIED,
        "hidden_dissatisfaction": SatisfactionEnum.HIDDEN_DISSATISFACTION
    }
    
    result = AnalysisResult(
        conversation_id=conversation_id,
        intent=intent_mapping.get(analysis_data.get('intent', 'other'), IntentEnum.OTHER),
        satisfaction=satisfaction_mapping.get(analysis_data.get('satisfaction', 'neutral'), SatisfactionEnum.NEUTRAL),
        quality_score=analysis_data.get('quality_score', 3),
        agent_mistakes=analysis_data.get('agent_mistakes', []),
        resolution_status=analysis_data.get('resolution_status', 'unknown'),
        hidden_dissatisfaction_score=analysis_data.get('hidden_dissatisfaction_score', 0.0),
        key_action_items=analysis_data.get('key_action_items', []),
        agent_performance=analysis_data.get('agent_performance', 'adequate'),
        detected_persona=analysis_data.get('detected_persona', 'unknown')
    )
    
    return result

async def analyze_all_conversations_async(
    input_file: str = "data/chats.json",
    output_file: str = "data/analysis_results.json",
    concurrency_limit: int = 10
):
    print("Starting conversation analysis...")
    
    conversations = await load_conversations_async(input_file)
    if not conversations:
        return
    
    results = []
    failed_conversations = []
    
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def analyze_with_semaphore(conv):
        async with semaphore:
            try:
                analysis_data = await analyze_single_conversation_async(conv)
                result = validate_and_create_result(conv['id'], analysis_data)
                return result, None
            except Exception as e:
                return None, (conv['id'], str(e))
    
    tasks = [analyze_with_semaphore(conv) for conv in conversations]
    task_results = await asyncio.gather(*tasks)
    
    for i, (result, error) in enumerate(task_results, 1):
        if result:
            results.append(result)
            print(f"  ✅ Conversation {i}/{len(conversations)}: Quality {result.quality_score}/5, Satisfaction: {result.satisfaction.value}")
        else:
            conv_id, error_msg = error
            failed_conversations.append(conv_id)
            print(f"  ❌ Conversation {i}/{len(conversations)} (ID: {conv_id}) failed: {error_msg}")
    
    final_results = AnalysisResults(
        results=results,
        metadata={
            "analyzed_at": datetime.now().isoformat(),
            "total_conversations": len(results),
            "failed_conversations": failed_conversations,
            "input_file": input_file,
            "analysis_temperature": 0.0,
            "concurrency_limit": concurrency_limit
        }
    )
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results.model_dump(), f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("📊 ANALYSIS SUMMARY")
    print("="*60)
    print(f"Total conversations analyzed: {len(results)}")
    print(f"Failed conversations: {len(failed_conversations)}")
    
    if results:
        sat_counts = {}
        for r in results:
            sat_counts[r.satisfaction.value] = sat_counts.get(r.satisfaction.value, 0) + 1
        
        print("\nSatisfaction distribution:")
        for sat, count in sat_counts.items():
            print(f"  {sat}: {count}")
        
        avg_score = sum(r.quality_score for r in results) / len(results)
        print(f"\nAverage quality score: {avg_score:.2f}/5")
        
        hidden_scores = [r.hidden_dissatisfaction_score for r in results]
        avg_hidden = sum(hidden_scores) / len(hidden_scores)
        print(f"Average hidden dissatisfaction score: {avg_hidden:.2f}")
        
        mistake_counts = {}
        for r in results:
            for mistake in r.agent_mistakes:
                mistake_counts[mistake] = mistake_counts.get(mistake, 0) + 1
        
        if mistake_counts:
            print("\nTop agent mistakes:")
            for mistake, count in sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"  {mistake}: {count}")
    
    print(f"\n✅ Results saved to: {output_file}")

def analyze_all_conversations(
    input_file: str = "data/chats.json",
    output_file: str = "data/analysis_results.json",
    concurrency_limit: int = 10
):
    asyncio.run(analyze_all_conversations_async(input_file, output_file, concurrency_limit))

if __name__ == "__main__":
    analyze_all_conversations(concurrency_limit=10)