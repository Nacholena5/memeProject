"""
Identity Gate Service
======================
Aplica las reglas duras de clasificación basadas en identidad.
Actúa como gatekeeper entre scoring y decisión final.
"""
from __future__ import annotations

from app.services.token_metadata_service import TokenMetadata


class IdentityGateResult:
    """Resultado de aplicar el identity gate."""

    def __init__(
        self,
        allowed: bool,
        modified_decision: str,
        reason: str,
        rule_applied: str | None,
        confidence_cap: float,
    ):
        self.allowed = allowed
        self.modified_decision = modified_decision
        self.reason = reason
        self.rule_applied = rule_applied
        self.confidence_cap = confidence_cap

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "modified_decision": self.modified_decision,
            "reason": self.reason,
            "rule_applied": self.rule_applied,
            "confidence_cap": self.confidence_cap,
        }


class IdentityGate:
    """
    Motor de reglas duras basado en identidad.
    Estas reglas son no-negociables y se aplican antes de la clasificación final.
    """

    @staticmethod
    def apply_rules(
        metadata: TokenMetadata,
        proposed_decision: str,
        quality_score: int,
    ) -> IdentityGateResult:
        """
        Aplica todas las reglas de identidad al decision propuesto.

        Args:
            metadata: TokenMetadata con provenance completo
            proposed_decision: decisión propuesta por el clasificador
            quality_score: score calculado por IdentityQualityService (0-100)

        Returns:
            IdentityGateResult con decision final, razón y caps de confianza
        """

        # === REGLA A: FALLBACK ===
        if metadata.metadata_confidence == "fallback":
            return IdentityGate._apply_rule_a_fallback(proposed_decision, quality_score)

        # === REGLA B: UNVERIFIED ===
        if metadata.metadata_confidence == "unverified":
            return IdentityGate._apply_rule_b_unverified(proposed_decision)

        # === REGLA C: CONFLICT ===
        if metadata.metadata_conflict:
            return IdentityGate._apply_rule_c_conflict(proposed_decision)

        # === REGLA D: INFERRED ===
        if metadata.metadata_confidence == "inferred":
            return IdentityGate._apply_rule_d_inferred(proposed_decision, quality_score)

        # === REGLA E: CONFIRMED ===
        if metadata.metadata_confidence == "confirmed":
            return IdentityGate._apply_rule_e_confirmed(proposed_decision)

        # Sin restricciones de identidad
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="No identity-based restrictions",
            rule_applied=None,
            confidence_cap=1.0,
        )

    @staticmethod
    def _apply_rule_a_fallback(proposed_decision: str, quality_score: int) -> IdentityGateResult:
        """
        REGLA A: Identidad fallback (local, sintética)
        - NO permitir LONG_SETUP / LONG_AHORA
        - NO permitir SHORT_SOLO_PAPER si riesgo general es alto
        - Opciones: WATCHLIST_PRIORITARIA, WATCHLIST_SECUNDARIA, NO_TRADE
        """
        if proposed_decision in ["LONG_SETUP", "LONG_AHORA", "LONG_PAPER"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="WATCHLIST_PRIORITARIA",
                reason="Fallback identity (local/synthetic) cannot be LONG_SETUP",
                rule_applied="RULE_A_FALLBACK_NO_LONG",
                confidence_cap=0.35,
            )

        if proposed_decision in ["SHORT_SOLO_PAPER", "SHORT_PAPEL"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="WATCHLIST_PRIORITARIA",
                reason="Fallback identity cannot be SHORT_SOLO_PAPER",
                rule_applied="RULE_A_FALLBACK_NO_SHORT_PAPER",
                confidence_cap=0.35,
            )

        # SHORT_SETUP es aceptable si score es decente
        if proposed_decision in ["SHORT_SETUP", "SHORT_AHORA"]:
            if quality_score < 25:
                return IdentityGateResult(
                    allowed=False,
                    modified_decision="WATCHLIST_PRIORITARIA",
                    reason="Fallback identity with very low quality score cannot be SHORT_SETUP",
                    rule_applied="RULE_A_FALLBACK_LOW_SCORE",
                    confidence_cap=0.35,
                )

        # WATCHLIST o NO_TRADE: permitido
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="Fallback identity allows watchlist/no-trade",
            rule_applied="RULE_A_FALLBACK_WATCHLIST",
            confidence_cap=0.35,
        )

    @staticmethod
    def _apply_rule_b_unverified(proposed_decision: str) -> IdentityGateResult:
        """
        REGLA B: Identidad no verificada
        - NO permitir LONG_SETUP / LONG_AHORA
        - NO permitir SHORT_SOLO_PAPER
        - Máximo: WATCHLIST_SECUNDARIA o NO_TRADE
        """
        if proposed_decision in ["LONG_SETUP", "LONG_AHORA", "LONG_PAPER"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="WATCHLIST_SECUNDARIA",
                reason="Unverified identity cannot be LONG_SETUP",
                rule_applied="RULE_B_UNVERIFIED_NO_LONG",
                confidence_cap=0.25,
            )

        if proposed_decision in ["SHORT_SOLO_PAPER", "SHORT_PAPER"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="NO_TRADE",
                reason="Unverified identity cannot be SHORT_SOLO_PAPER",
                rule_applied="RULE_B_UNVERIFIED_NO_SHORT_PAPER",
                confidence_cap=0.15,
            )

        if proposed_decision in ["SHORT_SETUP", "SHORT_AHORA"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="WATCHLIST_SECUNDARIA",
                reason="Unverified identity, SHORT_SETUP not allowed",
                rule_applied="RULE_B_UNVERIFIED_NO_SHORT_SETUP",
                confidence_cap=0.20,
            )

        # WATCHLIST_SECUNDARIA o NO_TRADE: permitido
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="Unverified identity allows secondary watchlist",
            rule_applied="RULE_B_UNVERIFIED_DEFAULT",
            confidence_cap=0.25,
        )

    @staticmethod
    def _apply_rule_c_conflict(proposed_decision: str) -> IdentityGateResult:
        """
        REGLA C: Conflicto entre fuentes
        - Penalización fuerte: subir riesgo, bajar confianza
        - Bloquear LONG_SETUP salvo override explícito (no implementado aquí)
        - Preferencia por NO_TRADE o watchlist
        """
        if proposed_decision in ["LONG_SETUP", "LONG_AHORA", "LONG_PAPER"]:
            return IdentityGateResult(
                allowed=False,
                modified_decision="WATCHLIST_PRIORITARIA",
                reason="Source conflict: metadata from different sources disagree - cannot be LONG_SETUP",
                rule_applied="RULE_C_CONFLICT_NO_LONG",
                confidence_cap=0.40,
            )

        # SHORT: tolerado pero con penalización
        if proposed_decision in ["SHORT_SETUP", "SHORT_AHORA", "SHORT_SOLO_PAPER"]:
            return IdentityGateResult(
                allowed=True,
                modified_decision=proposed_decision,
                reason="Source conflict reduces confidence for SHORT setup",
                rule_applied="RULE_C_CONFLICT_SHORT_CAP",
                confidence_cap=0.45,
            )

        # Watchlist u otros: permitido
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="Source conflict - confidence capped",
            rule_applied="RULE_C_CONFLICT_CAP",
            confidence_cap=0.50,
        )

    @staticmethod
    def _apply_rule_d_inferred(proposed_decision: str, quality_score: int) -> IdentityGateResult:
        """
        REGLA D: Identidad inferida
        Permite LONG_SETUP solo si:
        - score alto (>=70)
        - propuesta es efectivamente LONG_SETUP
        - de lo contrario, watchlist
        """
        if proposed_decision in ["LONG_SETUP", "LONG_AHORA", "LONG_PAPER"]:
            if quality_score >= 70:
                # Permitir pero con cap de confianza
                return IdentityGateResult(
                    allowed=True,
                    modified_decision=proposed_decision,
                    reason="Inferred identity with good quality score allows LONG_SETUP",
                    rule_applied="RULE_D_INFERRED_LONG_OK",
                    confidence_cap=0.75,
                )
            else:
                # Muy bajo score, rechazar LONG
                return IdentityGateResult(
                    allowed=False,
                    modified_decision="WATCHLIST_PRIORITARIA",
                    reason="Inferred identity with low quality score - must be watchlist",
                    rule_applied="RULE_D_INFERRED_LOW_SCORE",
                    confidence_cap=0.50,
                )

        # SHORT: permitido con cap
        if proposed_decision in ["SHORT_SETUP", "SHORT_AHORA", "SHORT_SOLO_PAPER"]:
            return IdentityGateResult(
                allowed=True,
                modified_decision=proposed_decision,
                reason="Inferred identity allows SHORT with reduced confidence",
                rule_applied="RULE_D_INFERRED_SHORT",
                confidence_cap=0.65,
            )

        # Watchlist: permitido
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="Inferred identity - watchlist allowed",
            rule_applied="RULE_D_INFERRED_DEFAULT",
            confidence_cap=0.70,
        )

    @staticmethod
    def _apply_rule_e_confirmed(proposed_decision: str) -> IdentityGateResult:
        """
        REGLA E: Identidad confirmada (cross-source verified)
        - Permitir flujo normal
        - Sin caps específicos por identidad
        - Otros factores (riesgo, líquidez, etc) siguen siendo relevantes
        """
        return IdentityGateResult(
            allowed=True,
            modified_decision=proposed_decision,
            reason="Confirmed identity - no identity-based restrictions",
            rule_applied="RULE_E_CONFIRMED_ALLOWED",
            confidence_cap=1.0,
        )
