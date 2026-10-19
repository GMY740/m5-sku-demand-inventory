"""Full-coverage inventory comparison, using identical forecast method for before/after."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .core import load_m5,make_abc_xyz,train_ridge,policy_backtest
from .market_forecast import train_price_ridge,PRICE_METHOD
from .market import save_table

def score_ledger(ledger):
    rows=[]
    for policy,g in ledger.groupby('policy'):
        demand=g.demand.sum()
        rows.append(dict(policy=policy,simulation_fill_rate=g.fulfilled.sum()/demand if demand else np.nan,
            demand_units=demand,fulfilled_units=g.fulfilled.sum(),lost_units=g.lost.sum(),
            avg_ending_on_hand=g.groupby('date').ending_on_hand.sum().mean(),total_ordered_units=g.ordered.sum(),po_events=(g.ordered>0).sum(),
            terminal_on_hand=g[g.date==g.date.max()].ending_on_hand.sum(),terminal_pipeline=g[g.date==g.date.max()].in_transit.sum()))
    return pd.DataFrame(rows)

def build_inventory(raw,out,baseline):
    out=Path(out);base=Path(baseline)
    items,y,cal,prices,start=load_m5(raw);origin=start+56;abc=make_abc_xyz(items,y,cal,prices,start)
    fixed={it.item_id:train_ridge(y[i],cal,origin) for i,it in items.iterrows()}
    selection=json.loads((out/'model_selection.json').read_text(encoding='utf-8'));chosen=selection['selected_method']
    if chosen==PRICE_METHOD:
        from .market import match_prices
        px=match_prices(items,prices,cal.iloc[:y.shape[1]].wm_yr_wk.to_numpy())
        regs={it.item_id:train_price_ridge(y[i],cal,px[i],origin) for i,it in items.iterrows()}
    else:regs=fixed
    logs=[];scoreparts=[]
    for lead in [3,7,14]:
        log,_=policy_backtest(items,y,cal,abc,origin,'ridge',fixed,lead_days=lead)
        score=score_ledger(log);score.insert(0,'lead_days',lead);score['method']='ridge';logs.append(log);scoreparts.append(score)
    all_log=pd.concat(logs,ignore_index=True);all_score=pd.concat(scoreparts,ignore_index=True)
    old=pd.read_csv(base/'inventory_scores.csv');new=all_score[all_score.lead_days==7]
    compare=old.merge(new,on='policy',suffixes=('_before','_after'),validate='one_to_one')
    for metric in ['simulation_fill_rate','lost_units','avg_ending_on_hand','total_ordered_units','po_events']:
        compare[metric+'_change']=compare[metric+'_after']-compare[metric+'_before']
    candidate,_=policy_backtest(items,y,cal,abc,origin,chosen,regs,lead_days=7)
    tables={'inventory_ledger':all_log,'inventory_scores':all_score,'inventory_fix_comparison':compare,
        'inventory_candidate_ledger':candidate,'inventory_candidate_scores':score_ledger(candidate),'classification':abc,'items':items}
    for name,df in tables.items():save_table(out,name,df)
    info={'version':'m5_market_v1','kind':'D ASSUMPTIONS AND SIMULATION','fixed_comparison_method':'ridge','candidate_method':chosen,
        'history_demand_start':str(cal.iloc[origin].date.date()),'history_demand_end':str(cal.iloc[y.shape[1]-1].date.date()),
        'calendar_end':str(cal.iloc[-1].date.date()),'calendar_source':'Official calendar, includes known post-sales dates. No invented SNAP/event flags.',
        'forecast_coverage':'At least28 days every decision; target lead+review fully covered, no truncation',
        'initial_stock':'ceil(pre-test84day daily mean*14), same all policies and lead cases','starting_pipeline':0,'review_days':7,
        'lead_days':[3,7,14],'lost_sales':True,'costs':'Not available; no cost savings or real inventory claim',
        'terminal_effect':'Full forecast coverage fixed; finite28day evaluation and terminal outstanding POs remain. Terminal pipeline and onhand reported.',
        'rolling_information':'Each decision uses actual sales and price history strictly before that decision; fixed test-origin fitted coefficients.'}
    (out/'inventory_manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print(compare.to_string(index=False),flush=True)
    return tables
