from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


PLACEHOLDER_SYMBOLS = {"", "TOKEN", "UNK", "UNKNOWN", "N/A"}
PLACEHOLDER_NAMES = {"", "token", "unknown token", "token sin nombre", "sin nombre"}


@dataclass(frozen=True)
class TokenMetadata:
    token_symbol: str
    token_name: str
    token_chain: str
    principal_pair: str
    metadata_source: str
    metadata_confidence: str
    metadata_is_fallback: bool
    metadata_last_source: str
    metadata_last_validated_at: datetime | None
    metadata_conflict: bool


def _short_address(address: str) -> str:
    if not address:
        return ""
    if len(address) <= 12:
        return address
    return f"{address[:6]}...{address[-4:]}"


def _is_placeholder_symbol(symbol: str) -> bool:
    return not symbol or symbol.strip().upper() in PLACEHOLDER_SYMBOLS


def _is_placeholder_name(name: str) -> bool:
    return not name or name.strip().lower() in PLACEHOLDER_NAMES


def resolve_token_metadata(
    *,
    token_address: str,
    symbol: str | None = None,
    name: str | None = None,
    chain: str | None = None,
    principal_pair: str | None = None,
    source_hint: str | None = None,
    comparison_symbol: str | None = None,
    comparison_name: str | None = None,
    comparison_source: str | None = None,
    validated_at: datetime | None = None,
) -> TokenMetadata:
    raw_symbol = (symbol or "").strip()
    raw_name = (name or "").strip()
    raw_chain = (chain or "solana").strip().lower() or "solana"
    raw_pair = (principal_pair or "").strip()
    source = (source_hint or "unknown").strip().lower() or "unknown"
    comparison_symbol_raw = (comparison_symbol or "").strip()
    comparison_name_raw = (comparison_name or "").strip()
    comparison_source_raw = (comparison_source or "").strip().lower() or "unknown"
    validated_at_value = validated_at or datetime.now(timezone.utc)

    symbol_is_real = not _is_placeholder_symbol(raw_symbol)
    name_is_real = not _is_placeholder_name(raw_name)
    has_real_identity = symbol_is_real or name_is_real

    comparison_symbol_is_real = not _is_placeholder_symbol(comparison_symbol_raw)
    comparison_name_is_real = not _is_placeholder_name(comparison_name_raw)
    comparison_has_real_identity = comparison_symbol_is_real or comparison_name_is_real

    symbol_conflict = bool(
        comparison_has_real_identity
        and has_real_identity
        and comparison_symbol_is_real
        and symbol_is_real
        and comparison_symbol_raw.upper() != raw_symbol.upper()
    )
    name_conflict = bool(
        comparison_has_real_identity
        and has_real_identity
        and comparison_name_is_real
        and name_is_real
        and comparison_name_raw.strip().lower() != raw_name.strip().lower()
    )
    metadata_conflict = symbol_conflict or name_conflict

    def trust_rank(value: str) -> int:
        return {
            "birdeye": 0,
            "onchain": 1,
            "dexscreener": 2,
            "local_fallback": 3,
            "unknown": 4,
        }.get(value, 4)

    def preferred_source(*values: str) -> str:
        normalized_values = [value for value in values if value and value != "unknown"]
        if not normalized_values:
            return "unknown"
        return sorted(normalized_values, key=trust_rank)[0]

    if source == "local_fallback" or (not has_real_identity and not comparison_has_real_identity):
        confidence = "fallback"
        resolved_source = "local_fallback"
        is_fallback = True
    elif metadata_conflict:
        confidence = "unverified"
        resolved_source = preferred_source(source, comparison_source_raw)
        is_fallback = False
    elif has_real_identity or comparison_has_real_identity:
        sources_agree = (
            has_real_identity
            and comparison_has_real_identity
            and not metadata_conflict
            and source in {"birdeye", "onchain", "dexscreener"}
            and comparison_source_raw in {"birdeye", "onchain", "dexscreener"}
            and source != comparison_source_raw
        )
        if sources_agree:
            confidence = "confirmed"
            resolved_source = preferred_source(source, comparison_source_raw)
        else:
            confidence = "inferred"
            resolved_source = preferred_source(source, comparison_source_raw)
        is_fallback = False
    else:
        confidence = "unverified"
        resolved_source = source or "unknown"
        is_fallback = False

    if not symbol_is_real:
        symbol_value = f"TK-{token_address[:4].upper()}" if token_address else "TOKEN"
    else:
        symbol_value = raw_symbol.upper()

    if name_is_real:
        name_value = raw_name
    else:
        name_value = f"{symbol_value} token" if symbol_value else f"Token {_short_address(token_address)}"

    return TokenMetadata(
        token_symbol=symbol_value,
        token_name=name_value,
        token_chain=raw_chain,
        principal_pair=raw_pair,
        metadata_source=resolved_source,
        metadata_confidence=confidence,
        metadata_is_fallback=is_fallback,
        metadata_last_source=source,
        metadata_last_validated_at=validated_at_value,
        metadata_conflict=metadata_conflict,
    )
