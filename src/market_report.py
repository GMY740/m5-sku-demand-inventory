"""Business deliverables built from saved M5 evidence, without rerunning models."""
from pathlib import Path
import base64
import html
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from .dashboard_labels import business_frame, CATEGORY_NAMES, METHOD_NAMES, POLICY_NAMES
from .market_inventory import score_ledger
from .market_forecast import summarize_predictions

REPORT_VERSION = 'm5_market_business_v3_20261018'
TITLE = '零售商品市场需求分析、销量预测与采购策略研究'

def md_table(frame, limit=None, names=None):
    """Chinese display copy; percentages keep their actual denominator."""
    d = business_frame(frame.head(limit) if limit else frame, names)
    def fmt(x):
        if pd.isna(x): return '—'
        if isinstance(x, (float, np.floating)):
            return f'{x:,.0f}' if x == int(x) else f'{x:,.2f}'
        if isinstance(x, (int, np.integer)): return f'{x:,}'
        return str(x).replace('|', '／').replace('\n', ' ')
    return '| ' + ' | '.join(d.columns) + ' |\n|' + '|'.join(['---']*len(d.columns)) + '|\n' + '\n'.join('| ' + ' | '.join(fmt(x) for x in row) + ' |' for row in d.itertuples(index=False, name=None))

def store_day_rates(daily, group_columns):
    """Sum sales over unique recorded store-dates, not department-row counts."""
    keys = list(group_columns)
    sums = daily.groupby(keys, observed=True)[['units', 'sales_value']].sum()
    days = daily.drop_duplicates(keys + ['store_id', 'date']).groupby(keys, observed=True).size()
    result = sums.join(days.rename('observed_store_days')).reset_index()
    result['units_per_store_day'] = result.units / result.observed_store_days
    return result

def collect_evidence(out):
    out = Path(out)
    names = ['item_demand_trends','category_daily','category_totals','department_totals',
             'regional_category_comparison','regional_item_comparison','forecast_predictions',
             'forecast_metrics','forecast_sku_metrics','forecast_price_deltas',
             'price_change_events','price_associations','focus_weekly_prices_sales',
             'inventory_ledger','inventory_scores','inventory_candidate_ledger',
             'inventory_candidate_scores','inventory_fix_comparison','classification']
    c = {name: pd.read_csv(out / f'{name}.csv') for name in names}
    for name in ['market_manifest','model_selection','inventory_manifest','forecast_verification']:
        c[name] = json.loads((out / f'{name}.json').read_text(encoding='utf-8'))
    m = c['market_manifest']; d = c['category_daily']
    d = d[d.date.between(m['analysis_start'], m['analysis_end'])].copy()
    c['recent_daily'] = d
    # The current dashboard divides by days * stores. Prove its equivalence on
    # the complete current store/category/date grid before using this wording.
    grid = d[['store_id','cat_id','date']].drop_duplicates()
    expected = len(m['stores']) * d.cat_id.nunique() * m['analysis_days']
    assert len(grid) == expected
    assert grid.groupby(['store_id','cat_id']).date.nunique().eq(m['analysis_days']).all()
    c['observed_store_days'] = len(d[['store_id','date']].drop_duplicates())
    d['period'] = d.date.str[:7]
    c['monthly'] = store_day_rates(d, ['cat_id','period'])
    t = c['item_demand_trends']; cats = c['category_totals']
    for field in ['units','sales_value','priced_units']:
        assert np.isclose(t[field].sum(), d[field].sum())
        bycat = d.groupby('cat_id')[field].sum().sort_index()
        assert np.allclose(bycat, cats.set_index('cat_id')[field].sort_index())
    rows = []
    dates = sorted(d.date.unique())
    for cat, g in d.groupby('cat_id'):
        tr = t[t.cat_id == cat]
        windows = []
        for lo, hi in [(-168,-112),(-112,-56),(-56,None)]:
            sub = g[g.date.isin(dates[lo:hi])]
            windows.append(sub.units.sum() / len(sub[['store_id','date']].drop_duplicates()))
        rows.append(dict(cat_id=cat, series_count=len(tr), earlier=windows[0], previous=windows[1], recent=windows[2],
                         change=windows[2]/windows[1]-1, median_weekly_demand_cv=tr.weekly_cv.median(),
                         high_volatility_count=int(tr.high_volatility.sum()), decline_count=int(tr.sustained_decline.sum()),
                         median_price_cv=tr.price_cv.median(), total_changes=int(tr.price_changes.sum())))
    c['category_decisions'] = pd.DataFrame(rows)
    c['window_dates'] = [(dates[-168],dates[-113]),(dates[-112],dates[-57]),(dates[-56],dates[-1])]
    pr = c['forecast_predictions']
    calc = summarize_predictions(pr, ['stage','method'])
    j = calc.merge(c['forecast_metrics'], on=['stage','method'], suffixes=('_calc','_saved'), validate='one_to_one')
    for metric in ['wape','mae','evaluated_item_days','actual_units']:
        assert np.allclose(j[metric+'_calc'], j[metric+'_saved'])
    for ledger_name, score_name in [('inventory_ledger','inventory_scores'),('inventory_candidate_ledger','inventory_candidate_scores')]:
        log = c[ledger_name]; saved = c[score_name]
        for lead, g in log.groupby('lead_days'):
            ss = saved[saved.lead_days==lead] if 'lead_days' in saved else saved
            j = score_ledger(g).merge(ss, on='policy', suffixes=('_calc','_saved'), validate='one_to_one')
            for col in ['simulation_fill_rate','lost_units','avg_ending_on_hand','total_ordered_units','po_events','terminal_pipeline']:
                assert np.allclose(j[col+'_calc'],j[col+'_saved'])
        for _, g in log.groupby(['lead_days','policy','item_id']):
            g = g.sort_values('date'); lead = int(g.lead_days.iloc[0])
            assert np.allclose(g.ending_on_hand, g.opening_on_hand+g.arrivals-g.fulfilled)
            assert np.allclose(g.arrivals, g.ordered.shift(lead,fill_value=0))
            assert np.allclose(g.in_transit,g.in_transit.shift(1,fill_value=0)+g.ordered-g.arrivals)
            assert np.allclose(g.demand,g.fulfilled+g.lost)
            assert (g.forecast_days >= g.target_coverage_days).all()
    c['case'] = t[(t.item_id=='FOODS_3_120') & (t.store_id=='CA_1')].iloc[0]
    c['price_case'] = c['price_change_events'].query("store_id=='CA_1' and item_id=='FOODS_3_681' and comparable").iloc[0]
    c['case_ledger'] = c['inventory_ledger'].query("lead_days==7 and item_id=='FOODS_3_120' and policy=='rop'").copy()
    c['case_scores'] = score_ledger(c['inventory_ledger'].query("lead_days==7 and item_id=='FOODS_3_120'"))
    c['metrics_validation'] = c['forecast_metrics'].query("stage=='validation'").set_index('method')
    c['metrics_test'] = c['forecast_metrics'].query("stage=='test'").set_index('method')
    delta = c['forecast_price_deltas'].query("stage=='test'")
    c['improved'] = int((delta.wape_change_pp < -1e-8).sum())
    c['worsened'] = int((delta.wape_change_pp > 1e-8).sum())
    c['unchanged'] = len(delta)-c['improved']-c['worsened']
    return c

def make_figures(c, folder):
    folder = Path(folder); folder.mkdir(exist_ok=True)
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists(): plt.rcParams['font.family'] = FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False})
    colors=['#249e8c','#63a9ef','#d9a347']
    def finish(name, note):
        plt.gcf().text(.02,.01,note,fontsize=8,color='#546477')
        plt.tight_layout(rect=(0,.055,1,1));plt.savefig(folder/name,dpi=170,bbox_inches='tight');plt.close()
    cats=c['category_totals'];plt.figure(figsize=(9,4))
    plt.bar([CATEGORY_NAMES[x] for x in cats.cat_id],cats.sales_value/1e6,color=colors)
    plt.ylabel('销售金额估算（百万美元）')
    finish('01_category.png','10家M5样本门店 · 2015-05-25至2016-05-22 · 销售数量×对应周零售价格，非利润')
    plt.figure(figsize=(9,4))
    for (cat,g),color in zip(c['monthly'].groupby('cat_id'),colors):
        plt.plot(g.period,g.units_per_store_day,marker='o',label=CATEGORY_NAMES[cat],color=color)
    plt.xticks(rotation=35);plt.ylabel('销量（件/店·日）');plt.legend()
    finish('02_monthly.png','10店 · 销售数量÷实际记录门店日数 · 首月7天、末月22天；不能据此断言固定季节规律')
    reg=c['regional_category_comparison'];plt.figure(figsize=(9,4));states=['CA','TX','WI'];x=np.arange(3)
    for j,cat in enumerate(sorted(reg.cat_id.unique())):
        g=reg[reg.cat_id==cat].set_index('state_id').reindex(states)
        plt.bar(x+(j-1)*.24,g.units_per_store_day,.24,label=CATEGORY_NAMES[cat],color=colors[j])
    plt.xticks(x,['加利福尼亚 CA','得克萨斯 TX','威斯康星 WI']);plt.legend();plt.ylabel('销量（件/店·日）')
    finish('03_regional.png','同一364天 · CA 4店、TX 3店、WI 3店 · 不代表地区消费者偏好或总体市场份额')
    pc=c['price_case'];w=c['focus_weekly_prices_sales'];m=c['market_manifest']
    w=w[(w.store_id==pc.store_id)&(w.item_id==pc.item_id)&w.date.between(m['analysis_start'],m['analysis_end'])]
    fig,ax=plt.subplots(2,1,figsize=(9,5),sharex=True)
    ax[0].plot(pd.to_datetime(w.date),w.sell_price,color=colors[0]);ax[0].set_ylabel('零售价格（美元/件）')
    ax[1].plot(pd.to_datetime(w.date),w.units/w.days,color=colors[1]);ax[1].set_ylabel('销售数量（件/日）');ax[1].set_xlabel('零售周起始日期')
    for a in ax:a.axvline(pd.Timestamp(pc.date),linestyle='--',color=colors[2])
    finish('04_price.png','2015-05至2016-05 · 周销量÷该周实际天数 · 虚线为案例价格调整周，前后变化不构成因果证据')
    methods=['seasonal_naive_7','moving_mean_28','ridge','ridge_price_history'];x=np.arange(4);plt.figure(figsize=(9,4))
    for shift,stage,color in [(-.17,'validation',colors[0]),(.17,'test',colors[1])]:
        g=c['forecast_metrics'].query('stage==@stage').set_index('method').reindex(methods)
        plt.bar(x+shift,g.wape*100,.34,label='验证期' if stage=='validation' else '测试期',color=color)
    plt.xticks(x,[METHOD_NAMES[x] for x in methods]);plt.ylabel('预测误差 WAPE（%）');plt.legend()
    finish('05_forecast.png','CA_1 30商品 · 验证2016-02-29至04-24、测试04-25至05-22 · WAPE不是预测准确率')
    plt.figure(figsize=(9,4));g=c['inventory_scores'].query('lead_days==7')
    for j,row in enumerate(g.itertuples()):
        plt.scatter(row.avg_ending_on_hand,row.simulation_fill_rate*100,s=85,color=colors[j]);plt.annotate(POLICY_NAMES[row.policy],(row.avg_ending_on_hand,row.simulation_fill_rate*100),xytext=(5,7),textcoords='offset points')
    plt.ylabel('模拟需求满足率（%）');plt.xlabel('模拟日均期末库存（件）');plt.margins(.28)
    finish('06_inventory.png','CA_1 30商品 · 2016-04-25至05-22 · 相同Ridge、期初库存、7天交期；非企业实际库存表现')

def inline_html(text):
    s=html.escape(text)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s

def render_html(markdown, base):
    """Small dependency-free renderer for our headings, tables, links and images."""
    parts=[];lines=markdown.splitlines();i=0
    while i<len(lines):
        line=lines[i];i+=1
        if not line.strip():continue
        if line.strip()=='<!-- PAGEBREAK -->':parts.append('<div class="page-break"></div>');continue
        if line.startswith('|'):
            block=[line]
            while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
            rows=[[x.strip() for x in l.strip().strip('|').split('|')] for l in block]
            parts.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline_html(x)+'</th>' for x in rows[0])+'</tr></thead><tbody>')
            for row in rows[2:]:parts.append('<tr>'+''.join('<td>'+inline_html(x)+'</td>' for x in row)+'</tr>')
            parts.append('</tbody></table></div>');continue
        match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if match:
            path=base/match[2];src='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
            parts.append('<figure><img alt="'+html.escape(match[1])+'" src="'+src+'"><figcaption>'+inline_html(match[1])+'</figcaption></figure>');continue
        if line.startswith('#'):
            n=min(4,len(line)-len(line.lstrip('#')));parts.append(f'<h{n}>'+inline_html(line[n:].strip())+f'</h{n}>')
        elif line.startswith('- '):parts.append('<p class="bullet">• '+inline_html(line[2:])+'</p>')
        elif line.startswith('> '):parts.append('<blockquote>'+inline_html(line[2:])+'</blockquote>')
        else:parts.append('<p>'+inline_html(line)+'</p>')
    css='@page{size:A4 portrait;margin:17mm 16mm 18mm}body{font-family:"Microsoft YaHei",Arial,sans-serif;color:#263747;background:#eef2f5;margin:0}main{max-width:960px;margin:28px auto;background:white;padding:38px 48px;box-shadow:0 5px 26px #14283a12}h1{font-size:29px;line-height:1.45;color:#163f56;border-bottom:3px solid #248a80;padding-bottom:16px}h2{font-size:21px;line-height:1.4;margin-top:38px;padding-top:18px;border-top:1px solid #d9e2e7;color:#163f56}h3{font-size:16px;line-height:1.4;color:#236b70;margin:25px 0 8px}p{font-size:14px;line-height:1.8;margin:8px 0 14px}a{color:#14677f}code{background:#eef3f5;padding:2px 4px;font-size:12px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:12px;margin:14px 0 22px}th{background:#e8f0f2;text-align:left;color:#234454}td,th{padding:8px;border-bottom:1px solid #dbe3e7;line-height:1.5;vertical-align:top}img{max-width:100%;height:auto}figure{margin:18px 0 22px;padding:0}figcaption{font-size:11px;color:#637484;line-height:1.45;margin-top:5px}header{color:#71818b;font-size:11px;letter-spacing:.04em;margin-bottom:20px}blockquote{margin:16px 0;padding:10px 16px;border-left:3px solid #248a80;background:#f2f7f6;color:#315365}.page-break{break-after:page}@media(max-width:700px){main{padding:20px;margin:0}h1{font-size:24px}.table-wrap{overflow-x:auto}}@media print{body{background:white}main{box-shadow:none;margin:0;padding:0;max-width:none}header{font-size:9px}h1{font-size:24px}h2{break-after:avoid}h3{break-after:avoid}figure,tr,.table-wrap{break-inside:avoid}a{color:inherit;text-decoration:none}.page-break{break-after:page}}'
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+TITLE+'</title><style>'+css+'</style></head><body><main><header>M5历史分析 · 管理决策报告 · 历史观察与模拟情景分列</header>'+''.join(parts)+'</main></body></html>'

def render_pdf(markdown, base, target):
    font='C:/Windows/Fonts/msyh.ttc'; bold='C:/Windows/Fonts/msyhbd.ttc'
    if Path(font).exists():
        pdfmetrics.registerFont(TTFont('M5YaHei',font,subfontIndex=0))
        pdfmetrics.registerFont(TTFont('M5YaHei-Bold',bold,subfontIndex=0))
        bodyfont='M5YaHei'; boldfont='M5YaHei-Bold'
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'));bodyfont=boldfont='STSong-Light'
    body=ParagraphStyle('M5Body',fontName=bodyfont,fontSize=9.2,leading=14.2,textColor=colors.HexColor('#263747'),spaceAfter=7,wordWrap='CJK')
    small=ParagraphStyle('M5Small',parent=body,fontSize=7.5,leading=10,spaceAfter=0)
    h1=ParagraphStyle('M5H1',parent=body,fontName=boldfont,fontSize=20,leading=28,textColor=colors.HexColor('#163f56'),spaceAfter=16,keepWithNext=True)
    h2=ParagraphStyle('M5H2',parent=body,fontName=boldfont,fontSize=15,leading=21,textColor=colors.HexColor('#163f56'),spaceBefore=17,spaceAfter=9,keepWithNext=True)
    h3=ParagraphStyle('M5H3',parent=body,fontName=boldfont,fontSize=11.5,leading=16,textColor=colors.HexColor('#236b70'),spaceBefore=11,spaceAfter=5,keepWithNext=True)
    def para(s,style=body):
        return Paragraph(s,style)
    def table_block(rows):
        cleaned=rows[2:] if len(rows)>1 and set(rows[1]) <= {'---',':---','---:',' :---:'} else rows[1:]
        rows=[rows[0]]+cleaned
        n=max(len(r) for r in rows); avail=A4[0]-3.4*cm
        weights=[max(5,max((len(r[i]) if i<len(r) else 0 for r in rows))*1.0) for i in range(n)]
        if sum(weights)>avail/13: weights=[max(1,w**.72) for w in weights]
        widths=[avail*w/sum(weights) for w in weights]
        data=[[Paragraph(inline_html(cell),small) for cell in (r+['']*n)[:n]] for r in rows]
        tab=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f2')),('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#234454')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#d4dfe4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        return tab
    story=[]; lines=markdown.splitlines(); i=0
    while i<len(lines):
        line=lines[i];i+=1
        if not line.strip():continue
        if line.strip()=='<!-- PAGEBREAK -->':story.append(PageBreak());continue
        if line.startswith('|'):
            block=[line]
            while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
            rows=[[x.strip() for x in row.strip().strip('|').split('|')] for row in block]
            story.extend([table_block(rows),Spacer(1,9)]);continue
        if line.startswith('!['):
            match=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
            if match:
                img=Image(str(base/match[2]),width=17.8*cm,height=7.4*cm,kind='proportional')
                img.hAlign='CENTER';story.extend([KeepTogether([img,para(match[1],small)]),Spacer(1,8)])
            continue
        if line.startswith('#'):
            n=len(line)-len(line.lstrip('#')); style={1:h1,2:h2,3:h3}.get(n,h3);story.append(para(line[n:].strip(),style));continue
        if line.startswith('- '):line='• '+line[2:]
        story.append(para(inline_html(line)))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont(bodyfont,7.5);canvas.setFillColor(colors.HexColor('#71818b'))
        canvas.drawString(1.7*cm,1.05*cm,'M5零售商品市场与采购策略分析')
        canvas.drawRightString(A4[0]-1.7*cm,1.05*cm,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(target),pagesize=A4,leftMargin=1.7*cm,rightMargin=1.7*cm,topMargin=1.55*cm,bottomMargin=1.7*cm,title=TITLE,author='M5 project analysis')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def build_market_report(out, root):
    out=Path(out);root=Path(root)
    if out.resolve()==(root/'outputs/m5').resolve():raise ValueError('Historical baseline is immutable')
    c=collect_evidence(out)
    from .market_report_content import business_sections, interview_document, terminology_document, methodology_document, dictionary_document
    sections=business_sections(c)
    report='# '+TITLE+'\n\nM5公开历史销售分析｜3州10店｜市场窗口 2015-05-25 至 2016-05-22\n\n'+sections[0][1]+'\n\n<!-- PAGEBREAK -->\n\n'+'\n\n'.join(text for _,text in sections[1:])
    make_figures(c,out/'figures')
    (out/'market_business_report.md').write_text(report,encoding='utf-8')
    (out/'market_business_report.html').write_text(render_html(report,out),encoding='utf-8')
    render_pdf(report,out,out/'market_business_report.pdf')
    docs=root/'docs'
    interview=interview_document(c)
    (docs/'17_interview_market.md').write_text(interview,encoding='utf-8')
    resume=interview.split('## 八、可以写进校招简历的项目表述')[1]
    (docs/'04_resume.md').write_text('# 当前项目简历表述\n\n'+resume+'\n\n旧版文案保存在audit/final_documents_20261018/history_before/docs/04_resume.md，不与当前结果混用。\n',encoding='utf-8')
    (docs/'20_business_terminology.md').write_text(terminology_document(),encoding='utf-8')
    (docs/'10_market_methodology.md').write_text(methodology_document(c),encoding='utf-8')
    (docs/'11_market_data_dictionary.md').write_text(dictionary_document(),encoding='utf-8')
    mapping={'market':'12_market_report.md','price':'13_price_sales_report.md','regional':'14_regional_market_report.md','forecast':'15_price_forecast_experiment.md','inventory':'16_procurement_recommendations.md','limits':'18_market_limitations.md'}
    for key,text in sections:
        if key in mapping:
            text=re.sub(r'!\[([^\]]*)\]\(figures/([^)]+)\)',r'![\1](../outputs/m5_market/figures/\2)',text)
            text=text.replace('../../docs/', '')
            (docs/mapping[key]).write_text(text+'\n\n完整上下文见[业务报告](../outputs/m5_market/market_business_report.md)。\n',encoding='utf-8')
    tables=out/'report_tables';tables.mkdir(exist_ok=True)
    for name,frame in [('monthly_store_day_rates',c['monthly']),('category_decisions',c['category_decisions']),('case_inventory_scores',c['case_scores'])]:frame.to_csv(tables/f'{name}.csv',index=False,encoding='utf-8-sig')
    checks={'report_version':REPORT_VERSION,'calculation_version':c['market_manifest']['version'],'source':'existing official M5 outputs; no forecast or simulation rerun','observed_store_days':c['observed_store_days'],'store_category_date_grid_complete':True,'forecast_metrics_reconciled':True,'inventory_metrics_and_conservation_reconciled':True,'market_units':float(c['item_demand_trends'].units.sum()),'market_sales_value':float(c['item_demand_trends'].sales_value.sum()),'test_wape':c['metrics_test'].wape.to_dict(),'files_are_presentation_and_derived_tables':True}
    (tables/'report_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    chart_rows=[
        ['图表','业务指标','计算范围与口径','来源结果文件'],
        ['01 品类销售金额结构','按零售售价估算的销售金额（百万美元）','10家样本门店，364天；数量×对应周零售价','category_totals.csv'],
        ['02 月度单店日均销量','销售数量（件/店·日）','品类月销量÷有记录的门店日数；首末月不完整','category_daily.csv；report_tables/monthly_store_day_rates.csv'],
        ['03 地区品类比较','各州品类单店日均销量（件/店·日）','同一364天；州内门店平均','regional_category_comparison.csv'],
        ['04 价格与销量案例','零售价格（美元/件）、日均销售数量（件/日）','CA_1 FOODS_3_681周售价及该周销售数量÷周天数','focus_weekly_prices_sales.csv；price_change_events.csv'],
        ['05 预测误差对比','验证和测试WAPE（%）','同30 SKU、相同窗口；销量加权绝对误差率','forecast_metrics.csv'],
        ['06 补货模拟权衡','模拟需求满足率、平均期末库存','CA_1 30 SKU，2016-04-25至05-22，7天假设提前期','inventory_scores.csv']]
    (tables/'chart_data_mapping.csv').write_text('\ufeff'+'\n'.join(','.join('"'+str(x).replace('"','""')+'"' for x in row) for row in chart_rows),encoding='utf-8')
    (docs/'22_chart_data_mapping.md').write_text('# 图表与数据来源对照\n\n'+'\n'.join('| '+' | '.join(row)+' |' for row in chart_rows[:1]+[['---']*4]+chart_rows[1:])+'\n',encoding='utf-8')
    (docs/'21_report_restructure_notes.md').write_text(f'''# 市场与采购策略业务报告重构说明

本次重构只改报告内容组织、文案、图表呈现与排版；未重新计算市场指标、训练预测模型或运行库存策略。生成过程从已保存的`outputs/m5_market`结果读取，并进行口径复核。旧`outputs/m5`基线不作改写。

## 章节调整

旧版从业务背景、范围和技术方法逐段展开，管理结论和行动建议出现在后段。新版首页先给5项管理摘要，随后按商品需求、价格与销量、地区差异、预测与补货决策、行动建议及方法附录组织。长方法解释、数据口径及限制收进附录，正文保留影响业务解释的必要边界。

## 视觉与校验

统一A4纵向留白、商务蓝绿色、中文指标名称和业务单位。六张真实结果图表取消重复内嵌标题；图下注明范围、单位与解释。正文表格只保留行动相关字段，数量和金额按阅读精度展示。HTML适配屏幕和打印，PDF嵌入Windows微软雅黑字体并带页码。

关键结论仍标明历史观测、模型误差或模拟情景。零售售价不写作成本；价格前后变化不解释为因果；模拟满足率不描述为企业实际绩效。

## 输出文件

- `outputs/m5_market/market_business_report.html`
- `outputs/m5_market/market_business_report.pdf`
- `outputs/m5_market/market_business_report.md`
- 图表映射见[图表数据来源对照](22_chart_data_mapping.md)
''',encoding='utf-8')
    print('Business report, interview guide, terminology and current module documents updated; computed input tables preserved.',flush=True)
