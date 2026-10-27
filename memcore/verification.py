"""Repository-grounded verification engine to connect memories with actual code evidence."""

import os
import re
from typing import List, Optional

from memcore.models import MemoryRecord, VerificationResult, VerificationStatus
from memcore.storage import BaseMemoryStore


class RepositoryVerifier:
    """Checks whether stored memories still match the active codebase."""

    def __init__(self, repo_root: str, store: BaseMemoryStore):
        self.repo_root = os.path.abspath(repo_root)
        self.store = store

    def verify_memory(self, memory: MemoryRecord) -> VerificationResult:
        """Verifies a memory record against the files on disk."""
        evidence: List[str] = []
        conflicts: List[str] = []
        status = VerificationStatus.VERIFIED
        confidence = 0.9

        # 1. Check associated files
        if memory.associated_files:
            missing_files = []
            present_files = []
            for rel_file in memory.associated_files:
                full_path = os.path.join(self.repo_root, rel_file)
                if os.path.exists(full_path):
                    present_files.append(rel_file)
                else:
                    missing_files.append(rel_file)

            if missing_files:
                conflicts.append(f"Associated files missing from repository: {', '.join(missing_files)}")
                status = VerificationStatus.STALE
                confidence *= 0.5
            if present_files:
                evidence.append(f"Verified files exist: {', '.join(present_files)}")

        # 2. Check associated symbols within present files
        if memory.associated_symbols and memory.associated_files:
            for rel_file in memory.associated_files:
                full_path = os.path.join(self.repo_root, rel_file)
                if not os.path.isfile(full_path):
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_content = f.read()
                    
                    found_symbols = []
                    missing_symbols = []
                    for sym in memory.associated_symbols:
                        # Search for symbol definition or mention
                        pattern = r'\b' + re.escape(sym) + r'\b'
                        if re.search(pattern, file_content):
                            found_symbols.append(sym)
                        else:
                            missing_symbols.append(sym)

                    if found_symbols:
                        evidence.append(f"Symbol(s) {', '.join(found_symbols)} found in {rel_file}")
                    if missing_symbols:
                        conflicts.append(f"Symbol(s) {', '.join(missing_symbols)} NOT found in {rel_file}")
                        status = VerificationStatus.CONFLICT
                        confidence *= 0.4
                except Exception as e:
                    conflicts.append(f"Error reading {rel_file}: {e}")

        # 3. Check for obvious keyword contradictions in content
        # e.g., if memory says "uses MySQL" but package.json / requirements.txt / pyproject.toml specifies postgres
        content_lower = memory.content.lower()
        if "postgresql" in content_lower and self._check_file_contains("requirements.txt", "mysql"):
            conflicts.append("Memory mentions PostgreSQL, but requirements.txt mentions mysql")
            status = VerificationStatus.CONFLICT
        elif "mysql" in content_lower and self._check_file_contains("requirements.txt", "psycopg"):
            conflicts.append("Memory mentions MySQL, but requirements.txt specifies psycopg/postgresql")
            status = VerificationStatus.CONFLICT

        if not memory.associated_files and not memory.associated_symbols:
            # Cannot firmly verify file references, mark as unverified but plausible
            status = VerificationStatus.UNVERIFIED
            evidence.append("No file or symbol references to verify directly on disk")
            confidence = memory.confidence

        res = VerificationResult(
            memory_id=memory.id,
            status=status,
            confidence=confidence,
            evidence=evidence,
            conflicts=conflicts,
            proposed_resolution=(
                "Update associated_files or update memory content to reflect current code"
                if conflicts
                else None
            ),
        )

        # Update memory state
        memory.verification_status = status
        memory.verification_notes = (
            f"Verified with {len(evidence)} evidence points. Conflicts: {'; '.join(conflicts) if conflicts else 'None'}"
        )
        self.store.update_memory(memory)

        return res

    def _check_file_contains(self, rel_path: str, term: str) -> bool:
        full_path = os.path.join(self.repo_root, rel_path)
        if not os.path.isfile(full_path):
            return False
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return term.lower() in f.read().lower()
        except Exception:
            return False

    def verify_all_active(self, project_id: str = "default") -> List[VerificationResult]:
        memories = self.store.list_memories(project_id=project_id)
        results = []
        for mem in memories:
            results.append(self.verify_memory(mem))
        return results
