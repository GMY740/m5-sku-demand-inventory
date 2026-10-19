import numpy as np
import pandas as pd
from src.market_forecast import historical_price_features,train_price_ridge

def fixture():
    n=240;cal=pd.DataFrame({'date':pd.date_range('2015-01-01',periods=n),'snap':0,'event_flag':0})
    y=10+np.arange(n)%7;prices=2.+(np.arange(n)//28)*.1
    return y,cal,prices

def test_price_model_training_and_forecast_ignore_future_sales_and_price():
    y,c,p=fixture();z=y.copy();q=p.copy();z[180:]=999999;q[180:]=99999
    a=train_price_ridge(y,c,p,180);b=train_price_ridge(z,c,q,180)
    assert np.allclose(a.reg[-1].coef_,b.reg[-1].coef_)
    assert np.allclose(a.forecast(y,c,180,28),b.forecast(z,c,180,28))

def test_price_cold_start_does_not_backward_fill():
    x=historical_price_features([np.nan]*60);assert np.allclose(x,[0,0,1])
    y,c,p=fixture();p[:180]=np.nan;r=train_price_ridge(y,c,p,180)
    assert np.isfinite(r.forecast(y,c,180,28)).all()

def test_price_model_uses_historical_prices():
    y,c,p=fixture();a=train_price_ridge(y,c,p,180);x=a.forecast(y,c,180,28)
    assert len(x)==28 and (x>=0).all()
