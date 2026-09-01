# gemrb-mods

Repository of GemRB mods and tools not included with GemRB itself. Available under GPLv2; see `COPYING` for details.

Some simple mods require only setting tweaks. For those, see the GemRB modding page: https://gemrb.org/Modding.html

## Prerequisites

- WeiDU
- GemRB
- A supported Infinity Engine game

## Active custom classes

| Mod | Current version | Shared runtime | Release status |
| --- | --- | --- | --- |
| [Cipher](cipher/README.md) | 0.2.0 | `common/` + `GemRBModCore` | automated validation; real-engine acceptance tracked in #50 |
| [Psion](psion/README.md) | 1.3.0 | `common/` + `GemRBModCore` | automated validation; real-engine acceptance tracked in #50 |
| [Sorcerer/Monk](sorcerer-monk/README.md) | 2.0 | shared chargen layer | automated/WeiDU validation complete; live campaign qualification tracked in #51 |

See [the compatibility and release matrix](docs/compatibility.md) for supported game families, runtime requirements, and the distinction between automated validation and live-engine acceptance.

## Unified Cipher/Psion installation

Cipher and Psion share a versioned runtime API. For the new installation path, place the matching `common/`, selected class directory/directories and `gemrb_mods.py` in the game directory. Then use the top-level driver for both WeiDU and GemRB GUI installation:

```text
python gemrb_mods.py preflight cipher --game . --guiscripts /path/to/GemRB/gemrb/GUIScripts
python gemrb_mods.py install cipher --game . --guiscripts /path/to/GemRB/gemrb/GUIScripts
python gemrb_mods.py status --game . --guiscripts /path/to/GemRB/gemrb/GUIScripts
```

Use `psion` instead of `cipher` for Psion. Uninstall through the same entry point:

```text
python gemrb_mods.py uninstall cipher --game . --guiscripts /path/to/GemRB/gemrb/GUIScripts
```

The driver rejects a mismatched class/common runtime API, a package/TP2 version mismatch, a missing WeiDU executable, an invalid game target, or an incompatible GemRB GUI-script layout before the first installation mutation. GUI compatibility is checked by running the existing shared installer against a disposable copy of the target `GUIScripts` tree.

Install uses WeiDU first and then delegates GUI mutation to `common/tools/install_guiscripts.py`. Uninstall removes that class's GUI handler first and then invokes WeiDU. If a second phase fails, the driver reports the resulting partial state rather than claiming an atomic rollback. `status` distinguishes `not installed`, `weidu only`, `runtime only/inconsistent`, `installed`, and `installed with other handlers`.

The existing class-specific WeiDU and `tools/install_guiscripts.py` commands remain supported as low-level compatibility entry points.

## Installation layout

WeiDU does not handle arbitrary repository nesting as a user-facing installation layout. Keep each selected class directory and its matching `common/` sibling at the game root. The unified driver and the forthcoming release archive builder use the same layout, so installed packages do not depend on paths outside the extracted bundle.
