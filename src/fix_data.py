"""Script to fix captured prize JSON structure to list format."""
import json
import os

def fix_json():
    input_file = "captured_prize_data.json"
    output_file = "all_results.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Check structure
    results_list = []
    if isinstance(data, dict):
        if 'data' in data and 'resultData' in data['data']:
             results_list = data['data']['resultData']
             print(f"Found {len(results_list)} records in data.resultData")
        else:
             print("Could not find data.resultData in keys:", data.keys())
             return
    elif isinstance(data, list):
        results_list = data
        print("Input is already a list.")
    
    # Save as list to all_results.json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=4)
    
    print(f"Saved {len(results_list)} records to {output_file}")

if __name__ == "__main__":
    fix_json()
