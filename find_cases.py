#!/usr/bin/env python
from __future__ import annotations

import sqlite3
import json

db = sqlite3.connect('meme_research.db')
db.row_factory = sqlite3.Row
c = db.cursor()

# Get counts
c.execute('''
SELECT metadata_confidence, COUNT(*) as cnt
FROM score_snapshots
GROUP BY metadata_confidence
ORDER BY cnt DESC
''')

print('Distribution by metadata_confidence:')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Get samples from each
cases = {}
for conf in ['confirmed', 'inferred', 'fallback', 'unverified']:
    c.execute('''
    SELECT token_address, token_symbol, token_name, metadata_confidence, 
           metadata_source, metadata_is_fallback, metadata_conflict,
           decision, principal_pair
    FROM score_snapshots
    WHERE metadata_confidence = ?
    LIMIT 1
    ''', (conf,))
    row = c.fetchone()
    if row:
        cases[conf] = dict(row)

print('\nExample tokens:')
for conf, token in cases.items():
    sym = token.get('token_symbol', 'N/A')
    dec = token.get('decision', 'N/A')
    addr = token.get('token_address', '')[:20]
    print(f'{conf}: {sym} ({dec}) - {addr}...')

print('\nJSON all cases:')
for conf, token in cases.items():
    print(f'\n# {conf}')
    print(json.dumps(token, indent=2, default=str)[:500])
