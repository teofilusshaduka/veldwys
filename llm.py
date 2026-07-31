import os
import json
import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Standardized tool definition format:
# [
#   {
#       "name": "get_rainfall",
#       "description": "Fetch rainfall data",
#       "parameters": {
#           "type": "object",
#           "properties": {
#               "lat": {"type": "number"},
#               "lon": {"type": "number"}
#           },
#           "required": ["lat", "lon"]
#       }
#   }
# ]

def convert_tools_for_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    converted = []
    for t in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"]
            }
        })
    return converted

def convert_tools_for_anthropic(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    converted = []
    for t in tools:
        converted.append({
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"]
        })
    return converted

def convert_messages_for_anthropic(messages: List[Dict[str, Any]]) -> (str, List[Dict[str, Any]]):
    system_prompt = ""
    anthropic_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_prompt += m["content"] + "\n"
        elif m["role"] in ["user", "assistant"]:
            if "tool_calls" in m:
                # Handle tool calls conversion (simplified)
                tool_use_content = []
                if m.get("content"):
                    tool_use_content.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    tool_use_content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"])
                    })
                anthropic_msgs.append({"role": "assistant", "content": tool_use_content})
            elif "tool_call_id" in m:
                # Handle tool result
                anthropic_msgs.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m["tool_call_id"],
                        "content": m["content"]
                    }]
                })
            else:
                anthropic_msgs.append({"role": m["role"], "content": m["content"]})
    return system_prompt.strip(), anthropic_msgs

async def call_openai(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
    # If system_prompt is passed, we might need to prepend it, but usually it's in the messages array
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=convert_tools_for_openai(tools) if tools else None,
            temperature=0.2,
            max_tokens=700
        )
        msg = response.choices[0].message
        
        if msg.tool_calls:
            return {
                "provider": "openai",
                "tool_calls": [{
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                } for tc in msg.tool_calls]
            }
        else:
            return {
                "provider": "openai",
                "text": msg.content
            }
    except Exception as e:
        raise Exception(f"OpenAI error: {e}")

async def call_anthropic(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    system_prompt, anthropic_msgs = convert_messages_for_anthropic(messages)
    try:
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5",
            system=system_prompt,
            messages=anthropic_msgs,
            tools=convert_tools_for_anthropic(tools) if tools else None,
            temperature=0.2,
            max_tokens=700
        )
        
        # Parse Anthropic response
        tool_calls = []
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })
                
        if tool_calls:
            return {
                "provider": "anthropic",
                "text": text, # Anthropic can return text and tool calls together
                "tool_calls": tool_calls
            }
        else:
            return {
                "provider": "anthropic",
                "text": text
            }
    except Exception as e:
        raise Exception(f"Anthropic error: {e}")

async def respond(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], provider: str = "openai") -> Dict[str, Any]:
    """Unified responder with failover."""
    if provider == "openai" or provider == "auto":
        try:
            return await call_openai(messages, tools)
        except Exception as e:
            print(f"Primary provider failed: {e}. Failing over to Anthropic...")
            return await call_anthropic(messages, tools)
    elif provider == "anthropic":
        return await call_anthropic(messages, tools)
    else:
        raise ValueError("Unknown provider")
