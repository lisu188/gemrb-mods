# GemRB real-engine acceptance

`common/tools/gemrb_acceptance.py` is the shared runner for deterministic acceptance scenarios that need an actual process boundary. It records the command, scenario identity, fixture/game metadata, exit code, timeout state, log assertions and failure classification in `manifest.json`.

The harness deliberately does not contain copyrighted game data. Real BG-family fixtures are supplied externally by the developer, CI runner or self-hosted environment. Public CI exercises the runner with synthetic processes so command execution, timeout handling, error detection and manifest compatibility remain continuously tested.

## Scenario format

Scenario files live in `common/acceptance/scenarios/` and use a small JSON contract:

```json
{
  "id": "scenario-id",
  "description": "What behavior this scenario proves.",
  "timeout_seconds": 120,
  "expected_exit_codes": [0],
  "expected_log_markers": ["EXPECTED_MARKER"],
  "forbidden_log_markers": ["KNOWN_FAILURE"],
  "supported_game_types": ["bgee", "bg2ee"]
}
```

`Traceback (most recent call last):` is always forbidden. Scenario-specific forbidden markers are additive.

## Synthetic smoke run

```text
python common/tools/gemrb_acceptance.py \
  --scenario common/acceptance/scenarios/harness-smoke.json \
  --output acceptance-out \
  --game-type synthetic \
  --fixture-id public-ci \
  --gemrb-commit synthetic \
  -- python -c "print('GEMRB_ACCEPTANCE_READY')"
```

A successful run writes:

```text
acceptance-out/
├── gemrb.log
└── manifest.json
```

The command exits non-zero for a timeout, unexpected exit code, missing expected log marker, forbidden log marker, process launch failure or invalid scenario configuration.

## Preparing a disposable real fixture

`prepare_acceptance_fixture.py` copies an existing legal game fixture and an existing GemRB `GUIScripts` tree into a disposable workspace, then copies the requested repository packages into the game copy. The source directories are never modified.

```text
python common/tools/prepare_acceptance_fixture.py \
  --source-game /fixtures/BGEE \
  --source-guiscripts /opt/gemrb/GUIScripts \
  --output /tmp/gemrb-acceptance-bgee \
  --fixture-id bgee-local-clean \
  --game-type bgee \
  --mod cipher \
  --mod psion
```

The resulting `fixture.json` stores only the fixture identifier, game type, relative prepared paths and copied package list. It deliberately does not persist the original fixture paths.

Preparation fails before mutation if a source directory or repository package is missing or if the destination already exists. It also rejects a source game copy that already contains one of the packages being injected, because lifecycle acceptance must start from a clean baseline.

## Cipher/Psion shared-runtime lifecycle matrix

`common/acceptance/matrices/cipher-psion-lifecycle.json` contains four cases: both class install orders crossed with both first-uninstall choices. Run the complete matrix against a prepared fixture with:

```text
python common/tools/run_shared_runtime_lifecycle.py \
  --fixture /tmp/gemrb-acceptance-bgee/fixture.json \
  --matrix common/acceptance/matrices/cipher-psion-lifecycle.json \
  --output /tmp/gemrb-acceptance-bgee/lifecycle \
  --weidu weidu
```

Each case performs component-0 WeiDU install, then delegates GUI mutation to the existing class `tools/install_guiscripts.py` wrapper. On uninstall it removes the GUI handler and then force-uninstalls WeiDU component 0. After every GUI transition it checks the exact `.gemrbmodcore.<handler>.active` set.

The runner snapshots all shared GUI patch targets and installed common/runtime modules before each case. After the last handler is removed, every watched file must match the baseline SHA-256 or original non-existence state. This acceptance layer does not duplicate `_patch_*` or ownership logic from `common/tools/install_guiscripts.py`.

Per-command logs and `lifecycle-manifest.json` are written under the selected output directory. A command failure, handler-marker mismatch, dirty initial runtime, timeout or restoration mismatch fails the matrix.

## Metadata

For deterministic scenario runs, pass the exact evidence needed to reproduce failures:

- `--gemrb-version`
- `--gemrb-commit`
- `--game-type`
- `--fixture-id`
- repeated `--component`
- repeated `--install-order`

Fixture IDs are descriptive identifiers only; fixture paths and proprietary assets are intentionally not committed to the repository.

## Interactive chargen recorder

`common/tools/run_chargen_text_acceptance.py` remains the interactive screenshot frontend for manual chargen evidence. It emits the same manifest schema/version and run metadata fields as the deterministic harness while retaining screenshot-specific capture records.

The recorder supports an explicit `soundset` capture. When the disposable GemRB `GUICG19.py` has been instrumented with `common/tools/patch_soundset_diagnostic.py`, the manifest also contains parsed `soundset_diagnostics` records with the `CHR_SOUNDS` count, bounded sample, actor slot, class row and gender. See [soundset-diagnostic.md](soundset-diagnostic.md) for the immutable-fixture Fighter/custom-class A/B procedure used by #65.

Screenshots are evidence, not the primary oracle. New deterministic scenarios should prefer engine logs, installed resources and explicit actor/state assertions wherever a stable probe exists.

## Remaining live scenario families

The acceptance infrastructure from #50 is in place. Legal external BG-family fixtures are still required to produce real-engine evidence for:

1. shared Cipher/Psion lifecycle execution on BGEE and BG2EE-family fixtures;
2. Cipher, Psion and Sorcerer/Monk live class smoke tests;
3. Focus/PP/rest/save-load/quickslot/minimal-combat state transitions;
4. low/mid/high-level level-up coverage;
5. the #65 soundset A/B baseline and persistence check.
