"""Verify the readable patch chain reverses to the exact retained Git baseline."""

from pathlib import Path
import hashlib, json

root = Path("vendor/keshif")
baseline = json.loads((root / "baseline.json").read_text())
source = (root / "keshif.js").read_text()
for patch in reversed(json.loads((root / "patches.json").read_text())):
    before, after = patch["before"], patch["after"]
    if source.count(after) != 1:
        raise RuntimeError(
            "Patch ledger no longer matches canonical source: " + after[:70]
        )
    source = source.replace(after, before)
assert hashlib.sha256(source.encode()).hexdigest() == baseline["sha256"]["keshif.js"], (
    "Canonical source differs from documented patches"
)
for name in ("vendor.js", "vendor_mapping.js", "keshif.css"):
    assert (
        hashlib.sha256((root / name).read_bytes()).hexdigest()
        == baseline["sha256"][name]
    ), name + " baseline changed"
print("Verified Keshif baseline and complete patch chain")
