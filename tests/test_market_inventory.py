import numpy as np
import pandas as pd
import pytest
from src.core import simulate_one,Policy

def cal(n):return pd.DataFrame({'date':pd.date_range('2015-01-01',periods=n),'snap':0,'event_flag':0})

def test_end_of_sales_keeps_full_target_coverage():
    y=np.ones(140)*3;l=simulate_one(y,cal(168),112,28,'moving_mean_28',Policy('rop',7,7),None,initial_units=0)
    assert (l.forecast_days==28).all() and (l.forecast_target_units==42).all()
    assert l.iloc[-1].target_coverage_days==14

def test_insufficient_known_calendar_fails_explicitly():
    with pytest.raises(ValueError,match='calendar'):simulate_one(np.ones(140),cal(140),112,28,'moving_mean_28',Policy('rop',7,7),None)

def test_po_arrivals_inventory_and_pipeline_conserve_each_day():
    l=simulate_one(np.arange(180)%7+2,cal(208),152,28,'moving_mean_28',Policy('rop',7,7),None,initial_units=0)
    for i,r in l.iterrows():
        assert r.ending_on_hand==r.opening_on_hand+r.arrivals-r.fulfilled
        assert r.demand==r.fulfilled+r.lost
        expected=0 if i<7 else l.iloc[i-7].ordered
        assert r.arrivals==expected
        prior=0 if i==0 else l.iloc[i-1].in_transit
        assert r.in_transit==prior+r.ordered-r.arrivals
        if r.ordered:assert pd.Timestamp(r.order_arrival_date)-pd.Timestamp(r.date)==pd.Timedelta(days=7)

def test_current_decision_ignores_current_and_future_sales():
    y=np.arange(180)%7+2;z=y.copy();z[152:]=999999
    a=simulate_one(y,cal(208),152,1,'moving_mean_28',Policy('rop',7,7),None,initial_units=0)
    b=simulate_one(z,cal(208),152,1,'moving_mean_28',Policy('rop',7,7),None,initial_units=0)
    assert a.iloc[0].ordered==b.iloc[0].ordered
