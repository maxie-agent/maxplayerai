# CI compilation experiment — 2026-09-25

[Run 36133207336](https://github.com/maxie-agent/maxplayerai/actions/runs/36133207336)
· [experiment branch](https://github.com/maxie-agent/maxplayerai/tree/experiment/ci-compile-times)

Measured commit: `de2078cfe83f0f9ae06391e44f2e65ab83a59119`, based on `bd73904`.
All six artifacts were downloaded into a fresh directory and their `results.json`,
`environment.txt`, and cold/warm/test logs inspected. Five jobs passed; union/baseline
failed in tests, not compilation. No production CI, release profile, or test coverage
was changed. Nothing was merged.

## Method and environment

Each independent GitHub-hosted `ubuntu-latest` job used Rust 1.98.1
(`48a229cea`, LLVM 22.1.8), Cargo 1.98.1 (`797e8a9bc`), 4 logical CPUs
(2 cores × 2 threads), and approximately 15 GiB RAM.

- Baseline: existing release profile, thin LTO, default release optimization (3).
- No LTO: command-local `profile.release.lto="off"`; optimization otherwise unchanged.
- No LTO + core opt1: additionally `profile.release.package.maxplayer-core.opt-level=1`.
- Union: `cargo test -p maxplayer-core --release --locked --features acp,gateway,git-delivery,wallet`.
- Money: `cargo test -p maxplayer-core --release --locked --no-default-features --features gateway,git-delivery,wallet,live-mints`.
- Cold: `--no-run --timings`, without a restored cache.
- Dependency-warm: clean only `maxplayer-core` and `maxplayer-private-protocol`
  with `cargo clean --release -p ...`, then repeat `--no-run --timings`.
- Tests: execute the same full suite without `--no-run`. This phase includes
  Cargo freshness checks and doctest overhead, not just test-body runtime.
  Warm+tests is the sum of those two phases, not whole-job wall time.

## Measured seconds

| Suite | Variant | CPU model | Cold build | Warm build | Tests | Warm + tests |
|---|---|---|---:|---:|---:|---:|
| Money | Baseline | Intel Xeon Platinum 8573C | 965.83 | 823.98 | 305.99 | 1129.97 |
| Money | No LTO | Intel Xeon Platinum 8573C | 393.80 | 223.70 | 317.05 | 540.75 |
| Money | No LTO + core opt1 | AMD EPYC 7763 | 380.90 | 199.67 | 314.61 | 514.28 |
| Union | Baseline | Intel Xeon Platinum 8573C | 1130.30 | 980.88 | 293.80* | 1274.68* |
| Union | No LTO | AMD EPYC 9V74 | 361.22 | 214.53 | 334.86 | 549.39 |
| Union | No LTO + core opt1 | AMD EPYC 7763 | 393.69 | 210.89 | 317.07 | 527.96 |

\* Failed after the library tests; later integration tests and doctests were not
executed. This is an incomplete baseline, not a successful full-suite duration.

## Savings versus baseline

| Suite | Variant | Warm build saving | Warm + tests saving | Cold build saving (separate) |
|---|---|---:|---:|---:|
| Money | No LTO | 600.28s (72.85%) | 589.22s (52.14%) | 572.03s (59.23%) |
| Money | No LTO + core opt1 | 624.31s (75.77%) | 615.69s (54.49%) | 584.93s (60.56%) |
| Union | No LTO | 766.35s (78.13%) | Not valid as full-suite comparison | 769.08s (68.04%) |
| Union | No LTO + core opt1 | 769.99s (78.50%) | Not valid as full-suite comparison | 736.61s (65.17%) |

For transparency, subtracting the successful union totals from the *failed partial*
baseline gives 725.29s (56.90%) and 746.72s (58.58%), respectively. These are only
observed elapsed-time differences; they are not validated full-suite savings.

The strongest comparison is money baseline versus no-LTO: same CPU model, full
suite success, warm build 13m44s → 3m44s and warm+tests 18m50s → 9m01s.
The test phase itself increased by 11.06s. Most observed benefit is compilation.
Core opt1 saved another 24.03s of money warm compilation (26.47s including tests)
and 3.64s of union warm compilation (21.43s including tests) versus no-LTO;
different CPU models prevent attributing these small differences to optimization.

## Test counts and baseline failure

Counts below sum the individual test-binary summaries, including doctests where run.
No tests were filtered out and existing ignored tests were left unchanged.

| Suite / variants | Passed | Failed | Ignored | Result summaries |
|---|---:|---:|---:|---:|
| Money / all three | 1900 each | 0 | 5 each | 28 each |
| Union / both no-LTO variants | 1998 each | 0 | 48 each | 28 each |
| Union / baseline | 1911 | 1 | 19 | 1 (library only) |

The money library component was 1816 passed / 2 ignored in every variant;
successful union library components were 1912 passed / 19 ignored.

Union baseline failed
`seller_node::run::tests::an_unknown_id_closed_costs_no_reconnect_and_no_resubscribe`
at `crates/maxplayer-core/src/seller_node/run.rs:17093`. The log first explicitly
reports `RELAY-CLOSED UNKNOWN-ID` / `no recovery forced`, then a separate
`RELAY-STALL detected` at the 3-second watchdog threshold, followed by successful
reconnection. The test interprets any changed connection count during its 20-second
window as an unknown-ID-triggered reconnect. Source inspection confirms a 1-second
heartbeat with the watchdog enabled. The log supports watchdog interference with
the assertion, plausibly under runner contention; a scheduling flake is not proven
by this single sample. Both alternative union profiles passed this test.

There is no demonstrated benchmark-script defect to repair. The failure remains
visible; no tests were removed, retries hidden, or product/test code changed to
make the benchmark green. A repeat baseline and focused contention reproduction
are needed before treating union full-suite performance as validated.

## Interpretation and next step

This is one sample per suite/profile on separate runners, not a promised speedup.
Union compares three different CPU models; even matching model names do not control
host contention or frequency. Money also includes live-mint network variation.
The warm-cache simulation rebuilds both workspace crates and is not a measurement
of every real CI cache-hit pattern. Setup, queue time, cleaning and artifact uploads
are outside the measured phase totals. Union/no-LTO started later; finish order is
not evidence of relative performance.

Recommend a repeated, CPU-matched comparison of baseline and **no-LTO only** as the
next experiment, including a clean union baseline and investigation of the watchdog
failure. No-LTO has the clearest benefit; core opt1 has no convincing incremental
advantage from this sample. If reproduced, propose a CI-test-only override while
keeping production/release LTO and every feature suite unchanged. Do not change
production settings or merge based on this run alone.

This report-only commit uses CI skip markers so publishing findings does not rerun
the expensive benchmark.
