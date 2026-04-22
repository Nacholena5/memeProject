#!/usr/bin/env python
from __future__ import annotations

import requests
import json

r = requests.get('http://127.0.0.1:8000/signals/latest?limit=20').json()

print('Latest signals (full):')
for s in r[:20]:
    sym = s.get('token_symbol', 'NONE')
    conf = s.get('metadata_confidence', 'NONE')
    dec = s.get('decision', 'NONE')
    addr = s.get('token_address', '')[:15]
    print(f'  {sym:15} conf={conf:12} decision={dec:20} addr={addr}...')

# Look for our synthetic tokens
print('\nSearching for synthetic tokens:')
for name in ['SOLAR', 'TK-FB11', 'BOME', 'TOKEN']:
    found = [s for s in r if s.get('token_symbol') == name]
    if found:
        f = found[0]
        print(f'  Found {name}: {f.get("metadata_confidence")}')
    else:
        print(f'  NOT FOUND: {name}')
