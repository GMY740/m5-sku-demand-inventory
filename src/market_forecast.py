"""Fixed-protocol price-feature experiment. Test is never used for selection."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from .core import feature,train_ridge,forecast,wape,METHODS
from .market import match_prices,save_table

PRICE_METHOD='ridge_price_history'

def historical_price_features(history):
    """Only strictly past prices. No backward fill from first future price."""
    p=np.asarray(history,float);p=np.where(np.isfinite(p)&(p>0),p,np.nan)
    valid=p[np.isfinite(p)];last=float(valid[-1]) if len(valid) else 0.
    recent=p[-28:];known=recent[np.isfinite(recent)]
    average=float(known.mean()) if len(known) else 0.
    return np.array([np.log1p(last),last/average-1 if average else 0.,float(np.isnan(recent).mean()) if len(recent) else 1.])

class PriceRidge:
    def __init__(self,reg,prices):self.reg=reg;self.prices=np.asarray(prices,float)
    def forecast(self,series,cal,origin,horizon):
        h=list(map(float,series[:origin]));ph=list(map(float,self.prices[:origin]))
        known=[p for p in ph if np.isfinite(p) and p>0];frozen=known[-1] if known else np.nan
        predictions=[]
        for day in range(origin,origin+horizon):
            x=np.r_[feature(h,day,cal),historical_price_features(ph)]
            pred=max(0.,float(self.reg.predict(x[None,:])[0]));predictions.append(pred)
            h.append(pred);ph.append(frozen) # assumed persistence, never actual future prices
        return np.array(predictions)

def train_price_ridge(series,cal,prices,cutoff):
    earliest=max(56,cutoff-560)
    X=np.stack([np.r_[feature(series[:t],t,cal),historical_price_features(prices[:t])] for t in range(earliest,cutoff)])
    reg=make_pipeline(StandardScaler(),Ridge(alpha=15.0));reg.fit(X,np.asarray(series[earliest:cutoff],float))
    return PriceRidge(reg,prices)

def summarize_predictions(pred,keys):
    rows=[]
    for key,g in pred.groupby(keys,observed=True):
        if not isinstance(key,tuple):key=(key,)
        row=dict(zip(keys,key));row.update(wape=wape(g.actual,g.prediction),mae=float(np.abs(g.actual-g.prediction).mean()),
            evaluated_item_days=len(g),actual_units=float(g.actual.sum()));rows.append(row)
    return pd.DataFrame(rows)

def run_experiment(items,y,cal,prices,start,out,baseline):
    out=Path(out);base=Path(baseline);frozen=pd.read_csv(base/'items.csv')
    if items.item_id.tolist()!=frozen.item_id.tolist():raise ValueError('Original30 SKU order differs; experiment stopped')
    p=match_prices(items,prices,cal.iloc[:y.shape[1]].wm_yr_wk.to_numpy())
    methods=list(METHODS)+[PRICE_METHOD];records=[];regs={m:{} for m in ['ridge',PRICE_METHOD]};chosen=None
    for stage,origins in [('validation',[start,start+28]),('test',[start+56])]:
        for origin in origins:
            for i,it in items.iterrows():
                a=train_ridge(y[i],cal,origin);b=train_price_ridge(y[i],cal,p[i],origin)
                if stage=='test':regs['ridge'][it.item_id]=a;regs[PRICE_METHOD][it.item_id]=b
                for method in methods:
                    pred=b.forecast(y[i],cal,origin,28) if method==PRICE_METHOD else forecast(y[i],cal,origin,28,method,a)
                    for j,pr in enumerate(pred):records.append(dict(stage=stage,origin=str(cal.iloc[origin].date.date()),date=str(cal.iloc[origin+j].date.date()),
                        d_idx=origin+j,item_id=it.item_id,cat_id=it.cat_id,method=method,actual=float(y[i,origin+j]),prediction=float(pr)))
        if stage=='validation':
            metrics=summarize_predictions(pd.DataFrame(records),['stage','method'])
            chosen=metrics.sort_values(['wape','method']).iloc[0].method
            selection={'version':'m5_market_v1','selection_basis':'Two validation folds aggregate WAPE only; frozen before test calculation',
                'selected_method':chosen,'alpha':15.,'price_features':['log1p_last_known','last_to_past28_mean','past28_missing_share'],
                'future_price_assumption':'Freeze last strictly pre-origin known price across recursive forecast; cold start0 plus missing flag',
                'candidate_C':'Not searched: fixed B protocol, no test-driven feature tuning','test_status':'Same already published2016 test, subsequent comparison; not pristine unseen research holdout',
                'validation_metrics':metrics.to_dict('records')}
            (out/'model_selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
    pred=pd.DataFrame(records);metrics=summarize_predictions(pred,['stage','method'])
    sku=summarize_predictions(pred,['stage','method','cat_id','item_id']);category=summarize_predictions(pred,['stage','method','cat_id'])
    original=pd.read_csv(base/'forecast_predictions.csv')
    keys=['stage','origin','date','item_id','method'];joint=original.merge(pred,on=keys,suffixes=('_old','_new'),validate='one_to_one')
    maxdiff=float(np.abs(joint.prediction_old-joint.prediction_new).max())
    if len(joint)!=len(original) or maxdiff>1e-8:raise ValueError(f'Original forecast reproduction mismatch {maxdiff}')
    delta=sku[sku.method=='ridge'].merge(sku[sku.method==PRICE_METHOD],on=['stage','cat_id','item_id'],suffixes=('_ridge','_price'),validate='one_to_one')
    delta['wape_change_pp']=(delta.wape_price-delta.wape_ridge)*100
    delta['mae_change']=delta.mae_price-delta.mae_ridge
    for name,df in {'forecast_predictions':pred,'forecast_metrics':metrics,'forecast_sku_metrics':sku,'forecast_category_metrics':category,'forecast_price_deltas':delta}.items():save_table(out,name,df)
    check={'original_prediction_rows':len(joint),'original_max_abs_difference':maxdiff,'selection':chosen,
        'validation_item_days_per_method':30*56,'test_item_days_per_method':30*28}
    (out/'forecast_verification.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
    return chosen,regs
