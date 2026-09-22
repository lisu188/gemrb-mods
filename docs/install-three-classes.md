# Installing Sorcerer/Monk, Cipher and Psion together

## Package scope

The unified driver accepts `sorcerer-monk`, `cipher` and `psion`. Each package
owns its existing GUI module: `SorcererMonkUI`, `Cipher` or `Psionics`.
Sorcerer/Monk uses the shared character-creation integration; it does not
become a PP/Focus caster and its native spontaneous spell rules are unchanged.
The separate experimental Sorcerer/Monk/Cleric mod is not part of this bundle.

A combined archive includes all three class directories, `common/`,
`gemrb_mods.py` and the compatibility documentation. Individual and two-class
archives are also supported. Extract the archive at the game root, alongside
`chitin.key`, not inside an extra repository folder. Keep `common/` and every
selected package from the same revision.

## Engine prerequisite

Use a GemRB build containing the fixes merged in `lisu188/gemrb#3`
(merge commit `91e64d19c90f169530f99f5a08ecf96f1402cf67`).
Cipher and Psion require `GemRB.SetSpellCastCheck`; merely patching Python
scripts into an older engine does not add this native API. The engine fixes
also cover Sorcerer/Monk progression, fists and saving.

Psion 1.4.0's summoned psicrystal additionally requires `GemRB.ManageCompanion`
from `lisu188/gemrb#4`. Without this native API, the existing personality bonus
remains available but the summon/dismiss actions are not granted. Installing
new Python scripts alone cannot add persistent companion support to an old
binary. Verify both capabilities in the actual engine used for this game.
Dismiss every psicrystal before removing its owner from the party or
uninstalling Psion; WeiDU cannot remove creatures already stored in a save.
The new companion uses saved owner locals, not party-slot identities or the
shared familiar subsystem. A living recalled body retains its injuries.
Creation or replacement is limited to once per completed rest.

Run that engine against the game once to create `gemrb_path.txt` before
installing. WeiDU and Python must be available. Back up saves and use a
separate game installation for acceptance testing. Do not install mods while
the game is running, except when a temporary AppImage/Flatpak mount is needed
for WeiDU to access the engine resources; do not continue gameplay during
installation.

See [cast accounting](cast-runtime.md) and [compatibility](compatibility.md).
Accepted commands spend PP/Focus when queued, not when effects land. Later
interruption does not refund them. This release does not claim to migrate
existing characters affected by the old incorrectly oriented CLAB tables.

## Installation

From the extracted game directory, replace the GUI path below with the
GUIScripts directory of the actual GemRB build used to run this game.
Preflight every selected package first, then install each one:

```sh
python gemrb_mods.py preflight sorcerer-monk --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py preflight cipher --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py preflight psion --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py install sorcerer-monk --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py install cipher --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py install psion --game . --guiscripts /path/to/GUIScripts
python gemrb_mods.py status --game . --guiscripts /path/to/GUIScripts --json
```

The driver's preflight checks package versions, the WeiDU parser and GUI
patchability. It does not execute the engine or certify gameplay. Each install
runs WeiDU and then installs its GUI handler; failure in the second phase is
reported as a partial installation, not an automatic rollback.

## Removal

Use the same driver with `uninstall` and the selected package name. A removed
package must not remove another package's shared hooks. The last GUI handler
removal restores the pre-mod GUI files. WeiDU separately manages game-resource
backups and may reinstall later components when removing an earlier one.
Do not manually delete `common/`, ownership markers or WeiDU backups before
uninstalling.

## Reproducible build and tests

From the source repository:

```sh
python common/tools/build_release.py sorcerer-monk
python common/tools/build_release.py cipher psion sorcerer-monk
python common/tests/validate_three_class_release.py
python psion/tests/validate_psicrystal_companion.py
```

The package tests cover all seven nonempty package subsets, deterministic ZIP
ordering including `release-manifest.json`, and all 36 combinations of
installation and removal ordering. They execute the actual extracted driver
and shared GUI installer against synthetic GUI files with a fake WeiDU
boundary. They also check repeated installation, preservation of pre-existing
handler files and byte-for-byte GUI restoration. These checks are not live
BGEE/BG2EE gameplay acceptance or a substitute for the real WeiDU suites.

Full campaign qualification still requires the scenarios under
`common/acceptance/`, including combat, advancement, inn rest and save/reload.
