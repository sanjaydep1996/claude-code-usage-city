# Contributing to DevCity

Thank you for contributing! DevCity is built to be a privacy-first, zero-dependency, local observability cockpit for software engineers.

## Non-Negotiable Privacy Rules

When contributing code or new collectors, you must uphold these non-negotiable rules:
1. **Never Collect Raw Text**: Prompts, assistant replies, source code, and diffs must be discarded at parse time. Only token integers, timestamps, model names, and tool names may be stored.
2. **Never Store Absolute Paths**: Only folder basenames (e.g. `ecommerce-api`) are retained. Never store `/Users/...`, `/home/...`, git remotes, or usernames.
3. **Zero Outbound Telemetry**: DevCity runs 100% offline. No analytics, tracking pings, or cloud phone-home calls.
4. **Secret Leak Test**: Every new collector must pass `tests/test_privacy.py` asserting that secret tokens fed through mock fixtures never appear in JSON outputs or SQLite tables.

## Adding a New Collector

1. Read `plugins/template_collector.py`.
2. Implement your collector inheriting from `devcity.collectors.base.BaseCollector`.
3. Add a test in `tests/test_<your_tool>_collector.py` using synthetic fixtures.
4. Run the test suite:
   ```bash
   python3 -m unittest discover tests/
   ```
5. Submit a pull request!
