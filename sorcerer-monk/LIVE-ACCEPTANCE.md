# Sorcerer/Monk live acceptance

Issue #51 is the live-engine release qualification for Sorcerer/Monk 2.0. Static and WeiDU tests remain the fast regression layer; a release-qualification result must additionally come from an actual GemRB process using a legal BG-family fixture.

## Build the oracle from the installed game

Do not hard-code expected class IDs, fist resources, proficiency rates, Monk skill metadata or HLA rows in the live runner. Install Sorcerer/Monk into the disposable fixture first, then build the expected-state oracle from the resulting override resources:

```text
python sorcerer-monk/tools/build_live_oracle.py \
  /tmp/gemrb-acceptance-bgee/game \
  --output /tmp/gemrb-acceptance-bgee/sorcerer-monk-oracle.json \
  --game-type bgee \
  --fixture-id bgee-local-clean \
  --gemrb-commit <exact-gemrb-commit> \
  --weidu-version 251.00
```

The builder validates the installed identity before writing the oracle. `CLASS.IDS`, the `SORCERER` and `MONK` `CLSKILLS.2DA` positions, the `SORCERER_MONK` `CLSKILLS.2DA` position and the custom class ID must resolve consistently. It also verifies that the positional `QSLOTS.2DA` row exists and that a declared custom HLA abbreviation resolves to an installed generated LU table.

The JSON records SHA-256 hashes for the installed tables used as evidence. This makes a live result traceable to the exact installation rather than only to repository source expectations.

## Oracle fields used by live checkpoints

The live runner should compare GemRB state to the following installed-data sections:

- `identity.class_id`: custom class identity expected before and after save/reload;
- `installed.clskills`: Sorcerer spell-table/book metadata and Monk class-ability metadata installed for the multiclass;
- `installed.qslots`: the exact positional action-bar row GemRB resolves for the custom class ID;
- `installed.fistweap.by_monk_level`: expected fist resource keyed by Monk component level;
- `installed.clswpbon`: installed Monk-derived unarmed combat progression metadata;
- `installed.profs`: installed proficiency award rule;
- `installed.thiefskl` and `installed.thiefscl`: installed Monk skill-point and availability metadata when the modern tables exist;
- `installed.weapprof`: the installed custom proficiency column when present;
- `installed.hpclass` / `installed.classes`: installed true-multiclass HP/class metadata for the active class-table layout;
- `installed.hla`: generated HLA table identity, rows and `LUNUMAB` metadata when HLA support is installed.

Source-component snapshots under `components.sorcerer` and `components.monk` are included to diagnose inheritance regressions. They are evidence, not a substitute for the installed custom row.

## Required live matrix

### BGEE low level

Create a Sorcerer/Monk through GemRB chargen and enter gameplay. Record:

1. actor class ID and resolved class row;
2. spontaneous Sorcerer book availability and one successful cast;
3. Search/Stealth/action-bar availability against `installed.qslots`;
4. one Monk class ability invocation;
5. save, reload, then re-check class identity and spellbook state.

### Component progression

Use a deterministic state where the Monk component advances from level 1 to 2. Compare the post-level-up unarmed resource directly with `installed.fistweap.by_monk_level["2"]`. Also record the installed `CLSWPBON`, proficiency and skill rules used for the expected result.

The test must use component levels. Total/average multiclass level is not the oracle.

### BG2EE/ToB high level

On an HLA-capable fixture, require `installed.hla.enabled == true`, open HLA selection, verify the generated table can be loaded, complete one legal selection and re-check class identity and spontaneous spellbook metadata afterward.

If the installed oracle says HLA support is absent, the HLA checkpoint is unsupported for that fixture; it must not be reported as passed.

## Result requirements

Every live result must include:

- the oracle JSON;
- the real-engine acceptance manifest and GemRB log;
- game family and fixture identifier;
- exact GemRB commit/version and WeiDU version;
- actual versus expected values at each checkpoint;
- the first failing checkpoint when a run fails.

A screenshot may accompany a checkpoint but is not the state oracle. No product-code workaround should be merged for #51 without a live run that reproduces the incorrect state against the installed-data oracle.
