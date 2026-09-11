"""PIC supervisor loop. Rebuilds context each wake. Tools get args only."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KERNEL = """You are the pilot in command (supervisor). Automation flies. You decide and communicate.

Priority: aviate, then navigate, then communicate.
Never invent a clearance. Read back ATC before acting on it.
Do not poll. Aircraft state is in SNAPSHOT. Prior wakes are in HISTORY.
To use a procedure, load_skill then set_intent. Radio is xmit."""

TOOL_SCHEMAS = [
    {
        'type': 'function',
        'function': {
            'name': 'load_skill',
            'description': 'Load one skill body by catalog name. Replaces any skill already loaded.',
            'parameters': {
                'type': 'object',
                'properties': {'name': {'type': 'string'}},
                'required': ['name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'xmit',
            'description': 'Transmit one radio phrase to ATC.',
            'parameters': {
                'type': 'object',
                'properties': {'text': {'type': 'string'}},
                'required': ['text'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'set_intent',
            'description': 'Ask automation to run a high-level intent (taxi, takeoff, engine_start).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'route': {'type': 'string'},
                    'hold_short': {'type': 'string'},
                },
                'required': ['name'],
            },
        },
    },
]


class Event:
    def __init__(self, kind, text, clearance=None):
        self.kind = kind
        self.text = text
        self.clearance = clearance


class WakeResult:
    def __init__(self, text, outcomes, tokens, calls):
        self.text = text
        self.outcomes = outcomes
        self.tokens = tokens
        self.calls = calls


class World:
    def __init__(self):
        self.callsign = 'Demo 12'
        self.mission = 'ALFA → BRAVO'
        self.phase = 'parked'
        self.position = 'ALFA / Stand 1'
        self.engine = 'off'
        self.clearances = []
        self.pending_atc = ''
        self.intent = ''

    def has_clearance(self, kind):
        token = kind.lower()
        return any(token in item.lower() for item in self.clearances)

    def set_intent(self, name, route='', hold_short=''):
        name = (name or '').lower()
        if name == 'taxi':
            if not self.has_clearance('taxi'):
                return 'blocked: no taxi clearance'
            self.intent = ''
            self.phase = 'holding_short'
            self.position = f"ALFA / Runway {hold_short or '27'}"
            return f"completed: holding short {hold_short or '27'} via {route or 'A'}"
        if name == 'takeoff':
            if not self.has_clearance('takeoff'):
                return 'blocked: no takeoff clearance'
            self.intent = ''
            self.phase = 'airborne'
            return 'completed: takeoff'
        if name in {'engine_start', 'start_engines'}:
            self.engine = 'running'
            self.intent = ''
            return 'completed: engine running'
        return f'blocked: unknown intent {name}'


def parse_skill(text):
    if not text.startswith('---'):
        return '', '', text.strip()
    parts = text.split('---', 2)
    if len(parts) < 3:
        return '', '', text.strip()
    meta = {}
    for line in parts[1].splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            meta[key.strip()] = value.strip()
    return meta.get('name', ''), meta.get('description', ''), parts[2].strip()


def load_catalog(skills_dir):
    catalog = []
    bodies = {}
    if not skills_dir.is_dir():
        return catalog, bodies
    for path in sorted(skills_dir.glob('*/SKILL.md')):
        name, description, body = parse_skill(path.read_text())
        name = name or path.parent.name
        catalog.append((name, description))
        bodies[name] = body
    return catalog, bodies


class Harness:
    def __init__(self, adapter, skills_dir=None, runs_dir=None, run_id='run', max_calls=None, atc_keep=5):
        self.adapter = adapter
        self.skills_dir = Path(skills_dir) if skills_dir else ROOT / 'skills'
        self.runs_dir = Path(runs_dir) if runs_dir else ROOT / 'runs'
        self.run_id = run_id
        self.max_calls = max_calls or int(os.environ.get('FLIGHTOPS_MAX_CALLS', '12'))
        self.atc_keep = atc_keep
        self.world = World()
        self.catalog, self.skill_bodies = load_catalog(self.skills_dir)
        self.loaded_skill = ''
        self.loaded_body = ''
        self.atc_log = []
        self.turns = []
        self.transcript = []
        self._log_path = None

    def tool_schemas(self):
        return TOOL_SCHEMAS

    def snapshot(self):
        return {
            'callsign': self.world.callsign,
            'mission': self.world.mission,
            'phase': self.world.phase,
            'position': self.world.position,
            'engine': self.world.engine,
            'clearances': list(self.world.clearances),
            'pending_atc': self.world.pending_atc,
            'intent': self.world.intent,
            'loaded_skill': self.loaded_skill,
        }

    def snapshot_text(self):
        snap = self.snapshot()
        lines = ['SNAPSHOT']
        for key, value in snap.items():
            lines.append(f'{key}: {value}')
        return '\n'.join(lines)

    def memory_text(self):
        return 'MEMORY\nmission: {0}\nclearances: {1}'.format(
            self.world.mission, self.world.clearances
        )

    def history_text(self):
        lines = ['HISTORY']
        for turn in self.turns:
            lines.append(
                f"{turn['id']}: {turn['event']} → {turn['outcomes']}"
            )
        recent = self.atc_log[-self.atc_keep:]
        if recent:
            lines.append('ATC_VERBATIM')
            lines.extend(recent)
        return '\n'.join(lines) if len(lines) > 1 else 'HISTORY\n(none)'

    def catalog_text(self):
        if not self.catalog:
            return 'SKILLS\n(none)'
        lines = ['SKILLS']
        for name, description in self.catalog:
            lines.append(f'- {name}: {description}')
        return '\n'.join(lines)

    def assemble(self, event):
        messages = [
            {'role': 'system', 'content': KERNEL + '\n\n' + self.catalog_text()},
            {'role': 'system', 'content': self.snapshot_text()},
            {'role': 'system', 'content': self.memory_text()},
            {'role': 'system', 'content': self.history_text()},
        ]
        if self.loaded_body:
            messages.append({
                'role': 'system',
                'content': f'SKILL_BODY {self.loaded_skill}\n{self.loaded_body}',
            })
        messages.append({'role': 'user', 'content': f'{event.kind}: {event.text}'})
        return messages

    def execute(self, name, args):
        args = dict(args or {})
        if name == 'load_skill':
            return self._load_skill(args.get('name', ''))
        if name == 'xmit':
            return self._xmit(args.get('text', ''))
        if name == 'set_intent':
            return self.world.set_intent(
                args.get('name', ''),
                route=args.get('route', ''),
                hold_short=args.get('hold_short', ''),
            )
        return f'blocked: unknown tool {name}'

    def _load_skill(self, name):
        name = (name or '').strip()
        if name not in self.skill_bodies:
            self.loaded_skill = ''
            self.loaded_body = ''
            return f'blocked: unknown skill {name}'
        self.loaded_skill = name
        self.loaded_body = self.skill_bodies[name]
        return f'loaded {name}'

    def _xmit(self, text):
        text = (text or '').strip()
        self.atc_log.append(f'OUT: {text}')
        self.world.pending_atc = ''
        return f'sent: {text}'

    def _apply_event(self, event):
        if event.kind == 'operator':
            self.transcript.append(('OPERATOR', event.text))
        elif event.kind == 'atc':
            self.world.pending_atc = event.text
            self.atc_log.append(f'IN: {event.text}')
            self.transcript.append(('ATC', event.text))
            if event.clearance:
                self.world.clearances.append(event.clearance)
        elif event.kind == 'phase_change':
            self.world.phase = event.text

    def wake(self, event):
        self._apply_event(event)
        self._log({'type': 'event', 'kind': event.kind, 'text': event.text})
        messages = self.assemble(event)
        outcomes = []
        tokens = 0
        calls = 0
        final_text = ''
        while calls < self.max_calls:
            turn = self.adapter.complete(messages, self.tool_schemas())
            calls += 1
            tokens += turn.tokens
            if turn.tool_calls:
                messages.append(_assistant_tools(turn))
                for call in turn.tool_calls:
                    result = self.execute(call.name, call.args)
                    outcomes.append({'name': call.name, 'args': call.args, 'result': result})
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': call.id,
                        'content': result,
                    })
                    self.transcript.append(('TOOL', f'{call.name}({call.args})'))
                    self.transcript.append(('RESULT', result))
                    self._log({'type': 'tool', 'name': call.name, 'args': call.args, 'result': result})
                continue
            final_text = turn.text
            if final_text:
                self.transcript.append(('AI', final_text))
            break
        else:
            final_text = 'stopped: max calls'
        record = {
            'id': len(self.turns) + 1,
            'event': f'{event.kind}: {event.text}',
            'snapshot': self.snapshot(),
            'loaded_skill': self.loaded_skill,
            'outcomes': [f"{item['name']}:{item['result']}" for item in outcomes],
        }
        self.turns.append(record)
        self._log({'type': 'turn', **record})
        return WakeResult(text=final_text, outcomes=outcomes, tokens=tokens, calls=calls)

    def _log(self, row):
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        if self._log_path is None:
            self._log_path = self.runs_dir / f'{self.run_id}.jsonl'
        with self._log_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(row, default=str) + '\n')


def _assistant_tools(turn):
    message = {'role': 'assistant', 'content': turn.text or None, 'tool_calls': []}
    for call in turn.tool_calls:
        message['tool_calls'].append({
            'id': call.id,
            'type': 'function',
            'function': {
                'name': call.name,
                'arguments': json.dumps(call.args),
            },
        })
    return message
