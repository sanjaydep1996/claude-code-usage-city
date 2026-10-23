"""Template collector for community contributions (<50 lines).

Copy this file to add support for a new AI coding tool (e.g. Cursor, Ollama, Aider).
Remember: Never extract prompt text, response text, code diffs, or absolute paths!
"""

import datetime as dt
import pathlib
from typing import List, Optional

from devcity.collectors.base import BaseCollector, NormalizedSession


class TemplateCollector(BaseCollector):
    id = "my-tool"
    name = "My AI Tool"
    description = "Parses session logs from ~/.my-tool/**/*.json."

    def __init__(self, root: Optional[pathlib.Path] = None):
        self.root = pathlib.Path(root or pathlib.Path.home() / ".my-tool")

    def detect(self) -> bool:
        """Returns True if the tool logs exist on the machine."""
        return self.root.exists() and any(self.root.rglob("*.json"))

    def collect(self, since: dt.datetime, anonymize: bool = False) -> List[NormalizedSession]:
        """Parses local logs and returns normalized sessions."""
        if not self.root.exists():
            return []

        sessions = []
        for f in self.root.rglob("*.json"):
            # 1. Parse timestamps and session ID
            # 2. Extract ONLY token numbers, model name, tool names, and folder BASENAME
            # 3. Drop all prompt text, replies, and file contents immediately!
            sessions.append(
                NormalizedSession(
                    source=self.id,
                    project_name=f.parent.name,   # folder basename ONLY!
                    session_id=f.stem,
                    timestamp=dt.datetime.now(dt.timezone.utc),
                    model="model-name",
                    input_tokens=1000,
                    output_tokens=200,
                    cache_write_tokens=0,
                    cache_read_tokens=0,
                    tool_calls={"my_tool_call": 1},
                    event_timestamps=[dt.datetime.now(dt.timezone.utc).timestamp()]
                )
            )
        return sessions
