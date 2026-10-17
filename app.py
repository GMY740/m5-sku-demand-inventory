"""M5 business dashboard. Presentation only; computed baselines remain immutable."""
from pathlib import Path
import html
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='M5 需求与库存分析',layout='wide',page_icon='◈',initial_sidebar_state='collapsed')
st.markdown('<style>'+ (ROOT/'assets/dashboard.css').read_text(encoding='utf-8-sig')+'</style>',unsafe_allow_html=True)
MINT='#38d6b0';BLUE='#63a9ef';GOLD='#efbd62';PURPLE='#aa94ee';RED='#f27e98';MUTED='#91a3bf'
ABC={'A':MINT,'B':BLUE,'C':GOLD,'U':PURPLE}
METHOD={'seasonal_naive_7':'周同期','moving_mean_28':'28日均值','ridge':'Ridge'}
POLICY={'weekly_cover':'周度覆盖','rop':'订货点','abc_xyz':'分类补货'}
CAT={'FOODS':'食品','HOUSEHOLD':'家庭用品','HOBBIES':'兴趣用品'}
COLORS=[MINT,BLUE,GOLD,PURPLE,RED]
PAGES=['经营总览','商品分层','预测分析','库存策略','每日台账','数据说明']

@st.cache_data
def load(folder,signature):
    p=Path(folder)
    summary=json.loads((p/'summary.json').read_text(encoding='utf-8'))
    tables={name:pd.read_csv(p/f'{name}.csv') for name in ['classification','forecast_predictions','forecast_metrics','inventory_ledger','inventory_scores','leadtime_sensitivity','forecast_sku_metrics']}
    return summary,tables

def number(v):
    return f'{v/10000:,.2f}万' if abs(v)>=10000 else f'{v:,.0f}'

def kpis(cards):
    blocks=[]
    for i,(label,value,note) in enumerate(cards):
        esc=lambda x:html.escape(str(x))
        blocks.append(f'<div class="kpi" style="--accent:{COLORS[i%len(COLORS)]}"><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div><div class="kpi-note">{esc(note)}</div></div>')
    st.markdown('<div class="kpis">'+''.join(blocks)+'</div>',unsafe_allow_html=True)

def head(title,note=''):
    st.markdown(f'<div class="panel-head"><span class="panel-title">{html.escape(title)}</span><span class="panel-note">{html.escape(note)}</span></div>',unsafe_allow_html=True)

def chart(fig,height=255):
    fig.update_layout(height=height,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Microsoft YaHei, Arial, sans-serif',color='#b7c7dd',size=11),colorway=COLORS,margin=dict(l=14,r=54 if any(getattr(t,'orientation',None)=='h' for t in fig.data) else 18,t=18,b=28),legend=dict(orientation='h',y=1.13,x=0,font=dict(size=10),bgcolor='rgba(0,0,0,0)'),hoverlabel=dict(bgcolor='#1a2941',font_size=12,bordercolor='#31445e'))
    fig.update_xaxes(gridcolor='#202d44',zeroline=False,linecolor='#2b3950',tickfont_size=10,title_font_size=10,automargin=True)
    fig.update_yaxes(gridcolor='#202d44',zeroline=False,linecolor='#2b3950',tickfont_size=10,title_font_size=10,automargin=True)
    if fig.data and fig.data[0].type=='pie':
        fig.update_layout(legend=dict(x=.5,xanchor='center',y=-.05,yanchor='top'),margin=dict(l=12,r=12,t=6,b=22))
    if any(getattr(trace,'x',None) is not None and len(trace.x) and isinstance(trace.x[0],str) and len(trace.x[0])==10 and trace.x[0][4]=='-' for trace in fig.data):
        fig.update_xaxes(tickformat='%m-%d',nticks=7)
    st.plotly_chart(fig,width='stretch',theme=None,config={'displayModeBar':False,'responsive':True})

def donut(labels,values,center):
    f=go.Figure(go.Pie(labels=labels,values=values,hole=.73,sort=False,marker=dict(colors=COLORS,line=dict(color='#111c30',width=3)),textinfo='none',hovertemplate='%{label}<br>%{value:,.0f}<br>占比 %{percent}<extra></extra>'))
    f.add_annotation(text=center,x=.5,y=.5,showarrow=False,font=dict(color='#e9f0fb',size=22))
    f.update_layout(legend=dict(y=-.1,x=.5,xanchor='center'))
    return f

def horizontal(labels,values,color=MINT,percent=False):
    f=go.Figure(go.Bar(x=values,y=labels,orientation='h',marker_color=color,text=[f'{v:.1%}' if percent else number(v) for v in values],textposition='outside',cliponaxis=False,hovertemplate='%{y}<br>%{x:,.2f}<extra></extra>'))
    f.update_yaxes(autorange='reversed',showgrid=False)
    f.update_xaxes(showgrid=True,tickformat='.0%' if percent else None)
    f.update_layout(margin=dict(r=50))
    return f

def matrix_frame(a):
    cols=['X','Y','Z']
    return pd.crosstab(a.abc,a.xyz).reindex(index=[x for x in ['A','B','C','U'] if x in set(a.abc)],columns=cols,fill_value=0).fillna(0)

def matrix(a):
    m=matrix_frame(a)
    f=go.Figure(go.Heatmap(z=m.values,x=m.columns,y=m.index,colorscale=[[0,'#17273d'],[1,'#249e8c']],showscale=False,xgap=5,ygap=5,text=m.values,texttemplate='%{text}',textfont=dict(size=19,color='#edf8f7'),hovertemplate='%{y}%{x}类 · %{z}个SKU<extra></extra>'))
    f.update_xaxes(showgrid=False,side='bottom');f.update_yaxes(showgrid=False,autorange='reversed');return f

def metrics(p):
    rows=[]
    for (stage,method),g in p.groupby(['stage','method']):
        denom=g.actual.abs().sum();err=(g.actual-g.prediction).abs()
        rows.append(dict(stage=stage,method=method,wape=err.sum()/denom if denom else np.nan,mae=err.mean()))
    return pd.DataFrame(rows)

def error_bars(m):
    f=go.Figure()
    for stage,name,color in [('validation','验证',BLUE),('test','测试',MINT)]:
        g=m[m.stage==stage].set_index('method').reindex(METHOD)
        f.add_bar(x=list(METHOD.values()),y=g.wape,name=name,marker_color=color)
    f.update_layout(barmode='group',bargap=.42);f.update_yaxes(tickformat='.0%');return f

def table(df,names,height=270):
    st.dataframe(df.rename(columns=names),hide_index=True,width='stretch',height=height)

header,source=st.columns([5,1.15],vertical_alignment='center')
with header:st.markdown('<div class="brand"><div class="brand-mark">◈</div><div><h1>商品需求与库存分析看板</h1><p>M5 RETAIL INTELLIGENCE &nbsp; / &nbsp; CA_1</p></div></div>',unsafe_allow_html=True)
with source:choice=st.selectbox('数据来源',['m5','demo'],format_func=lambda x:'M5 真实历史' if x=='m5' else '合成演示',key='source')
folder=ROOT/'outputs'/choice
if not (folder/'summary.json').exists():
    st.warning('尚无该数据源的计算结果');st.stop()
files=list(folder.glob('*.csv'))+[folder/'summary.json']
s,tab=load(str(folder),tuple((p.name,p.stat().st_mtime_ns) for p in files))
kind=s.get('data_kind','');demo='SYNTHETIC DEMO' in kind
if not demo and kind!='M5 PUBLIC HISTORICAL SALES':st.error('数据来源无法确认');st.stop()
if demo:st.warning('合成演示数据 · 仅用于功能展示')
source_label='合成演示销量' if demo else 'M5真实历史销量'
st.markdown(f'<div class="source-row"><span class="pill">{source_label}</span><span class="pill gold">库存与采购为情景模拟</span><span>CA_1 · {s["sku_count"]}个重点SKU</span><span class="range">历史 {s["data_start"]} — {s["data_end"]}</span></div>',unsafe_allow_html=True)
page=st.radio('分析页面',PAGES,horizontal=True,label_visibility='collapsed',key='page')
a=tab['classification'].copy();p=tab['forecast_predictions'].copy();selected=s['selected_forecast_method']
if page in PAGES[:3]:
    filters=st.columns([1,1.6,2.4])
    with filters[0]:cat=st.selectbox('商品品类',['全部品类']+sorted(a.cat_id.unique().tolist()),format_func=lambda x:CAT.get(x,x),key='category')
    if cat!='全部品类':
        a=a[a.cat_id==cat];p=p[p.item_id.isin(a.item_id)]
    with filters[2]:st.markdown('<div class="section-label" style="padding-top:28px">筛选同步更新图表与指标 · 分类仅使用验证前历史</div>',unsafe_allow_html=True)
m=metrics(p);v=m[(m.stage=='validation')&(m.method==selected)].iloc[0];te=m[(m.stage=='test')&(m.method==selected)].iloc[0]
value=a.history_value.sum();ac=a[a.abc=='A'];share=ac.history_value.sum()/value if value else 0
actual_name='演示销量' if demo else '真实历史销量'

if page=='经营总览':
    score=tab['inventory_scores'].sort_values('simulation_fill_rate',ascending=False).iloc[0]
    kpis([('重点商品',f'{len(a)}','预验证历史筛选'),('历史交易价值',number(value),'美元 · 预验证364天'),('留出测试误差',f'{te.wape:.2%}',METHOD[selected]+' · WAPE'),('A类价值贡献',f'{share:.2%}',f'{len(ac)}个A类商品 · 当前样本')])
    left,right=st.columns([1,2.15])
    with left,st.container(border=True):
        head('品类价值构成','历史交易价值')
        g=a.groupby('cat_id').history_value.sum();f=donut([CAT.get(x,x) for x in g.index],g.values,number(value));chart(f,245)
    with right,st.container(border=True):
        head('测试期销量走势',s['test_start']+' — '+s['test_end'])
        g=p[(p.stage=='test')&(p.method==selected)].groupby('date')[['actual','prediction']].sum().reset_index()
        f=go.Figure();f.add_scatter(x=g.date,y=g.actual,name=actual_name,mode='lines',line=dict(color=MINT,width=2.5),fill='tozeroy',fillcolor='rgba(56,214,176,.08)');f.add_scatter(x=g.date,y=g.prediction,name=METHOD[selected]+'预测',mode='lines',line=dict(color=GOLD,width=2,dash='dot'));f.update_layout(hovermode='x unified');chart(f,245)
    l,c,r=st.columns([1,1.2,1.2])
    with l,st.container(border=True):head('ABC–XYZ分类','SKU数量');chart(matrix(a),225)
    with c,st.container(border=True):
        head('重点商品价值排名','前7位 · 美元')
        g=a.nlargest(7,'history_value');chart(horizontal(g.item_id.tolist(),g.history_value.tolist()),225)
    with r,st.container(border=True):head('预测方法对比','WAPE · 越低越好');chart(error_bars(m),225)

elif page=='商品分层':
    kpis([('A类商品',str(len(ac)),f'当前样本共{len(a)}个SKU'),('A类价值贡献',f'{share:.2%}','分母为当前选中样本'),('历史交易价值',number(value),'美元 · 销量乘对应周售价'),('价格匹配覆盖',f'{a.priced_unit_coverage.min():.0%}','当前商品最低覆盖率')])
    l,r=st.columns([1.8,1])
    with l,st.container(border=True):
        head('历史交易价值排名','前10位 · 美元');g=a.nlargest(10,'history_value');chart(horizontal(g.item_id.tolist(),g.history_value.tolist()),310)
    with r,st.container(border=True):
        head('价值与需求波动','周销量变异系数')
        f=go.Figure()
        for k,g in a.groupby('abc'):f.add_scatter(x=g.weekly_cv,y=g.history_value,mode='markers',name=k+'类',marker=dict(color=ABC.get(k,PURPLE),size=10,line=dict(width=1,color='#111c30')),text=g.item_id,hovertemplate='%{text}<br>周需求CV %{x:.2f}<br>历史价值 %{y:,.2f}美元<extra></extra>')
        f.update_xaxes(title='周需求CV');f.update_yaxes(title='历史价值 · 美元');chart(f,310)
    l,r=st.columns([1,2.2])
    with l,st.container(border=True):head('分类矩阵','SKU数量');chart(matrix(a),275)
    with r,st.container(border=True):
        head('商品分类明细','按历史价值排序')
        view=a.sort_values('history_value',ascending=False)[['item_id','cat_id','history_units','history_value','weekly_cv','abc_xyz']].copy();view.cat_id=view.cat_id.map(CAT);view.history_value=view.history_value.round(2);view.weekly_cv=view.weekly_cv.round(3)
        table(view,{'item_id':'商品SKU','cat_id':'品类','history_units':'历史销量','history_value':'历史价值 · 美元','weekly_cv':'周需求CV','abc_xyz':'分类'},275)

elif page=='预测分析':
    with filters[1]:sku=st.selectbox('商品SKU',a.sort_values('history_value',ascending=False).item_id.tolist(),key='forecast_sku')
    kpis([('选定预测方法',METHOD[selected],'依据全样本两折验证选择'),('验证误差',f'{v.wape:.2%}','WAPE · 两个28天窗口'),('测试误差',f'{te.wape:.2%}','WAPE · 独立28天窗口'),('测试平均误差',f'{te.mae:.2f}','件 / SKU日 · MAE')])
    l,r=st.columns([1,2])
    with l,st.container(border=True):head('模型验证与测试','WAPE');chart(error_bars(m),300)
    with r,st.container(border=True):
        head('单品销量与预测',sku)
        sample=p[(p.stage=='test')&(p.item_id==sku)];f=go.Figure()
        for i,(method,name) in enumerate(METHOD.items()):
            g=sample[sample.method==method];f.add_scatter(x=g.date,y=g.prediction,name=name,mode='lines',line=dict(color=[BLUE,PURPLE,GOLD][i],width=1.7,dash='dot' if method!=selected else 'solid'))
        g=sample[sample.method==selected];f.add_scatter(x=g.date,y=g.actual,name=actual_name,mode='lines+markers',line=dict(color=MINT,width=2.5),marker_size=4);f.update_layout(hovermode='x unified');chart(f,300)
    l,r=st.columns([1.4,1])
    sm=tab['forecast_sku_metrics'];sm=sm[(sm.stage=='test')&(sm.method==selected)&sm.item_id.isin(a.item_id)].sort_values('wape',ascending=False)
    with l,st.container(border=True):
        head('需要优先复核的商品','测试WAPE前10位');g=sm.head(10);chart(horizontal(g.item_id.tolist(),g.wape.tolist(),BLUE,True),290)
    with r,st.container(border=True):
        head('单品测试明细',METHOD[selected]);view=sm[['item_id','wape','mae','observed_units']].copy();view.wape=view.wape.map(lambda x:f'{x:.2%}');view.mae=view.mae.round(2);table(view,{'item_id':'商品SKU','wape':'WAPE','mae':'MAE','observed_units':'测试销量'},290)

elif page=='库存策略':
    ctrl,note=st.columns([1,3])
    ls=tab['leadtime_sensitivity']
    with ctrl:lead=st.select_slider('模拟采购提前期',options=sorted(ls.lead_days.unique().tolist()),value=int(s['inventory_assumptions']['lead_days']))
    with note:st.markdown('<div class="section-label" style="padding-top:28px">统一初始库存 · 初始在途为零 · 相同历史销量 · 提前期单位为天</div>',unsafe_allow_html=True)
    scores=ls[ls.lead_days==lead].copy();best=scores.sort_values('simulation_fill_rate',ascending=False).iloc[0]
    kpis([('最高模拟满足率',f'{best.simulation_fill_rate:.2%}',POLICY[best.policy]+f' · 假设提前期{lead}天'),('对应平均库存',f'{best.avg_ending_on_hand:,.0f}','件 · 每日期末库存合计的均值'),('对应模拟流失',f'{best.lost_units:,.0f}','件 · 未满足即流失'),('对应订货次数',f'{best.po_events:,.0f}','次 · 非零订货事件')])
    l,r=st.columns([1,1.7])
    with l,st.container(border=True):head('策略模拟满足率',f'提前期{lead}天');chart(horizontal([POLICY[x] for x in scores.policy],scores.simulation_fill_rate.tolist(),MINT,True),280)
    with r,st.container(border=True):
        head('满足率与库存占用','点大小代表模拟订货量')
        f=go.Figure()
        for i,row in enumerate(scores.itertuples()):f.add_scatter(x=[row.avg_ending_on_hand],y=[row.simulation_fill_rate],mode='markers+text',text=[POLICY[row.policy]],textposition='top center',name=POLICY[row.policy],marker=dict(size=max(18,np.sqrt(row.total_ordered_units)*.35),color=COLORS[i],opacity=.85),hovertemplate='平均库存 %{x:,.1f}件<br>模拟满足率 %{y:.2%}<extra>'+POLICY[row.policy]+'</extra>')
        f.update_yaxes(tickformat='.1%',title='模拟需求满足率');f.update_xaxes(title='平均期末库存 · 件');f.update_layout(showlegend=False);chart(f,280)
    l,r=st.columns([1.5,1])
    with l,st.container(border=True):
        head('提前期敏感性','3天 / 7天 / 14天')
        f=go.Figure()
        for i,(policy,g) in enumerate(ls.groupby('policy')):f.add_scatter(x=g.lead_days,y=g.simulation_fill_rate,name=POLICY[policy],mode='lines+markers',line=dict(width=2.2,color=COLORS[i]),marker_size=6)
        f.update_yaxes(tickformat='.0%');f.update_xaxes(tickvals=sorted(ls.lead_days.unique()),title='假设提前期 · 天');chart(f,270)
    with r,st.container(border=True):
        head('策略比较明细',f'提前期{lead}天');view=scores[['policy','simulation_fill_rate','avg_ending_on_hand','lost_units','po_events']].copy();view.policy=view.policy.map(POLICY);view.simulation_fill_rate=view.simulation_fill_rate.map(lambda x:f'{x:.2%}');view.avg_ending_on_hand=view.avg_ending_on_hand.round(1);table(view,{'policy':'策略','simulation_fill_rate':'模拟满足率','avg_ending_on_hand':'平均库存','lost_units':'流失件数','po_events':'订货次数'},245)

elif page=='每日台账':
    log=tab['inventory_ledger'];l,r,blank=st.columns([1,1,2])
    with l:sku=st.selectbox('商品SKU',sorted(log.item_id.unique()),key='ledger_sku')
    with r:policy=st.selectbox('模拟补货策略',list(POLICY),format_func=lambda x:POLICY[x],key='policy')
    sub=log[(log.item_id==sku)&(log.policy==policy)].sort_values('date')
    kpis([('历史销量',f'{sub.demand.sum():,.0f}','件 · 当前商品28天'),('模拟满足量',f'{sub.fulfilled.sum():,.0f}','件 · 按日库存约束'),('模拟流失量',f'{sub.lost.sum():,.0f}','件 · 不结转欠交'),('模拟平均库存',f'{sub.ending_on_hand.mean():,.1f}','件 · 每日期末库存均值')])
    with st.container(border=True):
        head('销量、到货与库存轨迹',sku+' · '+POLICY[policy])
        f=go.Figure();f.add_bar(x=sub.date,y=sub.arrivals,name='模拟到货',marker_color=BLUE,opacity=.55);f.add_scatter(x=sub.date,y=sub.ending_on_hand,name='模拟期末库存',mode='lines',line=dict(color=MINT,width=2.6),fill='tozeroy',fillcolor='rgba(56,214,176,.06)');f.add_scatter(x=sub.date,y=sub.demand,name=actual_name,mode='lines',line=dict(color=GOLD,width=1.8));f.update_layout(hovermode='x unified');f.update_yaxes(title='数量 · 件');chart(f,300)
    with st.container(border=True):
        head('每日执行明细','全部订单、到货及库存均为模拟')
        columns=['date','demand','ordered','arrivals','fulfilled','lost','ending_on_hand','in_transit']
        table(sub[columns],{'date':'日期','demand':'历史销量','ordered':'模拟订货','arrivals':'模拟到货','fulfilled':'模拟满足','lost':'模拟流失','ending_on_hand':'期末库存','in_transit':'在途库存'},285)
        st.download_button('下载当前台账',sub.to_csv(index=False).encode('utf-8-sig'),file_name='模拟库存台账.csv')
else:
    kpis([('研究门店',s['store'],'单店重点SKU案例'),('历史跨度',f'{s["history_days"]:,}','天 · 公开历史记录'),('测试窗口','28天',s['test_start']+' 至 '+s['test_end']),('数据与算法','基线复现','分类、预测与库存模拟')])
    l,r=st.columns([1.3,1])
    with l,st.container(border=True):
        head('数据来源与业务含义','真实记录与模拟分开展示')
        frame=pd.DataFrame([['真实历史','每日销量、日历、周售价','来自M5公开CSV'],['分析结果','ABC–XYZ分类、预测误差','按本项目时间窗口计算'],['情景模拟','期初库存、采购订单、到货、流失','由库存策略及假设产生'],['实际缺失','供应商PO、采购成本、真实库存、真实交期','不能推算实际采购降本']],columns=['数据类型','内容','说明']);table(frame,{},280)
    with r,st.container(border=True):
        head('分析时间线','不使用未来实际销量')
        timeline=pd.DataFrame([['分类历史','2015-03-02 至 2016-02-28' if not demo else '首次验证前历史'],['验证窗口',s['validation_start']+' 至 '+str((pd.Timestamp(s['test_start'])-pd.Timedelta(days=1)).date())],['测试窗口',s['test_start']+' 至 '+s['test_end']],['模型选择',METHOD[selected]+' · 仅依据验证误差']],columns=['阶段','口径']);table(timeline,{},280)
    with st.container(border=True):
        head('结论边界','需要保留的解释')
        st.markdown('''- 分类价值是历史交易金额估算，不是利润或采购成本。
- 历史销量可能受到缺货抑制，不能等同无约束需求。
- 库存模拟按日更新历史信息，采购订单在下单日加提前期后入库。
- 原算法临近历史末端会缩短预测覆盖期，策略排名与敏感性受此边界影响。
- 结果仅适用于本次单门店重点SKU及有限测试窗口。
- 不能据此宣称沃尔玛实际库存改善、采购降本或供应商履约提升。''')
        st.download_button('下载本次数据摘要',json.dumps(s,ensure_ascii=False,indent=2),file_name='M5分析摘要.json')
st.markdown('<div class="footnote">M5公开历史数据 · 重点SKU个案分析　|　分类与预测为计算结果　|　库存、采购订单、提前期与需求满足率均为情景模拟</div>',unsafe_allow_html=True)
