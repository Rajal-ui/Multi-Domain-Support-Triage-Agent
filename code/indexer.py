"""
Search index builder using TF-IDF vectorization from scikit-learn.

Builds a sparse vector index over all corpus chunks for fast retrieval.
Supports domain-scoped queries (only search within a specific domain).
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from corpus_loader import Chunk

logger = logging.getLogger("triage_agent.indexer")


class SearchIndex:
    """TF-IDF-based search index over corpus chunks."""
    
    def __init__(self, chunks: list[Chunk]):
        """
        Build the TF-IDF index from chunks.
        
        Args:
            chunks: List of Chunk objects with text and metadata
        """
        self.chunks = chunks
        self.chunk_texts = [
            " ".join([
                c.title,
                c.product_area.replace("-", " ").replace("_", " "),
                c.file_path.replace("\\", " ").replace("/", " "),
                c.text,
            ])
            for c in chunks
        ]
        
        logger.info(f"Building TF-IDF index over {len(chunks)} chunks...")
        
        self.vectorizer = TfidfVectorizer(
            max_features=20000,
            stop_words="english",
            ngram_range=(1, 2),    
            min_df=2,              
            max_df=0.95,           
            sublinear_tf=True,     
        )
        
        self.tfidf_matrix = self.vectorizer.fit_transform(self.chunk_texts)
        
        self._domain_indices: dict[str, list[int]] = {}
        for idx, chunk in enumerate(chunks):
            if chunk.domain not in self._domain_indices:
                self._domain_indices[chunk.domain] = []
            self._domain_indices[chunk.domain].append(idx)
        
        logger.info(
            f"Index built: {self.tfidf_matrix.shape[0]} chunks × "
            f"{self.tfidf_matrix.shape[1]} features"
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        domain: str | None = None,
        min_score: float = 0.05,
    ) -> list[tuple[Chunk, float]]:
        """
        Search the index for chunks matching the query.
        
        Args:
            query: Search query (typically the ticket issue + subject)
            top_k: Number of results to return
            domain: If set, only search within this domain
            min_score: Minimum cosine similarity score to include
            
        Returns:
            List of (Chunk, score) tuples, sorted by relevance
        """
        query_vec = self.vectorizer.transform([query])
        
        if domain and domain in self._domain_indices:
            indices = self._domain_indices[domain]
            domain_matrix = self.tfidf_matrix[indices]
            scores = cosine_similarity(query_vec, domain_matrix).flatten()
            
            scored_chunks = [
                (self.chunks[indices[i]], float(scores[i]))
                for i in range(len(scores))
                if scores[i] >= min_score
            ]
        else:
            scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            scored_chunks = [
                (self.chunks[i], float(scores[i]))
                for i in range(len(scores))
                if scores[i] >= min_score
            ]
        
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        results = scored_chunks[:top_k]
        
        if results:
            logger.debug(
                f"Query '{query[:60]}...' → {len(results)} results "
                f"(top score: {results[0][1]:.3f})"
            )
        else:
            logger.warning(f"No results for query: '{query[:60]}...'")
        
        return results
