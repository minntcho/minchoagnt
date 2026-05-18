import tempfile
import unittest
from pathlib import Path

from minchoagnt.memory import MemoryLimitError, MemoryMatchError, MemoryStore


class MemoryStoreTests(unittest.TestCase):
    def test_add_persists_but_current_snapshot_stays_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            store = MemoryStore(home, memory_limit=200, user_limit=120)
            store.load()

            store.add("memory", "Project uses Python unittest for the mini slice.")

            self.assertEqual(
                store.entries("memory"),
                ["Project uses Python unittest for the mini slice."],
            )
            self.assertIsNone(store.snapshot("memory"))

            next_session = MemoryStore(home, memory_limit=200, user_limit=120)
            next_session.load()

            self.assertIn("MEMORY", next_session.snapshot("memory"))
            self.assertIn("Python unittest", next_session.snapshot("memory"))

    def test_replace_requires_a_unique_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp))
            store.load()
            store.add("user", "User prefers short Korean answers.")
            store.add("user", "User prefers examples after the summary.")

            with self.assertRaises(MemoryMatchError):
                store.replace("user", "prefers", "User prefers concise Korean answers.")

            store.replace("user", "short Korean", "User prefers concise Korean answers.")

            self.assertEqual(
                store.entries("user"),
                [
                    "User prefers concise Korean answers.",
                    "User prefers examples after the summary.",
                ],
            )

    def test_limit_error_reports_current_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp), memory_limit=32)
            store.load()
            store.add("memory", "small fact")

            with self.assertRaises(MemoryLimitError) as caught:
                store.add("memory", "this fact is too long to fit in this tiny store")

            self.assertIn("small fact", caught.exception.current_entries)


if __name__ == "__main__":
    unittest.main()
