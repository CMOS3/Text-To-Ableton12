import json
with open('backend/device_catalog.json') as f:
    d = json.load(f)
for k, v in d.items():
    print(f"\n--- {k} ---")
    for p in v['parameters']:
        # Filter for some common parameters to show the user
        name = p['name'].lower()
        if any(x in name for x in ['freq', 'cut', 'res', 'env', 'attack', 'decay', 'sustain', 'release', 'level', 'gain', 'drive', 'time']):
            print(f"- {p['name']}")
