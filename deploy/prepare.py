#!/usr/bin/env python3
"""Prepare an operator-owned Linux installation; never runs sudo/systemctl/Caddy."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
try:
    from .configuration import read_config, PATH_PATTERN
except ImportError:
    from configuration import read_config, PATH_PATTERN


def prepare(prefix, config_path, user, *, prepare_only=False):
    if not re.fullmatch(PATH_PATTERN, str(prefix)) or '..' in prefix.parts:
        raise ValueError('PREFIX_MUST_BE_SAFE_ABSOLUTE_PATH_WITHOUT_SPACES')
    if not re.fullmatch('[a-z_][a-z0-9_-]{0,31}', user) or user == 'root':
        raise ValueError('NON_ROOT_SERVICE_USER_REQUIRED')
    try:
        import pwd
        if pwd.getpwnam(user).pw_uid == 0:
            raise ValueError('NON_ROOT_SERVICE_USER_REQUIRED')
    except KeyError:
        pass  # Administrator creates the dedicated account before service activation.
    config = read_config(config_path)
    if prefix.is_symlink():
        raise ValueError('PREFIX_MUST_NOT_BE_SYMLINK')
    if prefix.exists() and any(prefix.iterdir()):
        raise ValueError('PREFIX_MUST_BE_EMPTY_TO_PRESERVE_EXISTING_INSTALLATION')
    source = Path(__file__).resolve().parent.parent
    for directory in ('source','config','units','data','cache','models'):
        (prefix / directory).mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copytree(source / 'engine', prefix / 'source' / 'engine', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(source / 'requirements-service.txt', prefix / 'source' / 'requirements-service.txt')
    (prefix / 'source' / 'deploy').mkdir()
    for name in ('requirements-base.txt','configuration.py','smoke.py'):
        shutil.copy2(source / 'deploy' / name, prefix / 'source' / 'deploy' / name)
    # The runtime, not the caller's environment, selects this private directory.
    config['MHVIE_DATA'] = str(prefix / 'data')
    environment = prefix / 'config' / 'backend.env'
    environment.write_text(''.join(key + '=' + value + '\n' for key, value in sorted(config.items())))
    environment.chmod(0o600)
    replacements = {'@PREFIX@': str(prefix), '@USER@': user, '@DOMAIN@': config['MHVIE_DOMAIN']}
    for name in ('mhvie-api.service','mhvie-worker.service','Caddyfile'):
        text = (source / 'deploy' / 'templates' / (name + '.in')).read_text()
        for key, value in replacements.items():
            text = text.replace(key, value)
        destination = prefix / ('config' if name == 'Caddyfile' else 'units') / name
        destination.write_text(text)
    revision = subprocess.run(['git','rev-parse','HEAD'], cwd=source, text=True, capture_output=True, check=False).stdout.strip() or 'UNAVAILABLE'
    manifest = {'status': 'PREPARED_NOT_INSTALLED' if prepare_only else 'DEPENDENCIES_PENDING', 'source_commit': revision, 'service_user': user, 'models_downloaded': False, 'deployed': False, 'model_profile_verified': False}
    manifest_path = prefix / 'preparation.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if not prepare_only:
        subprocess.run([sys.executable,'-m','venv',str(prefix / 'venv')], check=True)
        subprocess.run([str(prefix / 'venv' / 'bin' / 'python'),'-m','pip','install','-r',str(prefix / 'source' / 'deploy' / 'requirements-base.txt')], check=True)
        subprocess.run([str(prefix / 'venv' / 'bin' / 'python'),'-m','pip','check'], check=True)
        subprocess.run([str(prefix / 'venv' / 'bin' / 'python'),'-c','from engine.service_api import create_app; from engine.job_handler import JobHandler; import zxingcpp; print("BACKEND_IMPORTS_OK")'],cwd=prefix / 'source',check=True)
        manifest['status'] = 'PREPARED_NOT_DEPLOYED'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, type=Path)
    parser.add_argument('--env', required=True, type=Path)
    parser.add_argument('--user', default='mhvie')
    parser.add_argument('--check-only', action='store_true', help='Validate configuration only; no writes or downloads')
    parser.add_argument('--prepare-only', action='store_true', help='Render/copy files without venv installation; services remain unready')
    args = parser.parse_args()
    try:
        if args.check_only:
            read_config(args.env)
            if not args.prefix.is_absolute() or not re.fullmatch(PATH_PATTERN, str(args.prefix)) or '..' in args.prefix.parts:
                raise ValueError('INVALID_PREFIX')
            if not re.fullmatch('[a-z_][a-z0-9_-]{0,31}', args.user) or args.user == 'root':
                raise ValueError('NON_ROOT_SERVICE_USER_REQUIRED')
            print('CONFIG_VALIDATED_NOT_DEPLOYED')
        else:
            result = prepare(args.prefix, args.env, args.user, prepare_only=args.prepare_only)
            print(result['status'])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Never print configuration values or environment contents.
        code = str(error) if isinstance(error, ValueError) else type(error).__name__
        print('PREPARATION_FAILED: ' + code, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
