import numpy as np
import pandas as pd
import pytest
from src.market_dashboard import filter_frame,market_kpis
from src.market_forecast import summarize_predictions
from run_market import safe_output

def test_dashboard_filters_update_kpi_and_export_scope():
    d=pd.DataFrame({'state_id':['CA','CA','TX'],'store_id':['CA_1','CA_2','TX_1'],'cat_id':['F','H','F'],'item_id':['a','b','a'],'units':[10,20,30],'sales_value':[20,60,60],'priced_units':[10,20,30]})
    f=filter_frame(d,state='CA',cat='F',sku='a');k=market_kpis(f)
    assert len(f)==1 and k['units']==10 and k['sales_value']==20
    assert k['store_sku_count']==len(f) and k['coverage']==1

def test_forecast_filtered_metric_is_weighted_total_not_sku_average():
    d=pd.DataFrame({'stage':['test']*2,'method':['ridge']*2,'actual':[1,99],'prediction':[2,89]})
    r=summarize_predictions(d,['stage','method']).iloc[0]
    assert r.wape==.11 and r.mae==5.5

def test_market_output_guard_rejects_baseline_and_descendants(tmp_path):
    root=tmp_path
    with pytest.raises(ValueError):safe_output(root,root/'outputs/m5')
    with pytest.raises(ValueError):safe_output(root,root/'outputs/m5/extra')
    assert safe_output(root,root/'outputs/m5_market').exists()
