import json
import os
from typing import Optional, Type, Any

from google import genai
from google.genai import types
from pydantic import ValidationError, BaseModel

from backend import schema
from backend.exceptions import LLMGenerationError, SchemaValidationError
from backend.logger import get_json_logger

logger = get_json_logger(__name__)

class RetrieverAgent:
    """Agent responsible for semantic catalog searches and executing localized structured extraction tasks."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-3.1-flash-lite-preview"
        self.prompt_tokens = 0
        self.candidate_tokens = 0

    async def execute_task(
        self, task_description: str, context_data: str, response_schema: Type[BaseModel], max_retries: int = 2
    ) -> BaseModel:
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
                    contents=prompt,
                    config=config,
                )

                if response.usage_metadata:
                    self.prompt_tokens += getattr(response.usage_metadata, "prompt_token_count", 0)
                    self.candidate_tokens += getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    )

                if not response.text:
                    raise LLMGenerationError("Empty response from Flash model.")

                data = json.loads(response.text)
                validated_obj = response_schema(**data)
                return validated_obj

            except (json.JSONDecodeError, ValidationError, LLMGenerationError) as e:
                logger.warning(f"Retriever parsing failed on attempt {attempt}", extra={"extra_data": {"error": str(e)}})
                
                if attempt == max_retries:
                    logger.error("Retriever max retries reached.", exc_info=True)
                    raise SchemaValidationError(
                        f"RetrieverAgent failed to produce valid JSON after {max_retries} retries. Error: {str(e)}"
                    ) from e

                # JSON Patch Refinement: Feed the exact error back to the model
                error_msg = str(e)
                prompt += f"\n\nERROR ON PREVIOUS ATTEMPT:\nThe parser threw this error:\n{error_msg}\n\nPlease analyze the error and output a corrected JSON payload that strictly matches the schema."

        raise LLMGenerationError("Unexpected fallback exit in execute_task loop.")

    async def search_catalog(self, device_name: str, intent: str) -> str:
        """Searches the local device_catalog.json for parameters matching the intent."""
        catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "device_catalog.json"
        )
        try:
            with open(catalog_path, encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception as e:
            logger.error("Failed to load device catalog", exc_info=True)
            return f"Error loading catalog: {e}"

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
        except SchemaValidationError as e:
            return f"Retriever schema validation failed: {e}"
        except Exception as e:
            logger.error("Retriever search failed", exc_info=True)
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
                contents=prompt,
                config=config,
            )
            title = response.text.strip().replace('"', "") if response.text else "Untitled Session"
            return title if title else "Untitled Session"
        except Exception as e:
            logger.error("Failed to generate session title", exc_info=True)
            return "Untitled Session"
