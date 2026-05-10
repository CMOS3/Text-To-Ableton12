import asyncio
import gzip
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Tuple

from google import genai
from google.genai import types
from dotenv import load_dotenv

from backend.logger import get_json_logger

logger = get_json_logger(__name__)

CATALOG_PATH = Path(__file__).parent / "device_catalog.json"

def calculate_md5(file_path: Path) -> str:
    """Calculates the MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_adg_macros(adg_path: Path) -> Tuple[Dict[int, str], Dict[int, str]]:
    """
    Unzips an .adg file in memory and parses the XML to extract Macro names and annotations.
    Returns: (macro_names, macro_annotations)
    """
    names: Dict[int, str] = {}
    annotations: Dict[int, str] = {}
    
    try:
        with gzip.open(adg_path, 'rb') as f:
            xml_content = f.read()
            
        root = ET.fromstring(xml_content)
        
        # Ableton XML structure for macros is usually under <MacroControls> or <MidiEffectRack>/<InstrumentRack>/<AudioEffectRack>
        # A simpler approach is to search recursively for <MacroDisplayNames.X>
        for i in range(16):
            # ElementTree xpath doesn't support wildcards well for node names with dots, so we iterate
            name_tag = f"MacroDisplayNames.{i}"
            for elem in root.iter(name_tag):
                val = elem.get('Value', '')
                if val and not val.lower().startswith("macro "):
                    names[i] = val
                    
            annotation_tag = f"MacroAnnotations.{i}"
            for elem in root.iter(annotation_tag):
                val = elem.get('Value', '')
                if val:
                    annotations[i] = val
                    
    except Exception as e:
        logger.error(f"Failed to parse ADG XML for {adg_path.name}", extra={"extra_data": {"error": str(e)}})
        
    return names, annotations

async def generate_semantic_description(client: genai.Client, device_name: str, names: Dict[int, str], annotations: Dict[int, str]) -> Dict[str, Any]:
    """Uses Gemini to generate semantic descriptions and parameters metadata."""
    if not names:
        return {"description": "A custom rack with no descriptively mapped macros.", "parameters": {}}
        
    prompt = f"""
You are an expert Ableton Live sound designer and mixing engineer.
I have a custom Ableton Device Group (.adg) named '{device_name}'.
The user has mapped specific parameters to the 16 Macros. 
Your task is to generate a JSON schema explaining these parameters, their likely use cases, and how they should be tweaked.
Ableton macros use a 0.0 to 1.0 float scale internally via the API.

Here are the extracted macro names:
"""
    for idx, name in names.items():
        prompt += f"- Macro {idx}: {name}"
        if idx in annotations:
            prompt += f" (Explicit user instructions: {annotations[idx]})"
        prompt += "\n"
        
    prompt += """
Output ONLY a raw JSON object with the following schema:
{
  "description": "A 1-2 sentence overview of what this device likely is and when to use it.",
  "parameters": {
    "Exact Macro Name Extracted": {
        "description": "How this parameter affects the sound. Provide specific examples of values on a 0.0 to 1.0 scale (e.g. 0.0 = dark, 1.0 = bright). If explicit user instructions were provided, you MUST map them accurately to the 0.0-1.0 scale (e.g. if instruction is '0=Sine, 127=Noise', map Sine to 0.0 and Noise to 1.0).",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    }
  }
}
Do NOT output markdown code blocks. Output the raw JSON object.
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite", # Using the GA flash-lite model
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        return json.loads(text.strip())
        
    except Exception as e:
        logger.error(f"Failed to generate semantic description for {device_name}", extra={"extra_data": {"error": str(e)}})
        return {"description": "Failed to generate AI description.", "parameters": {}}


async def build_catalog():
    """Main function to scan the directory, hash, parse, and query Gemini."""
    load_dotenv()
    
    user_lib_path_str = os.environ.get("ABLETON_USER_LIBRARY_PATH")
    if not user_lib_path_str:
        logger.warning("ABLETON_USER_LIBRARY_PATH is not set in environment. Skipping dynamic catalog build.")
        return
        
    racks_dir = Path(user_lib_path_str) / "Presets" / "Text-to-Ableton"
    if not racks_dir.exists():
        logger.info(f"Creating Text-to-Ableton directory at {racks_dir}")
        racks_dir.mkdir(parents=True, exist_ok=True)
        
    # Load existing catalog to check hashes
    existing_catalog = {}
    if CATALOG_PATH.exists():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                existing_catalog = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Existing device_catalog.json is corrupt. Rebuilding from scratch.")
            
    api_key = os.environ.get("GEMINI_API_KEY")
    client = None
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        logger.warning("GEMINI_API_KEY not set. Cannot generate semantic descriptions for new racks.")
        
    new_catalog = {}
    catalog_updated = False
    
    adg_files = list(racks_dir.glob("*.adg"))
    logger.info(f"Found {len(adg_files)} custom racks in {racks_dir}")
    
    for adg_path in adg_files:
        device_name = adg_path.stem
        file_hash = calculate_md5(adg_path)
        
        if device_name in existing_catalog and existing_catalog[device_name].get("_md5") == file_hash:
            # Unchanged, keep existing data
            new_catalog[device_name] = existing_catalog[device_name]
            continue
            
        logger.info(f"Processing new or modified rack: {device_name}")
        catalog_updated = True
        
        # 1. Parse XML
        macro_names, macro_annotations = extract_adg_macros(adg_path)
        
        # 2. Enrich with Gemini
        if client and macro_names:
            semantic_data = await generate_semantic_description(client, device_name, macro_names, macro_annotations)
        else:
            semantic_data = {"description": "No description available.", "parameters": {}}
            for _, name in macro_names.items():
                semantic_data["parameters"][name] = {"description": "Custom mapped macro.", "min": 0.0, "max": 1.0, "default": 0.5}
                
        # 3. Store
        new_catalog[device_name] = {
            "description": semantic_data.get("description", ""),
            "parameters": semantic_data.get("parameters", {}),
            "_md5": file_hash
        }
        
    # Also carry over any native Ableton devices that might have been hardcoded in the old catalog if we want backward compatibility?
    # Actually, the plan says "move the system away from hardcoded device lists and build a completely dynamic, directory-driven ecosystem".
    # But let's check if the existing catalog had non-MD5 entries (i.e. factory devices).
    for key, data in existing_catalog.items():
        if "_md5" not in data and key not in new_catalog:
             # It's an old native device. Let's keep it to prevent breaking existing sessions during transition.
             new_catalog[key] = data
             
    if catalog_updated:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(new_catalog, f, indent=4)
        logger.info("Successfully rebuilt device_catalog.json")
    else:
        logger.info("No rack changes detected. Catalog is up to date.")

if __name__ == "__main__":
    asyncio.run(build_catalog())
