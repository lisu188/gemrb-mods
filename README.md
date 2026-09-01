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

## Installation layout

WeiDU does not handle arbitrary repository nesting as a user-facing installation layout. Copy the mod directory you want to install together with any documented sibling dependencies, especially `common/` for the current custom-class mods. Follow each mod's README for the exact installation commands and supported games.
