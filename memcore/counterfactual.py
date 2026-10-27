"""Counterfactual memory testing pipeline for measuring the impact of memory changes."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from memcore.models import ContextBuildResult, MemoryRecord
from memcore.optimizer import TokenBudgetOptimizer
from memcore.storage import BaseMemoryStore


class CounterfactualTestResult(BaseModel):
    memory_id: str
    task_query: str
    baseline_tokens: int
    modified_tokens: int
    token_delta: int
    baseline_critical_preserved: bool
    modified_critical_preserved: bool
    is_safe: bool
    reason: str


class CounterfactualTester:
    """Evaluates whether removing or modifying a memory damages context quality or drops dependencies."""

    def __init__(self, store: BaseMemoryStore, optimizer: TokenBudgetOptimizer):
        self.store = store
        self.optimizer = optimizer

    def test_removal(
        self,
        memory_id: str,
        benchmark_tasks: List[str],
        token_budget: int = 1500,
    ) -> List[CounterfactualTestResult]:
        """Runs counterfactual evaluation by comparing baseline context with context when memory is absent."""
        target_mem = self.store.get_memory(memory_id)
        if not target_mem:
            return []

        results: List[CounterfactualTestResult] = []

        for task in benchmark_tasks:
            # 1. Baseline context
            baseline_ctx = self.optimizer.build_context(task_query=task, token_budget=token_budget)
            baseline_ids = {m.memory.id for m in baseline_ctx.selected_memories}

            # 2. Simulate removal by temporarily marking memory soft_deleted
            prev_status = target_mem.status
            target_mem.status = "soft_deleted"
            self.store.update_memory(target_mem)

            try:
                # 3. Modified context
                modified_ctx = self.optimizer.build_context(task_query=task, token_budget=token_budget)
                modified_ids = {m.memory.id for m in modified_ctx.selected_memories}
            finally:
                # 4. Restore original state immediately
                target_mem.status = prev_status
                self.store.update_memory(target_mem)

            token_delta = modified_ctx.used_tokens - baseline_ctx.used_tokens
            was_in_baseline = memory_id in baseline_ids

            # Evaluate safety
            is_safe = True
            reason = "Memory was not critical to this task context"

            if was_in_baseline:
                if target_mem.is_protected:
                    is_safe = False
                    reason = "Memory was in context and is protected"
                elif target_mem.memory_type.value in ("security_constraint", "db_schema"):
                    is_safe = False
                    reason = f"Critical {target_mem.memory_type.value} dropped from active context"
                else:
                    reason = f"Memory was retrieved in baseline; removed in counterfactual test saving {abs(token_delta)} tokens"

            results.append(
                CounterfactualTestResult(
                    memory_id=memory_id,
                    task_query=task,
                    baseline_tokens=baseline_ctx.used_tokens,
                    modified_tokens=modified_ctx.used_tokens,
                    token_delta=token_delta,
                    baseline_critical_preserved=not target_mem.is_protected or was_in_baseline,
                    modified_critical_preserved=not target_mem.is_protected or (memory_id in modified_ids),
                    is_safe=is_safe,
                    reason=reason,
                )
            )

        return results
