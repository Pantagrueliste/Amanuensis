import orjson
from config import Config
import json

class ConflictResolver:
    def __init__(self, config):
        """Initialize the ConflictResolver with configuration."""
        self.config = Config()  # Create a Config object
        self.ambiguous_aws = self.config.get_ambiguous_aws()  # Load ambiguous AWs using Config class
        self.machine_solutions = {}
        self.user_solutions = {}
        self.load_machine_solutions()
        self.load_user_solutions()

    def load_machine_solutions(self):
        """Load machine solutions from a JSON file."""
        try:
            with open(self.config.get('data', 'machine_solution_path'), "rb") as file:
                contents = file.read().strip()
                self.machine_solutions = orjson.loads(contents) if contents else {}
        except FileNotFoundError:
            self.machine_solutions = {}
            self.save_machine_solutions()

    def load_user_solutions(self):
        """Load user solutions from a JSON file."""
        try:
            with open(self.config.get('data', 'user_solution_path'), 'rb') as f:
                self.user_solutions = orjson.loads(f.read())
        except FileNotFoundError:
            self.user_solutions = {}
            self.save_user_solutions()

    def save_machine_solutions(self):
            """Save machine solutions to a JSON file."""
            with open(self.config.get('data', 'machine_solution_path'), 'w') as f:
                f.write(json.dumps(self.machine_solutions, indent=4))

    def save_user_solutions(self):
        """Save user solutions to a JSON file."""
        with open(self.config.get('data', 'user_solution_path'), 'w') as f:
            f.write(json.dumps(self.user_solutions, indent=4))

    def detect_and_resolve_conflicts(self):
        """Detect and resolve conflicts between machine and user solutions."""
        for aw, (ms, us) in self.identify_conflicts().items():
            if aw in self.ambiguous_aws:
                print(f"'{aw}' is ambiguous and will be left unchanged.")
                continue  # Skip processing ambiguous AWs
            self.resolve_individual_conflict(aw, ms, us)
        self.confirm_and_save_resolutions()

    def identify_conflicts(self):
            """Identify conflicts between machine and user solutions."""
            conflicts = {}
            for aw, ms in self.machine_solutions.items():
                if aw in self.user_solutions and aw not in self.ambiguous_aws:
                    us = self.user_solutions[aw]
                    if ms != us:
                        conflicts[aw] = (ms, us)
            return conflicts

    def resolve_individual_conflict(self, aw, ms, us):
        """Resolve an individual conflict."""
        print(f"Conflict detected for '{aw}': MS='{ms}' and US='{us}'")
        decision = input(
            "Enter 'M' to keep the Machine Solution, 'U' to keep the User Solution, or 'S' to skip: "
        ).upper()
        if decision == "M":
            self.user_solutions[aw] = ms
        elif decision == "U":
            self.machine_solutions[aw] = us
        elif decision == "S":
            pass  # Just skip
        else:
            print("Invalid input. Skipping this conflict.")

    def confirm_and_save_resolutions(self):
        """Confirm with the user and save the resolved conflicts."""
        self.save_user_solutions()
        self.save_machine_solutions()
