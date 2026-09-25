# Reusing builds across CI, development and releases

Analysis at experimental branch base bd73904, 2026-09-25. No shared service,
credentials, deployment or production build changes made.

## Three distinct reuse layers

1. **Compiler artifacts:** keep dependency and workspace compilation outputs.
   Useful when source/compiler/target/features/flags/build-script inputs match.
   Cargo target-directory caches are comparatively simple inside GitHub Actions;
   compiler wrappers such as sccache can share cacheable rustc outputs across machines.
   Source changes still invalidate affected crates. sccache does not cache rustc
   invocations that invoke the system linker (including executable/test linking),
   and requires Rust incremental compilation disabled. It is not a complete fix
   for the measured LTO-heavy test rebuilds. Measure hit rates and transfer cost.
2. **Immutable finished binaries:** build a release-compatible binary once per
   commit + target + feature set + toolchain + profile, verify it, retain its digest
   and provenance, then consume that exact artifact for local execution or release
   packaging. No compilation on a matching hit. Tests and publication gates still
   run as required. A cache hit is not evidence that tests passed.
3. **Nix store outputs:** the existing flake makes a signed Nix binary cache a natural
   option for `nix build`, deployment and development environments. A matching
   derivation can be downloaded instead of rebuilt. This does not automatically
   populate `target/` for `cargo test` inside `nix develop`.

## Actual compatibility boundaries in this repository

- CI uses rustup stable; this experiment pins 1.98.1. The Nix devshell and default
  package use rustc/cargo from the committed nixpkgs input, not the same rustup pin.
- Standard Linux CI has no explicit --target (GNU host). Release builds explicitly
  target x86_64-unknown-linux-musl, aarch64-unknown-linux-musl and aarch64-apple-darwin.
- Experimental tests disable LTO; release binaries retain thin LTO. Test harnesses
  are not the shipped maxplayer executable, even when their source commit matches.
- Release features are explicitly --no-default-features --features wallet,acp.
- maxplayer/build.rs embeds commit identity. Promotion needs the exact release
  commit/version, not just similar source; a PR synthetic merge artifact is not
  automatically an artifact for the final main merge commit.
- Release workflow already uploads built artifacts for downstream packaging jobs.
  The additional opportunity is verified *cross-run* reuse, not removing duplication
  that has already been eliminated within a single release run.
- flake.nix uses buildRustPackage with src=self and doCheck=false. It is packaging,
  not a replacement for the tested CI gates. Whole-source inputs also reduce reuse
  across unrelated changes. Crane can separate dependency artifacts and filtered
  source inputs if a future Nix build refactor is warranted.

## Practical sequence

1. Validate no-LTO for CI tests independently of caching.
2. Pilot workspace artifact reuse in CI with isolated keys and Cargo fingerprint
   validation; compare a fresh checkout/runner cache restore against the current
   dependency-only cache. Account for archive transfer, extraction, size/eviction,
   checkout mtimes, build-script paths and invalidation. Merely switching on
   cache-workspace-crates is not a proven cross-run speedup.
3. For local use of an unchanged main/release revision, download the matching
   verified binary, or use a Nix binary cache for the existing package. This has
   higher certainty than trying to transplant arbitrary Cargo target directories.
4. For release reuse, optionally produce release-profile binaries on trusted main
   builds and promote the matching outputs on a tag. This shifts compilation earlier;
   it only reduces total compute when the binaries are reused. Do not build every
   platform on every PR just to make tag latency look lower.
5. Only then pilot cross-machine compiler caching if measurements show substantial
   remaining cacheable compilation. Align toolchains deliberately; don't downgrade
   CI to the Nix toolchain solely to gain hits.

Use GitHub artifacts/cache for an initial existing-platform experiment. For a
cross-machine store, evaluate a standard signed Nix HTTP cache or an existing
self-hosted implementation; Attic is available but its README calls it an early
prototype. No new paid storage or hosting is assumed. Trusted release artifacts
must come from trusted build jobs; PR experiments cannot publish into that namespace.

## What savings are realistic?

- Exact finished artifact hit: replaces compilation with download/verification;
  transfer time is not measured yet.
- Full compatible test-artifact hit: could approach suite execution time plus cache
  restore/setup. Earlier successful test phases were roughly five minutes; this
  is a lower-bound scenario, not a forecast for every source change.
- Changed core source: expect a core rebuild; the no-LTO result is still valuable.
- Different platform/profile/toolchain/features: separate build/cache entries.

The paired benchmark additionally measures a no-op --no-run after a successful
warm build. This is only same-directory unchanged-artifact reuse; it does NOT prove
remote restore, fresh-checkout portability, or local/release cache integration.

## Primary references

- https://github.com/mozilla/sccache/blob/main/docs/Rust.md
- https://github.com/mozilla/sccache#storage-options
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- https://nix.dev/guides/recipes/add-binary-cache.html
- https://crane.dev/
- https://github.com/zhaofengli/attic
