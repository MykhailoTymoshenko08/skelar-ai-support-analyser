import openai
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Union, List, Optional, Dict, Any
import re
import httpx

from src.config import OPENROUTER_API_KEY, default_model, openrouter_api_base

openai.api_key = OPENROUTER_API_KEY

def get_llm_response(
    prompt: Union[str, List[Union[str, dict]]], 
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    try:
        client = httpx.Client()
        
        chat = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=OPENROUTER_API_KEY,
            base_url=openrouter_api_base,
            max_tokens=max_tokens,
            http_client=client,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Chat Analyzer"
            }
        )
        
        messages = []
        
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        if isinstance(prompt, str):
            messages.append(HumanMessage(content=prompt))
        elif isinstance(prompt, list):
            for msg in prompt:
                if isinstance(msg, str):
                    messages.append(HumanMessage(content=msg))
                elif isinstance(msg, dict):
                    if msg.get("role") == "system":
                        messages.append(SystemMessage(content=msg["content"]))
                    else:
                        messages.append(HumanMessage(content=msg["content"]))
        
        response = chat.invoke(messages)
        return response.content
        
    except Exception as e:
        print(f"Error getting LLM response: {e}")
        try:
            return fallback_llm_call(prompt, system_prompt, model, temperature, max_tokens)
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            return f"Error: {str(e)}"

def fallback_llm_call(
    prompt: Union[str, List[Union[str, dict]]],
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None
) -> str:
    client = openai.OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=openrouter_api_base
    )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    if isinstance(prompt, str):
        messages.append({"role": "user", "content": prompt})
    elif isinstance(prompt, list):
        for msg in prompt:
            if isinstance(msg, str):
                messages.append({"role": "user", "content": msg})
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                if role == "system":
                    messages.append({"role": "system", "content": msg["content"]})
                else:
                    messages.append({"role": "user", "content": msg["content"]})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content

def parse_json_response(response: str) -> Dict[str, Any]:
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        try:
            json_pattern = r'\{[^{}]*\}'
            matches = re.findall(json_pattern, response)
            
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
        except Exception:
            pass
        return {}

def get_llm_response_json(
    prompt: Union[str, List[Union[str, dict]]],
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    try:
        response = get_llm_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        parsed = parse_json_response(response)
        
        if not parsed and response and not response.startswith("Error"):
            return {"response": response}
            
        return parsed
        
    except Exception as e:
        print(f"Error in JSON response: {e}")
        return {"error": str(e)}