# Shared GemRB mod infrastructure

`common/` contains implementation shared by otherwise independent GemRB class mods. It owns reusable installer/runtime mechanisms; class rules remain in `psion/`, `cipher/`, and `sorcerer-monk/`.

The GUI layer has one owner (`GemRBModCore`) and dispatches to optional class handlers. Transactions, reusable innate charges, persistent actor-effect state, selector helpers, and WeiDU SPL/ITM constructors live here rather than under a particular class.

The compatibility shims under individual mods are intentional so third-party code that included an older helper path continues to work.
