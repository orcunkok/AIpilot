"""Terminal viewer for the harness. Curses layout; Session is the submit path."""
import curses
import os
import textwrap

from adapter import OpenAIAdapter
from harness import Event, Harness

DEMO_ATC = 'Demo 12, taxi via Alpha, hold short runway 27.'


class Session:
    def __init__(self, harness):
        self.harness = harness
        self.messages = [('SYSTEM', 'Type a message · /atc TEXT · /demo injects taxi ATC · /clear · q quits.')]
        if not os.environ.get('OPENAI_API_KEY'):
            self.messages.append(('SYSTEM', 'OPENAI_API_KEY is empty. Wakes will fail until it is set.'))
        self._seen = 0

    def submit(self, text):
        text = (text or '').strip()
        if text in {'q', '/quit', '/exit'}:
            return False
        if text == '/clear':
            self.messages.clear()
            return True
        if text == '/help':
            self.messages.append(('SYSTEM', 'Type a message · /atc TEXT · /demo injects taxi ATC · /clear · q quits.'))
            return True
        if text == '/demo':
            return self._wake(Event('atc', DEMO_ATC, clearance=DEMO_ATC))
        if text == '/atc' or text.startswith('/atc '):
            message = text[4:].strip()
            if not message:
                self.messages.append(('SYSTEM', 'Usage: /atc TEXT'))
                return True
            return self._wake(Event('atc', message, clearance=message))
        if text.startswith('/'):
            self.messages.append(('SYSTEM', 'Unknown command. Type /help.'))
            return True
        return self._wake(Event('operator', text))

    def _wake(self, event):
        self.messages.append(('SYSTEM', 'waking…'))
        try:
            self.harness.wake(event)
        except Exception as error:
            self.messages.append(('SYSTEM', f'wake failed: {error}'))
            return True
        self.messages.extend(self.harness.transcript[self._seen:])
        self._seen = len(self.harness.transcript)
        return True


def make_session(harness=None):
    if harness is None:
        harness = Harness(OpenAIAdapter(), run_id='ui')
    return Session(harness)


def run(screen, session=None):
    session = session or make_session()
    world = session.harness.world
    colors = {}
    if curses.has_colors():
        curses.start_color()
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            background = curses.COLOR_BLACK
        for i, (kind, color) in enumerate([('AI', curses.COLOR_CYAN), ('ATC', curses.COLOR_MAGENTA), ('TOOL', curses.COLOR_BLUE), ('RESULT', curses.COLOR_GREEN), ('ACTION', curses.COLOR_YELLOW), ('SYSTEM', curses.COLOR_WHITE)], 1):
            curses.init_pair(i, color, background)
            colors[kind] = curses.color_pair(i)
    screen.keypad(True)
    text, cursor, scroll = '', 0, 0
    history, history_index, draft = [], 0, ''

    def put(y, x, value, attr=0, limit=None):
        h, w = screen.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        value = ''.join(c if c.isprintable() else ' ' for c in str(value))
        try:
            screen.addnstr(y, x, value, max(0, min(w-x-1, limit if limit is not None else w)), attr)
        except curses.error:
            pass

    while True:
        screen.erase()
        h, w = screen.getmaxyx()
        sidebar = 32 if w >= 82 else 0
        left = sidebar + 3 if sidebar else 2
        body_width = max(8, w-left-2)
        body_height = max(1, h-8)
        put(0, 2, 'FLIGHTOPS', curses.A_BOLD | colors.get('AI', 0))
        put(0, 15, 'harness', curses.A_DIM)
        if sidebar:
            for y in range(2, max(2,h-5)):
                put(y, sidebar, '│', curses.A_DIM)
            y = 2
            clearances = world.clearances or ['none']
            latest = session.harness.atc_log[-2:] or ['none']
            sections = [
                ('AIRCRAFT', [f'{world.callsign} · {world.mission}', world.phase, world.position, 'Engine    '+world.engine]),
                ('CLEARANCES', clearances),
                ('LATEST ATC', latest),
            ]
            for title, values in sections:
                if y >= h-5: break
                put(y, 2, title, curses.A_BOLD, sidebar-4)
                y += 1
                for value in values:
                    for part in textwrap.wrap(str(value), sidebar-5) or ['']:
                        if y >= h-5: break
                        put(y, 2, part, colors.get('ATC',0) if title=='LATEST ATC' else curses.A_DIM, sidebar-4)
                        y += 1
                y += 1
        put(2, left, 'CONVERSATION', curses.A_BOLD)
        rows = []
        for kind, message in session.messages:
            nested = kind in {'TOOL', 'RESULT', 'ACTION'}
            prefix = ('    ↳ ' if nested else '') + kind.lower() + '  '
            continuation = ' ' * len(prefix)
            parts = textwrap.wrap(message, max(8,body_width-len(prefix)), replace_whitespace=True) or ['']
            style = colors.get(kind, 0) | (curses.A_DIM if kind in {'ACTION','SYSTEM'} else 0)
            for i, part in enumerate(parts):
                rows.append(((prefix if i == 0 else continuation)+part, style))
            if not nested: rows.append(('',0))
        max_scroll = max(0,len(rows)-body_height)
        scroll = min(scroll, max_scroll)
        start = max(0,len(rows)-body_height-scroll)
        for i, (value, style) in enumerate(rows[start:start+body_height]):
            put(3+i, left, value, style, body_width)
        put(h-4, 2, '─' * max(0,w-4), curses.A_DIM)
        input_width = max(1,w-7)
        offset = max(0,cursor-input_width+1)
        put(h-3, 2, '› ', colors.get('AI',0) | curses.A_BOLD)
        put(h-3, 4, text[offset:offset+input_width])
        hint = '/demo  /atc TEXT  /help  q quit · PgUp/PgDn scroll'
        if not sidebar: hint = 'Widen to 82 columns for sidebar · /demo · q quit'
        if scroll: hint = f'Scrolled {scroll} lines · End returns to latest'
        put(h-1, 2, hint, curses.A_DIM)
        try:
            screen.move(max(0,h-3), min(w-1,4+cursor-offset))
            screen.refresh()
            key = screen.get_wch()
        except curses.error:
            continue
        if key in ('\n','\r',curses.KEY_ENTER):
            message = text.strip()
            if message:
                history.append(message)
                if not session.submit(message): break
            text, cursor, scroll, draft = '', 0, 0, ''
            history_index = len(history)
        elif key in ('\x03','\x04'):
            if not text: break
            text, cursor = '', 0
        elif key in (curses.KEY_BACKSPACE,'\x7f','\b'):
            if cursor: text, cursor = text[:cursor-1]+text[cursor:], cursor-1
        elif key == curses.KEY_DC: text = text[:cursor]+text[cursor+1:]
        elif key == curses.KEY_LEFT: cursor = max(0,cursor-1)
        elif key == curses.KEY_RIGHT: cursor = min(len(text),cursor+1)
        elif key == curses.KEY_HOME: cursor = 0
        elif key == curses.KEY_END: cursor, scroll = len(text), 0
        elif key == curses.KEY_PPAGE: scroll = min(max_scroll,scroll+body_height)
        elif key == curses.KEY_NPAGE: scroll = max(0,scroll-body_height)
        elif key in (curses.KEY_UP,curses.KEY_DOWN):
            if history_index == len(history): draft = text
            history_index = max(0,min(len(history),history_index+(-1 if key==curses.KEY_UP else 1)))
            text = history[history_index] if history_index < len(history) else draft
            cursor = len(text)
        elif isinstance(key,str) and key.isprintable():
            text = text[:cursor]+key+text[cursor:]
            cursor += len(key)
