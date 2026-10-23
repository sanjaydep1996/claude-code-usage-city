"""Base collector interface and normalized session data structures."""

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
import datetime as dt
from typing import List, Dict, Tuple, Optional


@dataclass
class NormalizedSession:
    source: str               # "claude-code", "antigravity"
    project_name: str         # folder basename ONLY (e.g. "ecommerce-api"), or "Project A" if anonymized. NEVER absolute paths.
    session_id: str           # unique session identifier
    timestamp: dt.datetime    # session start or main event timestamp
    model: str                # model identifier
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    tool_calls: Counter = field(default_factory=Counter)
    event_timestamps: List[float] = field(default_factory=list)  # for active time computation

    def dedupe_key(self) -> Tuple[str, str]:
        return (self.source, self.session_id)


class BaseCollector(ABC):
    """Abstract collector that discovers and parses sessions from an AI coding tool."""

    id: str = "base"
    name: str = "Base Collector"
    description: str = ""

    @abstractmethod
    def detect(self) -> bool:
        """Returns True if the tool logs exist on the machine."""
        pass

    @abstractmethod
    def collect(self, since: dt.datetime, anonymize: bool = False) -> List[NormalizedSession]:
        """Collects sessions since a given date."""
        pass
