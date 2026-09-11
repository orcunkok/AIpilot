import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter import ModelTurn, ScriptedAdapter, ToolCall
from harness import Event, Harness


class HarnessProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.harness = Harness(
            ScriptedAdapter([]),
            skills_dir=ROOT / 'skills',
            runs_dir=self.tmp.name,
            run_id='protocol',
        )

    def _snapshot_blocks(self, messages):
        return [m['content'] for m in messages if m['content'].startswith('SNAPSHOT')]

    def test_snapshot_replaced_not_appended(self):
        self.harness.world.phase = 'parked'
        self.harness.assemble(Event('operator', 'first'))
        self.harness.world.phase = 'holding_short'
        messages = self.harness.assemble(Event('operator', 'second'))
        snaps = self._snapshot_blocks(messages)
        self.assertEqual(len(snaps), 1)
        self.assertIn('holding_short', snaps[0])
        self.assertNotIn('parked', snaps[0])

    def test_load_skill_replaces_prior_body(self):
        self.harness.execute('load_skill', {'name': 'taxi'})
        first = self.harness.assemble(Event('operator', 'x'))
        bodies = [m['content'] for m in first if m['content'].startswith('SKILL_BODY')]
        self.assertEqual(len(bodies), 1)
        self.assertIn('Do not enter the runway', bodies[0])
        self.harness.execute('load_skill', {'name': 'atc-phraseology'})
        second = self.harness.assemble(Event('operator', 'x'))
        bodies = [m['content'] for m in second if m['content'].startswith('SKILL_BODY')]
        self.assertEqual(len(bodies), 1)
        self.assertIn('SKILL_BODY atc-phraseology', bodies[0])
        self.assertNotIn('Do not enter the runway', bodies[0])

    def test_compaction_keeps_last_atc_verbatim(self):
        atc = 'Demo 12, taxi via Alpha, hold short runway 27.'
        self.harness.adapter = ScriptedAdapter([
            ModelTurn(tool_calls=[ToolCall('1', 'xmit', {'text': 'Taxi via Alpha, hold short 27, Demo 12'})]),
            ModelTurn(text='holding short'),
        ])
        self.harness.wake(Event('atc', atc, clearance='taxi via A hold short 27'))
        messages = self.harness.assemble(Event('operator', 'next'))
        history = [m['content'] for m in messages if m['content'].startswith('HISTORY')][0]
        self.assertIn(atc, history)
        self.assertNotIn('tool', [m['role'] for m in messages])
        raw = ''.join(m['content'] for m in messages)
        self.assertNotIn('tool_call_id', raw)

    def test_tools_receive_args_only(self):
        seen = []
        original = self.harness.world.set_intent

        def spy(name, route='', hold_short=''):
            seen.append({'name': name, 'route': route, 'hold_short': hold_short})
            return original(name, route=route, hold_short=hold_short)

        self.harness.world.set_intent = spy
        self.harness.execute('set_intent', {'name': 'taxi', 'route': 'A', 'hold_short': '27'})
        self.assertEqual(seen, [{'name': 'taxi', 'route': 'A', 'hold_short': '27'}])


if __name__ == '__main__':
    unittest.main()
