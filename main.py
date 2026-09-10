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


def plain_terminal():
    # Standard-library readline provides input editing and session history on Linux/macOS.
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

    color = sys.stdout.isatty() and not os.getenv('NO_COLOR')
    cyan, reset = ('\033[36m', '\033[0m') if color else ('', '')
    print(f'\n  {cyan}Flightops{reset}')
    print('  Type a message. /help for commands. q or /quit to exit.\n')
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
        if message in {'q', '/quit', '/exit'}:
            print('  Goodbye.')
            break
        if message == '/help':
            print('  /help  Show commands\n  /clear Clear screen\n  q /quit  Exit\n')
        elif message == '/clear':
            if sys.stdout.isatty():
                print('\033[2J\033[H', end='', flush=True)
        elif message.startswith('/'):
            print('  Unknown command. Type /help.\n')
        else:
            print(f'  Received: {message}\n')


def main():
    if sys.stdin.isatty() and sys.stdout.isatty() and os.getenv('TERM', '') not in {'', 'dumb'}:
        import curses
        from terminal_ui import run
        curses.wrapper(run)
    else:
        plain_terminal()


if __name__ == '__main__':
    use_venv()
    main()
