"""Game-family-safe text used by custom-class character generation."""

BACK = "Back"
DONE = "Done"
MULTI_CLASS = "Multi-Class"
SPECIALIST_MAGE = "Specialist Mage"
CHOOSE_CLASS = "Choose a class."
CHOOSE_ALIGNMENT = "Choose an alignment."
CHOOSE_PROFICIENCIES = "Choose weapon proficiencies."
PSION_DISCIPLINE = "PSION DISCIPLINE"
CHOOSE_PSION_DISCIPLINE = "Choose a Psion discipline."

CUSTOM_CLASS_ROWS = frozenset((
    "CIPHER",
    "SORCERER_MONK",
    "PSION_SEER",
    "PSION_SHAPER",
    "PSION_KINETICIST",
    "PSION_EGOIST",
    "PSION_NOMAD",
    "PSION_TELEPATH",
))


def is_custom_class(row_name):
    return str(row_name or "").upper() in CUSTOM_CLASS_ROWS
