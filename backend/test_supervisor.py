import sys
import os
import asyncio
import json

sys.path.append('d:/Sync/Dev/AbletonMCP_with_Gemini_API')
from backend.gemini_client import CreativePlannerAgent

async def test_supervisor():
    print("Testing CreativePlannerAgent E2E ReAct flow...")
    try:
        agent = CreativePlannerAgent()
        
        # This prompt should force the Supervisor to:
        # 1. Realize it needs track details or device details
        # 2. Issue a fetch_resource command
        # 3. Receive the JIT context
        # 4. Delegate to the Worker to generate precise 'sound_design' and 'inject_midi' schemas
        user_prompt = "On track Midi Track 1, add an Operator device, make it sound like a plucky bass, and create a 4-bar clip with a groovy baseline."
        
        print(f"\nUser Prompt: {user_prompt}\n")
        print("--- Supervisor Stream ---")
        
        async for chunk in agent.chat(user_prompt=user_prompt, require_approval=True):
            data = json.loads(chunk)
            msg_type = data.get("type")
            if msg_type == "status":
                print(f"[STATUS] {data.get('message')}")
            elif msg_type == "approval_required":
                print(f"\n[APPROVAL REQUIRED] Actions proposed by Supervisor:")
                print(json.dumps(data.get("actions"), indent=2))
                # For testing purposes, we automatically approve
                agent.is_approved = True
                agent.approval_event.set()
            elif msg_type == "final":
                print(f"\n[FINAL RESPONSE]")
                print(data.get("data", {}).get("response", ""))
                print(f"\nTokens used: Input {data.get('data', {}).get('input_tokens')} / Output {data.get('data', {}).get('output_tokens')}")
            else:
                print(f"[{msg_type.upper()}] {chunk.strip()}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_supervisor())
