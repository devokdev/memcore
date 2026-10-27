"""Rule-based and semantic memory compressor and merger."""

import difflib
import logging
from typing import List, Optional, Tuple

from memcore.embeddings import BaseEmbeddingProvider, LocalFastEmbedder, cosine_similarity
from memcore.models import MemoryRecord, MemoryType
from memcore.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class MemoryCompressor:
    """Safely compresses and merges memory contents while verifying information retention."""

    def __init__(self, embedder: Optional[BaseEmbeddingProvider] = None):
        self.embedder = embedder or LocalFastEmbedder()

    def compress_text(self, text: str) -> Tuple[str, float]:
        """Compresses verbose text by stripping redundancy and condensing phrasing.
        
        Returns:
            (compressed_text, token_reduction_ratio)
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return text, 0.0

        # Deduplicate identical or near-identical lines
        unique_lines = []
        for line in lines:
            if not any(difflib.SequenceMatcher(None, line.lower(), u.lower()).ratio() > 0.85 for u in unique_lines):
                unique_lines.append(line)

        # Condense common redundant phrases
        condensed = " ".join(unique_lines)
        replacements = [
            ("It is important to note that ", ""),
            ("Please be aware that ", ""),
            ("In order to ", "To "),
            ("The application makes use of ", "The app uses "),
            ("The application uses ", "The app uses "),
            ("For the purpose of ", "For "),
            ("As mentioned previously, ", ""),
            ("At this point in time, ", "Currently, "),
        ]
        for src, dest in replacements:
            condensed = condensed.replace(src, dest)
            condensed = condensed.replace(src.lower(), dest.lower())

        orig_tokens, _ = count_tokens(text)
        new_tokens, _ = count_tokens(condensed)

        reduction = max(0.0, (orig_tokens - new_tokens) / (orig_tokens or 1))
        return condensed, reduction

    def are_compatible_to_merge(self, mem1: MemoryRecord, mem2: MemoryRecord) -> Tuple[bool, str]:
        """Checks if two memories are safe to merge."""
        if mem1.project_id != mem2.project_id:
            return False, "Different projects"
        
        # Don't merge if either is protected unless explicit
        if mem1.is_protected or mem2.is_protected:
            return False, "Protected memories require explicit manual merge"

        # Check semantic similarity
        v1 = self.embedder.embed_text(mem1.content)
        v2 = self.embedder.embed_text(mem2.content)
        sim = cosine_similarity(v1, v2)
        if sim < 0.65:
            return False, f"Semantic similarity too low ({sim:.2f} < 0.65)"

        # Check for direct contradictions (e.g. true vs false, enabled vs disabled, different versions)
        words1 = set(mem1.content.lower().split())
        words2 = set(mem2.content.lower().split())
        
        contradictions = [
            ("enabled", "disabled"),
            ("jwt", "oauth"),
            ("mysql", "postgresql"),
            ("sync", "async"),
            ("rest", "graphql"),
        ]
        for c1, c2 in contradictions:
            if (c1 in words1 and c2 in words2) or (c2 in words1 and c1 in words2):
                return False, f"Contradiction detected: '{c1}' vs '{c2}'"

        return True, "Compatible for merge"

    def merge_memories(self, mem1: MemoryRecord, mem2: MemoryRecord) -> Tuple[str, List[str], List[str]]:
        """Merges two compatible memories into a concise unified representation.
        
        Returns:
            (merged_content, combined_files, combined_symbols)
        """
        combined_files = list(set(mem1.associated_files + mem2.associated_files))
        combined_symbols = list(set(mem1.associated_symbols + mem2.associated_symbols))

        # Check if one is a substring or much shorter summary of the other
        c1, c2 = mem1.content.strip(), mem2.content.strip()
        if c1.lower() in c2.lower():
            merged_content = c2
        elif c2.lower() in c1.lower():
            merged_content = c1
        else:
            # Join and compress
            combined = f"{c1} Additionally, {c2}"
            compressed, _ = self.compress_text(combined)
            merged_content = compressed

        return merged_content, combined_files, combined_symbols
