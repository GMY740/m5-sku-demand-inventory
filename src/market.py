"""Real M5 market analysis, bounded-memory store/SKU joins; no causal claims."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

VERSION = 'm5_market_v1'
META = ['item_id','dept_id','cat_id','store_id','state_id']

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def save_table(out,name,df):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')

def calendar_frame(raw):
    c=pd.read_csv(Path(raw)/'calendar.csv')
    if c.d.duplicated().any():raise ValueError('Duplicate calendar day')
    c['date']=pd.to_datetime(c.date)
    if not (c.date.diff().dropna()==pd.Timedelta(days=1)).all():raise ValueError('Noncontiguous calendar')
    c['event_flag']=c[['event_name_1','event_name_2']].notna().any(axis=1).astype(int)
    return c

def match_prices(meta,prices,weeks):
    """Returns SKU-store x day prices. Missing/invalid is NaN; never backfill."""
    if prices.duplicated(['store_id','item_id','wm_yr_wk']).any():raise ValueError('Duplicate store-item-week price')
    index=pd.MultiIndex.from_frame(meta[['store_id','item_id']])
    pivot=prices.pivot(index=['store_id','item_id'],columns='wm_yr_wk',values='sell_price')
    pivot=pivot.reindex(index=index,columns=pd.unique(weeks))
    result=pivot.to_numpy(dtype=float)[:,pd.Index(pivot.columns).get_indexer(weeks)]
    result[~np.isfinite(result)|(result<=0)]=np.nan
    return result

def period_rollup(daily,freq):
    d=daily.copy();d['period']=pd.to_datetime(d.date).dt.to_period(freq).astype(str)
    keys=['state_id','store_id','cat_id','dept_id','period']
    result=d.groupby(keys,observed=True).agg(units=('units','sum'),sales_value=('sales_value','sum'),
        priced_units=('priced_units','sum'),observed_days=('date','nunique'),period_start=('date','min'),period_end=('date','max')).reset_index()
    result['units_per_day']=result.units/result.observed_days
    result['value_per_day']=result.sales_value/result.observed_days
    result['priced_unit_coverage']=np.where(result.units>0,result.priced_units/result.units,np.nan)
    return result

def regional_comparison(structure):
    d=structure.groupby(['state_id','store_id','cat_id'],observed=True)[['units','sales_value','priced_units','observed_days']].agg(
        {'units':'sum','sales_value':'sum','priced_units':'sum','observed_days':'max'}).reset_index()
    result=d.groupby(['state_id','cat_id'],observed=True).agg(units=('units','sum'),sales_value=('sales_value','sum'),
        priced_units=('priced_units','sum'),store_count=('store_id','nunique'),observed_days=('observed_days','max')).reset_index()
    result['units_per_store_day']=result.units/result.store_count/result.observed_days
    result['value_per_store_day']=result.sales_value/result.store_count/result.observed_days
    result['category_unit_share']=result.units/result.groupby('state_id').units.transform('sum')
    result['category_value_share']=result.sales_value/result.groupby('state_id').sales_value.transform('sum')
    return result

def price_association(g):
    """Weekly conditional association, not elasticity; >=5 changes,26 weeks,half nonzero."""
    g=g[(g.days==7)&g.sell_price.notna()].sort_values('date').copy()
    n=len(g);consecutive=pd.to_datetime(g.date).diff().eq(pd.Timedelta(days=7))
    changes=int(((g.sell_price.pct_change().abs()>0.001)&consecutive).sum())
    status='eligible' if n>=26 and changes>=5 and (g.units>0).mean()>=.5 else 'insufficient_variation_or_sales'
    out=dict(weeks=n,price_changes=changes,status=status,partial_log_correlation=np.nan)
    if status!='eligible':return out
    month=pd.to_datetime(g.date).dt.month.to_numpy()
    controls=np.column_stack([np.ones(n),np.arange(n)/max(n-1,1),np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12),g.event_share,g.snap_share])
    x=np.log(g.sell_price.to_numpy());y=np.log1p(g.units.to_numpy())
    rx=x-controls@np.linalg.lstsq(controls,x,rcond=None)[0]
    ry=y-controls@np.linalg.lstsq(controls,y,rcond=None)[0]
    if np.std(rx)<1e-8 or np.std(ry)<1e-8:out['status']='no_residual_variation';return out
    out['partial_log_correlation']=float(np.corrcoef(rx,ry)[0,1]);return out

def price_events(weekly):
    records=[]
    for (store,item),g in weekly.groupby(['store_id','item_id'],observed=True):
        g=g.sort_values('date').reset_index(drop=True)
        for j in range(1,len(g)):
            before=g.iloc[j-1];now=g.iloc[j]
            if pd.isna(before.sell_price) or pd.isna(now.sell_price) or before.sell_price<=0:continue
            change=now.sell_price/before.sell_price-1
            if abs(change)<=.001:continue
            a=g.iloc[max(0,j-4):j];b=g.iloc[j:j+4]
            consecutive=len(a)==len(b)==4 and (pd.to_datetime(pd.concat([a,b]).date).diff().dropna()==pd.Timedelta(days=7)).all()
            stable=consecutive and (a.days==7).all() and (b.days==7).all() and a.sell_price.nunique()==1 and b.sell_price.nunique()==1
            rec={k:now[k] for k in META};rec.update(date=now.date,old_price=before.sell_price,new_price=now.sell_price,price_change=change,
                comparable=bool(stable),reason='isolated_4_week_windows' if stable else 'edge_missing_or_other_price_changes',
                pre_units_per_day=np.nan,post_units_per_day=np.nan,sales_change=np.nan,event_share_change=np.nan,snap_share_change=np.nan)
            if stable:
                pre=float(a.units.sum()/28);post=float(b.units.sum()/28)
                rec.update(pre_units_per_day=pre,post_units_per_day=post,sales_change=post/pre-1 if pre else np.nan,
                    event_share_change=float(b.event_share.mean()-a.event_share.mean()),snap_share_change=float(b.snap_share.mean()-a.snap_share.mean()))
            records.append(rec)
    return pd.DataFrame(records,columns=META+['date','old_price','new_price','price_change','comparable','reason','pre_units_per_day','post_units_per_day','sales_change','event_share_change','snap_share_change'])

def build_market(raw,out,focus_items):
    raw=Path(raw);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if (raw/'SYNTHETIC_DEMO_ONLY.txt').exists():raise ValueError('Market research requires official history; synthetic folder rejected')
    sales=raw/'sales_train_evaluation.csv'
    if not sales.exists():sales=raw/'sales_train_validation.csv'
    days=sorted([x for x in pd.read_csv(sales,nrows=0).columns if x.startswith('d_') and x[2:].isdigit()],key=lambda x:int(x[2:]))
    allcal=calendar_frame(raw);cal=allcal.set_index('d').loc[days].reset_index();n=len(days)
    start=max(0,n-364);recent=cal.iloc[start:].reset_index(drop=True);weeks=cal.wm_yr_wk.to_numpy()
    print('Reading official prices',flush=True)
    prices=pd.read_csv(raw/'sell_prices.csv',dtype={'store_id':'category','item_id':'category','wm_yr_wk':'int32','sell_price':'float64'})
    if prices.duplicated(['store_id','item_id','wm_yr_wk']).any():raise ValueError('Duplicate prices')
    if (prices.sell_price<=0).any() or prices.sell_price.isna().any():raise ValueError('Invalid source prices')
    daily_parts=[];daily_acc={};item_rows=[];weekly_parts=[];monthly_parts=[];rowcount=0;store_set=set()
    for chunk in pd.read_csv(sales,usecols=META+days,dtype={x:'int16' for x in days},chunksize=400):
        meta=chunk[META].reset_index(drop=True);y=chunk[days].to_numpy(dtype=float)
        if not np.isfinite(y).all() or (y<0).any():raise ValueError('Invalid source sales')
        store_set.update(meta.store_id);rowcount+=len(meta)
        subprices=prices[prices.store_id.isin(meta.store_id.unique())&prices.item_id.isin(meta.item_id.unique())]
        p=match_prices(meta,subprices,weeks);priced=np.isfinite(p);value=y*np.nan_to_num(p,nan=0)
        yr=y[:,start:];pr=p[:,start:];vr=value[:,start:];ok=priced[:,start:]
        for key,ix in meta.groupby(['state_id','store_id','cat_id','dept_id'],sort=False).groups.items():
            indices=np.array(list(ix))
            sums=np.stack([y[indices].sum(axis=0),value[indices].sum(axis=0),(y[indices]*priced[indices]).sum(axis=0)])
            if key in daily_acc:daily_acc[key]+=sums
            else:daily_acc[key]=sums
        wk=np.unique(recent.wm_yr_wk);full=[w for w in wk if int((recent.wm_yr_wk==w).sum())==7]
        weekly=np.stack([yr[:,recent.wm_yr_wk.to_numpy()==w].sum(axis=1) for w in full],axis=1)
        wm=weekly.mean(axis=1);ws=weekly.std(axis=1)
        first=np.array([np.flatnonzero(row)[0] if row.any() else n for row in priced])
        month_labels=recent.date.dt.to_period('M').astype(str)
        for i,it in meta.iterrows():
            a=float(yr[i,-56:].mean());b=float(yr[i,-112:-56].mean());c=float(yr[i,-168:-112].mean())
            total=float(yr[i].sum());cv=float(ws[i]/wm[i]) if wm[i]>0 else np.nan
            prior_dates=recent.date-pd.DateOffset(years=1);ix=pd.DatetimeIndex(cal.date).get_indexer(prior_dates)
            prior=float(y[i,ix].mean()) if (ix>=0).all() else np.nan
            f=int(first[i]);prezero=int((y[i,:f]==0).sum());postmissing=int((~priced[i,f:]).sum())
            pp=np.array([pr[i,recent.wm_yr_wk.to_numpy()==w][0] for w in full]);valid=np.isfinite(pp)
            changes=int(((np.abs(np.diff(pp))/pp[:-1]>.001)&np.isfinite(pp[1:])&np.isfinite(pp[:-1])).sum())
            rec=it.to_dict();rec.update(units=total,sales_value=float(vr[i].sum()),priced_units=float((yr[i]*ok[i]).sum()),
                priced_unit_coverage=float((yr[i]*ok[i]).sum()/total) if total else np.nan,observed_days=n-start,
                units_per_day=total/(n-start),recent_56_daily=a,previous_56_daily=b,earlier_56_daily=c,
                recent_change=a/b-1 if b else np.nan,sustained_decline=bool(b>0 and c>0 and a/b<.8 and b/c<.8),
                weekly_cv=cv,zero_day_share=float((yr[i]==0).mean()),first_price_date=str(cal.iloc[f].date.date()) if f<n else None,
                pre_first_price_zero_days=prezero,pre_first_price_positive_units=float(y[i,:f].sum()),post_first_price_missing_days=postmissing,
                missing_price_sales_units=float((yr[i]*(~ok[i])).sum()),price_changes=changes,full_weeks=len(full),
                price_cv=float(np.std(pp[valid])/np.mean(pp[valid])) if valid.any() else np.nan,
                same_dates_prior_year_daily=prior,yoy_daily_change=(total/(n-start))/prior-1 if prior>0 else np.nan)
            item_rows.append(rec)
        for i,it in meta.iterrows():
            if it.item_id not in focus_items:continue
            for w in np.unique(weeks):
                mask=weeks==w;sl=cal.loc[mask];px=p[i,mask][0]
                rec=it.to_dict();rec.update(wm_yr_wk=int(w),date=str(sl.date.min().date()),days=int(mask.sum()),
                    units=float(y[i,mask].sum()),sell_price=float(px) if np.isfinite(px) else np.nan,
                    event_share=float(sl.event_flag.mean()),snap_share=float(sl['snap_'+it.state_id].mean()))
                weekly_parts.append(rec)
            for mon in month_labels.unique():
                mask=(month_labels==mon).to_numpy();rec=it.to_dict();rec.update(period=mon,units=float(yr[i,mask].sum()),days=int(mask.sum()),units_per_day=float(yr[i,mask].mean()));monthly_parts.append(rec)
        if rowcount%4000==0:print('Processed sales rows',rowcount,flush=True)
    for key,sums in daily_acc.items():
        dd=pd.DataFrame({'date':cal.date.dt.strftime('%Y-%m-%d'),'units':sums[0],'sales_value':sums[1],'priced_units':sums[2]})
        for k,v in zip(['state_id','store_id','cat_id','dept_id'],key):dd[k]=v
        daily_parts.append(dd)
    daily=pd.concat(daily_parts,ignore_index=True)
    trend=pd.DataFrame(item_rows)
    # ABC denominator: all 30,490 store-SKU series with >=95% priced-unit coverage, last364 days.
    trend['abc']='U';valid=trend[trend.priced_unit_coverage>=.95].sort_values(['sales_value','store_id','item_id'],ascending=[False,True,True])
    denom=float(valid.sales_value.sum());before=(valid.sales_value.cumsum()-valid.sales_value)/denom
    trend.loc[valid.index,'abc']=np.where(before<.8,'A',np.where(before<.95,'B','C'))
    trend['xyz']=np.where(trend.weekly_cv<=.5,'X',np.where(trend.weekly_cv<=1,'Y','Z'));trend.loc[trend.weekly_cv.isna(),'xyz']='N'
    trend['abc_xyz']=trend.abc+trend.xyz
    trend['high_volume']=trend.units>=trend.units.quantile(.9);trend['high_value']=trend.abc=='A'
    trend['high_volatility']=(trend.weekly_cv>1)&(trend.units>=20)
    trend['recommendation']=np.select([trend.sustained_decline,trend.high_value&trend.high_volatility,trend.high_value,trend.high_volatility],
        ['谨慎补货并复核下滑原因','重点保障并复核缺货风险','重点保障并监控预测偏差','小批复核并关注波动'],default='常规跟踪')
    d=daily[pd.to_datetime(daily.date)>=recent.date.min()]
    structure=d.groupby(['state_id','store_id','cat_id','dept_id'],observed=True).agg(units=('units','sum'),sales_value=('sales_value','sum'),priced_units=('priced_units','sum'),observed_days=('date','nunique')).reset_index()
    structure['units_per_day']=structure.units/structure.observed_days;structure['value_per_day']=structure.sales_value/structure.observed_days
    structure['department_value_share_in_store']=structure.sales_value/structure.groupby('store_id').sales_value.transform('sum')
    weekly=pd.DataFrame(weekly_parts);wr=weekly[pd.to_datetime(weekly.date)>=recent.date.min()]
    associations=[]
    for key,g in wr.groupby(META,observed=True):
        rec=dict(zip(META,key));rec.update(price_association(g));associations.append(rec)
    associations=pd.DataFrame(associations);events=price_events(wr)
    regional=regional_comparison(structure)
    same=trend.groupby(['state_id','item_id','cat_id','dept_id'],observed=True).agg(units=('units','sum'),store_count=('store_id','nunique'),
        days=('observed_days','max'),price_coverage=('priced_unit_coverage','mean')).reset_index()
    same['units_per_store_day']=same.units/same.store_count/same.days
    base=same.groupby('item_id').agg(total=('units','sum'),stores=('store_count','sum'),days=('days','max'))
    same=same.join(base,on='item_id',rsuffix='_all');same['relative_demand_index']=same.units_per_store_day/(same.total/same.stores/same.days_all)
    tables={'category_daily':daily,'category_structure':structure,'item_demand_trends':trend,'priority_risk_items':trend[trend.high_value|trend.high_volatility|trend.sustained_decline],
        'regional_category_comparison':regional,'regional_item_comparison':same,'store_comparison':structure.groupby(['state_id','store_id']).agg(units=('units','sum'),sales_value=('sales_value','sum'),days=('observed_days','max')).reset_index(),
        'focus_weekly_prices_sales':weekly,'focus_monthly_demand':pd.DataFrame(monthly_parts),'price_change_events':events,'price_associations':associations}
    for freq,name in [('M','monthly'),('Q','quarterly'),('Y','annual')]:tables['category_'+name]=period_rollup(daily,freq)
    for name,df in tables.items():save_table(out,name,df)
    manifest={'version':VERSION,'data_kind':'M5 PUBLIC HISTORICAL SALES','sales_file':sales.name,'sales_rows':rowcount,'history_days':n,
        'history_start':str(cal.date.min().date()),'history_end':str(cal.date.max().date()),'analysis_start':str(recent.date.min().date()),'analysis_end':str(recent.date.max().date()),'analysis_days':len(recent),
        'stores':sorted(store_set),'price_rows':len(prices),'calendar_days':len(allcal),'focus_item_count':len(focus_items),
        'abc_denominator':'All store-SKU series with >=95% priced-unit coverage in analysis364 days','abc_total_value':denom,
        'price_association_scope':'Baseline30 item IDs across all10 stores, last364 days, full weeks; >=5 changes and26 weeks and50% nonzero',
        'association_eligible':int((associations.status=='eligible').sum()),'price_events':len(events),'comparable_price_events':int(events.comparable.sum()) if len(events) else 0,
        'tables':{name:len(df) for name,df in tables.items()},'source_files':{f.name:{'size':f.stat().st_size,'sha256':sha256(f)} for f in [sales,raw/'calendar.csv',raw/'sell_prices.csv']}}
    (out/'market_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
