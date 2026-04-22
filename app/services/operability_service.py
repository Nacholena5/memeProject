"""
Operability Classification Service
===================================
Define la elegibilidad operativa real de una señal.

SEPARA:
- "Señal fuerte del modelo" (score alto)
- "Token realmente operable" (cumple mínimos operativos)

Categorías finales:
- OPERABLE: puede tradear ahora mismo
- WATCHLIST: interesante pero no listo
- BLOQUEADO: score bueno pero veto por riesgos
- NO_TRADE: descartar

El objetivo es ELIMINAR confusión visual.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OperabilityClassification:
    """Resultado de clasificación de elegibilidad operativa."""
    status: str  # operable | watchlist | bloqueado | no_trade
    reason: str  # Por qué tiene este status
    can_long: bool  # Puede abrir LONG
    can_short: bool  # Puede abrir SHORT
    blocker: str | None  # Si es bloqueado, cuál es el motivo principal
    why_not: str | None  # Explicación para usuario final


class OperabilityService:
    """Clasifica si un token es realmente operable o solo una buena señal."""

    @staticmethod
    def classify(
        *,
        decision: str,  # LONG_SETUP | SHORT_SETUP | IGNORE
        veto: bool,
        score_long: float,
        score_short: float,
        confidence: float,
        metadata_confidence: str,  # confirmed | inferred | fallback | unverified
        metadata_is_fallback: bool,
        risk_label: str,  # bajo | medio | alto
        liquidity_usd: float,
        identity_quality_score: int,  # 0-100
        veto_reasons: list[str] | None = None,
        data_quality_degraded: bool = False,
    ) -> OperabilityClassification:
        """
        Clasifica si el token es operable según criterios operativos reales.
        
        Reglas:
        1. Identidad fallback/unverified → máximo WATCHLIST
        2. Riesgo alto → máximo WATCHLIST o BLOQUEADO
        3. Liquidez baja → WATCHLIST o BLOQUEADO
        4. Data quality degradada → máximo WATCHLIST
        5. Veto activo → BLOQUEADO
        
        OPERABLE requiere:
        - decision LONG_SETUP o SHORT_SETUP (no IGNORE)
        - sin veto
        - identidad confirmed o inferred
        - riesgo bajo o medio
        - liquidez suficiente (>= 150k USD)
        - data quality OK
        - confidence >= 0.72
        """
        
        veto_reasons = veto_reasons or []
        blocker = None
        why_not = None
        
        # === PASO 1: VETO ABSOLUTO ===
        if veto:
            blocker = veto_reasons[0] if veto_reasons else "veto_general"
            return OperabilityClassification(
                status="bloqueado",
                reason=f"Veto por {blocker}",
                can_long=False,
                can_short=False,
                blocker=blocker,
                why_not=f"Sistema bloqueó por: {blocker}. Revisar drawer para detalle.",
            )
        
        # === PASO 2: IDENTIDAD FALLBACK/UNVERIFIED ===
        # Nunca pueden ser OPERABLE, máximo WATCHLIST
        if metadata_confidence in {"fallback", "unverified"}:
            why_not = f"Identidad {metadata_confidence} (no confirmada). Necesita validación manual."
            
            if decision == "LONG_SETUP" and score_long >= 68:
                # Buen score pero identidad débil
                return OperabilityClassification(
                    status="watchlist",
                    reason="Señal fuerte pero identidad no confirmada",
                    can_long=False,
                    can_short=False,
                    blocker="identity_unconfirmed",
                    why_not=why_not,
                )
            elif decision == "SHORT_SETUP" and score_short >= 65:
                return OperabilityClassification(
                    status="watchlist",
                    reason="Señal bajista pero identidad no confirmada",
                    can_long=False,
                    can_short=False,
                    blocker="identity_unconfirmed",
                    why_not=why_not,
                )
            else:
                return OperabilityClassification(
                    status="no_trade",
                    reason="Identidad débil + score bajo",
                    can_long=False,
                    can_short=False,
                    blocker="identity_unconfirmed",
                    why_not=why_not,
                )
        
        # === PASO 3: RIESGO ALTO ===
        if risk_label == "alto":
            why_not = "Riesgo evaluado como alto por el sistema"
            
            if decision == "LONG_SETUP" and score_long >= 72:
                return OperabilityClassification(
                    status="bloqueado",
                    reason="Score fuerte pero riesgo alto",
                    can_long=False,
                    can_short=False,
                    blocker="high_risk",
                    why_not=why_not,
                )
            elif decision == "SHORT_SETUP" and score_short >= 70:
                return OperabilityClassification(
                    status="bloqueado",
                    reason="Short fuerte pero riesgo alto",
                    can_long=False,
                    can_short=False,
                    blocker="high_risk",
                    why_not=why_not,
                )
            else:
                return OperabilityClassification(
                    status="no_trade",
                    reason="Riesgo alto",
                    can_long=False,
                    can_short=False,
                    blocker="high_risk",
                    why_not=why_not,
                )
        
        # === PASO 4: DATA QUALITY DEGRADADA ===
        if data_quality_degraded:
            why_not = "Calidad de datos degradada; cambios pendientes en datasets"
            
            if decision in {"LONG_SETUP", "SHORT_SETUP"}:
                return OperabilityClassification(
                    status="watchlist",
                    reason="Señal válida pero data quality degradada",
                    can_long=False,
                    can_short=False,
                    blocker="data_quality",
                    why_not=why_not,
                )
            else:
                return OperabilityClassification(
                    status="no_trade",
                    reason="Sin señal + data degradada",
                    can_long=False,
                    can_short=False,
                    blocker="data_quality",
                    why_not=why_not,
                )
        
        # === PASO 5: LIQUIDEZ INSUFICIENTE ===
        # Umbral operativo mínimo: 150k USD
        if liquidity_usd < 150_000:
            why_not = f"Liquidez solo {liquidity_usd:,.0f} USD (mínimo 150k)"
            
            if decision == "LONG_SETUP" and score_long >= 70:
                return OperabilityClassification(
                    status="watchlist",
                    reason="Señal buena pero liquidez frágil",
                    can_long=False,
                    can_short=False,
                    blocker="low_liquidity",
                    why_not=why_not,
                )
            elif decision == "SHORT_SETUP" and score_short >= 67:
                return OperabilityClassification(
                    status="watchlist",
                    reason="Short válida pero liquidez frágil",
                    can_long=False,
                    can_short=False,
                    blocker="low_liquidity",
                    why_not=why_not,
                )
            else:
                return OperabilityClassification(
                    status="no_trade",
                    reason="Liquidez insuficiente",
                    can_long=False,
                    can_short=False,
                    blocker="low_liquidity",
                    why_not=why_not,
                )
        
        # === PASO 6: CONFIDENCE INSUFICIENTE ===
        if confidence < 0.72:
            why_not = f"Confianza {confidence:.2f} (mínimo 0.72)"
            
            if decision in {"LONG_SETUP", "SHORT_SETUP"}:
                return OperabilityClassification(
                    status="watchlist",
                    reason="Señal presente pero confianza media",
                    can_long=False,
                    can_short=False,
                    blocker="low_confidence",
                    why_not=why_not,
                )
            else:
                return OperabilityClassification(
                    status="no_trade",
                    reason="Sin señal clara",
                    can_long=False,
                    can_short=False,
                    blocker=None,
                    why_not=None,
                )
        
        # === PASO 7: ES OPERABLE ===
        # Pasó todos los filtros
        if decision == "LONG_SETUP":
            return OperabilityClassification(
                status="operable",
                reason="Cumple todos los mínimos operativos para LONG",
                can_long=True,
                can_short=False,
                blocker=None,
                why_not=None,
            )
        elif decision == "SHORT_SETUP":
            return OperabilityClassification(
                status="operable",
                reason="Cumple todos los mínimos operativos para SHORT",
                can_long=False,
                can_short=True,
                blocker=None,
                why_not=None,
            )
        else:
            # IGNORE
            return OperabilityClassification(
                status="no_trade",
                reason="Sin setup claro",
                can_long=False,
                can_short=False,
                blocker=None,
                why_not=None,
            )
