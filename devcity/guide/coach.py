"""Prompt Coach and Habit Coaching Rules for DevCity."""

from typing import Dict, List, Optional, Any

PROMPT_TEMPLATES = {
    "feature_spec": (
        "You are a Senior Software Engineer. We are designing [FEATURE_NAME].\n"
        "Requirements:\n"
        "1. [GOAL_1]\n"
        "2. [GOAL_2]\n"
        "Please provide:\n"
        "- Architecture plan\n"
        "- File touch points\n"
        "- Edge cases & test strategy\n"
        "Do not write final implementation code yet; let's align on the plan first."
    ),
    "explain_diff": (
        "Explain the following git diff in plain English for a code review:\n"
        "1. What business or technical change is being made?\n"
        "2. What are the potential security, performance, or regression risks?\n"
        "3. Are there any edge cases not covered by tests?"
    ),
    "compact_session": (
        "/compact Summarize our conversation so far, focusing strictly on:\n"
        "1. Architectural decisions made\n"
        "2. Files modified and current state\n"
        "3. Next immediate steps to finish the task"
    ),
    "security_review": (
        "Perform a focused security review on the following code:\n"
        "Check specifically for: injection (SQL, command, XSS), unauthenticated endpoints, "
        "improper error leakage, hardcoded credentials, and missing CSRF or CORS restrictions."
    )
}


class PromptCoach:
    """Provides prompt templates and habit coaching tips."""

    @staticmethod
    def get_template(name: str) -> Optional[str]:
        return PROMPT_TEMPLATES.get(name)

    @staticmethod
    def list_templates() -> List[str]:
        return list(PROMPT_TEMPLATES.keys())

    @staticmethod
    def evaluate_session_habits(session_meta: Dict[str, Any]) -> List[str]:
        """Evaluates session metadata and returns coaching advice."""
        tips = []
        turns = session_meta.get("turns", 0)
        cache_hit_rate = session_meta.get("cache_hit_rate", 1.0)
        cost = session_meta.get("cost_usd", 0.0)

        if turns > 35:
            tips.append(
                f"Session reached {turns} turns. Large prompt history increases token burn per request. "
                "Run `/compact` or `/clear` to reset context and save up to 40% on tokens."
            )
        if cache_hit_rate < 0.60:
            tips.append(
                f"Cache hit rate is low ({int(cache_hit_rate * 100)}%). "
                "Keep `CLAUDE.md` and system prompts stable; avoid frequent branch changes in one session."
            )
        if cost > 5.0:
            tips.append(
                f"Session cost reached ${cost:.2f}. Consider switching subtasks (e.g. tests or grep) "
                "to Claude 3.5 Haiku or Gemini Flash to cut costs."
            )
        return tips


def get_prompt_template(name: str) -> Optional[str]:
    return PromptCoach.get_template(name)
