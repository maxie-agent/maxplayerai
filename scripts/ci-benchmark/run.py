#!/usr/bin/env python3
"""Throwaway controlled CI compilation experiment; no production profile edits."""
import json
import os
from pathlib import Path
import subprocess
import time

variant = os.environ['VARIANT']
suite = os.environ['SUITE']
out = Path('benchmark-results')
out.mkdir(exist_ok=True)
results = {'variant': variant, 'suite': suite, 'sha': os.environ.get('GITHUB_SHA'), 'phases': []}
config = []
if variant != 'baseline':
    config += ['--config', 'profile.release.lto="off"']
if variant == 'no-lto-core-opt1':
    config += ['--config', 'profile.release.package.maxplayer-core.opt-level=1']
features = (['--features', 'acp,gateway,git-delivery,wallet'] if suite == 'union'
            else ['--no-default-features', '--features', 'gateway,git-delivery,wallet,live-mints'])
base = ['cargo', 'test', '-p', 'maxplayer-core', '--release', '--locked', *features, *config]

def measure(name, command):
    print(f'{name}: {command}', flush=True)
    started = time.monotonic()
    with (out / f'{name}.log').open('w') as log:
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    row = {'phase': name, 'seconds': round(time.monotonic() - started, 2), 'exit': proc.returncode}
    results['phases'].append(row)
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f"- {name}: {row['seconds']} seconds; exit {proc.returncode}\n")
    if proc.returncode:
        print((out / f'{name}.log').read_text()[-16000:], flush=True)
        raise SystemExit(proc.returncode)

measure('cold-build', [*base, '--no-run', '--timings'])
# Mimic CI's dependency-only cache: discard the two workspace crates seen
# rebuilding in the real CI logs, retaining dependencies and the toolchain.
subprocess.run(['cargo', 'clean', '--release', '-p', 'maxplayer-core',
                '-p', 'maxplayer-private-protocol'], check=True)
measure('dependency-warm-build', [*base, '--no-run', '--timings'])
measure('tests', base)
