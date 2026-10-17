"""Seven-page PDF and offline HTML from computed outputs; no fabricated metrics."""
import argparse
import base64
import html
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak

METHODS=['seasonal_naive_7','moving_mean_28','ridge']

def build(outdir:Path):
    outdir=Path(outdir)
    s=json.loads((outdir/'summary.json').read_text(encoding='utf-8'))
    required=['classification','forecast_metrics','forecast_sku_metrics','forecast_predictions','inventory_scores','inventory_ledger','leadtime_sensitivity']
    t={n:pd.read_csv(outdir/f'{n}.csv') for n in required}
    demo='SYNTHETIC DEMO' in s['data_kind']
    if not demo and s['data_kind']!='M5 PUBLIC HISTORICAL SALES':
        raise ValueError('Unknown data provenance; refusing to label output as real M5')
    label='合成演示数据；禁止用于真实M5成果' if demo else 'M5真实历史销量分析；库存与采购均为情景模拟'
    cls=t['classification'];met=t['forecast_metrics'];scores=t['inventory_scores'];lead=t['leadtime_sensitivity'];pred=t['forecast_predictions']
    selected=s['selected_forecast_method']
    v=met[(met.stage=='validation')&(met.method==selected)].iloc[0]
    te=met[(met.stage=='test')&(met.method==selected)].iloc[0]
    total_value=cls.history_value.sum();ranked=cls.sort_values('history_value',ascending=False).copy()
    ranked['value_share']=ranked.history_value/total_value if total_value else 0
    a=cls[cls.abc=='A'];a_share=a.history_value.sum()/total_value if total_value else 0
    best=scores.sort_values(['simulation_fill_rate','avg_ending_on_hand'],ascending=[False,True]).iloc[0]
    cover=scores[scores.policy=='weekly_cover'].iloc[0]
    lead_days=s['inventory_assumptions']['lead_days']
    figdir=outdir/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,3));x=range(3)
    for shift,stage,color in [(-.18,'validation','#1c6478'),(.18,'test','#e4a64d')]:
        g=met[met.stage==stage].set_index('method')
        ax.bar([i+shift for i in x],[100*g.loc[m,'wape'] for m in METHODS],width=.34,label=stage,color=color)
    ax.set_xticks(list(x),['Seasonal naive','Moving mean','Ridge']);ax.set_ylabel('WAPE (%)');ax.legend();ax.set_title('28-day recursive forecasts: validation vs held-out test');fig.tight_layout();fig.savefig(figdir/'forecast.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3));ax.scatter(scores.avg_ending_on_hand,scores.simulation_fill_rate*100,s=85,color='#1c6478')
    for r in scores.itertuples():ax.annotate(r.policy,(r.avg_ending_on_hand,r.simulation_fill_rate*100),xytext=(5,6),textcoords='offset points',fontsize=9)
    ax.margins(x=.25,y=.30);ax.set_xlabel('Average ending inventory (simulated units)');ax.set_ylabel('Simulated fill rate (%)');ax.set_title('Policy trade-off under common starting conditions');fig.tight_layout();fig.savefig(figdir/'inventory.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3))
    for policy,g in lead.groupby('policy'):ax.plot(g.lead_days,g.simulation_fill_rate*100,marker='o',label=policy)
    ax.set_xlabel('Assumed procurement lead time (days)');ax.set_ylabel('Simulated fill rate (%)');ax.set_xticks(sorted(lead.lead_days.unique()));ax.legend(fontsize=8);ax.set_title('Lead-time sensitivity: finite-horizon simulation');fig.tight_layout();fig.savefig(figdir/'sensitivity.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3));top=ranked.head(8).iloc[::-1]
    ax.barh(top.item_id,top.history_value,color='#1c6478');ax.set_xlabel('Historical sales value (USD estimate; selected subset)');ax.set_title('Top 8 selected SKUs by pre-validation historical sales value');fig.tight_layout();fig.savefig(figdir/'value.png',dpi=180);plt.close(fig)

    # Both formats share a single evidence-led page plan.
    pages=[]
    def page(title):
        p={'title':title,'blocks':[]};pages.append(p);return p
    def text(p,value):p['blocks'].append(('text',value))
    def table(p,rows,widths):p['blocks'].append(('table',(rows,widths)))
    def image(p,name):p['blocks'].append(('image',name))
    p=page('01 业务结论与研究边界')
    text(p,'SKU需求预测与库存补货策略分析 | CA_1门店')
    text(p,f'研究范围：{s["sku_count"]}个重点活跃SKU；{s["history_days"]}天历史，{s["data_start"]}至{s["data_end"]}。SKU按首次验证前364天销量筛选，不代表全门店或全M5总体。')
    table(p,[['问题','本次计算结果','业务解读'],['管理重点',f'A类{len(a)}个，占选中SKU价值{a_share:.2%}','历史交易价值集中，不能视为利润或采购成本'],['预测选择',f'{selected}；验证WAPE {v.wape:.2%}；测试WAPE {te.wape:.2%}','只在验证期选模，测试期用于独立检验'],['库存模拟',f'{best.policy}的模拟满足率最高：{best.simulation_fill_rate:.2%}','需同时看库存占用；不是实际经营改善']],[2.4,7.4,7.2])
    text(p,f'默认{lead_days}天采购提前期、7天复核周期；每SKU初始库存为测试前84天日均销量×14并向上取整，初始在途为0。三个策略面对相同历史销量冲击。')
    text(p,'真实记录：日销量、日历、周售价。计算结果：ABC-XYZ分类及预测误差。模拟变量：期初库存、采购PO、提前期、到货、缺货和需求满足率。M5不包含真实供应商采购系统。')
    text(p,'阅读结论时必须保留：单店重点子样本、28天测试窗口、销量可能受缺货抑制，以及模拟末端覆盖期缩短这四项限制。')
    p=page('02 数据范围、日期与完整性')
    validation=pred[pred.stage=='validation'];test=pred[pred.stage=='test']
    # First validation day is also the exclusive endpoint of classification history.
    allcal=pd.date_range(s['data_start'],periods=s['history_days'])
    start=s['history_days']-84;begin=max(0,start-364)
    table(p,[['环节','日期/样本','口径'],['历史销量',f'{s["data_start"]}至{s["data_end"]}；{s["history_days"]}天','本次优先读取sales_train_evaluation.csv（官方模式）'],['筛选与分类',f'{allcal[begin].date()}至{allcal[start-1].date()}；{start-begin}天','最近56天有销售，窗口销量≥20，取销量前N'],['验证窗口1',f'{allcal[start].date()}至{allcal[start+27].date()}','28天固定起点递归预测'],['验证窗口2',f'{allcal[start+28].date()}至{allcal[start+55].date()}','28天；两折汇总选择全局方法'],['最终测试',f'{s["test_start"]}至{s["test_end"]}','28天；不依据测试结果倒选模型'],['样本量',f'每模型验证{int(v.evaluated_item_days):,}、测试{int(te.evaluated_item_days):,}个SKU日','WAPE按总绝对误差/总真实销量汇总']],[3,7,7])
    text(p,f'分类价格覆盖：最小按销量加权覆盖率{cls.priced_unit_coverage.min():.2%}；U类{int((cls.abc=="U").sum())}个（覆盖不足95%）。未匹配价格不填补成采购成本。')
    text(p,'数据缺失：没有真实在手库存、库存状态、供应商PO、采购成本、MOQ、实际采购提前期与缺货标签。销量为0可能来自无需求、未上架或缺货，当前无法逐一识别。')
    text(p,'来源与复现：用户提供的Kaggle M5 CSV，复制件与源文件SHA-256一致。结构及记录数的独立核验、原始文件哈希见audit/real_m5/verification.json；不将本项目WAPE等同官方WRMSSE竞赛成绩。')
    p=page('03 重点SKU的价值贡献与分类')
    image(p,'value.png')
    table(p,[['类别','SKU数','历史交易价值占选中子样本比例']]+[[k,int(len(g)),f'{g.history_value.sum()/total_value:.2%}' if total_value else 'N/A'] for k,g in cls.groupby('abc')],[3,3,11])
    distribution='；'.join(f'{k}类{int(c)}个' for k,c in cls.abc_xyz.value_counts().sort_index().items())
    text(p,f'ABC-XYZ分布：{distribution}。前5个价值最高SKU合计占选中样本价值{ranked.head(5).value_share.sum():.2%}。贡献比例的分母仅为本次选中SKU，不是整个CA_1门店。')
    text(p,'ABC依据预验证销量×对应零售周售价；按累计前值80%/95%划分，跨阈值SKU保留在前一类。XYZ按wm_yr_wk周销量CV分类：≤0.5为X、≤1为Y、其余为Z；窗口两端可能是部分周。阈值为分析设定。')
    text(p,'计划含义：优先复核A类商品的预测偏差和需求变化；波动更大的Y/Z类需单独判断安全库存假设。X类表示本窗口周需求较稳定，不保证未来无波动，也不保证预测一定准确。')
    p=page('04 验证选模与独立测试误差')
    image(p,'forecast.png')
    rows=[['方法','验证WAPE','测试WAPE','测试MAE（件/SKU日）']]
    for m in METHODS:
        va=met[(met.stage=='validation')&(met.method==m)].iloc[0];tt=met[(met.stage=='test')&(met.method==m)].iloc[0]
        rows.append([m,f'{va.wape:.2%}',f'{tt.wape:.2%}',f'{tt.mae:.2f}'])
    table(p,rows,[5,4,4,4])
    text(p,f'验证选定{selected}；测试WAPE相对验证变化{(te.wape-v.wape)*100:+.2f}个百分点。WAPE是销量加权的误差率，不是“准确率=1-WAPE”，也不是企业经营绩效。')
    worst=t['forecast_sku_metrics'].query("stage=='test'")
    worst=worst[worst.method==selected].sort_values('wape',ascending=False).head(3)
    text(p,'选定模型测试WAPE较高的SKU：'+'；'.join(f'{r.item_id}（{r.wape:.2%}）' for r in worst.itertuples())+'。需同时关注销量分母，小销量SKU的百分比误差可能不稳定。')
    text(p,'泄漏检查：筛选和分类仅用首次验证前历史；每次训练仅用起点前真实销量；未来28天递归使用自身预测。日历特征含星期、月份、事件与SNAP；未来已实现售价不进入预测。')
    p=page('05 相同条件下的库存策略模拟')
    image(p,'inventory.png')
    table(p,[['模拟策略','满足率','流失件数','平均期末库存/件','PO次数']]+[[r.policy,f'{r.simulation_fill_rate:.2%}',int(r.lost_units),f'{r.avg_ending_on_hand:.1f}',int(r.po_events)] for r in scores.itertuples()],[4,3,3,4,3])
    text(p,f'本窗口最高满足率策略为{best.policy}。相对weekly_cover，模拟满足率变化{(best.simulation_fill_rate-cover.simulation_fill_rate)*100:+.2f}个百分点，平均期末库存变化{best.avg_ending_on_hand-cover.avg_ending_on_hand:+.1f}件。这是共同假设下的比较，不能写成实际缺货改善或采购降本。')
    text(p,'日内顺序：到货→按前一日以前信息做订货决策→用当天历史销量冲击库存→记录履约、流失与期末库存。PO仅在下单日+提前期入库，在途不提前满足需求。')
    text(p,'公平性：同SKU各策略的初始库存、销量输入、提前期、预测方法、初始在途相同；周检视、ROP触发与安全库存系数按策略不同。平均期末库存为每天跨SKU库存合计后按28天平均。')
    text(p,'观测假设：模拟即使缺货，仍可在次日获得原始历史销量需求；不模拟库存约束导致的需求信息丢失。因此它是历史销量驱动的政策情景比较。')
    p=page('06 采购提前期敏感性与边界')
    image(p,'sensitivity.png')
    table(p,[['模拟提前期/天','策略','满足率','平均期末库存/件']]+[[int(r.lead_days),r.policy,f'{r.simulation_fill_rate:.2%}',f'{r.avg_ending_on_hand:.1f}'] for r in lead.sort_values(['lead_days','policy']).itertuples()],[3,5,4,5])
    text(p,'3/7/14天均为假设，不是沃尔玛真实供应商交期。初始库存固定、初始在途为空、测试仅28天，较长提前期的影响与初始化密切相关，不应将这些曲线外推为长期经营规律。')
    text(p,'已知未修复边界：原代码仅保留销量历史内日历，临近测试末端会缩短预测覆盖期，导致补货目标不能持续覆盖完整提前期+复核周期。末端订单及库存可能偏低，策略排名与敏感性结论受此影响。基线算法与参数本次保持原样。')
    p=page('07 可执行建议、缺失信息与复现证据')
    table(p,[['可以据此做什么','需要补充什么才能落地'],['用历史价值和波动确定人工复核优先级','真实库存状态、商品在架与缺货标记'],['用两折验证比较预测方法，再单独报告测试','更多独立时间窗口；避免反复调参消耗测试集'],['在共同假设下讨论服务与库存取舍','供应商交期分布、MOQ、采购价、库存持有及缺货成本'],['追溯模拟PO、到货及每日库存台账','真实采购执行单据与企业试点结果']],[8.5,8.5])
    text(p,'审计结论：时间切分与递归预测设计未发现未来销量泄漏；独立脚本重算误差并核验逐日到货、库存及在途守恒。合成测试验证代码性质，真实输出核验验证本次结果口径，两者不能相互替代。')
    text(p,'目前不支持的结论：沃尔玛实际库存改善、采购成本节约、真实缺货率下降、供应商履约或企业OTD提升。M5日销量也不等同无约束潜在需求。')
    text(p,'复现入口：run.py --raw data/raw --store CA_1 --top-n 30 --lead-days 7；make_report.py --out outputs/m5。数据、模型与库存参数均沿用项目原设定，无新增模型或扩大样本范围。')
    text(p,'证据位置：outputs/m5下summary.json与各CSV；audit/real_m5/logs下运行和测试日志；audit/real_m5/verification.json为独立核验；浏览器截图与文件修改清单随交付审计包提供。')
    text(p,'下一步优先处理模拟末端覆盖期边界，并在独立输出目录做有记录的对照；若引入新时间窗或参数，应明确它属于后续实验，保留本次基线，不把调参后的结果继续称为原独立测试。')

    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    body=ParagraphStyle('body',fontName='STSong-Light',fontSize=10,leading=16,spaceAfter=10,textColor=colors.HexColor('#253649'))
    small=ParagraphStyle('small',parent=body,fontSize=8.5,leading=13,spaceAfter=0)
    heading=ParagraphStyle('heading',parent=body,fontSize=18,leading=25,spaceAfter=16,textColor=colors.HexColor('#1c6478'))
    story=[]
    def par(value,sty=body):return Paragraph(html.escape(str(value)),sty)
    def pdf_table(rows,widths):
        table=Table([[par(c,small) for c in row] for row in rows],colWidths=[w*cm for w in widths],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f3')),('GRID',(0,0),(-1,-1),.25,colors.HexColor('#ced9df')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        return table
    for i,p in enumerate(pages):
        if i:story.append(PageBreak())
        story.append(par(p['title'],heading))
        for kind,value in p['blocks']:
            if kind=='text':story.append(par(value))
            elif kind=='table':story.extend([pdf_table(*value),Spacer(1,12)])
            else:story.extend([Image(str(figdir/value),width=17*cm,height=6.375*cm),Spacer(1,10)])
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('STSong-Light',8);canvas.setFillColor(colors.HexColor('#637887'));canvas.drawString(2*cm,1.15*cm,label);canvas.drawRightString(A4[0]-2*cm,1.15*cm,f'{doc.page} / 7');canvas.restoreState()
    pdf=outdir/'project_report.pdf'
    SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=1.65*cm,bottomMargin=1.75*cm,title='M5 SKU需求预测与库存策略业务报告',author='M5 project analysis').build(story,onFirstPage=footer,onLaterPages=footer)
    pieces=[]
    for p in pages:
        blocks=[]
        for kind,value in p['blocks']:
            if kind=='text':blocks.append('<p>'+html.escape(value)+'</p>')
            elif kind=='table':blocks.append('<table>'+''.join('<tr>'+''.join('<'+('th' if i==0 else 'td')+'>'+html.escape(str(c))+'</'+('th' if i==0 else 'td')+'>' for c in row)+'</tr>' for i,row in enumerate(value[0]))+'</table>')
            else:blocks.append('<img alt="'+html.escape(value)+'" src="data:image/png;base64,'+base64.b64encode((figdir/value).read_bytes()).decode()+'">')
        pieces.append('<section><h2>'+html.escape(p['title'])+'</h2><div class="note">'+label+'</div>'+''.join(blocks)+'</section>')
    web=outdir/'project_report.html'
    web.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M5业务报告</title><style>body{margin:0;background:#eef3f6;color:#253649;font-family:system-ui,"Microsoft YaHei",sans-serif}.wrap{max-width:1050px;margin:auto;padding:28px}header{background:#16394a;color:white;border-radius:14px;padding:28px}section{background:white;padding:28px;margin:20px 0;border-radius:12px}h2{color:#1c6478}.note{background:#e8f0f3;padding:10px;font-size:13px}p{line-height:1.9}table{border-collapse:collapse;width:100%;margin:18px 0}td,th{border:1px solid #ced9df;padding:10px;text-align:left;line-height:1.6}th{background:#e8f0f3}img{width:100%;height:auto}footer{font-size:12px;color:#637887}</style><div class="wrap"><header><h1>M5 SKU需求预测与库存策略业务报告</h1><p>'+label+'</p></header>'+''.join(pieces)+'<footer>计算结果源自当前输出CSV；无真实采购降本或库存改善主张。</footer></div></html>',encoding='utf-8')
    print('Built',pdf,web)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='outputs/demo');args=parser.parse_args();build(Path(args.out))
