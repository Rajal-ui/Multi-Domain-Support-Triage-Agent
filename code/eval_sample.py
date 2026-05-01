"""
Quick sample-set evaluator for tuning escalation and prompt behavior.
Run the agent first with: python main.py --sample
Then run: python eval_sample.py
"""

import csv
from pathlib import Path


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file_handle:
        return list(csv.DictReader(file_handle))


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def main():
    expected = load_csv(Path("../support_tickets/sample_support_tickets.csv"))
    actual = load_csv(Path("../support_tickets/output.csv"))

    for i, (exp, act) in enumerate(zip(expected, actual), 1):
        issues = []

        if normalize(exp.get("Status")) != normalize(act.get("status")):
            issues.append(f"status expected={exp.get('Status')} actual={act.get('status')}")

        if normalize(exp.get("Request Type")) != normalize(act.get("request_type")):
            issues.append(
                f"request_type expected={exp.get('Request Type')} actual={act.get('request_type')}"
            )

        response = act.get("response", "")
        if "support specialist" in response.lower() and normalize(exp.get("Status")) == "replied":
            issues.append("possible over-escalation or weak grounding")

        if issues:
            print(f"Row {i}:")
            for issue in issues:
                print(" -", issue)


if __name__ == "__main__":
    main()
