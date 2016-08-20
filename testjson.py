import yaml
import json

def converttojson(dict):
    jsonstr = "{"
    for process in sorted(dict.keys()):
        jsonstr += str(process) + ": "
        if hasattr(dict[process], 'items') is True:
            jsonstr += "{"
            for variable in sorted(dict[process].keys()):
                jsonstr += str(variable) + ": "
                if hasattr(dict[process][variable], 'items') is True:
                    for k, v in sorted(dict[process][variable].items()):
                        jsonstr += str(k) + ": " + str(v) + ", "
            jsonstr += "}"
        else:
            jsonstr += str(dict[process]) + ", "
    jsonstr += "}"
    print(jsonstr)


# Function for loading config file
def loadconfig(filename):
    f = open(filename)
    datamap = yaml.safe_load(f)
    f.close()
    return datamap

processdict = loadconfig('Config.yaml')
converttojson(processdict)

print(json.dumps(processdict,sort_keys=True))
