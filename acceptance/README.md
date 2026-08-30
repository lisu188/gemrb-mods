# Live GemRB acceptance

This directory is the reproducible acceptance entry point for checks that require legally installed BGEE/BG2EE-family game data and a real GemRB executable. Repository CI cannot redistribute those assets.

Automated fixture success is not treated as live acceptance. `acceptance/run.py` records engine health and the human gameplay result separately and only writes `passed: true` when all of the following are true:

- GemRB exits successfully;
- required log patterns are present;
- no rejected log patterns are found;
- the operator explicitly records `--manual-result pass`;
- the run was not created with `--skip-launch`.

Every run also requires a named `--gemrb-revision`, which should be a release version, package revision, or git commit that uniquely identifies the tested engine.

## Preparation

Install the requested mods before launching the scenario:

```text
python tools/gemrb_mods.py install cipher psion --game /games/BGEE --guiscripts /opt/gemrb/share/gemrb/GUIScripts
python tools/gemrb_mods.py install sorcerer-monk --game /games/BG2EE
```

GemRB's documented command-line interface accepts `-c CONFIG-FILE`; the runner generates that configuration with logging, no audio, skipped intro videos, and the supplied game/GUIScripts paths.

Example after completing the scenario checklist successfully:

```text
python acceptance/run.py \
  --profile bgee \
  --scenario cipher-psion-cipher-first \
  --game /games/BGEE \
  --guiscripts /opt/gemrb/share/gemrb/GUIScripts \
  --gemrb-revision 0.9.4 \
  --manual-result pass
```

Each execution writes `gemrb.cfg`, `gemrb.log`, and `result.json` under `acceptance/artifacts/`. Keep successful records outside git when they contain machine-specific paths; attach them to the corresponding release or issue.

The runner automatically rejects Python tracebacks, `ModuleNotFoundError`, and `ImportError`. Additional failure signatures can be supplied with repeated `--reject-log PATTERN`; required signatures can be supplied with repeated `--expect-log PATTERN`.

## Cross-mod scenarios

Run the Cipher/Psion matrix on both BGEE and BG2EE-family data.

### Cipher then Psion

1. Start from a clean target and install Cipher, then Psion through `tools/gemrb_mods.py`.
2. Create one Cipher and one Psion.
3. Cipher: learn a power, hit a hostile creature, verify Focus gain, manifest a power, rest, save, reload, and verify Focus state.
4. Verify Reaping Knives on another ally: hostile weapon hit grants 5 Focus to the originating Cipher; friendly/neutral hits do not; a critical does not add a second Reaping-Knives-only credit; cap is respected.
5. Psion: learn a power, manifest a save-bearing power at two different current Intelligence modifiers, expend/recover psionic focus with Center Mind, rest, save, reload, and verify PP/focus state.
6. Choose a psicrystal personality, manifest the psicrystal, save/reload, rest, and verify personality/passive/summon-charge behavior remains actor-local.
7. Configure at least one Cipher and one Psion quickslot and cast through it.
8. Level both characters once and verify action bars and selectors still open without GUI exceptions.
9. Uninstall Cipher while Psion remains installed and verify Psion plus psicrystal runtime still works.
10. Reinstall Cipher, uninstall Psion, and verify Cipher plus subclass runtime still works.

### Psion then Cipher

Repeat the same scenario from a clean target in the opposite install order. Shared `GemRBModCore` ownership and dependency files must remain correct after both uninstall orders.

### Enemy Psion fixture

Use a test encounter or console-spawned Psion-class actor and exercise `PsionAI.py` through an encounter script/harness:

- initialize PP/focus without player GUI interaction;
- use one offensive, one defensive, and one mobility/control power;
- verify unaffordable manifestations are rejected;
- verify PP is deducted exactly once;
- verify a save-bearing manifestation uses that enemy's current Intelligence;
- save/reload the area and repeat a legal manifestation.

## Sorcerer/Monk scenarios

### BGEE low level

- Complete chargen as Sorcerer/Monk.
- Verify spontaneous Sorcerer spellbook, Cast/quickspell actions, Search, and Stealth.
- Verify unarmed start, equipment restrictions, proficiency/skill allocation, HP, and saves on level-up.
- Reach Monk component level 2 and verify the next fist tier is selected from the custom class row.
- Save and reload; verify class identity and spellbook are unchanged.

### BG2EE mid level

- Create/import a representative mid-level Sorcerer/Monk.
- Repeat spellcasting, Monk ability, fist/APR, proficiency, skill, HP/save, level-up, and save/reload checks.

### BG2EE/ToB high level

- Use a character eligible for HLAs.
- Open the HLA screen and verify the generated merged Sorcerer/Monk table resolves and selections complete without GUI errors.
- Save/reload after an HLA selection.

## Recording failure

Use `--manual-result fail` when the gameplay checklist exposes incorrect behavior even if GemRB exits cleanly. The result file preserves the engine return code and manual result independently.

Use `--manual-result not-run --skip-launch` only to inspect generated configuration/artifact layout; such a record can never pass acceptance.

## Release gate

Sorcerer/Monk 2.0 is source/installer validated but is not live-engine accepted until one BGEE low-level, one BG2EE mid-level, and one BG2EE/ToB high-level record have `passed: true` against named GemRB revisions.

Cipher/Psion releases that change shared runtime behavior require successful BGEE and BG2EE-family records in both install orders. The repository must not close that acceptance gate based only on automated fixture or parser results.
