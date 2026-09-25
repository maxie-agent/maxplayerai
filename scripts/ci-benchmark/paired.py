#!/usr/bin/env python3
"""Pair two variants on one runner, using independent target directories."""
import os
import subprocess

variants = ['baseline', 'no-lto']
if os.environ['ORDER'] == 'no-lto-first':
    variants.reverse()
failed = False
for variant in variants:
    env = dict(os.environ, VARIANT=variant, CARGO_TARGET_DIR=f'target-{variant}')
    result = subprocess.run(['python3', 'scripts/ci-benchmark/run.py'], env=env)
    failed |= result.returncode != 0
raise SystemExit(int(failed))
