"""Small synthetic M5-shaped dataset, NEVER real Walmart sales."""
from pathlib import Path
import numpy as np
import pandas as pd


def build_demo(root: Path, n_items: int = 24, days: int = 420, seed: int = 2026):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.date_range('2015-01-01', periods=days + 28)
    cal=[]
    for i,d in enumerate(dates,1):
        event = 'HolidayDemo' if (d.month==12 and d.day in [24,25]) else ''
        cal.append(dict(date=d.strftime('%Y-%m-%d'),wm_yr_wk=11501+(i-1)//7,
            weekday=d.day_name(),wday=d.dayofweek+1,month=d.month,year=d.year,d=f'd_{i}',
            event_name_1=event,event_type_1='Cultural' if event else '',
            event_name_2='',event_type_2='',snap_CA=int(d.day in range(1,11)),
            snap_TX=0,snap_WI=0))
    cal = pd.DataFrame(cal); cal.to_csv(root/'calendar.csv',index=False)
    sales=[]; prices=[]
    for k in range(n_items):
        cat=['FOODS','HOUSEHOLD','HOBBIES'][k%3]
        dept=f'{cat}_{1+k%2}'; item=f'{dept}_{k:03d}';store='CA_1'
        base = 1.5 + (k%7)*1.05
        weekly_mult = np.array([1.0,1.02,1.01,1.03,1.12,1.36,1.27])
        seasonal = 1 + .17*np.sin(np.arange(days)*2*np.pi/90 + k/3)
        event_boost = np.array([1.45 if (d.month==12 and d.day in [24,25]) else 1 for d in dates[:days]])
        lam = base * weekly_mult[np.array([d.dayofweek for d in dates[:days]])] * seasonal * event_boost
        if k%7==0:lam = lam * .28
        y = rng.poisson(np.maximum(lam,0))
        rec=dict(id=f'{item}_{store}_validation',item_id=item,dept_id=dept,cat_id=cat,store_id=store,state_id='CA')
        rec.update({f'd_{i+1}':int(y[i]) for i in range(days)})
        sales.append(rec)
        price=4.5 + (k%11)*2.1
        for wk in cal['wm_yr_wk'].unique():
            prices.append(dict(store_id=store,item_id=item,wm_yr_wk=wk,
                sell_price=round(price*(1 + .025*np.sin((wk-11501)/5 + k)),2)))
    pd.DataFrame(sales).to_csv(root/'sales_train_validation.csv',index=False)
    pd.DataFrame(prices).to_csv(root/'sell_prices.csv',index=False)
    (root/'SYNTHETIC_DEMO_ONLY.txt').write_text(
       'These three CSV files are generated synthetic data for functional testing. '
       'They are NOT the real M5/Walmart dataset and must NOT be used as real portfolio performance.',
       encoding='utf-8')
    return root
