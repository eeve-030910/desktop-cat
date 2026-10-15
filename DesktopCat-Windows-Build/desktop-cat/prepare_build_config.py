"""Export only allowlisted PUBLIC settings; never bundle .env."""
import json
import os
import sys
from pathlib import Path


def export_config(destination):
    root = Path(__file__).resolve().parent
    values = {}
    dotenv = root / '.env'
    if dotenv.exists():
        for line in dotenv.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, separator, value = line.partition('=')
            if not separator:
                raise ValueError('Invalid .env line (expected KEY=value)')
            values[key.strip()] = value.strip().strip('\"\'')
    values.update(os.environ)
    original = json.loads((root / 'update_config.json').read_text(encoding='utf-8'))
    # Explicit allowlist: never copy arbitrary environment variables or JSON keys.
    config = {key: original.get(key, default) for key, default in
              [('policy_url', ''), ('allowed_hosts', []), ('donate_url', '')]}
    for env_key, key in [('DESKTOPCAT_POLICY_URL', 'policy_url'),
                         ('DESKTOPCAT_DONATE_URL', 'donate_url')]:
        if env_key in values:
            config[key] = values[env_key]
    if 'DESKTOPCAT_ALLOWED_HOSTS' in values:
        config['allowed_hosts'] = [h.strip() for h in
                                   values['DESKTOPCAT_ALLOWED_HOSTS'].split(',') if h.strip()]
    Path(destination).write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    export_config(sys.argv[1])
