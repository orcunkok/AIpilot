import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter import ModelTurn, ScriptedAdapter
from harness import Harness
from terminal_ui import Session


class SessionTests(unittest.TestCase):
    def test_atc_grants_clearance_and_records_transcript(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        atc = 'Demo 12, taxi via Alpha, hold short runway 27.'
        harness = Harness(
            ScriptedAdapter([ModelTurn(text='Taxi via Alpha, hold short 27, Demo 12.')]),
            skills_dir=ROOT / 'skills',
            runs_dir=tmp.name,
            run_id='session',
        )
        session = Session(harness)
        self.assertTrue(session.submit('/atc ' + atc))
        self.assertTrue(any('taxi' in item.lower() for item in harness.world.clearances))
        self.assertEqual(harness.world.clearances, [atc])
        self.assertIn(('ATC', atc), harness.transcript)
        self.assertIn(('AI', 'Taxi via Alpha, hold short 27, Demo 12.'), harness.transcript)
        self.assertIn(('ATC', atc), session.messages)
        self.assertIn(('AI', 'Taxi via Alpha, hold short 27, Demo 12.'), session.messages)


if __name__ == '__main__':
    unittest.main()
