"""
Multi-Domain Support Triage Agent - Entry Point

Reads support tickets from CSV, processes each through the triage pipeline,
and writes structured results to output.csv.

Usage:
    python main.py                          # Process support_tickets.csv
    python main.py --sample                 # Process sample_support_tickets.csv
    python main.py --ticket 3               # Process only ticket #3
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from agent import process_ticket
from config import INPUT_CSV, OUTPUT_CSV, SAMPLE_CSV
from corpus_loader import load_corpus
from indexer import SearchIndex
from llm_client import init_llm
from output_writer import OutputWriter
from utils import setup_logging

logger = setup_logging()


def print_banner():
    lines = [
        "+" + "-" * 58 + "+",
        "| Multi-Domain Support Triage Agent                    |",
        "| HackerRank Orchestrate - May 2026                    |",
        "+" + "-" * 58 + "+",
    ]
    for line in lines:
        logger.info(line)


def read_tickets(csv_path: Path) -> list[dict]:
    """Read support tickets from a CSV file."""
    tickets = []
    with open(csv_path, "r", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        for row in reader:
            tickets.append({
                "issue": row.get("Issue", row.get("issue", "")),
                "subject": row.get("Subject", row.get("subject", "")),
                "company": row.get("Company", row.get("company", "")),
            })
    logger.info("Loaded %s tickets from %s", len(tickets), csv_path.name)
    return tickets


def main():
    parser = argparse.ArgumentParser(description="Multi-Domain Support Triage Agent")
    parser.add_argument("--sample", action="store_true", help="Process sample_support_tickets.csv instead")
    parser.add_argument("--ticket", type=int, default=None, help="Process only a specific ticket number (1-indexed)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--debug", action="store_true", help="Alias for verbose logging plus retrieval details")
    args = parser.parse_args()

    if args.verbose or args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    start_time = time.time()
    print_banner()

    logger.info("Initializing LLM client...")
    init_llm()

    logger.info("Loading support corpus...")
    _, chunks = load_corpus()

    logger.info("Building search index...")
    index = SearchIndex(chunks)

    input_csv = SAMPLE_CSV if args.sample else INPUT_CSV
    tickets = read_tickets(input_csv)

    if args.ticket is not None:
        if 1 <= args.ticket <= len(tickets):
            tickets = [tickets[args.ticket - 1]]
            logger.info("Processing only ticket #%s", args.ticket)
        else:
            logger.error("Ticket #%s out of range (1-%s)", args.ticket, len(tickets))
            sys.exit(1)

    writer = OutputWriter(OUTPUT_CSV)
    writer.open()

    total = len(tickets)
    escalated_count = 0
    replied_count = 0

    for i, ticket in enumerate(tickets, 1):
        logger.info("\n%s", "=" * 60)
        logger.info("Processing ticket %s/%s", i, total)
        logger.info("%s", "=" * 60)

        try:
            result = process_ticket(ticket, index, ticket_num=i)
            writer.write_row(ticket, result)
            time.sleep(15) 

            if result.get("status", "").lower() == "escalated":
                escalated_count += 1
            else:
                replied_count += 1
        except Exception as exc:
            logger.error("Error processing ticket %s: %s", i, exc, exc_info=True)
            fallback = {
                "status": "escalated",
                "product_area": "",
                "response": "This request requires human assistance.",
                "justification": f"Processing error: {exc}",
                "request_type": "product_issue",
            }
            writer.write_row(ticket, fallback)
            escalated_count += 1

    writer.close()

    elapsed = time.time() - start_time
    logger.info("\n%s", "=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info("%s", "=" * 60)
    logger.info("  Total tickets: %s", total)
    logger.info("  Replied:       %s", replied_count)
    logger.info("  Escalated:     %s", escalated_count)
    logger.info("  Time:          %.1fs (%.1fs/ticket)", elapsed, elapsed / total if total else 0.0)
    logger.info("  Output:        %s", OUTPUT_CSV)


if __name__ == "__main__":
    main()
