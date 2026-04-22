#!/usr/bin/env python
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

db = sqlite3.connect('meme_research.db')
c = db.cursor()

# Insert synthetic confirmed case
c.execute('''
INSERT INTO score_snapshots (
    token_address, ts, entry_price, long_score, short_score, confidence, 
    penalties, veto, decision, reasons_json, features_json,
    token_symbol, token_name, token_chain, principal_pair,
    metadata_source, metadata_confidence, metadata_is_fallback, metadata_last_source,
    metadata_last_validated_at, metadata_conflict
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'So1ar4EVw4bKCaKgaKWWWZX7kKEbLoTHSEAWE6cV1Z9',  # synthetic confirmed address
    datetime.now(timezone.utc),
    0.5,
    0.75, 0.25, 0.85,
    0.0, False, 'LONG_SETUP',
    '{"reason": "strong_confirmed_identity"}',
    '{}',
    'SOLAR', 'Solar Network', 'solana', 'SOLAR/USDC',
    'dexscreener', 'confirmed', False, 'dexscreener',
    datetime.now(timezone.utc), False
))

# Insert synthetic fallback case
c.execute('''
INSERT INTO score_snapshots (
    token_address, ts, entry_price, long_score, short_score, confidence, 
    penalties, veto, decision, reasons_json, features_json,
    token_symbol, token_name, token_chain, principal_pair,
    metadata_source, metadata_confidence, metadata_is_fallback, metadata_last_source,
    metadata_last_validated_at, metadata_conflict
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'FB11ac4EVw4bKCaKgaKWWWZX7kKEbLoTHSEAWE6cABCD',  # synthetic fallback address
    datetime.now(timezone.utc),
    0.02,
    0.35, 0.65, 0.15,
    0.1, False, 'WATCHLIST_SPECULATIVE',
    '{"reason": "fallback_local_only"}',
    '{}',
    'TK-FB11', 'TK-FB11 token', 'solana', '',
    'local_fallback', 'fallback', True, 'local_fallback',
    datetime.now(timezone.utc), False
))

db.commit()
print('Synthetic cases inserted:')
print('- confirmed: SOLAR (Solar Network)')
print('- fallback: TK-FB11 (local_fallback synthetic)')
