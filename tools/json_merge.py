import json

def merge_json_files_from_paths(input_path1, input_path2, output_path):
    """
    Merge two JSON files from given paths and write the result to an output file.
    Removes entries with unicode characters.

    Parameters:
        input_path1: str
            File path of the first JSON file.
        input_path2: str
            File path of the second JSON file.
        output_path: str
            File path to write the merged JSON file.

    Returns:
        None
    """

    # Read the first JSON file
    with open(input_path1, 'r', encoding='utf-8') as f1:
        json_file1 = json.load(f1)

    # Read the second JSON file
    with open(input_path2, 'r', encoding='utf-8') as f2:
        json_file2 = json.load(f2)

    # Merge the JSON files
    merged_json = {**json_file1, **json_file2}

    # Remove entries with unicode characters
    cleaned_json = {key: value for key, value in merged_json.items()
                    if not any(ord(char) > 127 for char in key) and not any(ord(char) > 127 for char in value)}

    # Write the cleaned JSON to output file
    with open(output_path, 'w', encoding='utf-8') as f_out:
        json.dump(cleaned_json, f_out, ensure_ascii=False, indent=4)


#####
input_path1 = "/Users/clem/Desktop/EEBOTest3/amanuensis/merge/user_solution_new.json"
input_path2 = "/Users/clem/Desktop/EEBOTest3/amanuensis/merge/user_solution_old.json"
output_path = "/Users/clem/Desktop/EEBOTest3/amanuensis/merge/user_solution_merged.json"

merge_json_files_from_paths(input_path1, input_path2, output_path)
