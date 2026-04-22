"""
New classification logic with integrated identity gate.
This module will replace parts of PlaybookScannerService._classify.
"""
from __future__ import annotations

from app.services.identity_gate_service import IdentityGate
from app.services.identity_quality_service import calculate_identity_quality_score
from app.services.token_metadata_service import TokenMetadata


def classify_with_identity_gate(
    token_address: str,
    symbol: str,
    score_long: float,
    score_short: float,
    confidence: float,
    risk_value: float,
    metadata: TokenMetadata,
    flags: dict,
    quality_score: int,
    market_bias_bearish: bool,
    context_degraded: bool,
    organic_flow_ok: bool,
    scanner_settings: dict,
) -> dict:
    """
    Clasifica un token considerando identidad como parte central de la decisión.

    Process:
    1. Calcula identity quality score
    2. Aplica identity gate rules
    3. Determina categoría final respetando gates
    4. Establece confidence cap basado en el gate
    5. Retorna clasificación con detalles de identidad

    Returns:
        dict con:
        - category: LONG ahora, SHORT, WATCHLIST (prioritaria/secundaria), NO TRADE, IGNORE
        - reason: razón principal
        - explanation: explicación larga
        - identity_quality_score: 0-100
        - identity_gate_reason: por qué el gate se disparó
        - identity_rule_applied: qué regla se aplicó
        - confidence_final: confidence después del cap
        - risk_adjusted: riesgo después del ajuste
    """

    # ===== PASO 1: Calcular identity quality score =====
    iq_result = calculate_identity_quality_score(metadata)
    identity_quality_score = iq_result["quality_score"]
    identity_warning = iq_result.get("warning")

    # ===== PASO 2: Aplica identity gate rules =====
    # Primero determinamos una "proposed decision" basada en scores
    if score_long >= scanner_settings.get("min_score_for_long", 65):
        proposed_decision = "LONG_SETUP"
    elif score_short >= scanner_settings.get("min_score_for_short", 60):
        proposed_decision = "SHORT_SETUP"
    elif score_long >= scanner_settings.get("min_score_for_long", 65) - 10:
        proposed_decision = "LONG_SETUP"
    else:
        proposed_decision = "WATCHLIST"

    gate_result = IdentityGate.apply_rules(metadata, proposed_decision, identity_quality_score)

    # ===== PASO 3: Determina categoría final respetando el gate =====
    # Primeros checks: calidad de datos, flags críticos
    if quality_score < scanner_settings.get("min_data_quality_score", 40):
        category = "NO TRADE"
        reason = "Calidad de datos insuficiente"
        explanation = "NO TRADE porque la calidad de datos en el escaneo actual es muy baja."
    elif flags.get("promo_flow_divergence") or flags.get("liquidity_fragile"):
        category = "NO TRADE"
        reason = "Promoción o liquidez frágil"
        explanation = "NO TRADE por flujo de atención pagada elevada sin base orgánica o liquidez inestable."
    elif flags.get("insufficient_pair_quality"):
        category = "IGNORE"
        reason = "Par principal de baja calidad"
        explanation = "IGNORE porque no hay un par principal de trading confiable en DExes principales."
    # ===== Si el identity gate rechazó la propuesta =====
    elif not gate_result.allowed:
        modified_decision = gate_result.modified_decision
        if "NO TRADE" in modified_decision:
            category = "NO TRADE"
            explanation = f"{gate_result.reason}. {gate_result.rule_applied}"
        elif "WATCHLIST_PRIORITARIA" in modified_decision:
            category = "WATCHLIST prioritaria"
            explanation = f"Identidad limitada a watchlist por: {gate_result.reason}"
        elif "WATCHLIST_SECUNDARIA" in modified_decision:
            category = "WATCHLIST secundaria"
            explanation = f"Identidad limitada a watchlist por: {gate_result.reason}"
        else:
            category = modified_decision
            explanation = gate_result.reason

        reason = f"IDENTITY GATE: {gate_result.rule_applied}"

    # ===== Flojo normal si el gate permitió =====
    elif (
        score_long >= scanner_settings.get("min_score_for_long", 65)
        and confidence >= scanner_settings.get("min_confidence_for_long", 0.65)
        and risk_value <= scanner_settings.get("max_risk_for_long", 25)
        and not market_bias_bearish
        and not flags.get("suspicious_vertical_pump")
        and organic_flow_ok
        and not context_degraded
    ):
        category = "LONG ahora"
        reason = "Score long alto + identidad permitida + contexto favorable"
        explanation = (
            f"LONG ahora: score_long={score_long:.1f}, confidence={confidence:.2f}, "
            f"risk={risk_value:.1f}, identity={metadata.metadata_confidence} (allowed), "
            f"organic flow confirmed, sin red flags graves."
        )
    elif (
        score_short >= scanner_settings.get("min_score_for_short", 60)
        and confidence >= scanner_settings.get("min_confidence_for_short", 0.60)
        and risk_value <= scanner_settings.get("max_risk_for_short", 30)
        and (market_bias_bearish or flags.get("suspicious_vertical_pump"))
    ):
        category = "SHORT solo paper"
        reason = "Setup bajista / agotamiento + score short alto"
        explanation = (
            f"SHORT solo paper: score_short={score_short:.1f}, confidence={confidence:.2f}, "
            f"market_bias_bearish={market_bias_bearish}, pump_exhaustion={flags.get('suspicious_vertical_pump')}."
        )
    elif (
        score_long >= scanner_settings.get("min_score_for_long", 65) - 8
        and confidence >= scanner_settings.get("min_confidence_for_long", 0.65) - 0.1
        and risk_value <= scanner_settings.get("max_risk_for_long", 25) + 6
        and organic_flow_ok
    ):
        category = "WATCHLIST prioritaria"
        reason = "Estructura buena, espera punto de entrada"
        explanation = (
            f"WATCHLIST prioritaria: estructura sólida (score_long={score_long:.1f}, "
            f"organic_flow=true) pero falta confirmación de timing o faltan condiciones para operar ya."
        )
    elif (
        score_long >= scanner_settings.get("min_score_for_long", 65) - 16
        or score_short >= scanner_settings.get("min_score_for_short", 60) - 14
    ):
        category = "WATCHLIST secundaria"
        reason = "Potencial visible, menos urgencia"
        explanation = (
            f"WATCHLIST secundaria: scores moderados (long={score_long:.1f}, short={score_short:.1f}) "
            f"but menos clarity para acción inmediata."
        )
    else:
        category = "IGNORE"
        reason = "Sin edge estadístico claro"
        explanation = "IGNORE por falta de ventaja clara en score, confianza y estructura combinada."

    # ===== PASO 5: Ajustar confidence final según caps de identity =====
    confidence_final = confidence * gate_result.confidence_cap

    # ===== Ajustar riesgo si hay conflicto =====
    risk_adjusted = risk_value
    if metadata.metadata_conflict:
        risk_adjusted = min(100, risk_value * 1.2)  # +20% de riesgo por conflicto

    return {
        "category": category,
        "reason": reason,
        "explanation": explanation,
        "identity_quality_score": identity_quality_score,
        "identity_warning": identity_warning,
        "identity_gate_reason": gate_result.reason,
        "identity_rule_applied": gate_result.rule_applied,
        "confidence_final": confidence_final,
        "confidence_original": confidence,
        "confidence_cap": gate_result.confidence_cap,
        "risk_adjusted": risk_adjusted,
        "risk_original": risk_value,
    }
