from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / "sorcerer-monk" / "setup-sorcerer-monk.tp2"
text = path.read_text(encoding="utf-8")
include = "INCLUDE ~sorcerer-monk/lib/source-row-preflight.tpa~\n\n"
assert text.count(include) == 1
text = text.replace(include, "", 1)
anchor = "// FISTWEAP rows are keyed only by numeric class ID. An existing row for the\n"
assert anchor in text
text = text.replace(anchor, include + anchor, 1)
path.write_text(text, encoding="utf-8")
Path(__file__).unlink()
(root / ".github" / "workflows" / "sm-preflight-order.yml").unlink()
