"""Market dashboard; all displayed KPIs share their chart filters."""
from pathlib import Path
import html,json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .market_forecast import summarize_predictions
from .market_inventory import score_ledger
from .market import regional_comparison
from .dashboard_labels import business_frame,percent,STATE_NAMES,METHOD_NAMES,POLICY_NAMES
PAGES=['经营与市场总览','商品需求分析','价格与销量分析','地区市场分析','需求预测评估','库存及采购策略','数据质量与研究局限']
COLORS=['#38d6b0','#63a9ef','#efbd62','#aa94ee','#f27e98']
CAT={'FOODS':'食品','HOUSEHOLD':'家庭用品','HOBBIES':'兴趣用品'}
METHOD=METHOD_NAMES
POLICY=POLICY_NAMES
@st.cache_data
def load_table(path,mtime):return pd.read_csv(path)
def filter_frame(frame,state='全部',store='全部',cat='全部',sku='全部'):
    d=frame.copy()
    for field,value in [('state_id',state),('store_id',store),('cat_id',cat),('item_id',sku)]:
        if value!='全部' and field in d:d=d[d[field]==value]
    return d
def market_kpis(d):
    return dict(units=float(d.units.sum()),sales_value=float(d.sales_value.sum()),store_sku_count=len(d),coverage=float(d.priced_units.sum()/d.units.sum()) if d.units.sum() else np.nan)
def num(x):return f'{x/10000:,.2f}万' if abs(x)>=10000 else f'{x:,.0f}'
def kpis(cards):
    pieces=[]
    for i,(label,value,note) in enumerate(cards):
        e=lambda v:html.escape(str(v))
        pieces.append(f'<div class="kpi" style="--accent:{COLORS[i%len(COLORS)]}"><div class="kpi-label">{e(label)}</div><div class="kpi-value">{e(value)}</div><div class="kpi-note">{e(note)}</div></div>')
    st.markdown('<div class="kpis">'+''.join(pieces)+'</div>',unsafe_allow_html=True)
def chart(f,title,unit,height=310):
    st.markdown('**'+title+'**')
    f.update_layout(height=height,colorway=COLORS,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#b7c7dd',family='Microsoft YaHei,Arial'),margin=dict(l=16,r=24,t=18,b=30),legend=dict(orientation='h',y=1.14),hovermode='x unified')
    f.update_xaxes(gridcolor='#202d44',automargin=True);f.update_yaxes(gridcolor='#202d44',title=unit,automargin=True)
    if f.data and f.data[0].type=='pie':
        f.update_traces(hovertemplate='%{label}<br>销售金额 %{value:,.2f}美元<br>销售金额占比 %{percent}<extra></extra>')
    else:
        axis='月份' if '月度' in title else '零售周起始日期' if '周度' in title else '州' if '各州' in title else '门店' if title=='单店日均销量' else '商品—门店销售组合' if '销售金额排名' in title else '商品综合分类' if title=='商品综合分类分布' else '预测模型' if '预测误差比较' in title else '日期'
        f.update_xaxes(title=axis)
        if axis in ['月份','零售周起始日期']:f.update_xaxes(tickformat='%Y-%m')
        elif axis=='日期':f.update_xaxes(tickformat='%m-%d')
    st.plotly_chart(f,width='stretch',theme=None,config={'displayModeBar':False})
def table(d,name,names=None):
    display=business_frame(d,names)
    st.dataframe(display,hide_index=True,width='stretch',height=min(400,80+min(len(d),9)*32))
    st.download_button('导出'+name,display.to_csv(index=False).encode('utf-8-sig'),file_name=name+'.csv',key='export_'+name)
def bars(labels,values):return go.Figure(go.Bar(x=labels,y=values,marker_color=COLORS[0]))
def render(root):
    out=root/'outputs/m5_market'
    if not (out/'market_manifest.json').exists():st.info('请先运行真实市场分析，结果目录 outputs/m5_market');return
    m=json.loads((out/'market_manifest.json').read_text(encoding='utf-8'))
    read=lambda n:load_table(str(out/f'{n}.csv'),(out/f'{n}.csv').stat().st_mtime_ns)
    st.markdown('<style>'+(root/'assets/dashboard.css').read_text(encoding='utf-8-sig')+'</style>',unsafe_allow_html=True)
    st.markdown('<div class="brand"><div class="brand-mark">◈</div><div><h1>零售商品市场需求与采购策略</h1><p>M5 RETAIL MARKET INTELLIGENCE</p></div></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="source-row"><span class="pill">M5官方历史数据</span><span class="pill gold">库存与采购情景模拟</span><span>{m["version"]} · 3州 · 10家样本门店</span><span class="range">市场分析期间 {m["analysis_start"]} — {m["analysis_end"]}</span></div>',unsafe_allow_html=True)
    page=st.radio('市场分析页面',PAGES,horizontal=True,label_visibility='collapsed',key='market_page')
    trend=read('item_demand_trends');state=store=cat='全部'
    if page in PAGES[:4]:
        a,b,c=st.columns(3)
        with a:state=st.selectbox('州',['全部']+sorted(trend.state_id.unique()),format_func=lambda x:STATE_NAMES.get(x,x),key='market_state')
        with b:store=st.selectbox('门店',['全部']+sorted(filter_frame(trend,state).store_id.unique()),key='market_store')
        with c:cat=st.selectbox('商品品类',['全部']+sorted(trend.cat_id.unique()),format_func=lambda x:CAT.get(x,x),key='market_cat')
    d=filter_frame(trend,state,store,cat)
    if d.empty:st.warning('当前筛选范围内无数据');return
    if page==PAGES[0]:
        k=market_kpis(d);kpis([('销售数量',num(k['units']),'件 · 当前筛选范围，364天'),('销售金额',num(k['sales_value']),'美元 · 按周零售价格估算'),('商品—门店销售组合数',f'{len(d):,}','商品编号与门店分别计数，含零销售记录'),('销量价格匹配率',percent(k['coverage']),'已匹配价格销售数量占总销售数量的比例')])
        l,r=st.columns([1,1.8]);g=d.groupby('cat_id').sales_value.sum()
        with l:chart(go.Figure(go.Pie(labels=[CAT.get(x,x) for x in g.index],values=g.values,hole=.67)),'品类销售金额占比','销售金额（美元）')
        daily=filter_frame(read('category_daily'),state,store,cat);daily=daily[daily.date.between(m['analysis_start'],m['analysis_end'])];daily['month']=pd.to_datetime(daily.date).dt.to_period('M').astype(str)
        mo=daily.groupby('month').agg(units=('units','sum'),days=('date','nunique'));mo['daily']=mo.units/mo.days/d.store_id.nunique()
        with r:chart(go.Figure(go.Scatter(x=mo.index,y=mo.daily,mode='lines+markers',fill='tozeroy')),'月度单店日均销量趋势','销量（件/店·日）')
        st.caption('单店日均销量＝当月销售数量÷实际统计天数÷所选门店数；不完整月份按实际天数计算。销售金额按对应周零售价格估算，未匹配价格部分不计入，不代表利润。')
        g=d.groupby('cat_id').agg(units=('units','sum'),sales_value=('sales_value','sum'),priced_units=('priced_units','sum')).reset_index();g['value_share']=g.sales_value/g.sales_value.sum();table(g,'当前品类销售结构')
        dept=d.groupby(['cat_id','dept_id'])[['units','sales_value']].sum().reset_index();table(dept,'当前部门销售结构')
        st.info(f'当前筛选范围有{int(d.high_volatility.sum()):,}个高需求波动销售组合、{int(d.sustained_decline.sum()):,}个销售数量连续下降组合。调整采购计划前，应复核缺货、商品在架及促销活动信息。')
    elif page==PAGES[1]:
        sku=st.selectbox('商品编号',['全部']+sorted(d.item_id.unique()),key='demand_sku');d=filter_frame(d,sku=sku);k=market_kpis(d)
        kpis([('销售数量',num(k['units']),'件 · 当前筛选商品'),('销售金额',num(k['sales_value']),'美元 · 最近364天'),('高需求波动销售组合数',str(int(d.high_volatility.sum())),'需求波动系数＞1，期间销售数量≥20件'),('销售数量连续下降组合数',str(int(d.sustained_decline.sum())),'连续两次56天比较，日均降幅均超20%')])
        l,r=st.columns(2);g=d.nlargest(12,'sales_value').copy();g['label']=g.item_id+' · '+g.store_id
        with l:chart(bars(g.label,g.sales_value),'商品销售金额排名','销售金额（美元）')
        with r:
            g=d.groupby('abc_xyz').size();chart(bars(g.index,g.values),'商品综合分类分布','销售组合数（个）')
        st.caption('销售金额分类以全样本中销量价格匹配率≥95%的商品—门店组合为基准，期间为364天，筛选后类别不变。ABC表示销售金额分类，XYZ表示需求波动分类。需求波动系数＝完整周销售数量标准差÷周均销售数量。排名展示当前范围前12个销售组合。')
        table(d.sort_values('sales_value',ascending=False)[['store_id','item_id','cat_id','dept_id','units','sales_value','abc_xyz','weekly_cv','recent_56_daily','previous_56_daily','earlier_56_daily','recent_change','sustained_decline','yoy_daily_change','first_price_date','priced_unit_coverage','recommendation']],'商品需求与采购建议明细')
    elif page==PAGES[2]:
        w=filter_frame(read('focus_weekly_prices_sales'),state,store,cat);w=w[w.date.between(m['analysis_start'],m['analysis_end'])]
        if w.empty:st.info('当前范围无价格分析案例；价格深度分析覆盖原30个商品编号在10家门店的销售记录。');return
        a,b=st.columns(2)
        with a:shop=st.selectbox('分析门店',sorted(w.store_id.unique()),key='price_shop')
        w=w[w.store_id==shop]
        with b:sku=st.selectbox('分析商品编号',sorted(w.item_id.unique()),key='price_sku')
        w=w[w.item_id==sku].sort_values('date');ev=read('price_change_events');ev=ev[(ev.store_id==shop)&(ev.item_id==sku)]
        ass=read('price_associations');ass=ass[(ass.store_id==shop)&(ass.item_id==sku)];ar=ass.iloc[0]
        kpis([('有记录零售周数',str(len(w)),'当前商品与门店，含不足7天的周'),('价格调整次数',str(len(ev)),'相邻有效周价格变化超过0.1%'),('可比较价格调整次数',str(int(ev.comparable.sum())),'前后各4个完整周，各侧价格稳定'),('价格与销量相关系数',f'{ar.partial_log_correlation:.3f}' if pd.notna(ar.partial_log_correlation) else '分析条件不足','已控制日历因素，非因果弹性')])
        l,r=st.columns(2)
        with l:chart(go.Figure(go.Scatter(x=w.date,y=w.sell_price,mode='lines+markers')),'周度零售价格趋势','零售价格（美元/件）')
        with r:chart(go.Figure(go.Scatter(x=w.date,y=w.units/w.days,mode='lines+markers')),'周度单品日均销量趋势','销售数量（件/日）')
        st.caption('日均销量＝零售周销售数量÷该周实际统计天数。前后比较仅使用完整周，以保持星期构成一致；相关系数已控制时间趋势、月份季节性、节日及SNAP适用天数占比，不能解释为因果价格弹性或促销增量。')
        table(ev,'商品价格调整明细');table(ass,'商品价格关联分析')
        st.markdown('**当前筛选范围的品类价格与需求波动**')
        diag=d.groupby('cat_id').agg(series_count=('item_id','size'),median_price_cv=('price_cv','median'),median_weekly_demand_cv=('weekly_cv','median'),total_changes=('price_changes','sum')).reset_index();table(diag,'品类价格与需求波动比较');st.caption('品类波动指标为当前所选商品—门店组合的波动系数中位数；并非品类汇总销售数量的波动系数。价格变化次数仅统计相邻有效完整周。')
        frequent=d[d.price_changes>=5].sort_values('price_changes',ascending=False)[['store_id','item_id','cat_id','price_changes','price_cv','weekly_cv']];table(frequent,'价格调整频繁商品明细');st.caption('价格调整频繁商品指分析期间相邻有效完整周的价格变化超过0.1%、累计至少5次的商品—门店销售组合。')
    elif page==PAGES[3]:
        mode=st.radio('地区比较对象',['品类与部门','同一商品'],horizontal=True,key='region_mode')
        if mode=='同一商品':
            focus=set(read('focus_weekly_prices_sales').item_id);sku=st.selectbox('地区比较商品编号',sorted(set(d.item_id)&focus),key='region_sku');d=d[d.item_id==sku]
        days=m['analysis_days'];n=d.store_id.nunique();k=market_kpis(d)
        kpis([('样本门店数',str(n),'当前筛选'),('单店日均销量',f'{k["units"]/days/n:,.1f}','件/店·日 · 统一364天'),('销售金额',num(k['sales_value']),'美元 · 当前范围'),('销量价格匹配率',percent(k['coverage']),'按销售数量加权计算')])
        ds=d.groupby(['state_id','store_id','cat_id']).agg(units=('units','sum'),sales_value=('sales_value','sum'),priced_units=('priced_units','sum')).reset_index();ds['observed_days']=days;reg=regional_comparison(ds)
        l,r=st.columns(2)
        with l:
            f=go.Figure()
            for category,g in reg.groupby('cat_id'):f.add_bar(x=g.state_id,y=g.units_per_store_day,name=CAT.get(category,category))
            f.update_layout(barmode='group');chart(f,'各州单店日均销量比较','销量（件/店·日）')
        with r:
            g=ds.groupby('store_id').units.sum()/days;chart(bars(g.index,g.values),'单店日均销量','销量（件/店·日）')
        st.caption('单店日均销量＝销售数量÷统计天数÷门店数，各地区均比较同一364天。占比分母为各州所选门店及品类的销售总量或金额；仅选一个品类时占比为100%。首次价格记录不等于上市日期，地区差异不能直接解释为消费者偏好或总体市场份额。')
        table(reg,'地区品类销售比较');table(d[['state_id','store_id','item_id','units_per_day','first_price_date','priced_unit_coverage']].sort_values('units_per_day',ascending=False),'门店商品销售明细')
        if mode=='品类与部门':
            dept=d.groupby(['state_id','cat_id','dept_id']).agg(units=('units','sum'),stores=('store_id','nunique')).reset_index();dept['units_per_store_day']=dept.units/dept.stores/days;table(dept,'地区部门销售比较')
            dd=filter_frame(read('category_daily'),state,store,cat);dd=dd[dd.date.between(m['analysis_start'],m['analysis_end'])];dd['month']=pd.to_datetime(dd.date).dt.to_period('M').astype(str);f=go.Figure()
            for state_name,g in dd.groupby('state_id'):
                z=g.groupby('month').agg(units=('units','sum'),days=('date','nunique'),stores=('store_id','nunique'));f.add_scatter(x=z.index,y=z.units/z.days/z.stores,name=state_name,mode='lines+markers')
            chart(f,'各州月度单店日均销量趋势','销量（件/店·日）')
    elif page==PAGES[4]:
        if not (out/'forecast_predictions.csv').exists():st.info('预测实验尚未完成');return
        pr=read('forecast_predictions');a,b=st.columns(2)
        with a:category=st.selectbox('预测评估品类',['全部']+sorted(pr.cat_id.unique()),format_func=lambda x:CAT.get(x,x),key='forecast_cat')
        pr=filter_frame(pr,cat=category)
        with b:sku=st.selectbox('预测评估商品编号',['全部']+sorted(pr.item_id.unique()),key='market_forecast_sku')
        pr=filter_frame(pr,sku=sku);metrics=summarize_predictions(pr,['stage','method']);te=metrics[metrics.stage=='test'].set_index('method')
        kpis([('基础模型测试误差 WAPE',f'{te.loc["ridge","wape"]:.2%}','当前品类与商品范围'),('价格模型测试误差 WAPE',f'{te.loc["ridge_price_history","wape"]:.2%}','相同窗口'),('测试WAPE变化',f'{(te.loc["ridge_price_history","wape"]-te.loc["ridge","wape"])*100:+.2f}','个百分点 · 负值为下降'),('单模型测试样本量',str(int(te.iloc[0].evaluated_item_days)),'商品·日')])
        l,r=st.columns(2)
        with l:
            f=go.Figure()
            for stage,g in metrics.groupby('stage'):f.add_bar(x=[METHOD[x] for x in g.method],y=g.wape,name='验证' if stage=='validation' else '测试')
            f.update_layout(barmode='group');f.update_yaxes(tickformat='.0%');chart(f,'验证期与测试期预测误差比较','加权绝对误差率 WAPE')
        with r:
            f=go.Figure();test=pr[pr.stage=='test']
            for method,g in test.groupby('method'):
                z=g.groupby('date').prediction.sum();f.add_scatter(x=z.index,y=z.values,name=METHOD[method],mode='lines')
            z=test[test.method=='ridge'].groupby('date').actual.sum();f.add_scatter(x=z.index,y=z.values,name='实际销售数量',mode='lines',line=dict(color='#ffffff',dash='dot'));chart(f,'测试期销售数量与预测对比','销售数量（件/日）')
        selected=json.loads((out/'model_selection.json').read_text(encoding='utf-8'))['selected_method'];st.caption('全30个商品经验证选择：'+METHOD[selected]+'。筛选仅更新所选范围的误差和图表，不重新训练或选择模型。测试沿用已披露的历史期间；预测时采用起点前最后已知价格。')
        st.caption(f'验证期间：{pr.loc[pr.stage=="validation","date"].min()} 至 {pr.loc[pr.stage=="validation","date"].max()}；测试期间：{pr.loc[pr.stage=="test","date"].min()} 至 {pr.loc[pr.stage=="test","date"].max()}。MAE按商品·日计算；WAPE按销售数量加权。')
        table(metrics,'预测误差比较明细');table(filter_frame(read('forecast_price_deltas'),cat=category,sku=sku),'历史价格特征预测误差变化')
    elif page==PAGES[5]:
        if not (out/'inventory_ledger.csv').exists():st.info('库存实验尚未完成');return
        mode=st.radio('模拟预测方案',['基础模型补货对照','验证选定模型'],horizontal=True,key='inv_mode');log=read('inventory_ledger' if mode=='基础模型补货对照' else 'inventory_candidate_ledger')
        a,b,c=st.columns(3)
        with a:lead=st.selectbox('模拟采购提前期',sorted(log.lead_days.unique()),index=list(sorted(log.lead_days.unique())).index(7),key='inv_lead')
        log=log[log.lead_days==lead]
        with b:category=st.selectbox('补货分析品类',['全部']+sorted(read('items').cat_id.unique()),format_func=lambda x:CAT.get(x,x),key='inv_cat')
        log=log[log.item_id.isin(filter_frame(read('items'),cat=category).item_id)]
        with c:sku=st.selectbox('补货分析商品编号',['全部']+sorted(log.item_id.unique()),key='inv_sku')
        log=filter_frame(log,sku=sku);scores=score_ledger(log);policy=st.selectbox('模拟补货策略',list(POLICY),format_func=lambda x:POLICY[x],key='inv_policy');g=log[log.policy==policy];r=scores[scores.policy==policy].iloc[0]
        kpis([('模拟需求满足率',f'{r.simulation_fill_rate:.2%}',POLICY[policy]+' · 当前范围'),('模拟日均期末库存',f'{r.avg_ending_on_hand:,.1f}','件 · 每日期末库存合计的期间均值'),('模拟订货数量',num(r.total_ordered_units),'件 · 模拟采购订单'),('模拟订货事件数',str(int(r.po_events)),'次 · 商品每日非零订货记录')])
        table(scores,'模拟补货策略比较');z=g.groupby('date')[['demand','arrivals','ending_on_hand','ordered']].sum();f=go.Figure();f.add_bar(x=z.index,y=z.arrivals,name='模拟到货数量')
        for col,label in [('demand','实际销售数量'),('ending_on_hand','模拟期末库存'),('ordered','模拟订货数量')]:f.add_scatter(x=z.index,y=z[col],name=label,mode='lines')
        chart(f,'销售数量与模拟库存变化','数量（件）');st.caption('筛选后指标、策略比较、库存曲线与台账同步更新。基础模型用于比较补货覆盖期修复效果；验证选定模型仅提供7天提前期情景。模拟需求采用历史销售数量。')
        st.caption(f'模拟评价期间：{g.date.min()} 至 {g.date.max()}；假设采购提前期：{lead}天。订货事件按商品每日非零订货记录计数，不代表合并采购订单数。')
        table(g,'模拟补货每日台账');st.caption('采购订单在下单日加提前期后模拟入库，评价期末在途订单继续保留。28天模拟结果受初始库存和评价期间影响，未评估采购成本。')
    else:
        kpis([('商品—门店销售组合数',f'{m["sales_rows"]:,}','销售组合数（个）'),('历史销售统计天数',str(m['history_days']),'天'),('商品—门店周价格记录数',num(m['price_rows']),'条 · 商品、门店与零售周'),('满足价格关联分析条件的组合数',str(m['association_eligible']),'原30个商品跨店300个候选销售组合')])
        st.markdown('''- **A 官方历史**：销量、日历、周度零售价格趋势、商品与门店标识。
- **B 历史计算**：销售金额估算、销售占比、日均销售数量、商品分类、统计关联及预测误差。
- **C 模型输出**：预测日销量；未来售价按历史延续，无未来真实售价输入。
- **D 人为假设与模拟**：期初库存、提前期、订单、到货、缺货、需求满足率。
- 首次记录价格日期仅作为商品可售状态的参考，不代表真实上市日期；未匹配价格的销售数量不计入估算金额。历史销售数量不等同于潜在需求。
- 地区差异仅反映M5样本门店；价格关联不代表因果弹性或促销增量。
- 测试期间已在历史版本披露，本版结果属于相同实验条件下的后续比较。
- 补货预测覆盖期已修复，使用官方已知日历；日历不足时停止计算并提示。
- 安全库存参数尚未经企业数据校准；模拟仍受初始库存、评价期间及在架差异影响。缺少采购价格、真实库存与提前期、最小订货量、促销及陈列数据。''')
        table(pd.DataFrame([{'file':name,**v} for name,v in m['source_files'].items()]),'官方数据文件校验')
        table(trend.groupby('cat_id').agg(units=('units','sum'),missing_price_sales_units=('missing_price_sales_units','sum'),pre_first_price_positive_units=('pre_first_price_positive_units','sum'),pre_first_price_zero_days=('pre_first_price_zero_days','sum')).reset_index(),'销售数量与价格匹配检查',{'pre_first_price_zero_days':'首价记录前零销售记录数（商品—门店·日）'})
        st.caption('本表销售数量及未匹配价格销售数量统计最近364天；首次价格记录前的销售数量与零销售记录统计全部历史。零销售记录数为各商品—门店组合的天数之和，不是日历跨度。')
        for name in ['market_manifest','model_selection','inventory_manifest','verification']:
            if (out/f'{name}.json').exists():
                with st.expander({'market_manifest':'数据来源与分析范围 · 技术明细','model_selection':'预测模型选择 · 技术明细','inventory_manifest':'库存模拟假设 · 技术明细','verification':'结果核验记录 · 技术明细'}[name]):st.json(json.loads((out/f'{name}.json').read_text(encoding='utf-8')))
    st.markdown('<div class="footnote">M5样本门店历史数据 · 销售金额按零售价格估算 · 价格关联不代表因果 · 库存与采购为情景模拟</div>',unsafe_allow_html=True)
