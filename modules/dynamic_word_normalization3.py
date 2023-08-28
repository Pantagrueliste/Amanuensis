import json


class DynamicWordNormalization3:
    def __init__(
        self,
        user_solution_path="data/user_solution.json",
        machine_solution_path="data/machine_solution.json",
    ):
        # Load user solutions and machine solutions
        self.user_solutions = self.load_solutions(user_solution_path)
        self.machine_solutions = self.load_solutions(machine_solution_path)

        # # Resolve inconsistencies
        # self.resolve_inconsistencies()

    def load_solutions(self, file_path):
        """Load solutions from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Solutions file '{file_path}' not found.")

    def resolve_inconsistencies(self):
        """Compare US and MS, and resolve any inconsistencies by prioritizing US."""
        for aw, us in self.user_solutions.items():
            ms = self.machine_solutions.get(aw)
            if ms and ms != us:
                # Inconsistency found, prioritize US
                self.machine_solutions[aw] = us
