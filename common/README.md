# Shared GemRB mod infrastructure

`common/` contains implementation shared by otherwise independent GemRB class mods. It owns reusable installer/runtime mechanisms; class rules remain in `psion/`, `cipher/`, and `sorcerer-monk/`.

The GUI layer has one owner (`GemRBModCore`) and dispatches to optional class handlers. Transactions, reusable innate charges, persistent actor-effect state, selector helpers, and WeiDU SPL/ITM constructors live here rather than under a particular class.

Custom-class chargen avoids BG1-era fixed TLK references for generic class, alignment, and proficiency help. The installer keeps vanilla classes on GemRB's stock text path, while Cipher, Psion, and Sorcerer/Monk use `GemRBModStrings.py` literals plus their dynamically allocated class-table descriptions. Shared GUI patches are backed up once and restored after the last active class handler is removed.

For live BGEE/BG2EE-family verification, launch GemRB through the guided acceptance recorder. It captures the class, class-description, alignment, and proficiency screens together with the complete engine log and a JSON manifest:

```bash
python common/tools/run_chargen_text_acceptance.py --output acceptance/bgee -- gemrb -c /path/to/GemRB.cfg
```

Use `--screen psion-discipline` in addition to the defaults when validating the Psion chooser. The runner uses `gnome-screenshot`, `scrot`, `grim`, or ImageMagick `import`, whichever is available.

The compatibility shims under individual mods are intentional so third-party code that included an older helper path continues to work.
