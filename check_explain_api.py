#!/usr/bin/env python
from __future__ import annotations

import requests
import json

# Get detailed info via /tokens/{address}/explain
cases = {
    'confirmed': 'So1ar4EVw4bKCaKgaKWWWZX7kKEbLoTHSEAWE6cV1Z9',
    'fallback': 'FB11ac4EVw4bKCaKgaKWWWZX7kKEbLoTHSEAWE6cABCD',
    'unverified': 'Fh3hFf3d3a2f9kLw9D3xQ8M9h2a1z0meme11111'
}

for case_name, addr in cases.items():
    try:
        r = requests.get(f'http://127.0.0.1:8000/tokens/{addr}/explain').json()
        print(f'\n{case_name.upper()}:')
        print(f'  symbol: {r.get("token_symbol")}')
        print(f'  name: {r.get("token_name")}')
        print(f'  confidence: {r.get("metadata_confidence")}')
        print(f'  source: {r.get("metadata_source")}')
        print(f'  source_last: {r.get("metadata_last_source")}')
        print(f'  is_fallback: {r.get("metadata_is_fallback")}')
        print(f'  decision: {r.get("decision")}')
        print(f'  principal_pair: {r.get("principal_pair")}')
    except Exception as e:
        print(f'{case_name}: ERROR - {e}')
