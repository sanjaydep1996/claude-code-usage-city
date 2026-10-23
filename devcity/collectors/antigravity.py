"""Collector for Google Antigravity session transcripts."""

import collections
import datetime as dt
import json
import os
import pathlib
import re
from typing import List, Optional

from .base import BaseCollector, NormalizedSession
from ..cache import MetricsCache


class AntigravityCollector(BaseCollector):
    id = "antigravity"
    name = "Google Antigravity"
    description = "Parses ~/.gemini/antigravity/brain/**/transcript*.jsonl session logs."

    def __init__(self, root: Optional[pathlib.Path] = None, cache: Optional[MetricsCache] = None):
        self.root = pathlib.Path(root or os.path.expanduser("~/.gemini/antigravity/brain"))
        self.cache = cache

    def detect(self) -> bool:
        return self.root.exists() and any(self.root.rglob("transcript*.jsonl"))

    def collect(self, since: dt.datetime, anonymize: bool = False) -> List[NormalizedSession]:
        if not self.root.exists():
            return []

        files = sorted(self.root.rglob("transcript*.jsonl"))
        if not files:
            return []

        sessions = []

        for f in files:
            # Skip duplicate full/compact pairs if both exist: prefer compact transcript.jsonl
            if f.name == "transcript_full.jsonl" and (f.parent / "transcript.jsonl").exists():
                continue

            conv_id = f.parent.parent.name if f.parent.name == "logs" else f.parent.name
            if conv_id == ".system_generated":
                conv_id = f.parent.parent.parent.name

            try:
                start_offset = 0
                if self.cache:
                    start_offset = self.cache.get_file_offset(f)

                current_project = None
                current_model = "gemini-3.8-flash"
                timestamps = []
                inp_tot = 0
                out_tot = 0
                cr_tot = 0
                cw_tot = 0
                tools = collections.Counter()
                first_time = None

                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    if start_offset > 0:
                        fh.seek(start_offset)

                    for line in fh:
                        if not line.strip():
                            continue
                        try:
                            d = json.loads(line)
                        except ValueError:
                            continue

                        ts = d.get("created_at")
                        if not ts:
                            continue
                        try:
                            t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except Exception:
                            continue

                        if t < since:
                            continue

                        if first_time is None or t < first_time:
                            first_time = t

                        timestamps.append(t.timestamp())

                        # Detect model setting changes if present in setting changes
                        content = d.get("content") or ""
                        if "Model Selection" in content:
                            m_match = re.search(r"Model Selection` from \S+ to ([^.\n]+)", content)
                            if m_match:
                                m_name = m_match.group(1).lower()
                                if "pro" in m_name:
                                    current_model = "gemini-2.5-pro"
                                elif "flash" in m_name:
                                    current_model = "gemini-3.8-flash"

                        # Extract token counts
                        inp = d.get("input_tokens") or 0
                        out = d.get("output_tokens") or 0
                        cr = d.get("cache_read_tokens") or 0

                        inp_tot += inp
                        out_tot += out
                        cr_tot += cr

                        # Extract tool calls and project directory basename ONLY
                        for tc in d.get("tool_calls") or []:
                            t_name = tc.get("name") or "tool"
                            tools[t_name] += 1
                            args = tc.get("args") or {}
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    args = {}
                            if not current_project:
                                raw_path = args.get("Cwd") or args.get("AbsolutePath") or args.get("TargetFile")
                                if raw_path:
                                    p = pathlib.Path(raw_path)
                                    if p.is_file():
                                        p = p.parent
                                    current_project = p.name.strip()

                    if self.cache:
                        self.cache.update_file_offset(f, fh.tell())

                if not first_time or (inp_tot == 0 and out_tot == 0 and len(tools) == 0):
                    continue

                proj = current_project or "antigravity-workspace"

                session = NormalizedSession(
                    source=self.id,
                    project_name=proj,
                    session_id=conv_id,
                    timestamp=first_time,
                    model=current_model,
                    input_tokens=inp_tot,
                    output_tokens=out_tot,
                    cache_write_tokens=cw_tot,
                    cache_read_tokens=cr_tot,
                    tool_calls=tools,
                    event_timestamps=sorted(timestamps),
                )
                sessions.append(session)

                if self.cache:
                    self.cache.save_session(
                        source=self.id,
                        project_name=proj,
                        session_id=conv_id,
                        timestamp_iso=first_time.isoformat(),
                        model=current_model,
                        input_tokens=inp_tot,
                        output_tokens=out_tot,
                        cache_write_tokens=cw_tot,
                        cache_read_tokens=cr_tot,
                        tool_calls=dict(tools),
                        event_timestamps=sorted(timestamps),
                    )
            except Exception:
                continue

        return sessions
