"""
Corpus loader: reads and parses all markdown files from data/ into structured documents.

Each document has:
- file_path: relative path within data/
- domain: hackerrank | claude | visa
- product_area: second-level directory (screen, interviews, privacy, etc.)
- title: extracted from first heading
- content: full cleaned text
- chunks: list of text chunks for retrieval
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field

from config import DATA_DIR, DOMAINS, CHUNK_SIZE, CHUNK_OVERLAP
from utils import clean_text, extract_title_from_markdown, chunk_text

logger = logging.getLogger("triage_agent.corpus")


@dataclass
class Document:
    """A single support document from the corpus."""
    file_path: str
    domain: str
    product_area: str
    title: str
    content: str
    chunks: list[str] = field(default_factory=list)

    def __repr__(self):
        return f"Document({self.domain}/{self.product_area}: {self.title[:50]})"


@dataclass
class Chunk:
    """A single chunk with metadata linking back to its source document."""
    text: str
    doc_index: int     
    chunk_index: int     
    domain: str
    product_area: str
    title: str
    file_path: str


def load_corpus() -> tuple[list[Document], list[Chunk]]:
    """
    Load all markdown files from the data/ directory.
    
    Returns:
        Tuple of (documents list, chunks list with metadata)
    """
    documents: list[Document] = []
    all_chunks: list[Chunk] = []
    
    for domain_name, domain_path in DOMAINS.items():
        if not domain_path.exists():
            logger.warning(f"Domain path does not exist: {domain_path}")
            continue
        
        md_files = sorted(domain_path.rglob("*.md"))
        logger.info(f"Loading {len(md_files)} files from {domain_name}/")
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Failed to read {md_file}: {e}")
                continue
            
            content = clean_text(content)
            if not content or len(content) < 20:
                continue
            
            rel_path = md_file.relative_to(DATA_DIR)
            parts = rel_path.parts 
            product_area = parts[1] if len(parts) > 2 else "general"
            
            title = extract_title_from_markdown(content)
            if not title:
                title = md_file.stem.replace("-", " ").replace("_", " ").title()
            
            doc = Document(
                file_path=str(rel_path),
                domain=domain_name,
                product_area=product_area,
                title=title,
                content=content,
            )
            
            doc.chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
            
            doc_index = len(documents)
            documents.append(doc)
            
            for chunk_idx, chunk_text_str in enumerate(doc.chunks):
                all_chunks.append(Chunk(
                    text=chunk_text_str,
                    doc_index=doc_index,
                    chunk_index=chunk_idx,
                    domain=domain_name,
                    product_area=product_area,
                    title=title,
                    file_path=str(rel_path),
                ))
    
    logger.info(
        f"Corpus loaded: {len(documents)} documents, "
        f"{len(all_chunks)} chunks across "
        f"{len(DOMAINS)} domains"
    )
    
    for domain in DOMAINS:
        domain_docs = [d for d in documents if d.domain == domain]
        domain_chunks = [c for c in all_chunks if c.domain == domain]
        areas = set(d.product_area for d in domain_docs)
        logger.info(
            f"  {domain}: {len(domain_docs)} docs, "
            f"{len(domain_chunks)} chunks, "
            f"areas: {sorted(areas)}"
        )
    
    return documents, all_chunks


def get_product_areas(documents: list[Document]) -> dict[str, set[str]]:
    """Get all valid product areas per domain."""
    areas: dict[str, set[str]] = {}
    for doc in documents:
        if doc.domain not in areas:
            areas[doc.domain] = set()
        areas[doc.domain].add(doc.product_area)
    return areas
