import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

def count_tokens():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Sample data
    data = [
        {"name": "Filter Freq", "min": 0.0, "max": 22000.0, "value": 150.0, "quantized": False},
        {"name": "Filter Res", "min": 0.0, "max": 1.0, "value": 0.5, "quantized": False},
        {"name": "Osc A Level", "min": -inf if False else -70.0, "max": 0.0, "value": -12.0, "quantized": False}
    ]
    
    # Minified JSON
    json_str = json.dumps(data, separators=(',', ':'))
    
    # Fake TOON (removing quotes from keys, basic compression)
    toon_str = "[{name:'Filter Freq',min:0.0,max:22000.0,value:150.0,quantized:False},{name:'Filter Res',min:0.0,max:1.0,value:0.5,quantized:False},{name:'Osc A Level',min:-70.0,max:0.0,value:-12.0,quantized:False}]"
    
    res_json = client.models.count_tokens(
        model='models/gemini-3.1-flash-lite-preview',
        contents=json_str
    )
    
    res_toon = client.models.count_tokens(
        model='models/gemini-3.1-flash-lite-preview',
        contents=toon_str
    )
    
    print(f"JSON Tokens: {res_json.total_tokens}")
    print(f"TOON Tokens: {res_toon.total_tokens}")

if __name__ == "__main__":
    count_tokens()
