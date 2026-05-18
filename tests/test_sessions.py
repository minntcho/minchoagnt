import tempfile
import unittest
from pathlib import Path

from minchoagnt.sessions import SessionDB


class SessionDBTests(unittest.TestCase):
    def test_appends_messages_and_searches_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDB(Path(tmp) / "state.db")
            session_id = db.create_session(source="cli")

            db.append_message(session_id, "user", "remember: deploy uses fly.io")
            db.append_message(session_id, "assistant", "Noted for review.")

            results = db.search_messages("deploy")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].session_id, session_id)
            self.assertEqual(results[0].role, "user")
            self.assertIn("fly.io", results[0].content)

    def test_loads_conversation_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDB(Path(tmp) / "state.db")
            session_id = db.create_session(source="cli")
            db.append_message(session_id, "user", "first")
            db.append_message(session_id, "assistant", "second")

            messages = db.get_messages(session_id)

            self.assertEqual([m.content for m in messages], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
