"""
Identity Quality Score Service
================================
Calcula un score agnostical (0-100) basado en la calidad y confiabilidad
de la identidad del token, impactando directamente en las decisiones del scanner.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.token_metadata_service import TokenMetadata


def calculate_identity_quality_score(metadata: TokenMetadata) -> dict:
    """
    Calcula un score de calidad de identidad (0-100) con penalidades y bonificaciones.

    Args:
        metadata: TokenMetadata con todos los campos de provenance.

    Returns:
        dict con:
        - quality_score: 0-100
        - base_score: puntuación según confidence
        - penalties: dict de penalidades aplicadas
        - bonuses: dict de bonificaciones aplicadas
        - warning: str si hay algo crítico
    """
    score = 100
    base_score = 0
    penalties = {}
    bonuses = {}

    # ===== 1. BASE SCORE según metadata_confidence =====
    if metadata.metadata_confidence == "confirmed":
        base_score = 85
    elif metadata.metadata_confidence == "inferred":
        base_score = 65
    elif metadata.metadata_confidence == "fallback":
        base_score = 25
    elif metadata.metadata_confidence == "unverified":
        base_score = 10
    else:
        base_score = 5

    # ===== 2. PENALIDAD: conflicto entre fuentes =====
    if metadata.metadata_conflict:
        penalties["conflict"] = -25
    else:
        penalties["conflict"] = 0

    # ===== 3. PENALIDAD: frescura de validación =====
    if metadata.metadata_last_validated_at:
        now = datetime.now(timezone.utc)
        minutes_ago = (now - metadata.metadata_last_validated_at).total_seconds() / 60

        if minutes_ago > 7 * 24 * 60:  # más de 7 días
            penalties["freshness"] = -20
        elif minutes_ago > 24 * 60:  # más de 24 horas
            penalties["freshness"] = -10
        elif minutes_ago > 6 * 60:  # más de 6 horas
            penalties["freshness"] = -5
        else:
            penalties["freshness"] = 0
    else:
        penalties["freshness"] = -10

    # ===== 4. PENALIDAD: si es fallback local =====
    if metadata.metadata_is_fallback:
        penalties["fallback_local"] = -30
    else:
        penalties["fallback_local"] = 0

    # ===== 5. PENALIDAD: source desconocida =====
    if metadata.metadata_source == "unknown":
        penalties["unknown_source"] = -20
    elif metadata.metadata_source == "local_fallback":
        penalties["unknown_source"] = -15
    else:
        penalties["unknown_source"] = 0

    # ===== 6. BONIFICACIÓN: confirmed + reciente =====
    if (
        metadata.metadata_confidence == "confirmed"
        and penalties.get("freshness", 0) == 0
        and not metadata.metadata_conflict
    ):
        bonuses["confirmed_fresh"] = +10
    else:
        bonuses["confirmed_fresh"] = 0

    # ===== 7. BONIFICACIÓN: inferred pero muy fresco =====
    if (
        metadata.metadata_confidence == "inferred"
        and metadata.metadata_last_validated_at
    ):
        now = datetime.now(timezone.utc)
        minutes_ago = (now - metadata.metadata_last_validated_at).total_seconds() / 60
        if minutes_ago < 2 * 60:  # menos de 2 horas
            bonuses["inferred_fresh"] = +5
        else:
            bonuses["inferred_fresh"] = 0
    else:
        bonuses["inferred_fresh"] = 0

    # ===== Calcular score final =====
    total_penalties = sum(penalties.values())
    total_bonuses = sum(bonuses.values())

    quality_score = base_score + total_penalties + total_bonuses
    quality_score = max(0, min(100, quality_score))  # clamp 0-100

    # ===== Determinar warning crítico =====
    warning = None
    if quality_score < 20:
        warning = "Identity quality critically low"
    elif metadata.metadata_conflict:
        warning = "Source conflict detected"
    elif metadata.metadata_is_fallback:
        warning = "Synthetic local identity"

    return {
        "quality_score": int(quality_score),
        "base_score": base_score,
        "penalties": penalties,
        "bonuses": bonuses,
        "total_adjustment": total_penalties + total_bonuses,
        "warning": warning,
        "recommendation": _get_recommendation(quality_score, metadata),
    }


def _get_recommendation(score: float, metadata: TokenMetadata) -> str:
    """
    Retorna una recomendación de uso según el score y la identidad.
    """
    if metadata.metadata_confidence == "confirmed":
        if score >= 80:
            return "Full confidence, standard classification"
        else:
            return "Confirmed pero con algunos concerns"
    elif metadata.metadata_confidence == "inferred":
        if score >= 70:
            return "Inferred y reciente, puede ser LONG con muy buenos otros factores"
        else:
            return "Inferred pero antiguo o con concerns, preferir watchlist"
    elif metadata.metadata_confidence == "fallback":
        return "Identidad fallback - bloquear LONG_SETUP, máximo watchlist prioritaria"
    elif metadata.metadata_confidence == "unverified":
        return "Identidad no verificada - máximo watchlist secundaria"
    else:
        return "Unknown confidence level"
