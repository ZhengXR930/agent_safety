"""Authoritative MCPTox catalog extraction from the rendered system prompt."""
from __future__ import annotations

import re


_TOOL_BLOCK = re.compile(
    r"(?ms)^Tool:\s*([^\n]+)\n.*?"
    r"(?=\n{3}Tool:\s*|\n{3}Choose the appropriate tool|\Z)"
)


def catalog_blocks(system: str) -> dict[str, str]:
    """Return exact rendered tool blocks keyed by tool name."""
    return {
        match.group(1).strip(): match.group(0).rstrip()
        for match in _TOOL_BLOCK.finditer(system)
    }


def poisoned_tool_block(clean_system: str, attack_system: str) -> tuple[str, str]:
    """Recover the one injected block from authoritative rendered catalogs.

    ``response_all.json`` stores literal ``\\n`` in 646 ``poisoned_tool``
    convenience fields. The rendered ``system`` field is what MCPTox actually
    presents and is therefore the only authoritative replay source.
    """
    clean = catalog_blocks(clean_system)
    attack = catalog_blocks(attack_system)
    changed = [
        (name, block) for name, block in attack.items()
        if clean.get(name) != block
    ]
    if len(changed) != 1:
        raise ValueError(
            f"MCPTox row must change exactly one tool block, found {len(changed)}"
        )
    return changed[0]
