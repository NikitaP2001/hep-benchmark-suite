# -*- coding: utf-8 -*-

import json
import sys

def print_tree(indent, key, data, json_data, max_depth):
    subkey_length = len(data) if isinstance(data, dict) else 0
    if subkey_length == 0:
        print(f"{indent} |__ {key} (No subkeys)")
    else:
        print(f"{indent} |__ {key} (N keys: {subkey_length})")

        if max_depth > 0:
            for subkey, subvalue in data.items():
                subsubkey_length = len(subvalue) if isinstance(subvalue, dict) else 0
                if subsubkey_length == 0:
                    print(f"{indent} \t |__ {subkey} (No subkeys)")
                else:
                    print_tree(f"{indent}  \t", subkey, subvalue, json_data, max_depth - 1)

# Check if the JSON file path is provided as a command-line argument
if len(sys.argv) != 3:
    print("Usage: python script.py <json_file> <max_depth>")
    sys.exit(1)

json_file = sys.argv[1]
max_depth = int(sys.argv[2])

# Read the JSON file
try:
    with open(json_file, 'r') as file:
        json_data = json.load(file)
except FileNotFoundError:
    print(f"Error: File not found: {json_file}")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: Invalid JSON format in file: {json_file}")
    sys.exit(1)

# Get the length of the top-level keys
top_level_keys = list(json_data.keys())

print(f"Top-level keys: {top_level_keys}")

# Loop through the top-level keys and print the tree up to the specified depth
for key in top_level_keys:
    print_tree("", key, json_data[key], json_data, max_depth)
