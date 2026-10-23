"""AI Health Score engine for DevCity.

Computes a deterministic A–F health grade and top 3 actionable tips
based on prompt cache efficiency, leak frequency, and session hygiene.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class HealthScoreResult:
    score: int  # 0 to 100
    grade: str  # 'A+', 'A', 'B+', 'B', 'C', 'D', 'F'
    cache_score: int
    hygiene_score: int
    savings_score: int
    top_tips: List[str] = field(default_factory=list)
    leaks_count: int = 0
    headline_savings: str = "$0.00"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "cache_score": self.cache_score,
            "hygiene_score": self.hygiene_score,
            "savings_score": self.savings_score,
            "top_tips": self.top_tips,
            "leaks_count": self.leaks_count,
            "headline_savings": self.headline_savings,
        }


def calculate_health_score(payload: Dict[str, Any]) -> HealthScoreResult:
    """Calculates deterministic health grade and tailored tips from aggregated payload."""
    t = payload.get("totals", {})
    projects = payload.get("projects", [])

    hit_rate = t.get("cacheHitRate", 0.0)
    cost = t.get("costUSD", 0.0)
    saved = t.get("costSavedUSD", 0.0)
    sessions = max(1, t.get("sessions", 1))
    active_hours = t.get("activeHours", 0.0)

    # 1. Cache Hit Score (max 40)
    if hit_rate >= 0.85:
        cache_score = 40
    elif hit_rate >= 0.70:
        cache_score = 32
    elif hit_rate >= 0.50:
        cache_score = 22
    elif hit_rate >= 0.30:
        cache_score = 14
    else:
        cache_score = 6

    # 2. Leaks Penalty (up to -25)
    leaks = [p for p in projects if p.get("cacheLeak")]
    leak_penalty = min(25, len(leaks) * 10)
    cache_score = max(0, cache_score - leak_penalty)

    # 3. Session Hygiene (max 30)
    avg_hours = active_hours / sessions
    if avg_hours <= 1.5:
        hygiene_score = 30
    elif avg_hours <= 3.5:
        hygiene_score = 22
    else:
        hygiene_score = 12

    # 4. Savings Score (max 30)
    total_potential = cost + saved
    savings_ratio = (saved / total_potential) if total_potential > 0 else 0.0
    if savings_ratio >= 0.50:
        savings_score = 30
    elif savings_ratio >= 0.30:
        savings_score = 22
    elif savings_ratio >= 0.15:
        savings_score = 15
    else:
        savings_score = 8

    final_score = min(100, max(0, cache_score + hygiene_score + savings_score))

    # Determine Grade
    if final_score >= 95:
        grade = "A+"
    elif final_score >= 90:
        grade = "A"
    elif final_score >= 85:
        grade = "B+"
    elif final_score >= 80:
        grade = "B"
    elif final_score >= 70:
        grade = "C"
    elif final_score >= 60:
        grade = "D"
    else:
        grade = "F"

    # Generate Top 3 Concrete Tips
    tips: List[str] = []
    if leaks:
        leak_names = [p["name"] for p in leaks[:2]]
        tips.append(
            f"Fix Cache Thrashing in {', '.join(leak_names)}: Cache writes exceeded reads. "
            "Keep system prompts and tool configurations stable across turns."
        )

    if hit_rate < 0.70:
        tips.append(
            f"Warm Your Prompt Cache: Current hit rate is {int(hit_rate * 100)}%. "
            "Keep CLAUDE.md under 150 lines and avoid switching branches mid-session."
        )

    if avg_hours > 2.5:
        tips.append(
            f"Reset Long Sessions: Average active session is {avg_hours:.1f} hours. "
            "Run `/compact` or `/clear` every ~35 turns to shed stale prompt context."
        )

    if len(tips) < 3:
        tips.append(
            "Use Right-Sized Models: Reserve Claude 3.7 Sonnet / Opus for architecture and multi-file refactors; "
            "use Haiku or Flash for quick edits and tests."
        )
    if len(tips) < 3:
        tips.append(
            f"Maintain High Savings: Prompt caching already saved ~${saved:,.2f} this period! "
            "Continue keeping project instructions stable."
        )
    if len(tips) < 3:
        tips.append(
            "Audit Your Repo: Run `devcity audit` on your active repositories to ensure CLAUDE.md and .gitignore are optimized."
        )
    if len(tips) < 3:
        tips.append(
            "Follow Production Playbooks: Use DevCity Playbooks to guide step-by-step feature development with tested prompt templates."
        )

    return HealthScoreResult(
        score=final_score,
        grade=grade,
        cache_score=cache_score,
        hygiene_score=hygiene_score,
        savings_score=savings_score,
        top_tips=tips[:3],
        leaks_count=len(leaks),
        headline_savings=f"${saved:,.2f}"
    )
