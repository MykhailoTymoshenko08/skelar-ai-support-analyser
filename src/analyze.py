import json
import os
from typing import List, Dict, Any
from datetime import datetime

from src.models import AnalysisResult, AnalysisResults, IntentEnum, SatisfactionEnum
from src.llm_utils import get_llm_response_json
from src.prompts import ANALYZER_PROMPT_SUMMARY

def load_conversations(filename: str = "data/chats.json") -> List[Dict[str, Any]]:
    if not os.path.exists(filename):
        print(f"❌ File {filename} not found!")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
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

def analyze_single_conversation(conversation: Dict[str, Any]) -> Dict[str, Any]:
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
    
    result = get_llm_response_json(
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

def analyze_all_conversations(
    input_file: str = "data/chats.json",
    output_file: str = "data/analysis_results.json"
):
    print("🔍 Starting conversation analysis...")
    
    conversations = load_conversations(input_file)
    if not conversations:
        return
    
    results = []
    failed_conversations = []
    
    for i, conv in enumerate(conversations, 1):
        print(f"Analyzing conversation {i}/{len(conversations)} (ID: {conv['id']})...")
        
        try:
            analysis_data = analyze_single_conversation(conv)
            result = validate_and_create_result(conv['id'], analysis_data)
            results.append(result)
            print(f"  ✅ Quality score: {result.quality_score}/5, Satisfaction: {result.satisfaction.value}")
            
        except Exception as e:
            print(f"  ❌ Error analyzing conversation {conv['id']}: {e}")
            failed_conversations.append(conv['id'])
            continue
    
    final_results = AnalysisResults(
        results=results,
        metadata={
            "analyzed_at": datetime.now().isoformat(),
            "total_conversations": len(results),
            "failed_conversations": failed_conversations,
            "input_file": input_file,
            "analysis_temperature": 0.0
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
    
    print(f"\n✅ Results saved to: {output_file}")

if __name__ == "__main__":
    analyze_all_conversations()