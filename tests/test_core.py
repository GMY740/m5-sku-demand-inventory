import numpy as np
import pandas as pd
from src.core import wape,forecast,Policy,simulate_one,feature,make_abc_xyz


def calendar(n=150):
    d=pd.date_range('2015-01-01',periods=n)
    return pd.DataFrame(dict(date=d,snap=np.zeros(n),event_flag=np.zeros(n)))


def test_wape_weighted_abs():
    assert wape([2,8],[4,4])==0.6
    assert wape([0,0],[0,0]) is None


def test_recursion_no_future_leakage():
    a=np.arange(150,dtype=float)
    b=a.copy(); b[120:]=99999
    ca=calendar()
    x=forecast(a,ca,120,28,'seasonal_naive_7')
    y=forecast(b,ca,120,28,'seasonal_naive_7')
    assert np.allclose(x,y)


def test_moving_mean_no_future():
    a=np.ones(150,dtype=float)*3;ca=calendar()
    assert np.allclose(forecast(a,ca,100,28,'moving_mean_28'),3)


def test_abc_uses_only_pre_validation_history():
    items=pd.DataFrame([dict(item_id='a',cat_id='F',dept_id='F_1')])
    y=np.ones((1,150));cal=calendar()
    cal['wm_yr_wk']=np.arange(150)//7
    p=pd.DataFrame([dict(item_id='a',wm_yr_wk=i,sell_price=10) for i in range(22)])
    old=make_abc_xyz(items,y,cal,p,110)
    y[:,110:]=1000
    new=make_abc_xyz(items,y,cal,p,110)
    assert old.history_units.tolist()==new.history_units.tolist()
    assert old.history_value.tolist()==new.history_value.tolist()


def test_inventory_conservation_and_leadtime():
    y=np.ones(140)*3
    ca=calendar(168)
    log=simulate_one(y,ca,100,28,'seasonal_naive_7',Policy('weekly_cover',lead_days=7,review_days=7),None,initial_units=7)
    assert (log.ending_on_hand>=0).all()
    assert (log.fulfilled+log.lost==log.demand).all()
    assert (log.iloc[:7].arrivals==0).all() # first new PO cannot arrive before lead days
    for i,row in log.iterrows():
        begin=row.initial_units if i==0 else log.iloc[i-1].ending_on_hand
        assert row.ending_on_hand == begin+row.arrivals-row.fulfilled


def test_invalid_leadtime_rejected():
    try:
        simulate_one(np.ones(140),calendar(140),100,5,'moving_mean_28',Policy('rop',0,7),None)
    except ValueError:
        return
    assert False,'Must reject lead time zero'


def test_end_to_end_synthetic_fixture(tmp_path):
    from src.demo_data import build_demo
    from src.core import build_full_project
    raw=build_demo(tmp_path/'demo',n_items=6,days=180,seed=123)
    summ,tables=build_full_project(raw,tmp_path/'out',store='CA_1',top_n=4,source='demo')
    assert summ['data_kind'].startswith('SYNTHETIC DEMO')
    assert len(tables['forecast_metrics'])==6
    assert len(tables['inventory_scores'])==3
    assert sorted(tables['leadtime_sensitivity'].lead_days.unique().tolist())==[3,7,14]
    assert (tables['inventory_ledger'].ending_on_hand>=0).all()
    assert (tmp_path/'out'/'summary.json').exists()
