import os
import sys
import json
import ast

# Ensure we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.mcp_proxy import proxy

def extract_schemas():
    print("Fetching session tracks...")
    session_res = proxy.request_state("get_session_info")
    if session_res.get("status") != "success":
        print(f"Error fetching session: {session_res}")
        return

    data = session_res.get("data", {})
    if isinstance(data, dict) and "result" in data:
        session_data = data["result"]
    else:
        session_data = data
        
    if isinstance(session_data, str):
        class CatchAll(dict):
            def __getitem__(self, key):
                if key == "False": return False
                if key == "True": return True
                if key == "None": return None
                return key
        try:
            session_data = eval(session_data, {}, CatchAll())
        except Exception as e:
            print(f"Failed to parse session data TOON: {e}")
            return

    tracks = session_data.get("tracks", [])
    if not tracks:
        print("No tracks found in the session. Please open Ableton and add tracks.")
        return

    catalog = {}
    
    for i, track in enumerate(tracks):
        track_name = track.get("name")
        print(f"\nInspecting track {i}: '{track_name}'")
        
        # We fetch device 0 parameters (assuming 1 device per track)
        try:
            param_res = proxy.request_state("get_device_parameters", {"track_index": i, "device_index": 0})
            if param_res.get("status") != "success":
                print(f"  -> Failed or no device: {param_res.get('message', param_res)}")
                continue
                
            res_data = param_res.get("data", {})
            if isinstance(res_data, dict) and "result" in res_data:
                params_str = res_data["result"]
            else:
                params_str = res_data

            # Safely evaluate the TOON string to a standard Python list/dict
            if isinstance(params_str, str):
                class CatchAll(dict):
                    def __getitem__(self, key):
                        if key == "False": return False
                        if key == "True": return True
                        if key == "None": return None
                        return key
                try:
                    params = eval(params_str, {}, CatchAll())
                except Exception as eval_e:
                    print(f"  -> Failed to evaluate TOON string: {eval_e}")
                    continue
            else:
                params = params_str

            catalog[track_name] = params
            print(f"  -> Successfully scraped {len(params)} parameters.")
            
        except Exception as e:
            print(f"  -> Error getting parameters: {e}")
            
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_catalog.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"\nSaved ground-truth catalog to {output_path}")

if __name__ == "__main__":
    extract_schemas()
