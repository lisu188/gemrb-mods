from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / "sorcerer-monk" / "setup-sorcerer-monk.tp2"
text = path.read_text(encoding="utf-8")

old = "PATCH_IF NOT (~%sm_luabbr_class%~ STRING_EQUAL_CASE ~SORCERER_MONK~) BEGIN"
new = "PATCH_IF !(~%sm_luabbr_class%~ STRING_EQUAL_CASE ~SORCERER_MONK~) BEGIN"
assert old in text
text = text.replace(old, new, 1)

old = "PATCH_IF NOT (IS_AN_INT ~%sm_thiefscl_value%~) BEGIN"
new = "PATCH_IF !(IS_AN_INT ~%sm_thiefscl_value%~) BEGIN"
assert old in text
text = text.replace(old, new, 1)

anchor = "// GemRB indexes several class-specific arrays directly with IE_CLASS and also\n"
insert = "INCLUDE ~sorcerer-monk/lib/source-row-preflight.tpa~\n\n" + anchor
assert anchor in text
text = text.replace(anchor, insert, 1)
path.write_text(text, encoding="utf-8")

Path(__file__).unlink()
workflow = root / ".github" / "workflows" / "sm-source-fix.yml"
workflow.unlink()
