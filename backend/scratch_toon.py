class CatchAll(dict):
    def __getitem__(self, key):
        if key == "False": return False
        if key == "True": return True
        if key == "None": return None
        return key

try:
    res = eval("[{device_name:'Wavetable',parameters:[{name:'Osc 1',value:0.5, quantized:False}]}]", {}, CatchAll())
    print(res)
except Exception as e:
    print(e)
