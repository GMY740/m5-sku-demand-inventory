import pandas as pd
from src.market_report import store_day_rates

def test_store_day_rates_handles_unequal_coverage_and_departments():
    # Two departments on one day must not inflate the store-day denominator;
    # store B has no second day, so stores * union-days would also be wrong.
    d=pd.DataFrame({'cat_id':['FOODS']*4,'period':['2016-05']*4,
                    'store_id':['A','A','A','B'],'date':['2016-05-01','2016-05-01','2016-05-02','2016-05-01'],
                    'units':[10.,20.,30.,60.],'sales_value':[20.,40.,60.,120.]})
    r=store_day_rates(d,['cat_id','period']).iloc[0]
    assert r.observed_store_days==3
    assert r.units_per_store_day==40
    assert r.sales_value==240
