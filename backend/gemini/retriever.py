import json
import logging
import os

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend import schema

logger = logging.getLogger(__name__)

class RetrieverAgent:
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-3.1-flash-lite-preview"
        self.prompt_tokens = 0
        self.candidate_tokens = 0

    async def execute_task(
        self, task_description: str, context_data: str, response_schema: type, max_retries: int = 2
    ):
        """
        Executes a localized task using Flash-Lite, enforcing Structured Outputs and
        utilizing a self-correction loop for validation errors.
        """
        prompt = f"TASK:\n{task_description}\n\nCONTEXT:\n{context_data}\n\nIMPORTANT: You must output ONLY a valid JSON object matching the requested schema. No markdown wrapping."

        config = types.GenerateContentConfig(
            temperature=0.0, response_mime_type="application/json", response_schema=response_schema
        )

        for attempt in range(max_retries + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
                    ],
                    config=config,
                )

                if response.usage_metadata:
                    self.prompt_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                    self.candidate_tokens += getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    )

                if not response.text:
                    raise ValueError("Empty response from model.")

                data = json.loads(response.text)
                validated_obj = response_schema(**data)
                return validated_obj

            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                if attempt == max_retries:
                    raise Exception(
                        f"RetrieverAgent failed to produce valid JSON after {max_retries} retries. Error: {str(e)}"
                    ) from e

                # JSON Patch Refinement: Feed the exact error back to the model
                error_msg = str(e)
                prompt += f"\n\nERROR ON PREVIOUS ATTEMPT:\nThe parser threw this error:\n{error_msg}\n\nPlease analyze the error and output a corrected JSON payload that strictly matches the schema."

    async def search_catalog(self, device_name: str, intent: str) -> str:
        """Searches the local device_catalog.json for parameters matching the intent."""
        # Note: device_catalog.json is still in backend/
        catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "device_catalog.json"
        )
        try:
            with open(catalog_path, encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception as e:
            return f"Error loading catalog: {e}"

        # Case insensitive key matching since Planner might pass 'wavetable' instead of 'Wavetable'
        target_key = None
        for k in catalog.keys():
            if k.lower() == device_name.lower():
                target_key = k
                break

        if not target_key:
            return f"Device '{device_name}' not found in the ground-truth catalog. (Available: {', '.join(catalog.keys())})"

        device_params = catalog[target_key].get("parameters", [])

        task_description = f"The Planner wants to achieve this intent: '{intent}' on the device '{device_name}'. Find all relevant parameters."
        context_data = json.dumps(device_params)

        try:
            response = await self.execute_task(
                task_description=task_description,
                context_data=context_data,
                response_schema=schema.RetrieverSearchResponse,
                max_retries=2,
            )
            return response.model_dump_json()
        except Exception as e:
            return f"Retriever search failed: {e}"

    async def generate_session_title(self, first_prompt: str) -> str:
        """Generates a short, concise title (max 4 words) for a session based on the first prompt."""
        task_description = "Generate a concise title (maximum 4 words) for a music production session based on the user's first prompt. Respond ONLY with the title string, no quotes."
        context_data = first_prompt

        prompt = f"TASK:\n{task_description}\n\nUSER PROMPT:\n{context_data}"

        config = types.GenerateContentConfig(temperature=0.7, response_mime_type="text/plain")

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                config=config,
            )
            title = response.text.strip().replace('"', "")
            return title if title else "Untitled Session"
        except Exception as e:
            logger.error(f"Failed to generate session title: {e}")
            return "Untitled Session"
