"""Smoke the actual macOS bundle sidecar on a separate validation DB, without scanning or LLM calls."""

import hashlib
import json
import os
import selectors
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/release-checkpoint-0.3c'
BUNDLE = ROOT / 'src-tauri/target/debug/bundle/macos/PETRUS.app'
DATA = OUT / 'package-smoke'


def main():
    binary = BUNDLE / 'Contents/MacOS/petrus-engine'
    assert binary.is_file()
    DATA.mkdir(parents=True, exist_ok=True)
    destination = DATA / 'petrus.sqlite3'
    assert not destination.exists(), 'Do not overwrite a prior package smoke database'
    source = OUT / 'before-dev.sqlite3'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as db:
        with sqlite3.connect(destination) as target:
            db.backup(target)
    process = subprocess.Popen(
        [str(binary), '--data-dir', str(DATA)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env={**os.environ, 'PATH': '/usr/bin:/bin'},
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    sequence = 0

    def rpc(method, params=None, expected_error=False):
        nonlocal sequence
        sequence += 1
        process.stdin.write(json.dumps({'id': sequence, 'method': method, 'params': params or {}}) + '\n')
        process.stdin.flush()
        if not selector.select(timeout=30):
            raise RuntimeError('Packaged sidecar RPC timed out')
        line = process.stdout.readline()
        if not line:
            raise RuntimeError('Packaged sidecar stopped')
        response = json.loads(line)
        assert response['id'] == sequence
        if expected_error:
            assert 'error' in response
            return response['error']
        assert 'error' not in response, response.get('error')
        return response['result']

    try:
        initial = rpc('snapshot')
        assert initial['stats']['papers'] == 10
        settings = initial['settings']
        assert (settings['llm_provider'], settings['llm_model'], settings['llm_temperature'],
                settings['llm_max_output_tokens'], settings['llm_timeout_seconds']) == (
                    'lmstudio', 'qwen/qwen3.5-9b', 0.1, 1600, 90)
        assert not settings['auto_scan'] and not settings['watch_folders']
        assert rpc('papers')['total'] == 10
        # Imports the packaged native provider, Ask and numpy; rejects before retrieval or generation.
        assert rpc('ask', {'question': ''}, expected_error=True) == 'ask_invalid_question'
        for key, invalids in [('llm_max_output_tokens', [True, '1600', 127, 8193]),
                              ('llm_timeout_seconds', [True, '90', 4, 601])]:
            for value in invalids:
                rpc('save_settings', {key: value}, expected_error=True)
        saved = rpc('save_settings', {'llm_max_output_tokens': 1600, 'llm_timeout_seconds': 90})
        assert saved['llm_model'] == 'qwen/qwen3.5-9b'
        final = rpc('snapshot')
        assert final['settings']['llm_max_output_tokens'] == 1600
        assert final['settings']['llm_timeout_seconds'] == 90
        assert initial['stats'] == final['stats'] and initial['jobs'] == final['jobs']
        assets = ROOT / 'app/dist/assets'
        javascript = '\n'.join(p.read_text() for p in assets.glob('*.js'))
        assert all(marker in javascript for marker in ['ask-form', 'ai.outputTokens', 'ai.provider', 'Library'])
        report = {
            'bundle': str(BUNDLE), 'sidecar': str(binary), 'data_dir': str(DATA),
            'sidecar_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
            'sidecar_started': True, 'snapshot_settings': True, 'library_papers': 10,
            'native_provider_ask_imports': True, 'settings_validation': True,
            'settings_round_trip': True, 'jobs_unchanged': True,
            'frontend_ask_settings_library_in_build': True,
            'packaged_gui_clicks_observed': False, 'llm_generations': 0, 'scans': 0,
        }
        (OUT / 'package-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        selector.close()
    assert process.returncode == 0
    print('Packaged sidecar, settings, library and Ask imports: OK; native GUI still requires manual verification.')


if __name__ == '__main__':
    main()
