def build_reasons(features: dict, penalties: float, veto_reasons: list[str]) -> dict:
    positives = sorted(
        [
            ("momentum", features.get("momentum", 0.0)),
            ("technical_structure", features.get("technical_structure", 0.0)),
            ("volume_acceleration", features.get("volume_acceleration", 0.0)),
            ("liquidity_quality", features.get("liquidity_quality", 0.0)),
            ("wallet_flow", features.get("wallet_flow", 0.0)),
        ],
        key=lambda item: item[1],
        reverse=True,
    )

    risks = sorted(
        [
            ("overextension", features.get("overextension", 0.0)),
            ("momentum_loss", features.get("momentum_loss", 0.0)),
            ("distribution_signal", features.get("distribution_signal", 0.0)),
            ("market_risk_off", features.get("market_risk_off", 0.0)),
        ],
        key=lambda item: item[1],
        reverse=True,
    )

    return {
        "top_positive": positives[:3],
        "top_risks": risks[:2],
        "penalties": penalties,
        "veto_reasons": veto_reasons,
    }
