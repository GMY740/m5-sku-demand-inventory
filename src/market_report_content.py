"""Business narrative templates; every displayed number comes from report evidence."""
import pandas as pd
from .market_report import md_table, REPORT_VERSION, TITLE
from .dashboard_labels import METHOD_NAMES

def business_sections(c):
    m=c['market_manifest']; t=c['item_demand_trends']; cat=c['category_totals']; q=c['category_decisions'].set_index('cat_id')
    food=cat.set_index('cat_id').loc['FOODS']; pc=c['price_case']; s=c['case']; reg=c['regional_category_comparison']
    ca=reg.query("state_id=='CA' and cat_id=='FOODS'").iloc[0]; wi=reg.query("state_id=='WI' and cat_id=='FOODS'").iloc[0]
    va=c['metrics_validation']; te=c['metrics_test']; inv=c['inventory_scores'].query('lead_days==7').set_index('policy'); candidate=c['inventory_candidate_scores'].set_index('policy')
    gain=(te.loc['ridge','wape']-te.loc['ridge_price_history','wape'])*100
    risk=t[t.sustained_decline].nlargest(3,'sales_value')
    period=f"{m['analysis_start']}至{m['analysis_end']}"
    sections=[]
    summary=f'''## 管理摘要

本报告分析M5公开零售历史：3州10家样本门店的品类需求与售价表现，并对CA_1的30个重点商品评估预测和补货情景。历史销售是已实现销量；采购订单、库存、交期和缺货结果为模拟。

**食品是销售结构核心。** 食品贡献样本销售金额的{food.value_share:.2%}，最近56天单店日均销量较前一阶段{q.loc['FOODS','change']:+.2%}。建议优先复核高金额食品商品的供货、预测偏差和可售状态。

**下降信号需要逐项排查。** {int(t.sustained_decline.sum()):,}个商品—门店组合连续两个56天阶段销量下降超过20%。这提示建立异常复核清单，但不能单凭销量判断商品衰退，应先排查缺货、下架和替代。

**地区占比不等同于单店需求。** WI食品销量占比为{wi.category_unit_share:.2%}，CA为{ca.category_unit_share:.2%}；食品单店日均销量分别为{wi.units_per_store_day:,.0f}和{ca.units_per_store_day:,.0f}件，接近。配置应进一步落到门店和具体商品。

**价格案例值得复盘，尚不能推出普遍弹性。** {pc.item_id}在CA_1由每件${pc.old_price:.2f}降至${pc.new_price:.2f}，前后可比窗口日均销量上升{pc.sales_change:.0%}；但300个候选商品—门店组合仅4个达到关联分析条件，促销、陈列和缺货等因素未被完整控制。

**更低预测误差带来的改善很小，库存取舍仍需共同评估。** 历史价格模型测试WAPE为{te.loc['ridge_price_history','wape']:.2%}，基础Ridge为{te.loc['ridge','wape']:.2%}，差{gain:.2f}个百分点。模拟订货点策略提高满足率，同时增加平均库存；这不是实际企业绩效。

**管理重点：** 按销售金额、近期趋势和波动筛出复核对象；把价格变动周作为活动复盘线索；用同店同品的单店日均支持地区配置；在真实库存、促销和供应商数据补齐前，将预测和补货结果用于方案比较，不用于自动下单。
'''
    sections.append(('summary',summary))
    sections.append(('market',f'''## 一、商品需求与品类结构

### 食品贡献过半销售金额，内部差异决定管理优先级

分析窗口为{period}，覆盖全部10家样本门店。食品销售金额估算为${food.sales_value/1e6:.2f}百万，占总额{food.value_share:.2%}；按零售售价估算，不代表利润或采购成本。

{md_table(cat.assign(sales_value=cat.sales_value/1e6)[['cat_id','units','sales_value','value_share']],names={'cat_id':'商品类别','units':'销售数量（件）','sales_value':'销售金额估算（百万美元）','value_share':'销售金额占比'})}

![食品销售金额估算占比，10店同一364天](figures/01_category.png)

食品最近56天单店日均销量为{q.loc['FOODS','recent']:,.0f}件，较此前相同长度窗口{q.loc['FOODS','change']:+.2%}。食品内部有{int(q.loc['FOODS','high_volatility_count']):,}个高波动组合，说明品类整体增长并不意味着每个商品都稳定。建议把高金额、增长且波动可控的商品纳入供货跟踪；高波动商品单独复核预测与可售情况，不对整个品类统一加库存。

### 连续下降和高波动是复核信号，不是直接删品结论

| 识别情形 | 商品—门店组合数 | 管理动作 |
|---|---:|---|
| 连续两个56天阶段销量均下降超过20% | {int(t.sustained_decline.sum()):,} | 先核查断货、下架、替代品及活动结束，再调整覆盖量 |
| 周需求波动较高且全年至少销售20件 | {int(t.high_volatility.sum()):,} | 对具体商品复核补货频率与库存缓冲 |

销售金额较高的下降案例：

{md_table(risk[['store_id','item_id','sales_value','earlier_56_daily','previous_56_daily','recent_56_daily']],names={'store_id':'门店','item_id':'商品','sales_value':'销售金额估算（美元）','earlier_56_daily':'较早阶段日均销量（件）','previous_56_daily':'前一阶段日均销量（件）','recent_56_daily':'最近阶段日均销量（件）'})}

例如CA_3的{risk.iloc[0].item_id}三个56天阶段日均销量由{risk.iloc[0].earlier_56_daily:.2f}降至{risk.iloc[0].previous_56_daily:.2f}，再降至{risk.iloc[0].recent_56_daily:.2f}件。数据没有在架或缺货记录，因此当前只能将其列为待查对象。

![月度单店日均销量按品类展示，首末月按实际记录门店日计算](figures/02_monthly.png)

首月和末月分别只有7天和22天，已按实际记录门店日计算单店日均销量。活动、商品上市和在架变化尚未剥离，月度走势适合作为进一步核查的线索。
'''))
    sections.append(('price',f'''## 二、价格与销量关系

### 价格案例值得复盘，但目前不能推导普遍价格敏感度

CA_1的{pc.item_id}在{pc.date}当周零售价由${pc.old_price:.2f}降至${pc.new_price:.2f}，调整前后各4个完整周的日均销量由{pc.pre_units_per_day:.2f}升至{pc.post_units_per_day:.2f}件，观察变化为{pc.sales_change:+.0%}。

![FOODS_3_681每件零售价与日均销售数量；虚线标记调价周](figures/04_price.png)

这是前后同时段的观察比较，不是“降价导致销量增长”。研究没有完整促销、陈列、缺货或竞品信息，也没有未调价对照组。300个候选商品—门店组合中仅{m['association_eligible']}个通过预设分析条件，因此不足以支持普遍弹性结论。建议将该案例列入活动备货复盘：核对促销计划、到货和在架记录，再评估是否需要提高活动期间的备货量。

## 三、地区与门店差异

### WI食品销售占比更高，但与CA单店日均销量接近

同一364天内，WI食品销量占比为{wi.category_unit_share:.2%}，CA为{ca.category_unit_share:.2%}；食品单店日均销量分别为{wi.units_per_store_day:,.0f}和{ca.units_per_store_day:,.0f}件。占比差异可能受到各品类构成影响，不能直接解释为WI食品绝对需求更旺。

![按州比较各品类单店日均销量，覆盖相同日期](figures/03_regional.png)

建议先在相同商品、相同门店周期内比较，再把差异用于门店配置复核。样本仅覆盖CA 4店、TX 3店和WI 3店，不代表州或全美市场份额；门店规模、客流及在架信息未纳入。

## 四、需求预测与采购判断

### 历史价格信息只带来很小的测试误差变化

预测问题是：历史销量、日历和预测时点已知的价格信息，能否更好地预估未来28天销售数量？价格方案只沿用预测起点前最后已知售价，不读取未来实际售价。

![不同方法在验证与测试窗口的销量加权误差](figures/05_forecast.png)

| 方法 | 测试WAPE | 测试MAE（件/商品·日） |
|---|---:|---:|
| 周同期法 | {te.loc['seasonal_naive_7','wape']:.2%} | {te.loc['seasonal_naive_7','mae']:.2f} |
| 28日均值法 | {te.loc['moving_mean_28','wape']:.2%} | {te.loc['moving_mean_28','mae']:.2f} |
| Ridge基础模型 | {te.loc['ridge','wape']:.2%} | {te.loc['ridge','mae']:.2f} |
| Ridge加入历史售价 | {te.loc['ridge_price_history','wape']:.2%} | {te.loc['ridge_price_history','mae']:.2f} |

测试误差分别以840个商品·日、17,278件实际销量为比较基础。价格方案相对基础Ridge仅改善{gain:.2f}个百分点，30个商品中{c['improved']}个误差下降、{c['worsened']}个上升、{c['unchanged']}个基本不变。WAPE是销量加权误差率，不是“预测准确率”。这一结果不支持宣称价格特征显著提升预测。

### 补货策略需要同时权衡保障水平与库存占用

订货点是在库存位置降至提前期需求与安全库存之和时下单。7天提前期的情景模拟中：

![不同补货策略模拟的需求满足率与日均库存](figures/06_inventory.png)

| 模拟策略 | 需求满足率 | 缺货件数 | 平均期末库存（件） | 模拟订货量（件） | 订单事件数 |
|---|---:|---:|---:|---:|---:|
| 定期补货 | {inv.loc['weekly_cover','simulation_fill_rate']:.2%} | {inv.loc['weekly_cover','lost_units']:,.0f} | {inv.loc['weekly_cover','avg_ending_on_hand']:,.0f} | {inv.loc['weekly_cover','total_ordered_units']:,.0f} | {inv.loc['weekly_cover','po_events']:,.0f} |
| 订货点 | {inv.loc['rop','simulation_fill_rate']:.2%} | {inv.loc['rop','lost_units']:,.0f} | {inv.loc['rop','avg_ending_on_hand']:,.0f} | {inv.loc['rop','total_ordered_units']:,.0f} | {inv.loc['rop','po_events']:,.0f} |
| 分类安全库存 | {inv.loc['abc_xyz','simulation_fill_rate']:.2%} | {inv.loc['abc_xyz','lost_units']:,.0f} | {inv.loc['abc_xyz','avg_ending_on_hand']:,.0f} | {inv.loc['abc_xyz','total_ordered_units']:,.0f} | {inv.loc['abc_xyz','po_events']:,.0f} |

相对定期补货，订货点情景减少{inv.loc['weekly_cover','lost_units']-inv.loc['rop','lost_units']:,.0f}件模拟缺货，同时增加约{inv.loc['rop','avg_ending_on_hand']-inv.loc['weekly_cover','avg_ending_on_hand']:,.0f}件日均期末库存。历史价格模型虽然固定28天预测WAPE略低，但递归补货中的缺货件数反而多{candidate.loc['rop','lost_units']-inv.loc['rop','lost_units']:,.0f}件，说明预测误差与下单、到货时点共同影响库存结果。

真实采购价、持有成本、缺货成本、供应商交期和MOQ均缺失；因此只能比较情景，不能判定经济最优或宣称真实库存改善。
'''))
    case_rows=c['case_ledger']; shown=case_rows[case_rows.date.isin(['2016-04-25','2016-04-28','2016-05-04','2016-05-05'])]
    sections.append(('recommendations',f'''## 五、采购与运营行动建议

| 数据发现 | 建议行动 | 优先对象 | 下一步核查 |
|---|---|---|---|
| 食品销售金额占比{food.value_share:.2%}，近56天单店日均销量增长{q.loc['FOODS','change']:+.2%} | 建立每周供货复核清单，查看预测偏差、库存与到货进度 | 高销售金额且近期增长的食品SKU，例如CA_1的FOODS_3_120 | 在架状态、促销计划、实际库存和到货日期 |
| {int(t.sustained_decline.sum()):,}个组合连续两阶段销量下降超过20% | 先查异常再调整补货覆盖，避免把断货当成需求下降 | CA_3的{risk.iloc[0].item_id}等高金额下降组合 | 缺货、下架、替代品、促销结束情况 |
| 价格分析有个案，符合关联条件的组合仅{m['association_eligible']}个 | 对调价周开展活动复盘，记录销量、库存、陈列及促销 | 有足够价格变动和销量记录的商品 | 促销投入、未调价对照、供应恢复情况 |
| WI食品占比高于CA，但单店日均接近 | 按具体门店与SKU核定配置，试行差异化陈列或货架组合 | 同期、同品类、相同商品 | 门店规模、客流、在架及售价 |
| 价格模型测试WAPE仅改善{gain:.2f}个百分点，模拟缺货结果未同步改善 | 保留简单基线，跨更多滚动窗口联合评价误差、库存、缺货和订单 | 30个预测SKU的下一轮验证 | 更多时间窗口、真实供应与成本参数 |

这些行动用于安排复核和后续验证，不表示已在沃尔玛或其他零售企业实施。
'''))
    sections.append(('appendix',f'''## 附录A：范围、口径与方法

### 数据范围

官方M5历史数据涵盖3州10店、30,490个商品—门店组合，历史范围{m['history_start']}至{m['history_end']}，共{m['history_days']:,}天。本次市场窗口为{period}，共364天；销售数量{t.units.sum():,.0f}件，按匹配周零售价估算销售金额${t.sales_value.sum():,.0f}，销量价格匹配率{t.priced_units.sum()/t.units.sum():.0%}。价格不是采购成本。

预测仅使用CA_1预验证历史筛选的30个SKU，验证为两段28天窗口，测试为2016-04-25至2016-05-22。每方法验证1,680个商品·日、测试840个商品·日，测试实际销量17,278件。市场全样本结果和30 SKU预测结果分属不同范围。

### 关键指标定义

- 单店日均销量＝销售数量÷有记录的门店日数。首末不完整月份按各自实际记录日计算。
- 销售金额估算＝销售数量×对应周零售售价。不是利润、采购成本或净销售额。
- 销售金额占比＝对应类别销售金额估算÷同一分析范围全部类别销售金额估算。
- 高波动组合＝完整周销量变异系数CV大于1，且全年销售至少20件；CV＝总体标准差÷均值。
- 连续下降组合＝连续两个56天阶段的单店日均销量均下降超过20%。这是筛查阈值，不是自动淘汰规则。
- WAPE＝全部商品日绝对误差之和÷全部商品日实际销售数量之和。MAE＝商品日绝对误差均值。
- 模拟需求满足率＝模拟履约数量÷历史销量驱动需求数量。模拟库存、采购订单和缺货不属于M5真实字段。

### 预测与补货约束

模型在每个预测起点只使用之前实际销量和当时已知特征，未来28天递归使用模型自身预测；历史售价信息以预测起点最后已知值延续，不读取预测期实际价格。周同期、28日均值和Ridge基础模型均保留。仅验证窗口用于方法选择，测试窗口用于既定方案评估。

库存情景采用7天交期、测试前84天日均销量乘14作为期初库存、期初在途为零。订货点策略按提前期需求和安全库存设触发阈值。订单在下单日加提前期后才入库，策略共享相同需求序列、初始条件、模型和交期。采购成本、持有成本、缺货成本、MOQ和真实PO均未提供。

### 研究边界

历史销售受库存与在架约束，不等于全部潜在需求；价格关联不能证明因果；3州10店不能代表全美市场；30个预测商品不能代表全部SKU。模拟改善不能表述为企业降本、真实缺货下降或沃尔玛运营绩效提升。

完整方法、字段字典和代码定位见[方法说明](../../docs/10_market_methodology.md)、[数据字典](../../docs/11_market_data_dictionary.md)及[代码证据索引](../../docs/19_market_evidence_index.md)。
'''))
    # Keep the full business narrative and the separately linked module reports aligned.
    expanded=[]
    for key,text in sections:
        if key!='price':
            expanded.append((key,text));continue
        price,regional=text.split('## 三、地区与门店差异',1)
        regional,forecast=regional.split('## 四、需求预测与采购判断',1)
        forecast,inventory=forecast.split('### 补货策略需要同时权衡保障水平与库存占用',1)
        expanded.extend([
            ('price',price.rstrip()),
            ('regional','## 三、地区与门店差异'+regional.rstrip()),
            ('forecast','## 四、需求预测与采购判断'+forecast.rstrip()),
            ('inventory','### 补货策略需要同时权衡保障水平与库存占用'+inventory.rstrip()),
        ])
    return expanded

def interview_document(c):
    t=c['item_demand_trends'];food=c['category_totals'].set_index('cat_id').loc['FOODS'];q=c['category_decisions'].set_index('cat_id');va=c['metrics_validation'];te=c['metrics_test'];pc=c['price_case'];s=c['case']
    inv=c['inventory_scores'].query('lead_days==7').set_index('policy');cand=c['inventory_candidate_scores'].set_index('policy')
    gain=(te.loc['ridge','wape']-te.loc['ridge_price_history','wape'])*100
    pr=c['forecast_predictions'].query("stage=='test' and method=='ridge' and item_id=='FOODS_3_120'")
    ae=(pr.actual-pr.prediction).abs().sum();n=len(pr);qty=pr.actual.sum()
    text=f'''# 面试讲解：{TITLE}

文档版本：{REPORT_VERSION}。以下数值均引用当前真实输出；A官方历史、B历史计算、C模型输出、D假设模拟。先读[业务报告](../outputs/m5_market/market_business_report.md)，公式及函数见[证据索引](19_market_evidence_index.md)。讲解以能实际说明和展示的参与程度为准。

## 一、30秒介绍：面向HR

这是一个基于M5公开零售数据的个人商业分析项目。我围绕商品采购和运营，分析10家样本门店的品类销售、价格变化和地区差异，再用30个重点商品比较销量预测和补货方案。结果显示食品是重要销售来源，但价格特征对预测帮助有限；更低预测误差也不一定带来更少模拟缺货。项目产出了七页交互看板和可追溯的业务报告，采购与库存均为情景模拟。

## 二、60—90秒介绍：讲完整业务过程

项目从一个采购问题出发：有限的管理精力应该优先放在哪些商品，怎样根据需求变化安排采购。我使用M5的日销量、周零售价格和日历，先把商品与门店的销售记录匹配起来，分析3州10店、30,490个商品—门店销售组合。

在同一364天内，食品贡献{food.value_share:.2%}的销售金额，最近56天单店日均销量比前一阶段增长{q.loc['FOODS','change']:.2%}；但食品内部有不少高波动商品，因此建议按商品分别复核。地区比较也很有启发：WI食品销售占比较高，但单店日均与CA接近，不能只看占比就增加采购。

预测部分用同30个商品比较简单基线、Ridge基础模型和历史价格模型。价格模型测试WAPE从{te.loc['ridge','wape']:.2%}变为{te.loc['ridge_price_history','wape']:.2%}，改善很小，且多数商品没有受益。补货模拟又显示，价格模型下缺货可能更多。所以我的结论是把预测误差、供应保障和库存占用一起评价，而不是只追求一个更好看的指标。这些是历史分析和模拟结论，没有真实企业降本主张。

## 三、采购管理与品类采购岗位版本

我会先说明采购数量需要建立在商品需求判断上。项目识别了食品的较高销售贡献，并把高金额、高波动、连续下降的商品分别列出。比如CA_1的FOODS_3_120近期日均销量上升，适合优先跟踪供货；连续下降商品则应先排查断货和下架，再决定是否减少订货。

价格分析研究的是零售价格，不是供应商采购价。它帮助我提出活动备货和需求变化的问题，不能直接算采购成本。补货部分用统一条件比较定期补货、订货点和分类安全库存，展示更高保障可能需要更多库存。真正落地还需要供应商交期、最小订货量、采购价、库存和预算。

## 四、市场、商品及产品运营岗位版本

我更关注商品表现背后的业务问题：哪些品类贡献高，近期变化是否持续，价格调整期间发生了什么，以及不同样本门店的商品结构有何差异。食品的金额贡献和近期增长提示可以优先做供货及商品表现复核，但不是所有食品都稳定。

价格案例中，FOODS_3_681降价期间销量上升，下一步应该检查活动、陈列和缺货记录，不能直接说降价产生了增量。地区分析则同时看单店日均和占比，避免把门店数量或其他品类较弱误判为偏好。对产品运营岗位，这体现需求拆解、指标定义、分组比较与验证意识；项目没有用户画像、转化漏斗或产品实验数据，不能冒充用户增长项目。

## 五、真实成果怎样分类表达

| 成果类型 | 已有证据 | 可以怎样说 |
|---|---|---|
| 历史业务发现 B | 364天销售数量{t.units.sum():,.0f}件，零售价格估算销售金额{t.sales_value.sum():,.2f}美元；食品占比{food.value_share:.2%} | 识别样本品类销售结构与复核优先级；金额不是利润 |
| 价格与地区 B | 300价格候选仅4个满足条件；CA、TX、WI按相同期间及门店日比较 | 明确证据不足与可比口径，没有因果价格弹性或市场份额 |
| 预测 C与误差B | 基础Ridge测试WAPE{te.loc['ridge','wape']:.4%}，价格模型{te.loc['ridge_price_history','wape']:.4%} | 小幅下降{gain:.4f}个百分点，{c['improved']}商品改善、{c['worsened']}恶化、{c['unchanged']}基本不变 |
| 库存策略 D | 7天交期Ridge订货点满足率{inv.loc['rop','simulation_fill_rate']:.4%}、日均期末库存{inv.loc['rop','avg_ending_on_hand']:,.2f}件 | 比较统一假设下的保障和占用，没有真实企业库存改善 |

## 六、两个真实商品案例

### 案例1：FOODS_3_120，连接商品判断、预测和补货

这是M5匿名商品编号，不是可识别的真实商品名称。CA_1门店364天销售{s.units:,.0f}件、金额{s.sales_value:,.2f}美元；金额÷数量对应本窗口4.98美元/件零售价格。完整周需求CV为{s.weekly_cv:.4f}，全样本ABC-XYZ为{s.abc_xyz}。最近56天日均{s.recent_56_daily:.2f}件，比此前{s.previous_56_daily:.2f}件增长{s.recent_change:.2%}，可作为供货复核信号。

测试28天实际销售{qty:,.0f}件，基础Ridge总绝对误差{ae:.4f}件，WAPE＝{ae:.4f}÷{qty:,.0f}＝{ae/qty:.4%}；MAE＝{ae:.4f}÷{n}＝{ae/n:.4f}件/日。加历史价格后该SKU误差没有变化，不应强行讲成“价格帮助了它”。

模拟期初库存496件，7天交期。4月28日库存位置400件、订货点403件，触发下单；目标708件，因此下单308件，5月5日到货。当天期末库存77＋308－26＝359件。订单和库存都是模拟，销量来自历史。该案例的全28天策略结果见报告衍生表`report_tables/case_inventory_scores.csv`，不能只用几个顺利到货的日期代表全部商品。

### 案例2：FOODS_3_681，用来解释价格分析的边界

CA_1在{pc.date}所在零售周，售价从{pc.old_price:.2f}变为{pc.new_price:.2f}美元/件；前后各28天日均销量从{pc.pre_units_per_day:.2f}变为{pc.post_units_per_day:.2f}件。能说明降价期间观察到销售变化，但促销、陈列或供应恢复也可能有影响。当前该组合的价格变化次数不足以通过更严格的条件关联门槛；事件前后比较与关联分析有不同的样本条件，不能混为一谈。

## 七、高频追问与可核查回答
'''
    questions=[
    ('为什么选择M5？','判断数据选择是否服务业务问题。','采购与运营需要同一商品在不同日期、门店的销量和价格记录。',f'我使用了官方日销量、周零售售价和日历。数据含3州10店、{c["market_manifest"]["sales_rows"]:,}个销售组合，便于做商品、地区和时间比较；没有采购系统数据。','如果拿到企业数据，首先要补什么？','不能把公开数据研究说成企业真实项目；优先补库存、在架、促销和供应商资料。','E01、E02'),
    ('为什么同时分析品类、价格和地区？','判断能否把分析转成业务行动。','品类回答管理重点，价格回答需求变化线索，地区回答配置是否应有差异。',f'食品占销售金额{food.value_share:.2%}，近期单店日均增长{q.loc["FOODS","change"]:.2%}，但内部高波动组合仍多；价格和地区分析帮助进一步区分需要复核的商品与门店。','三个模块是否都进入预测模型？','只有历史销量、日历及价格特征进入当前预测；州与品类分析主要用于业务洞察，没有声称训练区域模型。','E05—E10'),
    ('为什么原来只选择30个SKU，后来扩大分析范围？','检查代表性、资源约束与数据泄漏。','完整市场结构需要全样本，预测对照则需要固定样本和可比实验。','原30商品从CA_1首次验证之前364天中选取：销售至少20件、最近56天仍有销量，再按销量降序选前30。升级后市场分析扩至全部30,490组合，预测仍保持原30商品和相同日期。','是否有选择偏差？','偏向活跃高销量商品，不能代表低销量、冷启动或所有门店；选品不使用验证及测试销量。','E09、E10'),
    ('为什么使用Ridge回归？','检查是否理解模型适用性而非堆算法。','Ridge把多个预测线索组合，同时约束参数，减少相似销量滞后项带来的不稳定。',f'它与周同期、28日均值做同窗口对照，基础Ridge测试WAPE{te.loc["ridge","wape"]:.2%}，28日均值为{te.loc["moving_mean_28","wape"]:.2%}。输入包括历史销量、星期、月份、节日和SNAP。','为什么不用更复杂模型？','当前先检验基础方法和新增信息价值；没有证据证明Ridge对所有SKU最优，星期和月份以数值编码也有局限。','E10—E12'),
    ('新增价格信息后真的改善了吗？','检查是否诚实解释微小增益和个体差异。','整体误差变小不等于所有商品都变好。',f'验证WAPE从{va.loc["ridge","wape"]:.2%}降到{va.loc["ridge_price_history","wape"]:.2%}；测试从{te.loc["ridge","wape"]:.4%}到{te.loc["ridge_price_history","wape"]:.4%}，仅改善{gain:.4f}个百分点，3个商品改善、12个恶化、15个不变。','为什么没有继续尝试更多价格特征？','方案事先固定，只用验证选择；不根据已看到的测试结果反复调参，也不宣称稳定显著改善。','E11、E12'),
    ('怎样避免偷看未来？','检查回测是否可信。','做某天决策，只能使用当时可以获得的信息。','每个训练样本只使用目标日之前的销量和价格。28天预测将自己的前一天预测递归输入，价格延续最后已知值；确定性日历可用。测试包含扰动未来销量和价格后预测保持不变。','库存模拟每天是否重新训练？','参数固定在测试起点，但每日更新已发生历史用于预测；这与固定起点28天预测不同，不能把两者误差直接等同。','E10、E11、E14'),
    ('如何判断价格与销量的关系？','检查相关性与因果性意识。','先确认价格有足够变化和足够销售，再保持比较窗口可比。',f'300候选中仅4个满足关联条件；有163次变价，103次满足前后各4完整稳定价格周。FOODS_3_681的日均销量由{pc.pre_units_per_day:.2f}到{pc.post_units_per_day:.2f}件，但没有完整促销和库存资料。','有没有控制星期、季节和节日？','完整周保持星期构成，条件关联控制时间趋势、月份周期、节日和SNAP；前后事件比较只记录日历差异，不能说所有方法都完全控制了混杂。','E06、E07'),
    ('地区销售结构差异能说明什么？','检查是否考虑门店规模及分母。','占比体现构成，单店日均体现该样本的平均销售水平，含义不同。','WI食品销量占比70.39%，CA为63.98%，但食品单店日均分别约2,771和2,770件。WI占比较高不能直接解释为食品绝对需求更高。','能建议在WI增加食品采购吗？','只能提出配置复核或试点，还需同SKU、客流、店面积及在架资料；不能代表全州偏好。','E03、E08'),
    ('商品分析怎样指导采购？','判断能否给出具体动作。','先形成需要优先处理的商品清单，再决定要查什么、如何试点。',f'对高金额且近期增长的FOODS_3_120优先复核供货和偏差；对{int(t.sustained_decline.sum()):,}个连续下降组合先查缺货、下架和替代，再讨论收紧补货覆盖。','A类是否全部加安全库存？','不是；ABC按销售金额，不含采购成本，高贡献商品也可能下降或有缺货。市场期后分类没有传入历史模拟。','E05、E09、E13'),
    ('怎样平衡供应保障与库存占用？','检查是否理解业务权衡。','在共同条件下同时比较满足率、缺货件数、库存和在途。',f'7天交期基础Ridge下，订货点满足率{inv.loc["rop","simulation_fill_rate"]:.2%}，定期补货{inv.loc["weekly_cover","simulation_fill_rate"]:.2%}；订货点少缺货{inv.loc["weekly_cover","lost_units"]-inv.loc["rop","lost_units"]:,.0f}件，但日均期末库存多{inv.loc["rop","avg_ending_on_hand"]-inv.loc["weekly_cover","avg_ending_on_hand"]:,.2f}件。','哪种策略最赚钱？','没有采购、库存持有及缺货成本，不能计算利润或成本最优；结果都是D模拟。','E13—E15'),
    ('为什么预测更准，补货反而可能更差？','判断能否连接误差指标与执行结果。','缺货取决于错误出现在哪一天、库存阈值和订单何时到货，而不只看总误差。',f'价格模型WAPE略低，但7天订货点模拟缺货{cand.loc["rop","lost_units"]:,.0f}件，基础模型{inv.loc["rop","lost_units"]:,.0f}件。前者库存略低，保障也较弱。','下一步如何验证？','增加滚动起点和更长模拟，同时看误差方向、缺货日期及末端在途；不能凭这一个窗口宣布价格特征无用。','E12、E15'),
    ('补货模拟修复了什么？','检查能否说明逻辑问题和验证方法。','临近销量末端，订货仍需覆盖完整提前期，不能只预测历史剩余天数。','新版保留官方未来日历，每次至少预测28天，并覆盖提前期加复核期；缺少日历就停止。通过日期边界、未来数据扰动、到货提前期及库存守恒测试。','是否因此消除了所有模拟偏差？','没有，28天评价期、期初14天库存及期末在途仍影响结果；没有长期稳态和真实企业执行证据。','E14、E15'),
    ('WAPE、MAE、销售金额分别怎么算？','检查是否真正理解自己引用的指标。','金额表示按售价估算的销售规模；误差表示预测与真实销售的距离。',f'销售金额＝日销量×对应周零售价格。FOODS_3_120测试销售{qty:,.0f}件、总绝对误差{ae:.4f}件，所以WAPE为{ae/qty:.4%}、MAE为{ae/n:.4f}件/日。总体WAPE要先汇总误差和销量，不能平均SKU百分比。','1减WAPE就是准确率吗？','不是，WAPE甚至可能超过100%；金额不是利润，MAE单位必须带商品·日。','E02、E12'),
    ('项目最大的不足是什么？','检查是否识别真正影响决策的数据缺口。','观察到的销量未必是顾客想买的全部数量。','没有库存和在架记录，无法把无需求与没货卖区分。价格、地区解释和预测训练都可能受影响；再加短测试期，不能直接用于真实采购。','拿到企业数据后第一步做什么？','先对齐销量、库存、缺货、活动和采购订单时间，再验证同一规则，而不是立即增加算法复杂度。','E01、E06、E15'),
    ('哪些内容由AI完成，你本人完成了什么？','检查贡献真实性和能否独立解释结果。','把实际做过的需求定义、开发、复核和讲解分开说明。','项目基于已有工程，代码实现、测试和报告生成主要由Codex辅助完成。我提出了岗位方向、分析范围、真实性要求和迭代需求；当前正在学习业务逻辑和核对结果。面试时只讲自己能够现场复述、计算和演示的部分。','能否现场算一个指标或解释一笔订单？','优先演示上面的FOODS_3_120误差计算与308件订单。不虚构独立设计算法、独立编写全部代码或企业落地经历；尚未亲自完成的核查不能说成个人贡献。','本对话需求记录；E12、E14'),
    ('项目与你申请的岗位有什么联系？','检查能力迁移是否具体。','不同岗位强调同一分析链的不同环节。','采购岗位重点讲商品需求、供货风险和计划；品类/商品运营讲销售结构、价格活动复盘与地区配置；市场运营讲比较方法和证据边界；产品运营讲需求拆解、指标及验证。','是否做过供应商评估或用户增长实验？','没有供应商履约、报价、用户行为或实验数据，不能把本项目包装成这些工作经历。','E01—E15')]
    for i,(question,why,business,answer,follow,boundary,evidence) in enumerate(questions,1):
        text+=f'\n### {i}. {question}\n\n**面试官为什么问：** {why}\n\n**业务解释：** {business}\n\n**参考回答：** {answer}\n\n**进一步追问：** {follow}\n\n**不能夸大：** {boundary}\n\n证据：{evidence}，对应[最新证据索引](19_market_evidence_index.md)。\n'
    text+=f'''\n## 八、可以写进校招简历的项目表述

项目名称：{TITLE}。项目性质：基于M5公开数据、AI辅助开发的个人商业分析项目。

- 基于3州10家样本门店、30,490个商品—门店销售组合，分析品类销售贡献、需求波动、价格变化及地区差异，形成七页交互看板和采购运营复核建议。
- 对30个重点商品开展同窗口预测对照，基础Ridge测试WAPE为{te.loc['ridge','wape']:.2%}，历史价格方案为{te.loc['ridge_price_history','wape']:.2%}，如实分析有限增益与商品差异。
- 在统一假设下比较补货策略，检查采购提前期、完整预测覆盖及库存守恒，解释模拟供应保障与库存占用的权衡。

以上描述项目已具备的产出；使用“负责、独立完成、主导”等个人职责动词前，应有自己的学习、修改或核验记录支持。不要写“提升准确率至69%”“真实降低沃尔玛库存”“节约采购成本”等无依据成果。
'''
    return text

def terminology_document():
    return '''# 统一业务术语与指标口径

适用于当前市场报告、面试文档、README及七页看板。历史基线文档保留原版本，阅读时须按其日期和样本解释。

| 推荐名称 | 定义与单位 | 避免的表述与边界 |
|---|---|---|
| 销售数量 | 已实现销售件数 | 不直接称完整潜在需求 |
| 销售金额 | 日销售数量×匹配周零售价格，美元 | 非利润、采购成本或实收净额 |
| 销售金额占比 | 当前明确样本内品类/商品金额÷样本总金额 | 非全市场份额；需注明筛选分母 |
| 商品—门店销售组合数 | 商品编号和门店编号的不同组合数量 | 非独立商品数量；30,490组合不等于30,490种商品 |
| 单店日均销量 | 销售数量÷实际记录门店日数，件/店·日 | 不用“归一”；当前完整网格等于天数×门店数；未确认实际营业及在架 |
| 月度单店日均销量趋势 | 每月分别按实际记录门店日计算 | 首末不完整月份需标明，不直接比较期间总额 |
| 销量价格匹配率 | 已匹配有效价格销售数量÷总销售数量 | 非有价天数比；零销量分母返回缺失 |
| 商品匹配率的门店均值 | 同SKU各门店匹配率的算术均值 | regional_item_comparison中的price_coverage不能冒充按销量加权匹配率 |
| 需求波动系数 | 完整周销售数量总体标准差÷均值 | 无量纲；品类中位数不等于品类汇总CV |
| 价格变化率 | 新零售价格÷旧零售价格－1 | 价格不等于采购成本；相关不等于因果 |
| 预测误差 WAPE | 绝对误差总和÷实际销量绝对值总和，展示百分比 | 不称准确率，不平均SKU的WAPE |
| 预测误差 MAE | 绝对误差总和÷商品·日样本数，件/商品·日 | 与总误差或总量预测误差不同 |
| 模拟需求满足率 | 模拟满足件数÷作为需求的历史销量 | 非真实订单履约率 |
| 模拟日均期末库存 | 每日所选SKU期末在手库存合计的期间平均，件 | 非实际仓库库存；不等于SKU日均库存 |
| 模拟订货事件数 | 单个SKU单日订货量大于0的记录数 | 不等于合并供应商PO数量 |
| 评价期末模拟在途库存 | 评价最后一天仍未到货订单件数 | 不能视为已入库或忽略其后续占用 |
| 价格调整期间观察到销量变化 | 同一商品窗口前后统计比较 | 未识别因果时不写“降价带来增长” |
| 模拟策略的保障与占用差异 | 同条件模拟结果对照 | 没有成本数据不写“降低采购成本” |

A官方历史、B历史计算、C预测输出、D人为假设及模拟必须保留。技术字段放在[数据字典](11_market_data_dictionary.md)与[证据索引](19_market_evidence_index.md)，业务表格统一使用中文字段。
'''

def methodology_document(c):
    m=c['market_manifest']
    return f'''# 完整分析方法与样本边界

版本{REPORT_VERSION}，基础计算{m['version']}。业务结论见[业务报告](../outputs/m5_market/market_business_report.md)。

## 1. 数据与连接

官方evaluation销量30,490行×1,941天，2011-01-29至2016-05-22；周价格6,841,121行，日历1,969天。销量宽表转为分析矩阵，日历日期编号对应零售周，价格严格按门店、商品和零售周匹配。缺价保留缺失，不从未来补价；负销量或非有限销量拒绝，原始非正/缺失价格及重复价格键拒绝。数据版本及SHA见market_manifest.json。

## 2. 商品、品类与期间比较

市场窗口为2015-05-25至2016-05-22的364天。金额按零售价格估算；匹配率按销售数量加权。每个品类3640个记录门店日，经报告独立核对与天数×店数一致。新增报告按实际记录门店日计算月度单店日均，保留首月7天及末月22天。月份和星期画像属于描述，不是剔除上市、缺货和促销后的因果季节性。

商品趋势比较相邻三个56天：{'; '.join(a+'至'+b for a,b in c['window_dates'])}。连续两次比率均低于0.8标记下降；高销量为全部组合销量前10%阈值及以上；高波动为完整周CV＞1且总销量≥20。

市场ABC按364天全样本中销量价格匹配率≥95%的销售金额，排序后累计前值以80%和95%分档；XYZ用51个完整零售周CV，阈值0.5和1。零销量CV缺失标N，未满足金额匹配条件ABC标U。期后市场分类不用于历史预测和补货决策。

## 3. 价格及地区

价格深度分析为原30商品ID×10店的300个组合，窗口中完整周用于关联。至少26个有价完整周、至少5次价格变化、至少一半周有销售才分析；控制线性趋势、月份sin/cos、节日和SNAP后对log价格与log1p销量计算残差相关。

事件比较要求前后各4个完整、连续、各侧价格稳定的零售周，比较各28天日均；日历构成差异作为记录，不作完整混杂控制。当前163事件中103可比，4组合满足条件关联；无因果弹性及显著性保证。

地区比较同364天，按门店日计算同品类或同SKU销量，再计算州内份额。相对需求指数＝某州某SKU单店日均÷全部10店该SKU单店日均。price_coverage为门店匹配率算术均值，区别于按数量加权匹配率。

## 4. 预测与时点信息

CA_1先在2015-03-02至2016-02-28筛选：销量≥20、最近56天仍有销售，再按销量选前30。同样本验证两折28天、测试28天；Ridge训练每起点之前最多560天，标准化后alpha固定15。基础特征为销量滞后1/7/14/28/56天、7/28日均值与差、28日波动、星期、月份、节日、SNAP。价格候选增加最后已知价log1p、相对过去28天已知均价变化及28天缺价比例。

训练特征严格用目标日前历史。未来销量递归预测，未来价格固定最后已知值，冷启动为0并提供缺价标记；未来日历按预知信息使用。仅验证WAPE选模型。测试已披露，仅作为同协议后续比较；不继续测试驱动调参。

WAPE先汇总绝对误差再除实际销量，MAE除商品·日数；验证每模型1680、测试840个样本。原三方案7560条预测逐行复现。

## 5. 补货与公平比较

固定基础Ridge对照提前期3/7/14天×三策略；验证选定价格模型仅7天候选。评价2016-04-25至05-22。共同期初为ceil(此前84天日均×14)，期初在途0，历史销量为外生模拟需求；每日更新历史但不重训测试起点参数。

安全库存SS＝ceil(z×此前84天日销量总体标准差×sqrt(提前期))。基础订货点z=1.65；分类策略AZ为2.05、其他A为1.75、非A的Z为1.90、其余C为1.10、其他沿用1.65，判断有先后顺序。定期补货无SS，间隔7天。订货点为ceil(提前期预测量)+SS；目标为ceil(提前期+7天预测量)+SS。库存位置为到货后在手加原在途，触发后订货量max(目标－位置,0)。

到货先于当日销售扣减，新订单在下单日+提前期到货；缺货作为流失，不形成欠交。每次至少预测28天，日历不足报错，禁止截短目标需求覆盖。台账按期初+到货－满足=期末及前日在途+新单－到货=当日在途核验。

模拟使用原30SKU预验证ABC，其周销量包含窗口边缘不完整周；市场XYZ只用完整周，不能直接横比。无MOQ、整箱、随机交期、真实成本、暖机或长期稳态保证。指标计算和当前行号见[证据索引](19_market_evidence_index.md)。
'''

def dictionary_document():
    return '''# 数据字典与业务指标

所有表位于outputs/m5_market；技术字段仅用于追溯，业务名称遵循[术语表](20_business_terminology.md)。

| 文件与行粒度 | 主要技术字段 | 中文含义、公式与单位 | 属性 |
|---|---|---|---|
| category_daily：门店×部门×日期 | units, sales_value, priced_units, date | 销售数量、估算销售金额、匹配价格的销售数量；件、美元 | B，由A计算 |
| category_totals / department_totals：全窗口品类或部门 | cat_id, dept_id, units, sales_value, value_share | 商品品类、部门、销售数量、销售金额、全10店样本金额占比 | B |
| category_monthly / quarterly / annual：门店部门期间 | observed_days, units_per_day, value_per_day | 实际天数、单店部门日均销量及金额；部分期间按实际天数 | B |
| item_demand_trends：商品—门店 | units, sales_value, priced_unit_coverage | 364天销售数量、金额、按销量加权价格匹配率；零销量匹配率缺失 | B |
| item_demand_trends：商品—门店 | recent_56_daily, previous_56_daily, earlier_56_daily, recent_change | 三个56天日均销售数量及最近变化率 | B |
| item_demand_trends：商品—门店 | abc_xyz, weekly_cv, price_cv, price_changes | 销售金额及需求波动分类、周销量CV、价格CV、相邻完整周价格变化次数 | B |
| item_demand_trends：商品—门店 | first_price_date, pre_first_price_zero_days, missing_price_sales_units | 首价日期是可售参考；首价前零销售天数为全历史；未匹配销售数量为364天 | B |
| price_change_events：价格调整事件 | old_price, new_price, pre_units_per_day, post_units_per_day, comparable | 前后价格、日均销售数量、是否满足各4完整周比较条件 | B |
| price_associations：候选商品—门店 | weeks, price_changes, status, partial_log_correlation | 有效周数、变化次数、适用状态、控制日历后残差相关；非弹性 | B |
| regional_category_comparison：州×品类 | store_count, observed_days, units_per_store_day, category_unit_share | 门店数、天数、单店日均销量、州内销售数量占比 | B |
| regional_item_comparison：州×商品 | relative_demand_index, price_coverage | 同SKU相对全10店单店日均指数；匹配率的门店算术均值 | B |
| forecast_predictions：阶段×起点×商品×预测日×模型 | actual, prediction, origin, date | 实际销量、预测销量、起点、日期；单位件 | actual为A，prediction为C |
| forecast_metrics / sku_metrics / category_metrics | wape, mae, evaluated_item_days, actual_units | 汇总WAPE、MAE、商品·日样本数、对应实际销售数量 | B，对C评价 |
| forecast_price_deltas：阶段×商品 | wape_ridge, wape_price, wape_change_pp | 两模型WAPE及价格模型减基础模型的百分点变化；负数表示改善 | B |
| classification：原30个商品 | history_value, weekly_cv, abc_xyz | 预验证窗口销售金额与分类，仅用于预测/模拟管理规则 | B |
| inventory_ledger：交期×策略×商品×日 | opening_on_hand, arrivals, demand, fulfilled, lost, ordered, ending_on_hand, in_transit | 期初、到货、历史销售需求、满足、缺货、订货、期末、在途；均为件 | demand为A，其余D |
| inventory_ledger：同上 | safety_stock, reorder_point, inventory_position, target_stock, forecast_days, order_arrival_date | 安全库存、订货点、库存位置、目标、预测天数、预计到货日 | C与D |
| inventory_scores：交期×策略 | simulation_fill_rate, avg_ending_on_hand, total_ordered_units, po_events, terminal_pipeline | 满足率、每日SKU总期末库存均值、订货数量、SKU日订货事件、期末在途 | D |
| inventory_candidate_* | 同上，只有7天交期 | 验证选定预测方案的候选模拟，与基础方案分别呈现 | D |
| inventory_fix_comparison | *_before, *_after | 固定Ridge修复覆盖期前后；旧值只用于修复对照 | D |
| report_tables/monthly_store_day_rates | observed_store_days, units_per_store_day | 由现有日表计算的实际记录门店日数与单店日均 | B，本版报告衍生表 |
| report_tables/category_decisions | earlier, previous, recent, change, high_volatility_count, decline_count | 三个56天单店日均、最近变化率、风险组合数 | B，本版报告衍生表 |

零售价格单位美元/件；金额美元；销量和库存件。份额与WAPE在CSV以小数保存，展示为百分比；变化百分点＝两个比例之差×100。CV无量纲。没有真实采购成本、采购节约、利润或实际库存周转指标。

字段的计算函数、最新行号与测试见[代码证据索引](19_market_evidence_index.md)。
'''
