"""Budget Warnings & Runaway Cost Protection for DevCity."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class BudgetStatus:
    daily_budget_usd: float
    current_day_cost_usd: float
    is_exceeded: bool
    pct_used: float
    warning_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_budget_usd": self.daily_budget_usd,
            "current_day_cost_usd": self.current_day_cost_usd,
            "is_exceeded": self.is_exceeded,
            "pct_used": round(self.pct_used, 1),
            "warning_message": self.warning_message,
        }


class BudgetGuard:
    """Monitors daily and session costs against configured budget limits."""

    def __init__(self, daily_budget_usd: float = 10.0, session_warn_threshold_usd: float = 3.0):
        self.daily_budget_usd = daily_budget_usd
        self.session_warn_threshold_usd = session_warn_threshold_usd

    def check_daily_budget(self, today_cost_usd: float) -> BudgetStatus:
        pct = (today_cost_usd / self.daily_budget_usd * 100.0) if self.daily_budget_usd > 0 else 0.0
        exceeded = today_cost_usd >= self.daily_budget_usd

        msg = None
        if exceeded:
            msg = (
                f"🚨 Daily AI Budget Alert: Today's spend (${today_cost_usd:.2f}) has exceeded your "
                f"configured limit (${self.daily_budget_usd:.2f})."
            )
        elif pct >= 80.0:
            msg = (
                f"⚠️ Daily AI Budget Warning: Today's spend (${today_cost_usd:.2f}) is at {pct:.0f}% "
                f"of your daily limit (${self.daily_budget_usd:.2f})."
            )

        return BudgetStatus(
            daily_budget_usd=self.daily_budget_usd,
            current_day_cost_usd=today_cost_usd,
            is_exceeded=exceeded,
            pct_used=pct,
            warning_message=msg,
        )

    def check_session_runaway(self, session_cost_usd: float, turns: int) -> Optional[str]:
        """Detects if an ongoing agent session is burning excessive tokens."""
        if session_cost_usd >= self.session_warn_threshold_usd:
            return (
                f"⚠️ Runaway Agent Warning: Current session has reached ${session_cost_usd:.2f} across {turns} turns. "
                "Check for failing test retry loops or consider running `/compact`."
            )
        return None
