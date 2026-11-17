"""Replay the 0.3b.1c selections through unchanged Ask; no retrieval or database writes."""

import argparse
import hashlib
import json
import platform
import re
import sqlite3
import statistics
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from petrus_engine.llm.native import LMStudioNativeLLMProvider  # noqa: E402
from petrus_engine.rag.ask import AskPetrusService  # noqa: E402
from petrus_engine.rag.contracts import RetrievalHit  # noqa: E402
from petrus_engine.rag.index import current_units  # noqa: E402

DATA = ROOT / '.local-data/arbovirus-retrieval-validation-0.3b'
BASE = DATA / 'robustness-validation-0.3b1c'
OUT = DATA / 'model-comparison-0.3b1d2'
MODEL = 'qwen3.5-4b-mlx'
PRODUCT = [
    'engine/petrus_engine/rag/ask.py', 'engine/petrus_engine/rag/validation.py',
    'engine/petrus_engine/llm/local.py', 'engine/petrus_engine/llm/native.py',
    'engine/petrus_engine/rag/retrieval.py', 'engine/petrus_engine/rag/query.py',
]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class ReadOnlyDatabase:
    @contextmanager
    def connect(self):
        connection = sqlite3.connect((DATA / 'petrus.sqlite3').as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def state(db):
    with db.connect() as connection:
        settings = {r['key']: json.loads(r['value']) for r in connection.execute('SELECT * FROM settings')}
        dump_hash = hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest()
        libraries = [r[0] for r in connection.execute('SELECT root_path FROM libraries')]
    return {'settings': settings, 'database_logical_sha256': dump_hash, 'libraries': libraries,
            'product_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PRODUCT}}


def prepare():
    db = ReadOnlyDatabase()
    initial = state(db)
    assert initial['settings']['llm_model'] == 'qwen/qwen3.5-9b'
    assert initial['settings']['embedding_model'] == 'text-embedding-nomic-embed-text-v1.5'
    assert initial['libraries'] == [
        '/Users/alexranieri/Library/CloudStorage/OneDrive-Pessoal/Butantan/V-GEN Lab/Arbovirus_evolution'
    ]
    baseline = json.loads((BASE / 'queries.json').read_text())
    units = current_units(db)
    manifests, contexts = [], {}
    for row in baseline:
        context, identities = [], []
        for saved in row['evidence']:
            unit = units[saved['unit_id']]
            evidence = {
                'evidence_id': saved['evidence_id'], 'unit_id': unit.unit_id,
                'paper_id': unit.paper_id, 'paper_title': unit.title,
                'section': unit.heading or unit.section_type,
                'page_start': unit.page_start, 'page_end': unit.page_end, 'text': unit.text,
                'provenance': unit.provenance_level, 'evidence_role': unit.evidence_role,
                'supports_paginated_evidence': unit.supports_paginated_evidence,
            }
            assert {k: v for k, v in evidence.items() if k != 'text'} == saved, row['id']
            context.append(evidence)
            identities.append(asdict(unit) | {'text': None, 'text_sha256': hashlib.sha256(unit.text.encode()).hexdigest()})
        expected = {c['context_sha256'] for c in row['calls']}
        assert expected == {digest(context)}, row['id']
        assert [v['unit_id'] for v in context] == row['calls'][0]['unit_ids']
        manifests.append({'id': row['id'], 'context_sha256': digest(context),
                          'baseline_context_sha256': sorted(expected), 'matches': True,
                          'evidence': row['evidence'], 'units': identities})
        contexts[row['id']] = context
    return db, initial, baseline, units, contexts, manifests


def provider():
    return LMStudioNativeLLMProvider(MODEL, temperature=0.1, reasoning='off', context_length=8192)


def run_query(db, row, units, context):
    llm = provider()
    calls = []

    def wrap(kind, method):
        def observed(*args, **kwargs):
            assert digest(args[1]) == digest(context), 'frozen context mismatch'
            call = {'kind': kind, 'context_sha256': digest(args[1])}
            calls.append(call)
            started = time.perf_counter()
            try:
                raw = method(*args, **kwargs)
                if not candidate_policy_valid(llm.last_metadata):
                    raise ValueError('llm_capability_changed')
                if not re.search(r'<(?:think|analysis)>', raw, re.I):
                    call['raw_final_content'] = raw
                else:
                    call['thinking_in_message'] = True
                return raw
            finally:
                call['seconds'] = time.perf_counter() - started
                call['provider_metadata'] = llm.last_metadata.copy()
        return observed

    llm.answer = wrap('original', llm.answer)
    llm.repair = wrap('repair', llm.repair)
    hits = [RetrievalHit(units[v['unit_id']], 0.0) for v in context]
    service = AskPetrusService(db, llm=llm, expand=False)
    # Replay only: bypass retrieval AND selection, preserving saved order verbatim.
    # The real Ask performs serialization, generation, strict validation and bounded repair.
    with patch.object(service.retriever, 'hybrid_search', return_value=hits) as replay:
        with patch('petrus_engine.rag.ask.select_evidence', side_effect=lambda value: value):
            response = service.ask(row['question'])
    assert replay.call_count == 1
    assert digest(response['evidence']) == digest(context)
    ex = response['execution_metadata']
    assert len(calls) == ex['generation_attempts'] <= 2
    return {'id': row['id'], 'question': row['question'], 'model': MODEL, 'calls': calls,
            'execution_metadata': ex, 'answer': response['answer'], 'limitations': response['limitations'],
            'insufficient_evidence': response['insufficient_evidence'], 'citations': response['citations'],
            'evidence': row['evidence'], 'retrieval_executions': 0,
            'first_valid': ex['attempts'][0].get('validation_errors') == [] and not ex.get('generation_error'),
            'repair_valid': ex['repair_attempted'] and ex['final_status'] == 'accepted',
            'final_accepted': ex['final_status'] == 'accepted',
            'final_abstention': ex['final_status'] == 'accepted' and response['insufficient_evidence'],
            'generation_seconds': ex['first_generation_seconds'] + ex['repair_generation_seconds'],
            'accepted_citation_occurrences': len(re.findall(r'\[E\d+\]', response['answer']))
                if ex['final_status'] == 'accepted' else 0,
            'uncited_accepted_paragraphs': [i for i, paragraph in enumerate(
                re.split(r'\n\s*\n', response['answer'].strip()), 1)
                if paragraph.strip() and not re.search(r'\[E\d+\]', paragraph)]
                if ex['final_status'] == 'accepted' and not response['insufficient_evidence'] else [],
            'invalid_accepted_citations': [v for v in re.findall(r'\[(E[^\]]*)\]', response['answer'])
                if v not in {e['evidence_id'] for e in context}]
                if ex['final_status'] == 'accepted' else []}



def candidate_policy_valid(metadata):
    return (metadata.get('reasoning_capability_present') is False
            and metadata.get('reasoning_parameter_sent') is False)


def median(values):
    values = list(values)
    return statistics.median(values) if values else None


def summarize(rows):
    attempts = [a for r in rows for a in r['execution_metadata']['attempts']]
    stats = [a['provider_metadata'].get('stats', {}) for a in attempts]
    first_errors = [r['execution_metadata']['first_validation_errors'] for r in rows]
    categories = ('invalid_json', 'invalid_citation_syntax', 'missing_citation', 'paragraph_without_citation',
                  'unknown_evidence_id', 'security_violation')
    return {
        'questions': len(rows), 'first_pass_accepted': sum(r['first_valid'] for r in rows),
        'final_accepted': sum(r['final_accepted'] for r in rows),
        'repair_attempts': sum(r['execution_metadata']['repair_attempted'] for r in rows),
        'repair_successes': sum(r['repair_valid'] for r in rows),
        'valid_abstentions': [r['id'] for r in rows if r['final_abstention']],
        'failures': [r['id'] for r in rows if not r['final_accepted']],
        'median_first_generation_seconds': median(r['execution_metadata']['first_generation_seconds'] for r in rows),
        'median_final_generation_seconds': median(r['execution_metadata']['first_generation_seconds'] +
                                                  r['execution_metadata']['repair_generation_seconds'] for r in rows),
        'median_ttft_seconds': median(s['time_to_first_token_seconds'] for s in stats if 'time_to_first_token_seconds' in s),
        'median_tokens_per_second': median(s['tokens_per_second'] for s in stats if 'tokens_per_second' in s),
        'reasoning_output_tokens': sum(s.get('reasoning_output_tokens', 0) for s in stats),
        'first_error_query_counts': {c: sum(any(e['category'] == c for e in errors) for errors in first_errors) for c in categories},
        'all_attempt_error_counts': {c: sum(any(e['category'] == c for e in a.get('validation_errors', [])) for a in attempts) for c in categories},
        'generation_requests': len(attempts),
        'accepted_citation_occurrences': sum(r.get('accepted_citation_occurrences', 0) for r in rows),
        'invalid_accepted_citations': sum(len(r.get('invalid_accepted_citations', [])) for r in rows),
        'uncited_accepted_paragraphs': sum(len(r.get('uncited_accepted_paragraphs', [])) for r in rows),
        'median_reasoning_fraction': median(
            s['reasoning_output_tokens'] / s['total_output_tokens']
            for s in stats if 'reasoning_output_tokens' in s and s.get('total_output_tokens', 0) > 0),
        'total_output_tokens': sum(s.get('total_output_tokens', 0) for s in stats),
        'median_repair_generation_seconds': median(
            r['execution_metadata']['repair_generation_seconds'] for r in rows
            if r['execution_metadata']['repair_attempted']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'health', 'test-a', 'run', 'probe'))
    args = parser.parse_args()
    if args.mode == 'health' and (OUT / 'health.json').exists():
        raise SystemExit('Health already recorded; use a fresh stage directory for another round.')
    if args.mode == 'preflight' and (OUT / 'state-before.json').exists():
        raise SystemExit('Preflight already recorded; do not overwrite historical state.')
    db, initial, baseline, units, contexts, manifests = prepare()
    if args.mode in ('preflight', 'health'):
        write('frozen-manifest.json', manifests)
        write('state-before.json', initial)
        write('environment.json', {'platform': platform.platform(), 'python': sys.version,
                                   'model': MODEL, 'endpoint': 'http://127.0.0.1:1234/api/v1/chat'})
    else:
        assert initial == json.loads((OUT / 'state-before.json').read_text())
    if args.mode == 'preflight':
        print('9/9 frozen contexts match baseline. Read-only DB; selected model remains 9B.')
        return
    if args.mode == 'health':
        llm = provider()
        health = llm.status()
        if llm._model is not None:
            write('candidate-model.json', llm._model)
        write('health.json', health)
        print(json.dumps(health, ensure_ascii=False), flush=True)
        final = state(db)
        write('state-after.json', final)
        assert final == initial
        if (health['state'] != 'available' or not re.fullmatch(r'OK[.!]?', health.get('minimal_response', '').strip(), re.I)
                or health.get('http_status') != 200 or not candidate_policy_valid(health)):
            raise SystemExit('Health gate failed; no benchmark queries permitted.')
        return
    health = json.loads((OUT / 'health.json').read_text())
    assert health['state'] == 'available' and candidate_policy_valid(health)
    if args.mode == 'test-a':
        assert not (OUT / 'test-a.json').exists(), 'Do not repeat Test A silently'
        llm = provider()
        started = time.perf_counter()
        record = {'passed': False, 'repair_attempted': False}
        try:
            raw = llm.complete([{'role': 'user', 'content':
                'Return exactly this JSON object: {"answer":"native ok","insufficient_evidence":false,"limitations":[]}'}])
            assert candidate_policy_valid(llm.last_metadata)
            value = json.loads(raw)
            record.update(final_content=raw, json_valid=True)
            assert value == {'answer': 'native ok', 'insufficient_evidence': False, 'limitations': []}
            record['passed'] = True
        finally:
            record.update(metadata=llm.last_metadata, seconds=time.perf_counter() - started)
            write('test-a.json', record)
            final = state(db)
            write('state-after.json', final)
            assert final == initial
        print(json.dumps(record), flush=True)
        return
    assert json.loads((OUT / 'test-a.json').read_text())['passed']
    name = 'queries.json' if args.mode == 'run' else 'stability-probe.json'
    assert not (OUT / name).exists(), 'Do not silently repeat an existing round'
    rows = baseline if args.mode == 'run' else [r for _ in range(3) for r in baseline if r['id'] in ('Q5', 'Q6')]
    results = []
    try:
        for row in rows:
            result = run_query(db, row, units, contexts[row['id']])
            results.append(result)
            write(name, results)
            print(json.dumps({'id': result['id'], 'first_valid': result['first_valid'],
                              'final': result['execution_metadata']['final_status'],
                              'abstention': result['final_abstention'],
                              'attempts': len(result['calls']), 'seconds': round(result['generation_seconds'], 3)}), flush=True)
            if any(not candidate_policy_valid(c['provider_metadata']) for c in result['calls']):
                raise RuntimeError('Candidate capability/request changed: stop benchmark')
        write('summary.json' if args.mode == 'run' else 'probe-summary.json', summarize(results))
    finally:
        final = state(db)
        write('state-after.json', final)
        assert final == initial, 'Database/settings/product changed during benchmark'


if __name__ == '__main__':
    main()
