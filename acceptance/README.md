# Live GemRB acceptance

This directory is the reproducible acceptance entry point for tests that require legally installed BGEE/BG2EE-family game data and a real GemRB executable. Repository CI cannot redistribute those assets, so the runner records the exact local configuration and captures a complete engine log for each run.

## Preparation

Install the requested mods with the top-level driver before launching the scenario:

```text
python tools/gemrb_mods.py install --game /games/BGEE --guiscripts /opt/gemrb/share/gemrb/GUIScripts cipher psion
python tools/gemrb_mods.py install --game /games/BG2EE --guiscripts /opt/gemrb/share/gemrb/GUIScripts sorcerer-monk
```

Then run GemRB through `acceptance/run.py`. GemRB's documented command-line interface accepts `-c CONFIG-FILE`; the runner generates that configuration with logging, no audio, skipped intro videos, and the supplied game/GUIScripts paths.

```text
python acceptance/run.py --profile bgee --scenario cipher-psion-cipher-first --game /games/BGEE --guiscripts /opt/gemrb/share/gemrb/GUIScripts
python acceptance/run.py --profile bg2ee --scenario sorcerer-monk-mid --game /games/BG2EE --guiscripts /opt/gemrb/share/gemrb/GUIScripts
```

Each execution writes `gemrb.cfg`, `gemrb.log`, and `result.json` under `acceptance/artifacts/`. Keep successful records outside git when they contain machine-specific paths; attach them to the corresponding release or issue instead.

## Cross-mod scenarios

Run the Cipher/Psion matrix on both BGEE and BG2EE-family data:

1. Install Cipher, then Psion.
2. Create one Cipher and one Psion.
3. Cipher: learn a power, hit a hostile creature, verify Focus gain, manifest a power, rest, save, reload, and verify Focus state.
4. Psion: learn a power, manifest a save-bearing power at two different current Intelligence modifiers, expend/recover psionic focus with Center Mind, rest, save, reload, and verify PP/focus state.
5. Configure at least one Cipher/Psion quickslot and cast through it.
6. Level both characters once and verify action bars and selectors still open without GUI exceptions.
7. Uninstall Cipher while Psion remains installed and verify Psion still works.
8. Reinstall Cipher, uninstall Psion, and verify Cipher still works.
9. Repeat from a clean target in Psion-then-Cipher install order.

A run fails if the engine log contains an uncaught Python exception, class-table identity error, missing resource, or duplicated transaction spend.

## Sorcerer/Monk scenarios

### BGEE low level

- Complete chargen as Sorcerer/Monk.
- Verify spontaneous Sorcerer spellbook, Cast/quickspell actions, Search and Stealth.
- Verify unarmed start, legal equipment restrictions, proficiency/skill allocation, HP and saves on level-up.
- Reach Monk component level 2 and verify the next fist tier is selected from the custom class row.
- Save and reload; verify class identity and spellbook are unchanged.

### BG2EE mid level

- Create/import a representative mid-level Sorcerer/Monk.
- Repeat spellcasting, Monk ability, fist/APR, proficiency, skill, HP/save, level-up, and save/reload checks.

### BG2EE/ToB high level

- Use a character eligible for HLAs.
- Open the HLA screen and verify the generated merged Sorcerer/Monk table resolves and selections complete without GUI errors.
- Save/reload after an HLA selection.

## Release gate

Sorcerer/Monk 2.0 is source/installer validated but is not considered live-engine accepted until one BGEE low-level, one BG2EE mid-level, and one BG2EE/ToB HLA record have been completed against a named GemRB revision. Cipher/Psion releases that change shared runtime behavior require successful BGEE and BG2EE-family runs in both install orders.
