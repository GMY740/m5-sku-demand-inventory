import numpy as np
import pandas as pd
import pytest
from src.market import match_prices,period_rollup,regional_comparison,price_association,price_events

def test_prices_join_uses_store_item_and_retail_week():
    m=pd.DataFrame({'store_id':['CA_1','TX_1'],'item_id':['a','a']})
    p=pd.DataFrame({'store_id':['CA_1','TX_1','CA_1'],'item_id':['a']*3,'wm_yr_wk':[1,1,2],'sell_price':[2.,7.,3.]})
    x=match_prices(m,p,np.array([1,1,2]));assert np.allclose(x[0],[2,2,3]);assert x[1,0]==7;assert np.isnan(x[1,2])

def test_missing_price_not_filled_from_future_or_invalid():
    m=pd.DataFrame({'store_id':['CA_1'],'item_id':['a']})
    p=pd.DataFrame({'store_id':['CA_1']*2,'item_id':['a']*2,'wm_yr_wk':[2,3],'sell_price':[5,0]})
    x=match_prices(m,p,np.array([1,2,3]));assert np.isnan(x[0,0]) and np.isnan(x[0,2])
    with pytest.raises(ValueError):match_prices(m,pd.concat([p,p]),[1])

def test_period_length_uses_daily_rate():
    d=pd.DataFrame({'state_id':'CA','store_id':'CA_1','cat_id':'F','dept_id':'F_1','date':['2016-01-31','2016-02-01','2016-02-02'],'units':[10,10,10],'sales_value':[20,20,20],'priced_units':[10,10,10]})
    r=period_rollup(d,'M');assert r.observed_days.tolist()==[1,2];assert r.units_per_day.tolist()==[10,10]

def test_region_normalizes_store_counts():
    s=pd.DataFrame({'state_id':['CA','CA','TX'],'store_id':['CA_1','CA_2','TX_1'],'cat_id':['F']*3,'dept_id':['F_1']*3,'units':[70]*3,'sales_value':[140]*3,'priced_units':[70]*3,'observed_days':[7]*3})
    r=regional_comparison(s);assert r.units.tolist()==[140,70];assert r.units_per_store_day.tolist()==[10,10]

def test_constant_prices_do_not_claim_sensitivity():
    g=pd.DataFrame({'date':pd.date_range('2015-01-01',periods=52,freq='7D'),'days':7,'sell_price':2.,'units':10.,'event_share':0,'snap_share':0})
    assert price_association(g)['status']=='insufficient_variation_or_sales'

def test_event_requires_isolated_complete_comparable_weeks():
    g=pd.DataFrame({'date':pd.date_range('2015-01-01',periods=10,freq='7D').strftime('%Y-%m-%d'),'days':7,'sell_price':[2]*5+[3]*5,'units':[70]*5+[140]*5,'event_share':0.,'snap_share':0.,'item_id':'a','store_id':'CA_1','state_id':'CA','cat_id':'F','dept_id':'F_1'})
    e=price_events(g);assert len(e)==1 and e.iloc[0].comparable;assert e.iloc[0].sales_change==1
    g.loc[6,'sell_price']=4;e=price_events(g);assert not e.comparable.any()


def test_missing_weeks_do_not_create_price_change_evidence():
    g=pd.DataFrame({"date":pd.date_range("2015-01-01",periods=30,freq="14D"),"days":7,"sell_price":np.where(np.arange(30)%2,3.,2.),"units":10.,"event_share":0.,"snap_share":0.})
    result=price_association(g)
    assert result["price_changes"]==0 and result["status"]=="insufficient_variation_or_sales"
