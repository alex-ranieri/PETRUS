"""Separate, bounded Q1 budget diagnostic inspired by read-only PRAXIS inspection."""

import json

import compare_local_models as comparison
from petrus_engine.llm.native import LMStudioNativeLLMProvider


def main():
    comparison.OUT = comparison.DATA / 'praxis-budget-probe-0.3b1d2'
    assert not (comparison.OUT / 'trials.json').exists(), 'Do not overwrite an existing probe'
    db, initial, baseline, units, contexts, manifest = comparison.prepare()
    comparison.write('state-before.json', initial)
    comparison.write('frozen-manifest.json', manifest)
    question = next(r for r in baseline if r['id'] == 'Q1')
    results = []
    try:
        for budget in (2400, 4096):
            def explicit_provider():
                return LMStudioNativeLLMProvider(
                    comparison.MODEL, temperature=0.1, reasoning='off', context_length=8192,
                    max_output_tokens=budget, timeout=180,
                )

            comparison.provider = explicit_provider
            record = comparison.run_query(db, question, units, contexts['Q1'])
            record.update(max_output_tokens=budget, timeout_seconds=180, primary_benchmark=False)
            results.append(record)
            comparison.write('trials.json', results)
            print(json.dumps({'budget': budget, 'first_valid': record['first_valid'],
                              'final': record['execution_metadata']['final_status'],
                              'attempts': len(record['calls']), 'seconds': record['generation_seconds'],
                              'errors': record['execution_metadata']['final_validation_errors']}), flush=True)
            if record['final_accepted']:
                break
    finally:
        final = comparison.state(db)
        comparison.write('state-after.json', final)
        assert final == initial


if __name__ == '__main__':
    main()
