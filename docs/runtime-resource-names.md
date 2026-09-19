# Native rule-table resource names

GemRB resolves game resources through eight-character references. Descriptive
source table filenames are retained in each package, but installation uses the
following distinct runtime IDs. Debug-console `GemRB.LoadTable()` calls must use
the short ID, without the `.2da` extension.

| Source table stem | Installed/runtime stem |
| --- | --- |
| psionpool | pspool |
| psionknown | psknown |
| psiondisc | psdisc |
| psionskills | psskills |
| psionfeats | psfeats |
| psionfeatpick | psfeatpk |
| psionpowers | pspowers |
| psionaugment | psaugmnt |
| cipherpowers | cipowers |
| cipherknown | ciknown |
| cipherfocus | cifocus |

Other table IDs already fit and are unchanged. Build generators continue to
read the descriptive source files. The late Cipher item component reads
`cifocus.2da`, matching the main component's installed metadata.

`python3 common/tests/validate_runtime_resrefs.py` checks installed destinations,
collisions, every literal runtime table lookup, and actual Python runtime
access through a synthetic loader that truncates names like the native engine.
The Psion and Cipher runtime suites also use eight-character table resolution.
These checks do not replace real-engine acceptance.
