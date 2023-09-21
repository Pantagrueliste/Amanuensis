import json

def merge_json_files_from_paths(input_path1, input_path2, output_path):
    try:
        # Read the first JSON file
        print("Reading the first JSON file...")
        with open(input_path1, 'r', encoding='utf-8') as f1:
            json_file1 = json.load(f1)

        # Read the second JSON file
        print("Reading the second JSON file...")
        with open(input_path2, 'r', encoding='utf-8') as f2:
            json_file2 = json.load(f2)

        # Merge the JSON files
        print("Merging JSON files...")
        merged_json = {**json_file1, **json_file2}

        # Remove entries with unicode characters
        print("Cleaning JSON data...")
        cleaned_json = {key: value for key, value in merged_json.items()
                        if not any(ord(char) > 127 for char in key) and not any(ord(char) > 127 for char in value)}

        # Write the cleaned JSON to output file
        print("Writing cleaned JSON to output file...")
        with open(output_path, 'w', encoding='utf-8') as f_out:
            json.dump(cleaned_json, f_out, ensure_ascii=False, indent=4)

        print("Merge operation completed successfully.")

    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# File paths
input_path1 = "/Users/clem/GitHub/Amanuensis/data/user_solution.json"
input_path2 = "/Users/clem/GitHub/Amanuensis/data/user_solution_copy.json"
output_path = "/Users/clem/GitHub/Amanuensis/data/user_solution_merged.json"

# Call the function with error handling
merge_json_files_from_paths(input_path1, input_path2, output_path)
