# Real chargen controller

`common/tools/run_chargen_matrix.py` drives one character through the installed
BGEE/BG2EE `bg2` GUI scripts. It observes controls through the private console
described in [README.md](README.md) and sends actual `xdotool` mouse/keyboard
events. It requires `xdotool` and ImageMagick's `import` on the host, an idle
disposable game process, and exclusive ownership of that process's display.

Start at the character-generation overview or a supported chargen dialog:

```sh
python3 common/tools/run_chargen_matrix.py \
  --session /private/session --display :121 \
  --xauthority /private/display.xauth --output /private/evidence \
  --class psion-seer --name Acceptance --mode all
```

Class choices are `fighter`, `cipher`, `sorcerer-monk`, and `psion-` followed by
`seer`, `shaper`, `kineticist`, `egoist`, `nomad`, or `telepath`. The character
uses male/Human/lawful-neutral choices, the current portrait and colours, and
the default soundset. The controller uses class-table rows and live control
positions, checks that controls are visible/enabled, and stops if the focused
dialog is ambiguous. It never sets class/stats/GUI variables or calls chargen
callbacks through the console.

`--minimum-roll N` requests real rerolls (at most 100), and
`--min-intelligence N` moves legally available points using real plus/minus
buttons. Defaults accept the initial legal roll, never an injected all-18
build. Skill/proficiency allocation and arcane spell selection use the actual
enabled controls. Unsupported selectors or unallocatable points stop the run;
inspect the evidence instead of treating the stop as a pass.

`--mode inspect` observes without sending input. The default `--mode next`
advances one dialog action and reports only `staged`; it is a debugging helper,
not a resumable acceptance run. Use `--mode all` for the completion gate. Every
invocation writes a unique child directory below `--output`, preserving prior
actions, screenshots, and `controller-report.json` rather than overwriting them.

An `ui-complete` report requires that the same invocation clicked final Accept,
observed the expected class/kit/race/alignment/sex in gameplay, and observed a
new or updated native quicksave (slot 4 in ToB, slot 1 otherwise) after the real quicksave key (`q`, configurable with
`--quicksave-key`). Chapter-introduction Done is clicked through its observed
control; arbitrary cutscenes, conversations, or save restrictions are not
bypassed. `--timeout`, `--max-actions`, and `--delay` bound waits and progression.
The optional `--engine-log` stops progression if that log contains a traceback
or an explicit GUI runtime error;
use a fresh log, not one containing earlier diagnostic failures.

Each checkpoint contains observed identity and the independent installed-table
oracle captured before selection. A correct identity alone does not certify
all gameplay: engine-log classification, action/spell behavior, progression,
rest/save/reload, and HLA scenarios remain separate acceptance gates.

Synthetic safety checks (no display or game data required):

```sh
python3 common/tests/validate_chargen_controller.py
```
