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

## Metadata

For real runs, pass the exact evidence needed to reproduce failures:

- `--gemrb-version`
- `--gemrb-commit`
- `--game-type`
- `--fixture-id`
- repeated `--component`
- repeated `--install-order`

Fixture IDs are descriptive identifiers only; fixture paths and proprietary assets are intentionally not committed to the repository.

## Interactive chargen recorder

`common/tools/run_chargen_text_acceptance.py` remains the interactive screenshot frontend for manual chargen evidence. It now emits the same manifest schema/version and run metadata fields as the deterministic harness while retaining screenshot-specific capture records.

Screenshots are evidence, not the primary oracle. New deterministic scenarios should prefer engine logs, installed resources and explicit actor/state assertions wherever a stable probe exists.

## Planned scenario families

Issue #50 tracks the remaining slices:

1. shared Cipher/Psion install and uninstall lifecycle in both orders;
2. Cipher, Psion and Sorcerer/Monk live class smoke tests;
3. Focus/PP/rest/save-load/quickslot/minimal-combat state transitions;
4. low/mid/high-level level-up coverage;
5. soundset regression coverage from #65 after its baseline is classified.
