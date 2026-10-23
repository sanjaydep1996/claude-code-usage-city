"""Pricing calculation and model family classification for DevCity."""

import json
import pathlib
from typing import Dict, Any, Tuple, Optional

DEFAULT_PRICING = {
    "_note": "API list prices in USD per 1M tokens as of 2026-10-06. Used to estimate an API-EQUIVALENT cost.",
    "fastMultiplier": 2,
    "effectiveDate": "2026-10-06",
    "models": {
        "claude-fable-5-1": {"input": 10, "output": 50, "cacheRead": 0.25, "source": "anthropic"},
        "claude-mythos-5-1": {"input": 10, "output": 50, "cacheRead": 0.25, "source": "anthropic"},
        "claude-fable-5": {"input": 10, "output": 50, "source": "anthropic"},
        "claude-opus-5-5": {"input": 4, "output": 20, "cacheRead": 0.20, "source": "anthropic"},
        "claude-opus-5": {"input": 5, "output": 25, "source": "anthropic"},
        "claude-opus-4-8": {"input": 5, "output": 25, "source": "anthropic"},
        "claude-opus-4-7": {"input": 5, "output": 25, "source": "anthropic"},
        "claude-opus-4-6": {"input": 5, "output": 25, "source": "anthropic"},
        "claude-sonnet-5-5": {"input": 2, "output": 10, "cacheRead": 0.20, "source": "anthropic"},
        "claude-sonnet-5": {"input": 2, "output": 10, "source": "anthropic"},
        "claude-sonnet-4-6": {"input": 3, "output": 15, "source": "anthropic"},
        "claude-3-5-sonnet": {"input": 3, "output": 15, "cacheRead": 0.30, "source": "anthropic"},
        "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "source": "anthropic"},
        "claude-haiku-4-5": {"input": 1, "output": 5, "source": "anthropic"},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.0, "source": "anthropic"},
        "gemini-3.8-flash": {"input": 0.15, "output": 0.60, "cacheRead": 0.0375, "source": "google"},
        "gemini-2.5-pro": {"input": 1.25, "output": 5.00, "cacheRead": 0.3125, "source": "google"},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30, "cacheRead": 0.01875, "source": "google"},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "cacheRead": 0.025, "source": "google"},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00, "cacheRead": 0.3125, "source": "google"},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "cacheRead": 0.01875, "source": "google"}
    },
    "fallback": {"input": 3.0, "output": 15.0}
}


def load_pricing(pricing_file: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    if pricing_file and pricing_file.exists():
        try:
            return json.loads(pricing_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Try finding pricing.json in current or parent directories
    for candidate in [pathlib.Path("pricing.json"), pathlib.Path(__file__).resolve().parent.parent / "pricing.json"]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                pass
    return DEFAULT_PRICING


class PricingCalculator:
    def __init__(self, pricing_dict: Optional[Dict[str, Any]] = None):
        self.pricing = pricing_dict or load_pricing()
        self.models = self.pricing.get("models", {})
        self.fallback = self.pricing.get("fallback", {"input": 3.0, "output": 15.0})
        self.fast_mult = self.pricing.get("fastMultiplier", 1.0)
        self.effective_date = self.pricing.get("effectiveDate", "2026-10-06")

    def rates(self, model: str) -> Tuple[float, float, float, float]:
        """Returns (input, output, cacheWrite, cacheRead) cost in USD per 1M tokens."""
        if not model:
            r = self.fallback
        else:
            m_lower = model.lower()
            if m_lower in self.models:
                r = self.models[m_lower]
            else:
                r = None
                for k, v in self.models.items():
                    if k in m_lower or m_lower in k:
                        r = v
                        break
            if not r:
                r = self.fallback

        ri = r.get("input", 3.0)
        ro = r.get("output", 15.0)
        rw = r.get("cacheWrite", ri * 1.25)
        rr = r.get("cacheRead", ri * 0.1)
        return ri, ro, rw, rr

    def compute_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_write: int = 0,
        cache_read: int = 0,
        is_fast: bool = False
    ) -> float:
        ri, ro, rw, rr = self.rates(model)
        cost = (input_tokens * ri + output_tokens * ro + cache_write * rw + cache_read * rr) / 1e6
        if is_fast:
            cost *= self.fast_mult
        return cost

    def compute_cache_savings(self, model: str, cache_read: int) -> float:
        """Computes USD saved by cache reads vs standard input token rates."""
        if cache_read <= 0:
            return 0.0
        ri, _, _, rr = self.rates(model)
        saved = (cache_read * (ri - rr)) / 1e6
        return max(0.0, saved)


def classify_family(model: str) -> str:
    if not model:
        return "other"
    m = model.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    if "fable" in m or "mythos" in m:
        return "fable"
    if "gemini" in m:
        return "gemini"
    return "other"
