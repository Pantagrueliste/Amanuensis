import json


class ConflictResolver:
    def __init__(self, config):
        self.config = config
        self.load_machine_solutions()
        self.load_user_solutions()
        self.detect_and_resolve_conflicts()

    def load_machine_solutions(self):
        """
        Load machine solutions from a JSON file.
        """
        machine_solution_path = "data/machine_solution.json"
        try:
            with open(machine_solution_path, "r", encoding="utf-8") as file:
                contents = file.read().strip()  # Strip leading and trailing whitespace
                if contents:  # Check if the content is not empty
                    self.machine_solutions = json.loads(contents)
                else:
                    self.machine_solutions = {}
        except FileNotFoundError:
            self.machine_solutions = {}
            with open(machine_solution_path, "w", encoding="utf-8") as file:
                json.dump(self.machine_solutions, file)

    def load_user_solutions(self):
        """
        Load user solutions from a JSON file.
        """
        user_solution_path = self.config.get("data", "user_solution_path")
        try:
            with open("data/user_solution.json", "r", encoding="utf-8") as file:
                self.user_solutions = json.load(file)
        except FileNotFoundError:
            self.user_solutions = {}
            with open("data/user_solution.json", "w", encoding="utf-8") as file:
                json.dump(self.user_solutions, file)

    def save_machine_solutions(self):
        """
        Save machine solutions to a JSON file.
        """
        with open("data/machine_solution.json", "w", encoding="utf-8") as file:
            json.dump(self.machine_solutions, file)

    def save_user_solutions(self):
        """
        Save user solutions to a JSON file.
        """
        with open("data/user_solution.json", "w", encoding="utf-8") as file:
            json.dump(self.user_solutions, file)

    def detect_and_resolve_conflicts(self):
        """
        Compare Machine Solutions (MS) and User Solutions (US) for conflicts
        and prompt the user to resolve them.
        """
        conflicts = {
            aw: (ms, self.user_solutions[aw])
            for aw, ms in self.machine_solutions.items()
            if aw in self.user_solutions and ms != self.user_solutions[aw]
        }

        for aw, (ms, us) in conflicts.items():
            print(f"Conflict detected for '{aw}': MS='{ms}' and US='{us}'")
            decision = input(
                "Enter 'M' to keep the Machine Solution, 'U' to keep the User Solution, or 'S' to skip: "
            ).upper()

            if decision == "M":
                self.user_solutions[aw] = ms
            elif decision == "U":
                self.machine_solutions[aw] = us
            elif decision == "S":
                continue
            else:
                print("Invalid input. Skipping this conflict.")

        # Save the updated solutions back to their respective files
        self.save_user_solutions()
        self.save_machine_solutions()
