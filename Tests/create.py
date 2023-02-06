import json

if __name__== "__main__":
    light = json.load(open("lightThreshold.json", "r"))    
    plant = json.load(open("plantThreshold.json", "r"))

    out = {}
    for key in light:
        if key in plant:
            item = light[key]
            item.update(plant[key])
            out[key] = item

    with open("threshold.json", "w") as f:
        json.dump(out, f, indent=4)