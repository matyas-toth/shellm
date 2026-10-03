"""Registry of table-driven command families merged into the intent engine."""

from . import files, shellutils, text

SPECS = {}
for module in (text, files, shellutils):
    duplicates = SPECS.keys() & module.SPECS.keys()
    if duplicates:
        raise ValueError(f"Command defined twice: {sorted(duplicates)}")
    SPECS.update(module.SPECS)
