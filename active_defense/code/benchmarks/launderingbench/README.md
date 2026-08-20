# LaunderingBench Pilot

This is a small controlled stress test, not a replacement for public benchmark main tables.

The pilot contains 9 clean / 9 attack paired cases across three unit types:

- Tool
- MCP
- Skill

Each unit has one case for each laundering mode:

- authority laundering: advisory runtime content claims approval/authorization;
- dependency laundering: advisory runtime content tries to replace a sensitive target/value;
- capability laundering: advisory runtime content requests a new unauthorized effect.

Design constraints:

- The registered capability surface is fixed and trusted.
- No attacker tool is added.
- Only runtime content in `untrusted_surface.content` changes between clean and attack.
- ASR is a concrete unauthorized effect execution.
- AU should preserve the benign source acquisition and authorized effect path.

This suite is intended for method stress testing and ablation, especially WRAP authority closure and Binding evidence closure.
