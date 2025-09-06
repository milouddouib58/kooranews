# -*- coding: utf-8 -*-
import math
from typing import Dict, List, Tuple, Optional

def implied_from_decimal(odds: Dict[str, float]) -> Dict[str, float]:
    # يحوّل أودز عشرية إلى احتمالات ضمنية p_i = 1/odds_i
    out = {}
    for k, v in (odds or {}).items():
        try:
            v = float(v)
            out[k] = 0.0 if v <= 1.0 else 1.0 / v
        except Exception:
            pass
    return out

def normalize_proportional(imps: Dict[str, float]) -> Dict[str, float]:
    s = sum(max(0.0, float(v)) for v in imps.values())
    if s <= 0:
        return {k: 0.0 for k in imps.keys()}
    return {k: max(0.0, float(v)) / s for k, v in imps.items()}

def shin_fair_probs(imps: Dict[str, float], tol: float = 1e-9, max_iter: int = 200) -> Dict[str, float]:
    """
    تطبيق طريقة Shin لإزالة هامش الربح (overround).
    q_i = implied probs = 1/odds_i
    s_i(z) = (sqrt(z^2 + 4(1-z) q_i) - z) / (2(1-z)), ابحث عن z بحيث sum s_i = 1
    """
    qs = {k: max(1e-12, float(v)) for k, v in imps.items() if v is not None}
    if not qs:
        return {}
    def s_i(q, z):
        denom = max(1e-12, 2.0 * (1.0 - z))
        return max(0.0, (math.sqrt(z*z + 4.0*(1.0 - z)*q) - z) / denom)

    # بيسكشن على z ∈ [0, z_max)؛ عادة z صغير (<0.2)
    lo, hi = 0.0, 0.2
    # وسّع hi إذا احتجت
    def f(z):
        return sum(s_i(q, z) for q in qs.values()) - 1.0

    if f(0.0) <= 0:
        # لا حاجة لإزالة قوية
        return normalize_proportional(qs)

    while f(hi) > 0 and hi < 0.95:
        hi *= 1.5
        if hi > 0.95:
            hi = 0.95
            break

    z = hi
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        val = f(mid)
        if abs(val) < tol:
            z = mid
            break
        if val > 0:
            lo = mid
        else:
            hi = mid
        z = mid
    fair = {k: s_i(q, z) for k, q in qs.items()}
    s = sum(fair.values())
    if s > 0:
        fair = {k: v / s for k, v in fair.items()}
    return fair

def overround(imps: Dict[str, float]) -> float:
    return max(0.0, sum(max(0.0, float(v)) for v in imps.values()) - 1.0)

def kelly_fraction(p: float, odds_dec: float) -> Optional[float]:
    try:
        if p is None or odds_dec is None or odds_dec <= 1.0:
            return None
        b = odds_dec - 1.0
        return max(0.0, (p*odds_dec - 1.0) / b)
    except Exception:
        return None

def kelly_suggestions(probs: Dict[str, float], odds: Dict[str, float],
                      bankroll: float = 100.0, kelly_scale: float = 0.25, min_edge: float = 0.01) -> Dict[str, Dict]:
    out = {}
    for k, o in (odds or {}).items():
        try:
            o = float(o)
            p = float(probs.get(k, 0.0))
            if o <= 1.0 or p <= 0.0:
                continue
            implied = 1.0 / o
            edge = p - implied
            if edge < min_edge:
                continue
            k_full = kelly_fraction(p, o)
            if k_full is None or k_full <= 0:
                continue
            k_scaled = min(k_full, 0.25) * kelly_scale
            stake = round(bankroll * k_scaled, 2)
            out[k] = {
                "prob": round(p, 4),
                "odds": round(o, 3),
                "implied": round(implied, 4),
                "edge": round(edge, 4),
                "kelly_full": round(k_full, 4),
                "kelly_scaled": round(k_scaled, 4),
                "stake": stake
            }
        except Exception:
            continue
    return out

def aggregate_prices(prices: List[float], mode: str = "median") -> Optional[float]:
    arr = [float(x) for x in prices if isinstance(x, (int, float)) and float(x) > 1.0]
    if not arr:
        return None
    arr.sort()
    if mode == "best":
        return max(arr)
    if mode == "mean":
        return sum(arr)/len(arr)
    # median default
    n = len(arr)
    mid = n // 2
    return (arr[mid] if n % 2 == 1 else 0.5*(arr[mid-1] + arr[mid]))