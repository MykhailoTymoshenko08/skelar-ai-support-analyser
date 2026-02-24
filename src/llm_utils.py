import openai
import json
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Union, List, Optional, Dict, Any
import re

from src.config import OPENROUTER_API_KEY, default_model, openrouter_api_base

openai.api_key = OPENROUTER_API_KEY

async def get_llm_response_async(
    prompt: Union[str, List[Union[str, dict]]], 
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            chat = ChatOpenAI(
                model=model,
                temperature=temperature,
                openai_api_key=OPENROUTER_API_KEY,
                base_url=openrouter_api_base,
                max_tokens=max_tokens,
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
            
            response = await chat.ainvoke(messages)
            return response.content
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️ Rate limit hit. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Max retries reached. Rate limit error: {e}")
            else:
                print(f"Error getting LLM response: {e}")
            
            if attempt == max_retries - 1:
                try:
                    return await fallback_llm_call_async(prompt, system_prompt, model, temperature, max_tokens)
                except Exception as fallback_error:
                    print(f"Fallback also failed: {fallback_error}")
                    return f"Error: {str(e)}"
    
    return f"Error: Max retries exceeded"

async def fallback_llm_call_async(
    prompt: Union[str, List[Union[str, dict]]],
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None
) -> str:
    client = openai.AsyncOpenAI(
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
    
    response = await client.chat.completions.create(
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

async def get_llm_response_json_async(
    prompt: Union[str, List[Union[str, dict]]],
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    try:
        response = await get_llm_response_async(
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

def get_llm_response(
    prompt: Union[str, List[Union[str, dict]]], 
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    return asyncio.run(get_llm_response_async(
        prompt, system_prompt, model, temperature, max_tokens, response_format
    ))

def get_llm_response_json(
    prompt: Union[str, List[Union[str, dict]]],
    system_prompt: Optional[str] = None,
    model: str = default_model,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    return asyncio.run(get_llm_response_json_async(
        prompt, system_prompt, model, temperature, max_tokens
    ))