"""Playbook engine for DevCity.

Parses, validates, and renders markdown production playbooks.
"""

import pathlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

_PLAYBOOKS_DIR = pathlib.Path(__file__).parent.parent.parent / "playbooks"


@dataclass
class PlaybookStep:
    step_number: int
    title: str
    goal: str
    ai_tool_model: str
    why: str
    prompt_template: str
    checklist: List[str]
    common_mistakes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "goal": self.goal,
            "ai_tool_model": self.ai_tool_model,
            "why": self.why,
            "prompt_template": self.prompt_template,
            "checklist": self.checklist,
            "common_mistakes": self.common_mistakes,
        }


@dataclass
class Playbook:
    name: str
    title: str
    overview: str
    steps: List[PlaybookStep]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "overview": self.overview,
            "steps": [s.to_dict() for s in self.steps],
        }


def parse_playbook_markdown(name: str, content: str) -> Playbook:
    """Parses a playbook markdown file into structured steps."""
    lines = content.split("\n")
    title = name
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Extract overview
    overview = ""
    overview_match = re.search(r"## Architecture Overview\n(.*?)(?=\n## Step|\Z)", content, re.DOTALL)
    if overview_match:
        overview = overview_match.group(1).strip()

    # Split steps by '## Step N:'
    step_chunks = re.split(r"## Step (\d+):\s*(.*?)\n", content)
    steps: List[PlaybookStep] = []

    # re.split produces [preamble, step_num, step_title, step_body, step_num, step_title, step_body, ...]
    for i in range(1, len(step_chunks), 3):
        step_num = int(step_chunks[i])
        step_title = step_chunks[i+1].strip()
        body = step_chunks[i+2]

        goal_m = re.search(r"-\s*\*\*Goal:\*\*\s*(.*?)(?=\n-\s*\*\*|\Z)", body, re.DOTALL)
        tool_m = re.search(r"-\s*\*\*AI Tool & Model:\*\*\s*(.*?)(?=\n-\s*\*\*|\Z)", body, re.DOTALL)
        why_m = re.search(r"-\s*\*\*Why:\*\*\s*(.*?)(?=\n-\s*\*\*|\Z)", body, re.DOTALL)
        prompt_m = re.search(r"-\s*\*\*Prompt Template:\*\*\s*\n\s*```(?:text)?\n(.*?)\n\s*```", body, re.DOTALL)
        mistakes_m = re.search(r"-\s*\*\*Common Mistakes:\*\*\s*(.*?)(?=\n##|\Z)", body, re.DOTALL)

        checklist: List[str] = []
        for line in body.split("\n"):
            if "- [ ]" in line or "- [x]" in line:
                item = re.sub(r"^.*-\s*\[[ x]\]\s*", "", line).strip()
                if item:
                    checklist.append(item)

        steps.append(PlaybookStep(
            step_number=step_num,
            title=step_title,
            goal=goal_m.group(1).strip() if goal_m else "",
            ai_tool_model=tool_m.group(1).strip() if tool_m else "",
            why=why_m.group(1).strip() if why_m else "",
            prompt_template=prompt_m.group(1).strip() if prompt_m else "",
            checklist=checklist,
            common_mistakes=mistakes_m.group(1).strip() if mistakes_m else "",
        ))

    return Playbook(name=name, title=title, overview=overview, steps=steps)


def load_playbook(name_or_filename: str) -> Optional[Playbook]:
    """Loads a playbook by name or filename from playbooks/ directory."""
    filename = name_or_filename if name_or_filename.endswith(".md") else f"{name_or_filename}.md"
    path = _PLAYBOOKS_DIR / filename
    if not path.exists():
        # Check current working directory playbooks/
        path = pathlib.Path("playbooks") / filename
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    slug = path.stem
    return parse_playbook_markdown(slug, content)


def list_playbooks() -> List[str]:
    """Returns list of available playbook slugs."""
    dir_to_check = _PLAYBOOKS_DIR if _PLAYBOOKS_DIR.exists() else pathlib.Path("playbooks")
    if not dir_to_check.exists():
        return []
    return [p.stem for p in dir_to_check.glob("*.md")]
