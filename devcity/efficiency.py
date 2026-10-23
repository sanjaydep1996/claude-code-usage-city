"""Cache efficiency and leak detection rules for DevCity."""

from typing import Dict, Any, Tuple, Optional


DEFAULT_SOURCE_THRESHOLDS = {
    "claude-code": 0.75,   # Claude Code typically hits 85-95% cache hit rate
    "antigravity": 0.50,
    "default": 0.50
}


def calculate_cache_hit_rate(input_tokens: int, cache_write_tokens: int, cache_read_tokens: int) -> float:
    total_input = input_tokens + cache_write_tokens + cache_read_tokens
    if total_input <= 0:
        return 0.0
    return round(cache_read_tokens / total_input, 4)


def evaluate_cache_leak(
    source: str,
    cost_usd: float,
    input_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
    threshold: Optional[float] = None
) -> Tuple[bool, Optional[str]]:
    """Evaluates whether a project or session suffers from prompt cache thrashing/leaks."""
    # Only flag meaningful spend
    if cost_usd < 5.0:
        return False, None

    th = threshold if threshold is not None else DEFAULT_SOURCE_THRESHOLDS.get(source, DEFAULT_SOURCE_THRESHOLDS["default"])
    hit_rate = calculate_cache_hit_rate(input_tokens, cache_write_tokens, cache_read_tokens)

    # If hit rate is significantly below threshold and writes exceed reads (cache thrashing)
    if hit_rate < th and cache_write_tokens > cache_read_tokens:
        pct = round(hit_rate * 100, 1)
        reason = (
            f"Cache Thrashing: Hit rate is only {pct}% (expected >{int(th*100)}%). "
            f"{round(cache_write_tokens / 1e6, 2)}M tokens written to cache but only {round(cache_read_tokens / 1e6, 2)}M reused."
        )
        return True, reason

    if hit_rate < (th * 0.5) and (cache_write_tokens + cache_read_tokens) > 1_000_000:
        pct = round(hit_rate * 100, 1)
        reason = f"Low Cache Reuse: Only {pct}% hit rate on heavy context sessions. Gaps between prompts caused full context re-writes."
        return True, reason

    return False, None
