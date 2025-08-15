# backend/app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import numpy as np

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware


# ---- Волатилност: базови функции ----
def hist_vol(returns: List[float]) -> float:
    return float(np.std(returns, ddof=1))

def ewma_vol(returns: List[float], lambda_: float) -> float:
    weights = np.array([(1 - lambda_) * (lambda_ ** i) for i in range(len(returns))][::-1])
    mean_return = float(np.average(returns, weights=weights))
    variance = float(np.average((np.array(returns) - mean_return) ** 2, weights=weights))
    return float(np.sqrt(variance))


# ---- Риск функции ----
def historical_var(returns: List[float], confidence_level: float = 0.95) -> float:
    """
    Исторически Value at Risk: персентил на разпределението
    Отрицателен резултат = загуба
    """
    percentile = (1 - confidence_level) * 100
    return float(np.percentile(returns, percentile))

def historical_cvar(returns: List[float], confidence_level: float = 0.95) -> float:
    """
    Conditional VaR (Expected Shortfall)
    Средна загуба при резултати под VaR
    """
    var_value = historical_var(returns, confidence_level)
    losses = [r for r in returns if r <= var_value]
    return float(np.mean(losses)) if losses else var_value


# ---- APP конфигурация ----
app = FastAPI(title="Volatility API + VaR/CVaR")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Models ----
class FullVolatilityRequest(BaseModel):
    prices: List[float] = Field(..., description="Списък с цени (поне 2)")
    lambda_: float = Field(0.94, ge=0, le=1, description="Lambda за EWMA")
    confidence_level: float = Field(0.95, ge=0.5, le=0.999, description="Доверително ниво за VaR/CVaR")


# ---- Helper ----
def prices_to_returns(prices: List[float]) -> List[float]:
    arr = np.asarray(prices, dtype=float)
    if arr.size < 2:
        raise ValueError("Нужни са поне 2 цени.")
    return np.diff(np.log(arr)).tolist()


# ---- Endpoint ----
@app.post("/calc/volatility_full")
@limiter.limit("5/minute")
async def calculate_full_volatility(request: Request, data: FullVolatilityRequest):
    """
    Професионален вариант:
    - Приема само prices
    - Автоматично изчислява доходности
    - Връща HistVol, EWMA, VaR, CVaR
    """
    try:
        returns = prices_to_returns(data.prices)

        hist = hist_vol(returns)
        ewma = ewma_vol(returns, data.lambda_)
        var_value = historical_var(returns, data.confidence_level)
        cvar_value = historical_cvar(returns, data.confidence_level)

        return {
            "n_prices": len(data.prices),
            "n_returns": len(returns),
            "lambda_used": data.lambda_,
            "confidence_level": data.confidence_level,
            "hist_vol": hist,
            "ewma_vol": ewma,
            "VaR": var_value,
            "CVaR": cvar_value,
            "returns_sample": returns[:5]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- RUN ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
