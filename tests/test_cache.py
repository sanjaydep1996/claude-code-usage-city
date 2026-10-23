"""Unit tests for devcity/cache.py."""

import pathlib
import tempfile
import unittest
from devcity.cache import MetricsCache


class TestMetricsCache(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = pathlib.Path(self.temp_dir.name) / "test_cache.db"
        self.cache = MetricsCache(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_version(self):
        with self.cache._get_conn() as conn:
            cur = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["value"], "1")

    def test_incremental_file_offset_and_truncation(self):
        sample_file = pathlib.Path(self.temp_dir.name) / "sample.jsonl"
        sample_file.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")

        # Initial offset is 0
        offset0 = self.cache.get_file_offset(sample_file)
        self.assertEqual(offset0, 0)

        # Update offset to current file size
        fsize = sample_file.stat().st_size
        self.cache.update_file_offset(sample_file, fsize)

        # Next check returns updated offset
        self.assertEqual(self.cache.get_file_offset(sample_file), fsize)

        # Now truncate the file to smaller size
        sample_file.write_text('{"a": 1}\n', encoding="utf-8")
        # Offset must automatically reset to 0 to prevent missed data!
        self.assertEqual(self.cache.get_file_offset(sample_file), 0)

    def test_save_and_retrieve_session(self):
        self.cache.save_session(
            source="claude-code",
            project_name="my-project",
            session_id="sess_123",
            timestamp_iso="2026-10-23T12:00:00Z",
            model="claude-sonnet-5-5",
            input_tokens=1000,
            output_tokens=200,
            cache_write_tokens=5000,
            cache_read_tokens=20000,
            tool_calls={"Bash": 5},
            event_timestamps=[1729684800.0, 1729684900.0]
        )

        sessions = self.cache.get_sessions("2026-10-23T00:00:00Z")
        self.assertEqual(len(sessions), 1)
        s = sessions[0]
        self.assertEqual(s["source"], "claude-code")
        self.assertEqual(s["project_name"], "my-project")
        self.assertEqual(s["input_tokens"], 1000)
        self.assertEqual(s["tool_calls"], {"Bash": 5})


if __name__ == "__main__":
    unittest.main()
