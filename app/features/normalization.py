def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ratio_capped(numerator: float, denominator: float, cap: float = 3.0) -> float:
    if denominator <= 0:
        return 0.0
    return min(cap, numerator / denominator) / cap
