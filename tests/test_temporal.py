import numpy as np
import pandas as pd
from src.core import train_ridge,forecast,load_m5,make_abc_xyz

def test_ridge_training_and_recursion_ignore_future():
    n=220
    cal=pd.DataFrame({'date':pd.date_range('2015-01-01',periods=n),'snap':0,'event_flag':0})
    y=10+np.arange(n)%7
    other=y.copy();other[180:]=100000
    a=train_ridge(y,cal,180);b=train_ridge(other,cal,180)
    assert np.allclose(a[-1].coef_,b[-1].coef_)
    assert np.allclose(forecast(y,cal,180,28,'ridge',a),forecast(other,cal,180,28,'ridge',b))

def test_sku_selection_ignores_validation_and_test(tmp_path):
    from src.demo_data import build_demo
    raw=build_demo(tmp_path/'raw',n_items=8,days=220,seed=17)
    items,y,cal,prices,start=load_m5(raw,top_n=4)
    path=raw/'sales_train_validation.csv'
    sales=pd.read_csv(path)
    future=[f'd_{i+1}' for i in range(start,220)]
    sales[future]=999999
    sales.to_csv(path,index=False)
    altered,_,_,_,_=load_m5(raw,top_n=4)
    assert items.item_id.tolist()==altered.item_id.tolist()
