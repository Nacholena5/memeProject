#!/usr/bin/env python
from __future__ import annotations

import requests
import json

base = 'http://127.0.0.1:8000'

signals = requests.get(f'{base}/signals/latest?limit=200').json()

# Group by confidence 
by_conf = {}
for s in signals[:200]:
    conf = s.get('metadata_confidence', 'unknown')
    if conf not in by_conf:
        by_conf[conf] = []
    if len(by_conf[conf]) < 3:
        by_conf[conf].append({
            'addr': s.get('token_address'),
            'symbol': s.get('symbol'),
            'name': s.get('name'),
            'source': s.get('metadata_source'),
            'decision': s.get('decision'),
            'confidence': conf
        })

result = {}
for conf, items in sorted(by_conf.items()):
    if items:
        result[conf] = items[0]

print(json.dumps(result, indent=2))
