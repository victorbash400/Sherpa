import unittest

from backend.task_graph import AdmissionDecision, WorkerAssignment
from backend.task_graph import dependency_context, validate_admission_decision, validate_assignment_graph


class TaskGraphTests(unittest.TestCase):
    def assignment(self, key: str, *, depends_on: list[str] | None = None) -> WorkerAssignment:
        return WorkerAssignment(
            key=key,
            title=key.title(),
            instruction=f"Complete {key}",
            tools=["computer"],
            depends_on=depends_on or [],
        )

    def test_accepts_parallel_and_dependent_assignments(self) -> None:
        assignments = [
            self.assignment("mail"),
            self.assignment("drive"),
            self.assignment("finish", depends_on=["mail", "drive"]),
        ]

        validate_assignment_graph(assignments)

    def test_rejects_cycles(self) -> None:
        assignments = [
            self.assignment("first", depends_on=["second"]),
            self.assignment("second", depends_on=["first"]),
        ]

        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_assignment_graph(assignments)

    def test_dependency_context_contains_only_named_results(self) -> None:
        assignment = self.assignment("finish", depends_on=["mail"])

        prompt = dependency_context(
            assignment,
            {
                "mail": ("Find invoice", "Invoice total is 42", "Verified in message 12"),
                "unrelated": ("Other work", "Do not include this", "Other evidence"),
            },
        )

        self.assertIn("Invoice total is 42", prompt)
        self.assertIn("Verified in message 12", prompt)
        self.assertNotIn("Do not include this", prompt)

    def test_rejects_assignments_for_nonaccepted_decision(self) -> None:
        admission = AdmissionDecision(
            decision="needs_clarification",
            message="Which account?",
            assignments=[self.assignment("mail")],
        )

        with self.assertRaisesRegex(ValueError, "cannot include assignments"):
            validate_admission_decision(admission)


if __name__ == "__main__":
    unittest.main()
