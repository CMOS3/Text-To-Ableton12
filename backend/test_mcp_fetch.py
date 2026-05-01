import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp_proxy import proxy

def test_fetch():
    print("Testing fetch_resource for session state...")
    res = proxy.fetch_resource("ableton://session/state")
    print(json.dumps(res, indent=2))
    
    print("\nTesting fetch_resource for track 0 state...")
    res = proxy.fetch_resource("ableton://tracks/0/state")
    print(json.dumps(res, indent=2))
    
    print("\nTesting fetch_resource for track 0 clips...")
    res = proxy.fetch_resource("ableton://tracks/0/clips")
    print(json.dumps(res, indent=2))

    print("\nTesting fetch_resource for track 0 devices...")
    res = proxy.fetch_resource("ableton://tracks/0/devices")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test_fetch()
