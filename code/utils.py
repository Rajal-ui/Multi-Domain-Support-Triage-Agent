"""
Utility functions: text cleaning, markdown parsing, logging helpers.
"""

import re
import logging
from pathlib import Path

def setup_logging(level=logging.INFO):
    """Configure structured logging for the agent."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("triage_agent")

logger = setup_logging()


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize text for processing."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def extract_title_from_markdown(content: str) -> str:
    """Extract the first heading from a markdown document."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line.lstrip("# ").strip()
        if line.startswith("## "):
            return line.lstrip("# ").strip()
    return ""


def normalize_company(company: str) -> str | None:
    """Normalize company name to lowercase key or None."""
    if not company:
        return None
    c = company.strip().lower()
    if c in ("none", "", "nan"):
        return None
    from config import COMPANY_ALIASES
    if c in COMPANY_ALIASES:
        return COMPANY_ALIASES[c]
    for alias, normalized in COMPANY_ALIASES.items():
        if alias in c or c in alias:
            return normalized
    return None


def chunk_text(text: str, chunk_size: int = 2400, overlap: int = 400) -> list[str]:
    """
    Split text into overlapping chunks for indexing.
    
    Args:
        text: The full document text
        chunk_size: Target chunk size in characters (~600 tokens)
        overlap: Overlap between consecutive chunks
    
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break
            else:
                sent_break = text.rfind(". ", start + chunk_size // 2, end)
                if sent_break > start:
                    end = sent_break + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


def sanitize_for_csv(text: str) -> str:
    """Sanitize text for CSV output — handle quotes and newlines."""
    if not text:
        return ""
    return text.replace("\x00", "")


def detect_language(text: str) -> str:
    """Simple language detection based on common words."""
    text_lower = text.lower()
    
    french_indicators = ["bonjour", "je", "mon", "ma", "les", "une", "est",
                         "pour", "avec", "que", "carte", "été", "vous"]
    spanish_indicators = ["hola", "por favor", "gracias", "tarjeta", "ayuda"]
    
    french_count = sum(1 for w in french_indicators if w in text_lower)
    spanish_count = sum(1 for w in spanish_indicators if w in text_lower)
    
    if french_count >= 3:
        return "french"
    if spanish_count >= 3:
        return "spanish"
    return "english"
