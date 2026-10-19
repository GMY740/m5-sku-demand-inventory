"""Leakage-aware retail forecasting and inventory policy backtest.

Original sales/calendar/price fields follow the Kaggle M5 Forecasting Accuracy schema.
True M5 sales are observed; inventory, lead times and purchase decisions are simulated.
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON=28
METHODS=('seasonal_naive_7','moving_mean_28','ridge')


def wape(actual, pred):
    actual=np.asarray(actual,float); pred=np.asarray(pred,float)
    denom=float(np.abs(actual).sum())
    return float(np.abs(actual-pred).sum()/denom) if denom>0 else None


def load_m5(raw:Path,store:str='CA_1',top_n:int=30,horizon:int=28):
    raw=Path(raw); sp=raw/'sales_train_evaluation.csv'
    if not sp.is_file():sp=raw/'sales_train_validation.csv'
    if not sp.is_file():raise FileNotFoundError(f'Need sales_train_validation.csv or sales_train_evaluation.csv in {raw}')
    calendar=pd.read_csv(raw/'calendar.csv'); price_path=raw/'sell_prices.csv'
    if not price_path.is_file():raise FileNotFoundError(f'Need complete sell_prices.csv in {raw}')
    daycols=[x for x in pd.read_csv(sp,nrows=0).columns if x.startswith('d_') and x[2:].isdigit()]
    if len(daycols)<3*horizon+75:raise ValueError('Insufficient days to run chronological validation/test')
    daycols.sort(key=lambda s:int(s[2:]))
    # Only use the common, contiguous days in sales and calendar.
    cal=calendar.set_index('d').loc[daycols].reset_index()
    # Retain official known future calendar, not future observed sales or prices.
    extra=calendar.loc[calendar['d'].map(lambda x:int(str(x)[2:])>len(daycols))].copy()
    cal=pd.concat([cal,extra],ignore_index=True)
    cal['date']=pd.to_datetime(cal['date'])
    state=store.split('_')[0]; snap_name=f'snap_{state}'
    if snap_name not in cal:raise ValueError(f'Missing calendar {snap_name}')
    cal['event_flag']=cal[['event_name_1','event_name_2']].notna().any(axis=1).astype(int)
    cal['snap']=cal[snap_name].fillna(0).astype(int)
    numdays=len(daycols); first_validation=numdays-3*horizon
    select_start=max(0,first_validation-364)
    meta=['item_id','dept_id','cat_id','store_id','state_id']
    chunks=[]
    for part in pd.read_csv(sp,chunksize=300,usecols=meta+daycols):
        chosen=part.loc[part['store_id']==store]
        if not chosen.empty: chunks.append(chosen)
    if not chunks:raise ValueError(f'No rows found for store {store}')
    all_items=pd.concat(chunks,ignore_index=True)
    if all_items.duplicated(['store_id','item_id']).any(): raise ValueError('Duplicate store/item entries')
    raw_y=all_items[daycols].to_numpy(dtype=np.float32)
    volume=raw_y[:,select_start:first_validation].sum(axis=1)
    recent=raw_y[:,first_validation-56:first_validation].sum(axis=1)
    eligible=np.where((volume>=20)&(recent>0))[0]
    if not len(eligible):raise ValueError('No active series meet pre-validation selection criteria')
    order=sorted(eligible,key=lambda i:(-volume[i],str(all_items.iloc[i]['item_id'])))[:top_n]
    items=all_items.iloc[order][meta].reset_index(drop=True)
    values=raw_y[order].astype(float)
    if (values<0).any() or not np.isfinite(values).all():raise ValueError('Unexpected negative/nonfinite historical sales')
    price_rows=[]
    if price_path.exists():
        for chunk in pd.read_csv(price_path,chunksize=150000,usecols=['store_id','item_id','wm_yr_wk','sell_price']):
            c=chunk.loc[(chunk.store_id==store)&(chunk.item_id.isin(set(items.item_id)))]
            if not c.empty:price_rows.append(c)
    prices=pd.concat(price_rows,ignore_index=True) if price_rows else pd.DataFrame(columns=['store_id','item_id','wm_yr_wk','sell_price'])
    if len(prices) and prices.duplicated(['store_id','item_id','wm_yr_wk']).any():
        raise ValueError('Nonunique M5 price row per store-item-week')
    return items,values,cal,prices,first_validation


def feature(history, day:int,cal:pd.DataFrame):
    if len(history)<56:raise ValueError('Require 56 historical daily observations')
    h=np.asarray(history,float)
    dt=cal.iloc[day]
    return np.array([h[-1],h[-7],h[-14],h[-28],h[-56],
        h[-7:].mean(),h[-28:].mean(),h[-7:].mean()-h[-28:].mean(),
        np.std(h[-28:]),int(dt['date'].dayofweek),int(dt['date'].month),
        int(dt['event_flag']),int(dt['snap'])],dtype=float)


def train_ridge(series,cal,cutoff:int):
    # No training target >=cutoff, and each training feature uses earlier observations only.
    earliest=max(56,cutoff-560)
    X=np.stack([feature(series[:t],t,cal) for t in range(earliest,cutoff)])
    y=np.asarray(series[earliest:cutoff],float)
    reg=make_pipeline(StandardScaler(),Ridge(alpha=15.0))
    reg.fit(X,y)
    return reg


def predict_next(history,day:int,method:str,cal:pd.DataFrame,reg=None):
    h=np.asarray(history,float)
    if method=='seasonal_naive_7':v=h[-7]
    elif method=='moving_mean_28':v=h[-28:].mean()
    elif method=='ridge':
        if reg is None:raise ValueError('Ridge requires fitted model')
        v=float(reg.predict(feature(h,day,cal)[None,:])[0])
    else:raise ValueError(f'Unknown prediction method {method}')
    return float(max(v,0))


def forecast(series,cal,origin,horizon,method,reg=None):
    if origin+horizon>len(cal):raise ValueError('Insufficient known future calendar for full forecast coverage')
    if method=='ridge_price_history':return reg.forecast(series,cal,origin,horizon)
    hist=list(map(float,series[:origin]));pred=[]
    for d in range(origin,origin+horizon):
        val=predict_next(hist,d,method,cal,reg)
        pred.append(val);hist.append(val)  # recursive; strictly no future observed sales
    return np.asarray(pred)


def make_abc_xyz(items,values,cal,prices,selection_origin:int):
    beginning=max(0,selection_origin-364)
    weeks=cal.iloc[beginning:selection_origin]['wm_yr_wk'].to_numpy()
    pr={(str(r.item_id),int(r.wm_yr_wk)):float(r.sell_price) for r in prices.itertuples()}
    out=[]
    for i,it in items.iterrows():
        weekly=[];revenue=0.;priced_units=0.;total_units=0.
        sl=values[i,beginning:selection_origin]
        for week in np.unique(weeks):
            mask=weeks==week; qty=float(sl[mask].sum());weekly.append(qty)
            total_units+=qty
            price=pr.get((it.item_id,int(week)))
            if price is not None and np.isfinite(price) and price>0:
                revenue+=qty*price;priced_units+=qty
        avg=np.mean(weekly) if weekly else 0
        cv=float(np.std(weekly,ddof=0)/avg) if avg>0 else np.nan
        xyz=('X' if cv<=.5 else 'Y' if cv<=1.0 else 'Z') if np.isfinite(cv) else 'N'
        out.append(dict(item_id=it.item_id,cat_id=it.cat_id,dept_id=it.dept_id,
            history_units=round(total_units),history_value=round(revenue,2),
            priced_unit_coverage=float(priced_units/total_units) if total_units>0 else 0.,
            weekly_cv=cv,xyz=xyz))
    res=pd.DataFrame(out)
    # Only reasonably priced series contribute to financial ABC. Missing are 'U'.
    res['abc']='U'
    valid=res.loc[res.priced_unit_coverage>=.95].sort_values('history_value',ascending=False)
    total=valid.history_value.sum()
    if total>0:
        cumulative_before=(valid.history_value.cumsum()-valid.history_value)/total
        res.loc[valid.index,'abc']=np.where(cumulative_before<.8,'A',
            np.where(cumulative_before<.95,'B','C'))
    res['abc_xyz']=res.abc+res.xyz
    return res.sort_values(['abc','xyz','history_value'],ascending=[True,True,False]).reset_index(drop=True)


def backtest(items,values,cal,validation_start,horizon=HORIZON):
    n=values.shape[1];fold_origins=[validation_start,validation_start+horizon]
    test_origin=validation_start+2*horizon
    recs=[]; forecasters={}; details=[]
    for stage,origins in [('validation',fold_origins),('test',[test_origin])]:
        for origin in origins:
            for i,it in items.iterrows():
                y=values[i];reg=train_ridge(y,cal,origin)
                if stage=='test':forecasters[it.item_id]=reg
                for method in METHODS:
                    pred=forecast(y,cal,origin,horizon,method,reg)
                    actual=y[origin:origin+horizon]
                    for offset,(truth,p) in enumerate(zip(actual,pred)):
                        recs.append(dict(stage=stage,origin=str(cal.iloc[origin]['date'].date()),
                            date=str(cal.iloc[origin+offset]['date'].date()),d_idx=origin+offset,
                            item_id=it.item_id,cat_id=it.cat_id,method=method,
                            actual=float(truth),prediction=float(p)))
    preds=pd.DataFrame(recs)
    vals=[]
    for (stage,method),grp in preds.groupby(['stage','method']):
        vals.append(dict(stage=stage,method=method,wape=wape(grp.actual,grp.prediction),
            mae=float(np.abs(grp.actual-grp.prediction).mean()),
            evaluated_item_days=len(grp),actual_units=float(grp.actual.sum())))
    metrics=pd.DataFrame(vals).sort_values(['stage','wape'])
    chosen=metrics.loc[metrics.stage=='validation'].sort_values(['wape','method']).iloc[0]['method']
    return preds,metrics,chosen,test_origin,forecasters


@dataclass(frozen=True)
class Policy:
    name:str
    lead_days:int=7
    review_days:int=7
    service_z:float=1.65


def simulate_one(series,cal,origin:int,horizon:int,method:str,policy:Policy,reg,abc_xyz='BY',
                 initial_units:int|None=None):
    """Daily periodic/order-point planning with arriving POs and lost sales.

    Forecasts of demand beyond day t use only observed demand < t plus recursion.
    Decision at start of t can use historical actual through t-1 only.
    """
    if policy.lead_days<1 or policy.review_days<1:raise ValueError('Lead/review days >=1 required')
    recent=series[max(0,origin-84):origin]
    avg=float(np.mean(recent));sd=float(np.std(recent,ddof=0))
    if initial_units is None:initial_units=int(np.ceil(avg*14))
    on_hand=int(initial_units);pipeline=[];ledger=[]
    for j in range(horizon):
        day=origin+j
        arrivals=sum(q for when,q in pipeline if when==day)
        pipeline=[(when,q) for when,q in pipeline if when>day]
        opening_on_hand=on_hand
        on_hand+=arrivals
        # Forecast from information known at start of current day; no knowledge of today's actual demand.
        lead=policy.lead_days
        future=max(lead+policy.review_days,28)
        if day+future>len(cal):
            raise ValueError('Insufficient known future calendar; refusing shortened replenishment horizon')
        outlook=forecast(series,cal,day,future,method,reg)
        lead_demand=outlook[:lead].sum()
        target_demand=outlook[:lead+policy.review_days].sum()
        z=policy.service_z
        if policy.name=='abc_xyz':
            if abc_xyz.startswith('A') and abc_xyz.endswith('Z'):z=2.05
            elif abc_xyz.startswith('A'):z=1.75
            elif abc_xyz.endswith('Z'):z=1.90
            elif abc_xyz.startswith('C'):z=1.10
        ss=int(np.ceil(z*sd*np.sqrt(lead))) if policy.name!='weekly_cover' else 0
        inventory_position=on_hand+sum(q for _,q in pipeline)
        reorder_point=int(np.ceil(lead_demand))+ss
        target=int(np.ceil(target_demand))+ss
        trigger=(j%policy.review_days==0) if policy.name=='weekly_cover' else inventory_position<=reorder_point
        order_qty=max(target-inventory_position,0) if trigger else 0
        if order_qty>0:
            pipeline.append((day+lead,int(order_qty)))
        demand=int(series[day]); fulfilled=min(on_hand,demand)
        lost=demand-fulfilled;on_hand-=fulfilled
        ledger.append(dict(day_index=day,date=str(cal.iloc[day]['date'].date()),day=j,
            policy=policy.name,lead_days=lead,initial_units=initial_units,
            arrivals=arrivals,demand=demand,fulfilled=fulfilled,lost=lost,
            ordered=int(order_qty),ending_on_hand=on_hand,
            in_transit=sum(q for _,q in pipeline),reorder_point=reorder_point,
            safety_stock=ss,opening_on_hand=opening_on_hand,inventory_position=inventory_position,
            target_stock=target,forecast_lead_units=float(lead_demand),forecast_target_units=float(target_demand),
            forecast_days=future,target_coverage_days=lead+policy.review_days,
            order_arrival_date=str(cal.iloc[day+lead]['date'].date()) if order_qty>0 else None))
    return pd.DataFrame(ledger)


def policy_backtest(items,values,cal,abc,origin,method,forecasters,horizon=HORIZON,
                    lead_days=7,review_days=7):
    policies=[Policy('weekly_cover',lead_days,review_days),Policy('rop',lead_days,review_days),
              Policy('abc_xyz',lead_days,review_days)]
    abcs=dict(zip(abc.item_id,abc.abc_xyz))
    logs=[]
    for i,it in items.iterrows():
        series=values[i];initial=int(np.ceil(np.mean(series[origin-84:origin])*14))
        for p in policies:
            led=simulate_one(series,cal,origin,horizon,method,p,forecasters.get(it.item_id),
                abc_xyz=abcs.get(it.item_id,'BY'),initial_units=initial)
            led.insert(0,'item_id',it.item_id)
            logs.append(led)
    result=pd.concat(logs,ignore_index=True)
    scores=[]
    for policy,g in result.groupby('policy'):
        demand=g.demand.sum();fulfilled=g.fulfilled.sum()
        scores.append(dict(policy=policy,simulation_fill_rate=float(fulfilled/demand) if demand else None,
                           demand_units=int(demand),fulfilled_units=int(fulfilled),
                           lost_units=int(g.lost.sum()),avg_ending_on_hand=float(g.groupby('date').ending_on_hand.sum().mean()),
                           total_ordered_units=int(g.ordered.sum()),po_events=int((g.ordered>0).sum())))
    return result,pd.DataFrame(scores).sort_values('policy')


def build_full_project(raw:Path,out:Path,store='CA_1',top_n=30,source='m5',lead_days=7):
    out=Path(out)
    if out.resolve()==(Path(__file__).resolve().parents[1]/'outputs/m5').resolve():
        raise ValueError('Published outputs/m5 is immutable; use outputs/m5_market or another output')
    out.mkdir(parents=True,exist_ok=True)
    items,y,cal,prices,start=load_m5(raw,store,top_n)
    abc=make_abc_xyz(items,y,cal,prices,start)
    pred,met,chosen,test_origin,regs=backtest(items,y,cal,start)
    ledger,scores=policy_backtest(items,y,cal,abc,test_origin,chosen,regs,lead_days=lead_days)
    sku_m=[]
    for (stage,method,item),g in pred.groupby(['stage','method','item_id']):
        sku_m.append(dict(stage=stage,method=method,item_id=item,wape=wape(g.actual,g.prediction),
                          mae=float(np.abs(g.actual-g.prediction).mean()),
                          observed_units=float(g.actual.sum())))
    sku_metrics=pd.DataFrame(sku_m)
    # Changing lead times is a controlled sensitivity analysis; 7-day base output remains unchanged.
    sensitivity=[]
    for test_lead in sorted(set([3,7,14,lead_days])):
        _,sc=policy_backtest(items,y,cal,abc,test_origin,chosen,regs,lead_days=test_lead)
        sc.insert(0,'lead_days',test_lead)
        sensitivity.append(sc)
    lead_sensitivity=pd.concat(sensitivity,ignore_index=True)
    tables={'items':items,'classification':abc,'forecast_predictions':pred,
            'forecast_metrics':met,'forecast_sku_metrics':sku_metrics,
            'inventory_ledger':ledger,'inventory_scores':scores,
            'leadtime_sensitivity':lead_sensitivity}
    for name,df in tables.items():df.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    demo=(Path(raw)/'SYNTHETIC_DEMO_ONLY.txt').exists() or source=='demo'
    summary={'data_kind':'SYNTHETIC DEMO — NOT WALMART RESULTS' if demo else 'M5 PUBLIC HISTORICAL SALES',
             'source_name':source,'store':store,'sku_count':int(len(items)),
             'history_days':int(y.shape[1]),'data_start':str(cal.iloc[0]['date'].date()),
             'data_end':str(cal.iloc[y.shape[1]-1]['date'].date()),
             'validation_start':str(cal.iloc[start]['date'].date()),
             'test_start':str(cal.iloc[test_origin]['date'].date()),
             'test_end':str(cal.iloc[test_origin+HORIZON-1]['date'].date()),
             'selected_forecast_method':chosen,
             'validation_wape':{r.method:float(r.wape) for r in met.loc[met.stage=='validation'].itertuples()},
             'test_wape':{r.method:float(r.wape) for r in met.loc[met.stage=='test'].itertuples()},
             'inventory_assumptions':{'initial_stock':'mean actual daily demand from last 84 observed days *14; simulated',
               'lead_days':lead_days,'review_days':7,'lost_sales':True,
               'starting_pipeline':'empty','cost_model':'no actual cost data; no savings claims'},
             'inventory_results':scores.to_dict('records'),
             'limitations':['M5 lacks actual on-hand stock and procurement orders',
               'Simulation is not a real replenishment outcome',
               'Price is used for classification, not as forecast regressor',
               'A selected subset of active SKUs from one store is evaluated',
               'Past sales can be censored by stockouts; missing stockout labels']}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary,tables
