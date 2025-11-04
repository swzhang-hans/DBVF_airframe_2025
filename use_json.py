import json

def load_json(filepath):
    """
    Load data from a JSON file.

    Parameters:
        filepath (str): Path to the JSON file.

    Returns:
        dict: Parsed JSON data as a Python dictionary.
    """
    with open(filepath, "r") as f:
        return json.load(f)


def write_json(filepath, data, indent=2):
    """
    Write data to a JSON file.

    Parameters:
        filepath (str): Path to the output JSON file.
        data (dict): Python dictionary to write.
        indent (int): Indentation level for readability.
    """
    with open(filepath, "w") as f:
        json.dump(data, f, indent=indent)

''' usage example

# Load aircraft data
data = load_json("aircraft_data.json")

# Access CL and modify it
data["blade"]["C_LIFT"] = 0.1

# Save updated data
write_json("aircraft_data.json", data)

'''
