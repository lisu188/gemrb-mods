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
  "required_checkpoints": ["actor.after-action"],
  "prerequisites": ["Required fixture and independently derived expected values."],
  "instructions": ["Perform the real UI action and record its observed result."],
  "supported_game_types": ["bgee", "bg2ee"]
}
```

`Traceback (most recent call last):` and `[GUIScript/ERROR]: Runtime Error:` are
always forbidden, including GUI failures that provide no Python traceback.
Scenario-specific forbidden markers are additive.

`required_checkpoints`, `prerequisites` and `instructions` are optional, so existing log-marker scenarios retain their behavior. Required checkpoint IDs must be unique. The manifest retains schema version 1 and adds parsed `checkpoints`, required assertions and the scenario's prerequisite/instruction lists.

## Structured gameplay checkpoints

Copy `common/acceptance/GemRBAcceptance.py` into the **disposable** fixture's GUIScripts root. The helper only observes state and emits evidence; it never casts, levels an actor, grants XP or repairs a failed state. After performing an action through the real engine UI, emit an observation from its console or a temporary fixture probe:

```python
import GemRBAcceptance as Acceptance
from ie_stats import IE_CLASS, IE_KIT

actual = Acceptance.capture_actor(1, {"class": IE_CLASS, "kit": IE_KIT})
# Set these from the installed class tables before observing the actor.
expected = {"actor": 1, "stats": {"class": installed_class_id, "kit": installed_kit_id}, "variables": {}}
Acceptance.checkpoint("chargen.cipher.identity", actual, expected,
                      {"oracle": "installed class tables", "screenshot": "screenshots/cipher-record.png"})
```

`capture_actor(actor, stats, variables=(), base=False)` reads named GemRB stat IDs and optional GUI variables. `base=True` selects unmodified stats. More specific read-only engine queries, such as known powers or current pool accessors, can provide `actual` directly to `checkpoint`. Use independently derived installed-rule values or a previously recorded baseline for `expected`; assigning the current observation to both fields proves nothing. Screenshots and logs must establish the claimed UI actions and resource transitions. A successful checkpoint alone does not authenticate that a real engine or real UI action produced it.

The stdout protocol is one JSON object per line, optionally prefixed by the engine's log label:

```text
GEMRB_ACCEPTANCE_CHECKPOINT|{"id":"pool.after-cast","actual":7,"expected":7,"context":{"before":10,"installed_cost":3}}
```

Only `id`, `actual`, `expected` and optional object-valued `context` are allowed. The runner compares canonical JSON values, including list order and JSON types (`true` does not equal `1`). It records each observation, source line and computed status in `manifest.json`. It rejects invalid JSON, duplicate object fields, non-finite numbers, missing fields, extra success flags, duplicate checkpoint IDs and missing required checkpoints. All emitted mismatches fail, even for optional checkpoint IDs. Engine termination, forbidden log markers and timeouts remain independent failure gates.

The checked-in manual scenarios cover:

- `chargen-three-classes`: Fighter baseline, Cipher, Sorcerer/Monk and all six Psion disciplines.
- `psion-six-disciplines-chargen`: six real Psion identity flows and initial action/learning state; separate from combat and progression.
- `psion-gameplay-progression`: learning, PP, augmentation, current-INT DC selection, discipline access and progression/persistence.

- `cipher-gameplay-progression`: Focus gain/spending, two-Cipher Reaping Knives ownership and tier/progression/persistence.
- `sorcerer-monk-gameplay-progression`: casting, Monk actions, equipment, component-level progression and persistence.
- `sorcerer-monk-tob-hla`: real ToB merged HLA selection and save/reload, a separate required gate for ToB qualification.

When inspecting rule tables from the live console, use the documented
[eight-character runtime resource names](../../docs/runtime-resource-names.md),
not the longer authoring filenames. The resource-name regression is
`python3 common/tests/validate_runtime_resrefs.py`.

Run each scenario independently on the required game families. Their prerequisite and instruction lists describe the real session procedure; they are not automated gameplay scripts. Four-hour timeouts allow interactive runs, but the engine must exit normally. Missing or blocked checkpoints fail the scenario and must remain recorded as incomplete coverage. Public synthetic checkpoint tests validate the recorder only, not any class or campaign.

## Optional private live console

`common/tools/live_console.py` prepares an explicitly disposable GUI tree with a
local file mailbox. It installs `LiveControl.py` and the checkpoint helper, backs
up `bg2/Start.py`, and adds an opt-in startup hook:

```text
python common/tools/live_console.py --session /tmp/private-gemrb-session \
  --prepare /tmp/disposable-fixture/GUIScripts
```

Launch the real engine with `GEMRB_ACCEPTANCE_SESSION` set to that same directory.
Then `--session /tmp/private-gemrb-session --expression 'GemRB.GetCurrentArea()'`
observes the running engine; requests and results remain in the mailbox. This
POSIX-only console executes arbitrary Python expressions on the GUI thread with
the engine's privileges. It is **not** a sandbox or a production mod component.
Both endpoints reject symlink, shared-permission and differently owned session
directories. Newly prepared mailboxes use mode `0700`; existing directories must
already be private. Never expose the mailbox to untrusted writers.

Use `LiveControl.controls(...)` to observe current control geometry and drive
the real UI using mouse/keyboard input. Observations must not invoke mutating
helpers or replace the gameplay transition being tested. Controlled fixture/XP
preparation is separate and must be recorded. Keep mailboxes, screenshots, saves
and game assets local; they may contain private paths or proprietary content.

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
