"""Independent saved-output reconciliation; writes only market verification."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .market import sha256
from .market_inventory import score_ledger
from .market_forecast import summarize_predictions

def verify_market(out,base,raw=None):
    out=Path(out);base=Path(base);load=lambda n:pd.read_csv(out/f'{n}.csv')
    m=json.loads((out/'market_manifest.json').read_text(encoding='utf-8'));d=load('category_daily');t=load('item_demand_trends');s=load('category_structure')
    recent=d[d.date.between(m['analysis_start'],m['analysis_end'])]
    for col in ['units','sales_value','priced_units']:
        assert np.isclose(recent[col].sum(),s[col].sum()),col
        assert np.isclose(t[col].sum(),s[col].sum()),col
    assert len(t)==m['sales_rows'];assert not t.duplicated(['store_id','item_id']).any()
    assert set(t.state_id)=={'CA','TX','WI'} and t.store_id.nunique()==10
    assert (t.missing_price_sales_units>=0).all();assert np.allclose(t.priced_units+t.missing_price_sales_units,t.units)
    r=load('regional_category_comparison');assert np.allclose(r.groupby('state_id').category_unit_share.sum(),1)
    assert np.allclose(r.units_per_store_day,r.units/r.store_count/r.observed_days)
    assert np.isclose(r.sales_value.sum(),t.sales_value.sum())
    old=json.loads((base.parent.parent/'audit/market_upgrade/before_files.json').read_text(encoding='utf-8'))
    protected=[k for k in old if k.startswith('outputs/m5/')]
    for name in protected:assert sha256(base.parent.parent/name)==old[name],name
    checks={'version':m['version'],'market_reconciliation':True,'store_sku_rows':len(t),'baseline_unchanged_files':len(protected),
        'analysis_units':float(t.units.sum()),'analysis_sales_value':float(t.sales_value.sum()),'analysis_unpriced_units':float(t.missing_price_sales_units.sum())}
    if (out/'forecast_predictions.csv').exists():
        pr=load('forecast_predictions');met=load('forecast_metrics');calc=summarize_predictions(pr,['stage','method'])
        j=met.merge(calc,on=['stage','method'],suffixes=('_saved','_calc'),validate='one_to_one')
        for col in ['wape','mae','evaluated_item_days']:assert np.allclose(j[col+'_saved'],j[col+'_calc'])
        for _,g in pr.groupby(['stage','method']):assert len(g)==(1680 if g.stage.iloc[0]=='validation' else 840)
        checks['forecast_metrics_reconciled']=True
    if (out/'inventory_ledger.csv').exists():
        ledger=load('inventory_ledger')
        for (lead,policy,item),g in ledger.groupby(['lead_days','policy','item_id']):
            g=g.sort_values('date').reset_index(drop=True)
            assert np.allclose(g.ending_on_hand,g.opening_on_hand+g.arrivals-g.fulfilled)
            assert np.allclose(g.fulfilled+g.lost,g.demand)
            assert np.allclose(g.arrivals,g.ordered.shift(int(lead),fill_value=0))
            assert np.allclose(g.in_transit,g.in_transit.shift(1,fill_value=0)+g.ordered-g.arrivals)
            assert (g.forecast_days>=g.target_coverage_days).all()
            assert np.allclose(g.opening_on_hand.iloc[1:],g.ending_on_hand.iloc[:-1])
        for (lead,item,date),g in ledger.groupby(['lead_days','item_id','date']):
            assert g.initial_units.nunique()==1 and g.demand.nunique()==1
        met=load('inventory_scores')
        for lead,g in ledger.groupby('lead_days'):
            a=score_ledger(g);b=met[met.lead_days==lead];j=a.merge(b,on='policy',suffixes=('_calc','_saved'))
            for col in ['simulation_fill_rate','avg_ending_on_hand','total_ordered_units','po_events']:assert np.allclose(j[col+'_calc'],j[col+'_saved'])
        checks['inventory_rows_conserved']=len(ledger);checks['strategy_fairness']=True
    if (out/'inventory_candidate_ledger.csv').exists():
        log=load('inventory_candidate_ledger')
        for (policy,item),g in log.groupby(['policy','item_id']):
            g=g.sort_values('date').reset_index(drop=True);lead=int(g.lead_days.iloc[0])
            assert np.allclose(g.ending_on_hand,g.opening_on_hand+g.arrivals-g.fulfilled)
            assert np.allclose(g.arrivals,g.ordered.shift(lead,fill_value=0))
            assert np.allclose(g.in_transit,g.in_transit.shift(1,fill_value=0)+g.ordered-g.arrivals)
            assert np.allclose(g.fulfilled+g.lost,g.demand)
        a=load('classification').sort_values('item_id');b=pd.read_csv(base/'classification.csv').sort_values('item_id')
        assert a.abc_xyz.tolist()==b.abc_xyz.tolist()
        assert np.allclose(a.history_value,b.history_value)
        checks['candidate_inventory_rows_conserved']=len(log)
        checks['inventory_classification_equals_prevalidation_baseline']=True
    if raw is not None and (Path(raw)/m['sales_file']).exists():
        source=Path(raw)/m['sales_file']
        daycols=sorted([c for c in pd.read_csv(source,nrows=0).columns if c.startswith('d_') and c[2:].isdigit()],key=lambda c:int(c[2:]))[-m['analysis_days']:]
        independent=[]
        for chunk in pd.read_csv(source,usecols=['state_id','store_id','cat_id','dept_id']+daycols,chunksize=1000):
            meta=chunk[['state_id','store_id','cat_id','dept_id']].copy();meta['units']=chunk[daycols].sum(axis=1)
            independent.append(meta.groupby(['state_id','store_id','cat_id','dept_id']).units.sum())
        actual=pd.concat(independent).groupby(level=[0,1,2,3]).sum().reset_index()
        joined=actual.merge(s,on=['state_id','store_id','cat_id','dept_id'],suffixes=('_source','_output'),validate='one_to_one')
        assert len(joined)==len(s) and np.allclose(joined.units_source,joined.units_output)
        for name,info in m['source_files'].items():assert sha256(Path(raw)/name)==info['sha256']
        checks['official_source_independent_unit_reconciliation']=True
    (out/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8');return checks
