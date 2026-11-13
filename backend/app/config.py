import os
import secrets
from pathlib import Path

ROOT = Path(os.environ.get('IDCS_DATA_DIR', str(Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'IDCardStudio'))).resolve()
FOLDERS = ('database', 'projects', 'originals', 'approved', 'templates', 'generated', 'tmp', 'logs', 'backups', 'inbox')

def initialize():
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    for folder in FOLDERS:
        (ROOT / folder).mkdir(exist_ok=True, mode=0o700)
    for name in ('owner-token', 'agent-token'):
        path = ROOT / name
        if not path.exists():
            with path.open('x') as f:
                f.write(secrets.token_urlsafe(48))
            path.chmod(0o600)

def token(name='owner'):
    return (ROOT / f'{name}-token').read_text().strip()

def asset(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError('Invalid asset path')
    return path
