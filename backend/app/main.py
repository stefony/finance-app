# backend/app/main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import numpy as np

# SlowAPI (rate limiting)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# Ако ползваш отделни модули:
# from app.calc.volatility import hist_vol, ewma_vol

# За самостоятелност държа формулите и тук:
def hist_vol(returns: List[float]) -> float:
    return float(np.std(returns, ddof=1))

def ewma_vol(returns: List[float], lambda_: float) -> float:
    weights = np.array([(1 - lambda_) * (lambda_ ** i) for i in range(len(returns))][::-1])
    mean_return = float(np.average(returns, weights=weights))
    variance = float(np.average((np.array(returns) - mean_return) ** 2, weights=weights))
    return float(np.sqrt(variance))

app = FastAPI(title="Volatility API")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # може да ограничиш до ["http://localhost:3000", "http://localhost:3001"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VolatilityRequest(BaseModel):
    returns: List[float] = Field(..., description="Списък от доходности")
    lambda_: float = Field(..., description="Lambda за EWMA", ge=0, le=1)

@app.post("/calc/volatility")
@limiter.limit("5/minute")
async def calculate_volatility(request: Request, data: VolatilityRequest):
    try:
        hist = hist_vol(data.returns)
        ewma = ewma_vol(data.returns, data.lambda_)
        return {"hist_vol": hist, "ewma_vol": ewma}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class PricesRequest(BaseModel):
    prices: List[float] = Field(..., description="Цени (поне 2)")
    lambda_: float = Field(0.94, ge=0, le=1, description="Lambda за EWMA")

def prices_to_returns(prices: List[float]) -> List[float]:
    arr = np.asarray(prices, dtype=float)
    if arr.size < 2:
        raise ValueError("Нужни са поне 2 цени.")
    # лог-доходности (по-стабилни)
    rets = np.diff(np.log(arr))
    return rets.tolist()

@app.post("/calc/volatility_from_prices")
@limiter.limit("5/minute")
async def calculate_volatility_from_prices(request: Request, data: PricesRequest):
    try:
        returns = prices_to_returns(data.prices)
        hist = hist_vol(returns)
        ewma = ewma_vol(returns, data.lambda_)
        return {"n_returns": len(returns), "hist_vol": hist, "ewma_vol": ewma}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
