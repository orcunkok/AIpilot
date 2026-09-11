"""Start with: python main.py — no manual virtualenv activation needed."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / '.venv'


def use_venv():
    python = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Setting up .venv (first run only)…', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(VENV)], check=True)
    if Path(sys.prefix).resolve() != VENV.resolve():
        os.environ['VIRTUAL_ENV'] = str(VENV)
        os.environ['PATH'] = str(python.parent) + os.pathsep + os.environ.get('PATH', '')
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])


def load_env():
    path = ROOT / '.env'
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def plain_terminal(session):
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

    color = sys.stdout.isatty() and not os.getenv('NO_COLOR')
    cyan, reset = ('\033[36m', '\033[0m') if color else ('', '')
    print(f'\n  {cyan}Flightops{reset}')
    print('  Type a message. /help for commands. q or /quit to exit.\n')
    shown = 0
    for kind, text in session.messages:
        print(f'  {kind.lower()}  {text}')
        shown += 1
    print()
    while True:
        try:
            message = input('  flightops > ').strip()
        except EOFError:
            print('\n  Goodbye.')
            break
        except KeyboardInterrupt:
            print('\n  q or /quit to exit.')
            continue
        if not message:
            continue
        if not session.submit(message):
            print('  Goodbye.')
            break
        if len(session.messages) < shown:
            shown = 0
        for kind, text in session.messages[shown:]:
            print(f'  {kind.lower()}  {text}')
        shown = len(session.messages)
        print()


def main():
    load_env()
    from terminal_ui import make_session, run
    session = make_session()
    if not os.environ.get('OPENAI_API_KEY'):
        print('OPENAI_API_KEY is empty. UI will open; wakes will fail until it is set.', flush=True)
    if sys.stdin.isatty() and sys.stdout.isatty() and os.getenv('TERM', '') not in {'', 'dumb'}:
        import curses
        curses.wrapper(lambda screen: run(screen, session))
    else:
        plain_terminal(session)


if __name__ == '__main__':
    use_venv()
    main()
