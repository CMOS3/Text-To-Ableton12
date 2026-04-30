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
        
        # This prompt should force the Planner to:
        # 1. Load Wavetable
        # 2. Call search_device_parameters("Wavetable", "filter 1 cutoff and resonance")
        # 3. Use the exact internal names to set_device_parameter_batch
        user_prompt = "On track 0, load the Wavetable instrument. Use the search tool to find the parameters for Filter 1 frequency/cutoff and resonance. Set the frequency to maximum and resonance to a little bit above zero."
        
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
                d = data.get("data", {})
                print(f"\nTokens used: PRO Input {d.get('pro_input_tokens')} / PRO Output {d.get('pro_output_tokens')} | FLASH Input {d.get('flash_input_tokens')} / FLASH Output {d.get('flash_output_tokens')}")
            else:
                print(f"[{msg_type.upper()}] {chunk.strip()}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_supervisor())
