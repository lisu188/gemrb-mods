# Shared GemRB mod infrastructure

`common/` contains implementation shared by otherwise independent GemRB class mods. It owns reusable installer/runtime mechanisms; class rules remain in `psion/`, `cipher/`, and `sorcerer-monk/`.

The compatibility shims under individual mods are intentional so third-party code that included an older helper path continues to work.
