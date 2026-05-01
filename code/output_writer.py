"""
Output writer: writes validated results to output.csv in the required schema.
"""

import csv
import logging
from pathlib import Path

from config import OUTPUT_COLUMNS, OUTPUT_CSV

logger = logging.getLogger("triage_agent.output")


class OutputWriter:
    """Writes ticket results to the output CSV file."""

    def __init__(self, output_path: Path = OUTPUT_CSV):
        self.output_path = output_path
        self.rows_written = 0
        self._file = None
        self._writer = None

    def open(self):
        """Open the CSV file and write the header."""
        self._file = open(self.output_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=OUTPUT_COLUMNS)
        self._writer.writeheader()
        logger.info("Output file opened: %s", self.output_path)

    def write_row(self, ticket: dict, result: dict):
        """
        Write a single result row to the output CSV.

        Args:
            ticket: Original ticket dict with issue, subject, company
            result: Agent result with status, product_area, response, justification, request_type
        """
        row = {
            "issue": ticket.get("issue", ""),
            "subject": ticket.get("subject", ""),
            "company": ticket.get("company", ""),
            "response": result.get("response", ""),
            "product_area": result.get("product_area", ""),
            "status": result.get("status", "escalated").capitalize(),
            "request_type": result.get("request_type", "product_issue").lower(),
            "justification": result.get("justification", ""),
        }

        self._writer.writerow(row)
        self._file.flush()
        self.rows_written += 1
        logger.info(
            "Row %s: status=%s, type=%s, area=%s",
            self.rows_written,
            row["status"],
            row["request_type"],
            row["product_area"],
        )

    def close(self):
        """Close the output file."""
        if self._file:
            self._file.close()
            logger.info("Output complete: %s rows written to %s", self.rows_written, self.output_path)
