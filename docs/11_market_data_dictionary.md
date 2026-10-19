# 数据字典与业务指标

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
