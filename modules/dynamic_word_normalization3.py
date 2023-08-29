import os
import json
import shutil
import tempfile
from config import Config  # Assuming Config class is in a module named config
from concurrent.futures import ThreadPoolExecutor

class DynamicWordNormalization3:
    def __init__(self):
        self.config = Config()  # Initialize Config to get settings

    def atomic_json_update(self, data, file_path):
        with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
            json.dump(data, temp_file)
            temp_file.flush()
        os.replace(temp_file.name, file_path)

    def handle_problematic_files_with_atomic_update(self, sorted_problematic_ratios, user_solution_json_path):
        try:
            with open(user_solution_json_path, 'r') as f:
                current_data = json.load(f)
        except FileNotFoundError:
            current_data = {}

        for file_name, (count, ratio) in sorted_problematic_ratios.items():
            print(f"File: {file_name}, Problematic Passages: {count}, Ratio: {ratio:.2f}%")

            simulated_user_input = 'f'  # Replace with actual user input

            if simulated_user_input.lower() == 'd':
                print(f"Discarded {file_name}")
                continue
            elif simulated_user_input.lower() == 'f':
                new_data = {file_name: {"line": count, "solution": "new_solution"}}
                current_data.update(new_data)
                self.atomic_json_update(current_data, user_solution_json_path)
                print(f"Fix applied for {file_name}")
            else:
                print("Invalid option. Skipping to next file.")

    def copy_file(self, src, dest):
        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdest:
            shutil.copyfileobj(fsrc, fdest)

    def final_processing(self, files_to_copy, dest_folder):
        with ThreadPoolExecutor() as executor:
            futures = []
            for src_file in files_to_copy:
                dest_file = os.path.join(dest_folder, os.path.basename(src_file))
                futures.append(executor.submit(self.copy_file, src_file, dest_file))

            for future in futures:
                future.result()
