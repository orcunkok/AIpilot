import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter import OpenAIAdapter
from harness import Event, Harness


def _load_dotenv():
    path = ROOT / '.env'
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


class LiveWakeTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('OPENAI_API_KEY'), 'OPENAI_API_KEY not set')
    def test_alfa_bravo_no_takeoff_before_clearance(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        harness = Harness(
            OpenAIAdapter(),
            skills_dir=ROOT / 'skills',
            runs_dir=tmp.name,
            run_id='live',
        )
        first = harness.wake(Event('operator', 'Fly from ALFA to BRAVO.'))
        second = harness.wake(Event(
            'atc',
            'Demo 12, taxi via Alpha, hold short runway 27.',
            clearance='taxi via A hold short 27',
        ))
        tokens = first.tokens + second.tokens
        names = [item['name'] for item in first.outcomes + second.outcomes]
        takeoffs = [
            item for item in first.outcomes + second.outcomes
            if item['name'] == 'set_intent' and item['args'].get('name') == 'takeoff'
            and str(item['result']).startswith('completed')
        ]
        xmits = [
            item['args'].get('text', '')
            for item in first.outcomes + second.outcomes
            if item['name'] == 'xmit'
        ]
        print(f'live wake tokens={tokens} calls={first.calls + second.calls} tools={names}')
        self.assertGreater(tokens, 0)
        self.assertIn('load_skill', names)
        self.assertTrue(xmits, 'expected a radio readback')
        self.assertTrue(
            any('27' in text or 'Alpha' in text or 'taxi' in text.lower() for text in xmits),
            f'readback missing taxi details: {xmits}',
        )
        self.assertEqual(takeoffs, [], 'takeoff must not complete before takeoff clearance')


if __name__ == '__main__':
    unittest.main()
