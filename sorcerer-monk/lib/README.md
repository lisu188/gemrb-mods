# Sorcerer/Monk installer modules

`source-row-preflight.tpa` validates component source-table identity after class/IDS identity guards and before the installer derives multiclass policy. Row/header counts are checked independently of cell validity so malformed duplicates cannot be masked by one later valid source row while established identity diagnostics keep precedence.
