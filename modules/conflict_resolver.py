import orjson
from config import Config


class ConflictResolver:
    def __init__(self, config):
        self.config = config
        self.machine_solutions = {}
        self.user_solutions = {}
        self.load_machine_solutions()
        self.load_user_solutions()

    def load_machine_solutions(self):
        """
        Load machine solutions from a JSON file.
        """
        machine_solution_path = "data/machine_solution.json"
        try:
            with open(Config().machine_solution_path, "rb") as file:
                contents = file.read().strip()
                self.machine_solutions = orjson.loads(contents) if contents else {}
        except FileNotFoundError:
            self.machine_solutions = {}
            self.save_machine_solutions()

    def load_user_solutions(self):
        """
        Load user solutions from a JSON file.
        """
        try:
            with open(Config().get('data', 'user_solution_path'), 'rb') as f:
                self.user_solutions = orjson.loads(f.read())
        except FileNotFoundError:
            self.user_solutions = {}
            self.save_user_solutions()

    def save_machine_solutions(self):
        """
        Save machine solutions to a JSON file.
        """
        with open(Config().get('data', 'machine_solution_path'), 'wb') as f:
            f.write(orjson.dumps(self.machine_solutions))

    def save_user_solutions(self):
        """
        Save user solutions to a JSON file.
        """
        with open(Config().get('data', 'user_solution_path'), 'wb') as f:
            f.write(orjson.dumps(self.user_solutions))

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
