#!/usr/bin/env python3
"""Upload a local video using a prepare_video_upload response on stdin.

Usage: python3 upload_video.py VIDEO_FILE
Send one JSON line containing the exact prepare_video_upload result to stdin.
The presigned URL stays in memory and is sent to curl through stdin, not argv.
On a terminal, input echo is disabled. No bearer token is required or accepted.
After a successful PUT, call complete_video_upload through the same MCP session.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse


def quoted(value):
    if not isinstance(value, str) or any(c in value for c in ('\n', '\r', '\x00')):
        raise ValueError('invalid transfer header or URL')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def transfer(path, contract):
    path = Path(path).resolve(strict=True)
    upload = contract['upload']
    if upload.get('method') != 'PUT' or urlparse(upload['url']).scheme != 'https':
        raise ValueError('expected an HTTPS presigned PUT contract')
    if path.stat().st_size != contract['size_bytes']:
        raise ValueError('local byte count does not match the prepared upload')
    headers = upload.get('headers', {})
    if any(k.lower() == 'authorization' for k in headers):
        raise ValueError('presigned PUT must not include an Authorization header')
    config = 'url = ' + quoted(upload['url']) + '\n'
    for key, value in headers.items():
        config += 'header = ' + quoted(key + ': ' + value) + '\n'
    result = subprocess.run(['curl', '--silent', '--show-error', '--fail', '--max-time', '600',
                             '--request', 'PUT', '--upload-file', str(path), '--config', '-',
                             '--output', os.devnull, '--write-out', '%{http_code}'],
                            input=config, text=True, capture_output=True)
    if result.returncode:
        # Do not echo curl stderr; it can contain URLs from a server/proxy error.
        raise RuntimeError('presigned upload failed (curl exit %s, HTTP %s); read destination state before retrying' %
                           (result.returncode, result.stdout[-3:]))
    try:
        if not isinstance(result.stdout, str) or len(result.stdout) != 3 or not result.stdout.isascii() or not result.stdout.isdigit():
            raise ValueError('expected three-digit status')
        status = int(result.stdout)
    except (TypeError, ValueError):
        raise RuntimeError('presigned upload returned an invalid HTTP status; read destination state before retrying')
    if not 200 <= status < 300:
        raise RuntimeError('presigned upload failed (HTTP %s); read destination state before retrying' % result.stdout[-3:])
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'uploaded': True, 'http_status': status, 'size_bytes': path.stat().st_size,
            'sha256': digest.hexdigest(), 'next_step': 'complete_video_upload through the same MCP session'}


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    prior = None
    if sys.stdin.isatty():
        import termios
        prior = termios.tcgetattr(sys.stdin)
        mode = termios.tcgetattr(sys.stdin)
        mode[3] &= ~(termios.ECHO | termios.ICANON)
        mode[6][termios.VMIN] = 1
        mode[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin, termios.TCSANOW, mode)
    try:
        for filename in sys.argv[1:]:
            print('Ready for upload contract on stdin (input is not echoed): ' + str(Path(filename).name), flush=True)
            contract = json.loads(sys.stdin.readline())
            print(json.dumps(transfer(filename, contract)), flush=True)
    except Exception as exc:
        # Errors are deliberately classified without printing contracts or URLs.
        print(json.dumps({'uploaded': False, 'error_type': type(exc).__name__,
                          'message': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else 'Transfer failed; inspect local input and destination state.'}))
        raise SystemExit(1)
    finally:
        if prior is not None:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, prior)


if __name__ == '__main__':
    main()
