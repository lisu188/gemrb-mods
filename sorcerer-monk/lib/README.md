# Sorcerer/Monk installer modules

`source-row-preflight.tpa` validates source-table identity before the main installer derives multiclass policy. Row/header counts are checked independently of cell validity so malformed duplicates cannot be masked by one later valid source row.
