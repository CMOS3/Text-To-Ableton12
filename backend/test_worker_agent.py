import sys
import os
import asyncio
from pydantic import BaseModel, Field

sys.path.append('d:/Sync/Dev/AbletonMCP_with_Gemini_API')
from backend.gemini_client import WorkerAgent

# Define a strict schema for testing
class DummyClipFormatting(BaseModel):
    track_name: str = Field(..., description="The name of the track")
    tempo: float = Field(..., description="The tempo of the session")
    is_valid: bool = Field(..., description="Is the track valid?")
    
async def test_worker_agent():
    print("Testing WorkerAgent structured output generation...")
    try:
        agent = WorkerAgent()
        
        task_desc = "Extract the track name, tempo, and validity from the context."
        context_data = "We are running at 128.5 BPM. The current focus is on the 'Lead Synth' track. Yes, it is fully valid."
        
        result = await agent.execute_task(
            task_description=task_desc,
            context_data=context_data,
            response_schema=DummyClipFormatting
        )
        
        print("\n--- WorkerAgent Result ---")
        print(f"Track Name: {result.track_name}")
        print(f"Tempo: {result.tempo}")
        print(f"Is Valid: {result.is_valid}")
        
        assert result.track_name == "Lead Synth"
        assert result.tempo == 128.5
        assert result.is_valid is True
        
        print("\nWorkerAgent executed successfully and validated against Pydantic schema!")
        
    except Exception as e:
        print(f"\nWorkerAgent Test Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_worker_agent())
