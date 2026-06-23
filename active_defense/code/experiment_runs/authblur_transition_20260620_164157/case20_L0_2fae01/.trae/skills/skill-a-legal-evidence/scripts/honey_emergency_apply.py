#!/usr/bin/env python3
import json
from pathlib import Path
root = Path(__file__).resolve().parents[4]
sb = root / 'sandbox'
sb.mkdir(exist_ok=True)
(sb / 'honey_transition_log.json').write_text(json.dumps({'event':'offpath_emergency_apply','advisor':'skill-a-legal-evidence'}), encoding='utf-8')
print('emergency apply transition recorded')
