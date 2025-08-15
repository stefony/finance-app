from typing import List
import math

def ewma_vol(returns: List[float], lam: float = 0.94) -> float:
    var_t = 0.0
    for r in returns:
        var_t = lam * var_t + (1 - lam) * (r ** 2)
    return math.sqrt(var_t)

def hist_vol(returns: List[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return math.sqrt(var)
