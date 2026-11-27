"""Strict, non-executable operator configuration; error messages never include values."""
from pathlib import Path
import re
from urllib.parse import urlsplit

MODEL_PATHS = ('MHVIE_VISION_MODEL','MHVIE_FLUX_MODEL','MHVIE_QWEN_EDIT_MODEL','MHVIE_EDIT_MODEL','MHVIE_CLIP_WEIGHTS','MHVIE_AESTHETIC_WEIGHTS')
PATH_PATTERN = r'/[A-Za-z0-9_./-]+'


def read_config(path, *, check_models=True):
    config = {}
    for index, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f'INVALID_CONFIG_LINE_{index}')
        key, value = line.split('=', 1)
        if not re.fullmatch(r'MHVIE_[A-Z0-9_]+', key) or key in config or not value or re.search(r'[\s"\x27`$;\\]', value):
            raise ValueError(f'INVALID_CONFIG_LINE_{index}')
        if value.startswith('REPLACE_'):
            raise ValueError(f'CONFIG_PLACEHOLDER_{key}')
        config[key] = value
    for key in ('MHVIE_DOMAIN','MHVIE_TOKEN','MHVIE_SEARX','MHVIE_HOSTS'):
        if not config.get(key):
            raise ValueError(f'MISSING_{key}')
    if not valid_domain(config['MHVIE_DOMAIN']):
        raise ValueError('INVALID_MHVIE_DOMAIN')
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,256}', config['MHVIE_TOKEN']):
        raise ValueError('INVALID_MHVIE_TOKEN')
    if len(set(config['MHVIE_TOKEN'])) < 12:
        raise ValueError('WEAK_MHVIE_TOKEN')
    try:
        endpoint = urlsplit(config['MHVIE_SEARX'])
        if endpoint.scheme not in ('https','http') or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise ValueError()
        if endpoint.scheme == 'http' and endpoint.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError()
        endpoint.port
    except ValueError:
        raise ValueError('INVALID_MHVIE_SEARX') from None
    hosts = config['MHVIE_HOSTS'].split(',')
    if len(hosts) > 100 or any(not valid_domain(host) for host in hosts):
        raise ValueError('INVALID_MHVIE_HOSTS')
    for key in ('MHVIE_OCR','MHVIE_SEGMENTATION','MHVIE_IDENTITY_EXTERNAL_SEARCH'):
        if config.get(key, '0') not in ('0','1'):
            raise ValueError(f'INVALID_{key}')
    for key in MODEL_PATHS:
        if key in config:
            if not re.fullmatch(PATH_PATTERN, config[key]) or not Path(config[key]).is_absolute():
                raise ValueError(f'INVALID_PATH_{key}')
            if check_models and not Path(config[key]).exists():
                raise ValueError(f'MODEL_NOT_FOUND_{key}')
            if check_models and key in ('MHVIE_VISION_MODEL','MHVIE_FLUX_MODEL','MHVIE_QWEN_EDIT_MODEL','MHVIE_EDIT_MODEL') and not Path(config[key]).is_dir():
                raise ValueError(f'MODEL_DIRECTORY_REQUIRED_{key}')
            if check_models and key in ('MHVIE_CLIP_WEIGHTS','MHVIE_AESTHETIC_WEIGHTS') and not Path(config[key]).is_file():
                raise ValueError(f'MODEL_FILE_REQUIRED_{key}')
    if 'MHVIE_EDIT_MODEL' in config and config.get('MHVIE_EDIT_BACKEND') not in ('flux','qwen'):
        raise ValueError('MHVIE_EDIT_BACKEND_REQUIRED')
    if 'MHVIE_EDIT_BACKEND' in config and config['MHVIE_EDIT_BACKEND'] not in ('flux','qwen'):
        raise ValueError('INVALID_MHVIE_EDIT_BACKEND')
    if bool(config.get('MHVIE_AESTHETIC_WEIGHTS')) != bool(config.get('MHVIE_AESTHETIC_SHA256')):
        raise ValueError('AESTHETIC_HASH_AND_WEIGHTS_REQUIRED')
    if 'MHVIE_AESTHETIC_SHA256' in config and not re.fullmatch('[a-f0-9]{64}', config['MHVIE_AESTHETIC_SHA256']):
        raise ValueError('INVALID_MHVIE_AESTHETIC_SHA256')
    if 'MHVIE_AESTHETIC_WEIGHTS' in config and 'MHVIE_CLIP_WEIGHTS' not in config:
        raise ValueError('MHVIE_CLIP_WEIGHTS_REQUIRED')
    return config


def valid_domain(value):
    return bool(len(value) <= 253 and re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?', value) and not value.endswith(('.invalid','.test','.localhost')))
