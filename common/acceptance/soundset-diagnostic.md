# Soundset diagnostic acceptance

Issue #65 investigates an empty soundset list observed during live custom-class chargen. The diagnostic path is intentionally separate from the production GUI installer because pinned GemRB BG1 and BG2 `GUICG19.py` enumerate `CHR_SOUNDS` directly and do not filter by class.

## Prepare one immutable baseline

Use one legal game fixture and one exact GemRB `GUIScripts` revision for every comparison. The control order is:

1. clean Fighter;
2. clean second vanilla class;
3. Cipher only;
4. Psion only;
5. Sorcerer/Monk only;
6. Cipher then Psion;
7. Psion then Cipher;
8. combined set where class-ID capacity permits.

Do not compare independently sourced game directories. Recreate each disposable run from the same clean source fixture so resource discovery cannot drift between cases.

## Instrument the disposable GUIScripts tree

After preparing the fixture, instrument its copied GUIScripts tree:

```text
python common/tools/patch_soundset_diagnostic.py /tmp/gemrb-acceptance/guiscripts
```

The patch is backup-safe and only touches `bg1/GUICG19.py` and/or `bg2/GUICG19.py`. Immediately after `VoiceList.ListResources(CHR_SOUNDS)`, it writes one line to the captured GemRB output:

```text
GEMRB_MODS_SOUNDSET|family=bg2|count=12|slot=1|class=FIGHTER|gender=1|sample=['male1', 'male2']
```

The line records the raw enumeration count, a bounded sample, current chargen actor slot, resolved class row and actor sex. It does not change the returned voice list or inject fallback entries.

Restore the copied upstream files after the diagnostic run with:

```text
python common/tools/patch_soundset_diagnostic.py /tmp/gemrb-acceptance/guiscripts --uninstall
```

This helper must never be wired into Cipher, Psion or Sorcerer/Monk production installation.

## Capture the Sound screen

Run the existing interactive recorder with the diagnostic-patched GemRB tree and request the sound screen explicitly:

```text
python common/tools/run_chargen_text_acceptance.py \
  --output /tmp/soundset-fighter \
  --screen soundset \
  --game-type bgee \
  --fixture-id bgee-control \
  --gemrb-commit 8c853a764ab489eee7e990a713eeb24dc8cc2d53 \
  -- gemrb -c /path/to/GemRB.cfg
```

The resulting `manifest.json` includes a `soundset_diagnostics` array parsed from the engine log. The numeric count and raw sample are acceptance evidence; the screenshot is supporting evidence only.

For a deterministic command that already drives GemRB to the Sound screen and exits, use `common/acceptance/scenarios/soundset-enumeration.json` with `common/tools/gemrb_acceptance.py`. That scenario requires at least one `GEMRB_MODS_SOUNDSET|` log marker and rejects Python tracebacks.

## Classification

- Fighter count `0`: fixture/resource/GemRB configuration problem. Do not patch class code.
- Fighter count `>0`, custom count `0`: pre-sound custom-class chargen state regression. Diff slot/class/gender and the preceding custom-class transitions.
- Counts equal and `>0`, custom list visually empty: GUI control/window state regression after resource enumeration.
- List populated but preview or persistence fails: investigate sound selection/preview/persistence inputs, not enumeration.

A product-code fix is justified only after the same immutable fixture proves that a vanilla class enumerates voices while a custom-class path does not, or that equal enumeration counts produce divergent GUI behavior.
