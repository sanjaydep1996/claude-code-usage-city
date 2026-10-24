"""Tool & Model Advisor for DevCity.

Provides deterministic, dated recommendations for tool, model, and effort
given task parameters. No external LLM calls; 100% local and reproducible.
"""

import json
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

_DATA_PATH = pathlib.Path(__file__).parent / "advisor_data.json"


@dataclass
class TaskRecommendation:
    task_type: str
    recommended_tool: str
    recommended_model: str
    fallback_model: str
    effort_tier: str
    token_budget_est: str
    cost_est_usd: str
    rationale: str
    caveats: str
    size: str = "medium"
    domain: str = "fullstack"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "recommended_tool": self.recommended_tool,
            "recommended_model": self.recommended_model,
            "fallback_model": self.fallback_model,
            "effort_tier": self.effort_tier,
            "token_budget_est": self.token_budget_est,
            "cost_est_usd": self.cost_est_usd,
            "rationale": self.rationale,
            "caveats": self.caveats,
            "size": self.size,
            "domain": self.domain,
        }


class ToolAdvisor:
    """Advises developers on tool choice, model selection, and token budgets."""

    def __init__(self, data_file: Optional[pathlib.Path] = None):
        path = data_file or _DATA_PATH
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"rules": [], "citation": "Default rules"}
        self.rules_by_type = {r["task_type"]: r for r in self.data.get("rules", [])}

    def recommend(
        self,
        task_type: str,
        size: str = "medium",
        domain: str = "fullstack"
    ) -> TaskRecommendation:
        """Get deterministic recommendation for a given task, size, and domain."""
        rule = self.rules_by_type.get(task_type)
        if not rule:
            # Fallback for unknown tasks
            return TaskRecommendation(
                task_type=task_type,
                recommended_tool="Claude Code",
                recommended_model="Claude 3.7 Sonnet" if size in ("medium", "complex") else "Claude 3.5 Haiku",
                fallback_model="Claude 3.5 Haiku",
                effort_tier=f"{size.capitalize()} effort",
                token_budget_est="5k - 20k tokens",
                cost_est_usd="$0.02 - $0.08",
                rationale="Standard coding and editing task. Claude 3.7 Sonnet balances accuracy, prompt cache reuse, and speed.",
                caveats="Verify outputs with local unit tests.",
                size=size,
                domain=domain,
            )

        # Scale budget and cost by size
        token_est = rule["token_budget_est"]
        cost_est = rule["cost_est_usd"]
        rec_model = rule["recommended_model"]
        rec_tool = rule["recommended_tool"]

        if size == "quick" and "Haiku" in rule.get("fallback_model", ""):
            rec_model = rule["fallback_model"]
            token_est = "1k - 5k tokens"
            cost_est = "< $0.02"
        elif size == "complex":
            token_est = "20k - 60k tokens"
            cost_est = "$0.10 - $0.35"

        return TaskRecommendation(
            task_type=task_type,
            recommended_tool=rec_tool,
            recommended_model=rec_model,
            fallback_model=rule.get("fallback_model", "Claude 3.5 Haiku"),
            effort_tier=rule.get("effort_tier", size),
            token_budget_est=token_est,
            cost_est_usd=cost_est,
            rationale=rule.get("rationale", ""),
            caveats=rule.get("caveats", ""),
            size=size,
            domain=domain,
        )

    def list_task_types(self) -> List[str]:
        return list(self.rules_by_type.keys())


def recommend_tool(task_type: str, size: str = "medium", domain: str = "fullstack") -> TaskRecommendation:
    return ToolAdvisor().recommend(task_type, size=size, domain=domain)
