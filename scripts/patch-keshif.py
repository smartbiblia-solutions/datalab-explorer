"""Apply the complete ledger ONLY to a restored original baseline file."""

from pathlib import Path
import json

p = Path("vendor/keshif/keshif.js")
source = p.read_text()
for patch in json.loads(Path("vendor/keshif/patches.json").read_text()):
    before, after = patch["before"], patch["after"]
    if source.count(before) != 1:
        raise RuntimeError(
            "Not the expected unpatched baseline/patch order: " + before[:70]
        )
    source = source.replace(before, after)
p.write_text(source)
