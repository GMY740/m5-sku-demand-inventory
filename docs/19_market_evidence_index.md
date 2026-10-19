# 代码、函数与行号证据索引

此索引在本轮代码修改完成后，通过Python语法树读取实际函数起始行；未手工填写行号。数据版本m5_market_v1；报告版本m5_market_business_v2_20261018。

每项按“业务指标 → 已有结果 → 计算代码 → 验证与限制”组织。原始来源哈希见[数据清单](../outputs/m5_market/market_manifest.json)，本轮核验见[文档验收](../validation.md)。

## E01 数据来源、销售数量与样本

**定义：** 销售数量为历史已实现销售；市场364天按商品、门店、日期求和。

**输出及字段：** units、sales_rows、analysis_start/end；3州10店30,490组合。

- [outputs/m5_market/market_manifest.json](../outputs/m5_market/market_manifest.json)
- [outputs/m5_market/category_totals.csv](../outputs/m5_market/category_totals.csv)
- [outputs/m5_market/item_demand_trends.csv](../outputs/m5_market/item_demand_trends.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L98) | `build_market` | 98 |
| [src/core.py](../src/core.py#L26) | `load_m5` | 26 |

**测试与核验：** [test_sku_selection_ignores_validation_and_test](../tests/test_temporal.py#L14)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 历史销量不等于潜在需求，30商品预测样本不代表全市场。

## E02 销售金额与销量价格匹配率

**定义：** 销售金额＝Σ销量×匹配周零售价格；匹配率＝有有效价格的销量÷全部销量；缺价不回填。

**输出及字段：** sales_value、priced_units、priced_unit_coverage、missing_price_sales_units。

- [outputs/m5_market/category_totals.csv](../outputs/m5_market/category_totals.csv)
- [outputs/m5_market/item_demand_trends.csv](../outputs/m5_market/item_demand_trends.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L29) | `match_prices` | 29 |
| [src/market.py](../src/market.py#L98) | `build_market` | 98 |

**测试与核验：** [test_missing_price_not_filled_from_future_or_invalid](../tests/test_market.py#L11)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 零售价格非采购价；零销量匹配率无定义。单SKU区域表price_coverage是门店算术均值。

## E03 单店日均销量

**定义：** Σ销售数量÷去重后的实际记录门店日数；当前完整网格等于店数×统计天数。

**输出及字段：** units、observed_store_days、units_per_store_day；当前每品类3640门店日。

- [outputs/m5_market/category_daily.csv](../outputs/m5_market/category_daily.csv)
- [outputs/m5_market/report_tables/monthly_store_day_rates.csv](../outputs/m5_market/report_tables/monthly_store_day_rates.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market_report.py](../src/market_report.py#L38) | `store_day_rates` | 38 |
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |
| [src/market_dashboard.py](../src/market_dashboard.py#L50) | `render` | 50 |

**测试与核验：** [test_store_day_rates_handles_unequal_coverage_and_departments](../tests/test_market_report.py#L4)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 记录日不是已核实营业日或在架日；看板以完整当前网格为前提。

## E04 销售金额占比

**定义：** 所选品类金额÷同一明确样本总金额；筛选改变看板分母。

**输出及字段：** value_share；报告全部10店364天，FOODS占比55.6862%。

- [outputs/m5_market/category_totals.csv](../outputs/m5_market/category_totals.csv)
- [outputs/m5_market/category_daily.csv](../outputs/m5_market/category_daily.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |
| [src/market_dashboard.py](../src/market_dashboard.py#L50) | `render` | 50 |

**测试与核验：** [test_dashboard_filters_update_kpi_and_export_scope](../tests/test_market_dashboard.py#L8)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 样本金额占比不是美国或州市场份额。

## E05 趋势、需求波动与风险商品

**定义：** 周销量CV＝总体标准差÷均值；连续两次56天日均比率低于0.8标记下降；高波动为CV＞1且销量≥20。

**输出及字段：** weekly_cv、recent_56_daily、previous_56_daily、earlier_56_daily、sustained_decline。

- [outputs/m5_market/item_demand_trends.csv](../outputs/m5_market/item_demand_trends.csv)
- [outputs/m5_market/priority_risk_items.csv](../outputs/m5_market/priority_risk_items.csv)
- [outputs/m5_market/report_tables/category_decisions.csv](../outputs/m5_market/report_tables/category_decisions.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L98) | `build_market` | 98 |
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |

**测试与核验：** [test_period_length_uses_daily_rate](../tests/test_market.py#L17)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 阈值为研究规则；品类中位CV非汇总CV，缺货与低基数可能干扰。

## E06 价格调整前后销售变化

**定义：** 价格变化＝新价÷旧价－1；两侧各4完整连续稳定价格周，销量变化＝后28天日均÷前28天日均－1。

**输出及字段：** old_price、new_price、comparable、pre_units_per_day、post_units_per_day、sales_change。

- [outputs/m5_market/price_change_events.csv](../outputs/m5_market/price_change_events.csv)
- [outputs/m5_market/focus_weekly_prices_sales.csv](../outputs/m5_market/focus_weekly_prices_sales.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L76) | `price_events` | 76 |

**测试与核验：** [test_event_requires_isolated_complete_comparable_weeks](../tests/test_market.py#L29)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 仅观察性前后比较，没有未变价对照组；日历差异记录不等于完全控制混杂。

## E07 条件价格销量关联

**定义：** 至少26有效完整周、5次变化、半数周有销售；控制趋势、月份周期、节日、SNAP后对log价格和log1p周销量求残差相关。

**输出及字段：** status、weeks、price_changes、partial_log_correlation；300候选4合格。

- [outputs/m5_market/price_associations.csv](../outputs/m5_market/price_associations.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L60) | `price_association` | 60 |

**测试与核验：** [test_missing_weeks_do_not_create_price_change_evidence](../tests/test_market.py#L35)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 无因果弹性、统计显著性及品类间可推广价格敏感度。

## E08 地区市场可比性

**定义：** 同期间同品类：销量÷门店数÷天数；州内品类份额用州内分母；同SKU指数为州单店日均÷全10店单店日均。

**输出及字段：** store_count、observed_days、units_per_store_day、category_unit_share、relative_demand_index。

- [outputs/m5_market/regional_category_comparison.csv](../outputs/m5_market/regional_category_comparison.csv)
- [outputs/m5_market/regional_item_comparison.csv](../outputs/m5_market/regional_item_comparison.csv)
- [outputs/m5_market/store_comparison.csv](../outputs/m5_market/store_comparison.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L49) | `regional_comparison` | 49 |
| [src/market.py](../src/market.py#L98) | `build_market` | 98 |

**测试与核验：** [test_region_normalizes_store_counts](../tests/test_market.py#L21)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 当前各店完整同期；店面积、客流和在架未控制，不能外推偏好。

## E09 ABC-XYZ分类与时点隔离

**定义：** 市场ABC以全样本匹配率≥95%的金额排序，累计前值80%/95%分档；市场XYZ用完整周CV的0.5/1阈值；模拟分类用预验证30商品窗口。

**输出及字段：** abc、xyz、abc_xyz、history_value；两套分母和窗口不同。

- [outputs/m5_market/item_demand_trends.csv](../outputs/m5_market/item_demand_trends.csv)
- [outputs/m5_market/classification.csv](../outputs/m5_market/classification.csv)
- [outputs/m5_market/verification.json](../outputs/m5_market/verification.json)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market.py](../src/market.py#L98) | `build_market` | 98 |
| [src/core.py](../src/core.py#L116) | `make_abc_xyz` | 116 |
| [src/market_inventory.py](../src/market_inventory.py#L20) | `build_inventory` | 20 |

**测试与核验：** [test_abc_uses_only_pre_validation_history](../tests/test_core.py#L30)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 市场为期后分析不得倒用于测试模拟；原分类包含边缘不完整周。

## E10 基础Ridge训练与递归预测

**定义：** 每起点前最多560天训练，StandardScaler+Ridge alpha15；销量滞后及日历特征，未来销量递归。

**输出及字段：** origin、date、actual、prediction、method；原7560预测逐条复现。

- [outputs/m5_market/forecast_predictions.csv](../outputs/m5_market/forecast_predictions.csv)
- [outputs/m5_market/forecast_verification.json](../outputs/m5_market/forecast_verification.json)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/core.py](../src/core.py#L75) | `feature` | 75 |
| [src/core.py](../src/core.py#L85) | `train_ridge` | 85 |
| [src/core.py](../src/core.py#L106) | `forecast` | 106 |

**测试与核验：** [test_ridge_training_and_recursion_ignore_future](../tests/test_temporal.py#L5)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 只测试30个活跃高销量商品；数值星期/月编码有局限。

## E11 历史价格特征与验证选模

**定义：** 最后已知价log1p、相对过去28天均价、缺价比例；递归延续起点已知价格；仅验证WAPE选择。

**输出及字段：** price_features、selected_method、selection_basis；测试前写入选择记录。

- [outputs/m5_market/model_selection.json](../outputs/m5_market/model_selection.json)
- [outputs/m5_market/forecast_predictions.csv](../outputs/m5_market/forecast_predictions.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market_forecast.py](../src/market_forecast.py#L14) | `historical_price_features` | 14 |
| [src/market_forecast.py](../src/market_forecast.py#L34) | `train_price_ridge` | 34 |
| [src/market_forecast.py](../src/market_forecast.py#L24) | `PriceRidge.forecast` | 24 |
| [src/market_forecast.py](../src/market_forecast.py#L48) | `run_experiment` | 48 |

**测试与核验：** [test_price_model_training_and_forecast_ignore_future_sales_and_price](../tests/test_market_forecast.py#L10)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 价格持平是预测假设，非未来促销计划；测试已公开，无全新未见验证。

## E12 WAPE与MAE及模型差异

**定义：** WAPE＝Σ|实际－预测|÷Σ|实际|；MAE＝Σ|实际－预测|÷商品日数；价格WAPE减基础WAPE后×100为百分点变化。

**输出及字段：** wape、mae、evaluated_item_days、wape_change_pp。

- [outputs/m5_market/forecast_metrics.csv](../outputs/m5_market/forecast_metrics.csv)
- [outputs/m5_market/forecast_price_deltas.csv](../outputs/m5_market/forecast_price_deltas.csv)
- [outputs/m5_market/report_tables/report_checks.json](../outputs/m5_market/report_tables/report_checks.json)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/core.py](../src/core.py#L20) | `wape` | 20 |
| [src/market_forecast.py](../src/market_forecast.py#L40) | `summarize_predictions` | 40 |
| [src/market_forecast.py](../src/market_forecast.py#L48) | `run_experiment` | 48 |
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |

**测试与核验：** [test_forecast_filtered_metric_is_weighted_total_not_sku_average](../tests/test_market_dashboard.py#L14)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** WAPE不是准确率、官方WRMSSE或SKU百分比误差均值。

## E13 安全库存、订货点与目标库存

**定义：** SS＝ceil(z×测试前84天日销量标准差×sqrt(L))；ROP＝ceil(预测L天量)+SS；目标＝ceil(预测L+7天量)+SS；位置＝在手+原在途。

**输出及字段：** safety_stock、reorder_point、target_stock、inventory_position、ordered。

- [outputs/m5_market/inventory_ledger.csv](../outputs/m5_market/inventory_ledger.csv)
- [outputs/m5_market/inventory_manifest.json](../outputs/m5_market/inventory_manifest.json)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/core.py](../src/core.py#L179) | `Policy` | 179 |
| [src/core.py](../src/core.py#L186) | `simulate_one` | 186 |

**测试与核验：** [test_current_decision_ignores_current_and_future_sales](../tests/test_market_inventory.py#L27)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** z、L和期初库存为假设；SS并非经校准预测误差，不能保证理论服务水平。

## E14 到货提前期、完整覆盖及库存守恒

**定义：** 到货日＝下单日+L；期末＝期初+到货－满足；在途＝前日在途+新单－到货；预测天数≥max(L+7,28)。

**输出及字段：** order_arrival_date、arrivals、ending_on_hand、in_transit、forecast_days、target_coverage_days。

- [outputs/m5_market/inventory_ledger.csv](../outputs/m5_market/inventory_ledger.csv)
- [outputs/m5_market/inventory_candidate_ledger.csv](../outputs/m5_market/inventory_candidate_ledger.csv)
- [outputs/m5_market/inventory_fix_comparison.csv](../outputs/m5_market/inventory_fix_comparison.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/core.py](../src/core.py#L106) | `forecast` | 106 |
| [src/core.py](../src/core.py#L186) | `simulate_one` | 186 |
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |

**测试与核验：** [test_po_arrivals_inventory_and_pipeline_conserve_each_day](../tests/test_market_inventory.py#L16)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 仍有有限期末端、空在途和初始库存影响；历史外生销售不受模拟缺货约束。

## E15 策略评价与供应保障库存权衡

**定义：** 满足率＝Σ满足÷Σ历史需求；平均库存＝每日SKU期末总量的均值；订货事件＝ordered＞0记录数；同时报告期末在途。

**输出及字段：** simulation_fill_rate、avg_ending_on_hand、total_ordered_units、po_events、terminal_pipeline。

- [outputs/m5_market/inventory_scores.csv](../outputs/m5_market/inventory_scores.csv)
- [outputs/m5_market/inventory_candidate_scores.csv](../outputs/m5_market/inventory_candidate_scores.csv)
- [outputs/m5_market/inventory_fix_comparison.csv](../outputs/m5_market/inventory_fix_comparison.csv)

| 代码文件 | 函数/类 | 最新起始行 |
|---|---|---:|
| [src/market_inventory.py](../src/market_inventory.py#L10) | `score_ledger` | 10 |
| [src/market_inventory.py](../src/market_inventory.py#L20) | `build_inventory` | 20 |
| [src/market_report.py](../src/market_report.py#L47) | `collect_evidence` | 47 |

**测试与核验：** [test_end_of_sales_keeps_full_target_coverage](../tests/test_market_inventory.py#L8)；本轮report_checks逐项重算销售汇总、预测误差、库存指标并核验到货和守恒。日期不足另外由test_insufficient_known_calendar_fails_explicitly检查。测试数据为校验夹具，不用于真实业务成果。

**限制：** 同SKU、需求、初始、交期和方法比较；保障与占用不同向，无真实成本最优结论。

## 文档与看板生成入口

- [src/market_report.py 第250行](../src/market_report.py#L250)：`build_market_report`。
- [src/market_report_content.py 第6行](../src/market_report_content.py#L6)：`business_sections`。
- [src/market_report_content.py 第173行](../src/market_report_content.py#L173)：`interview_document`。
- [src/market_dashboard.py 第50行](../src/market_dashboard.py#L50)：`render`。
- [src/dashboard_labels.py 第37行](../src/dashboard_labels.py#L37)：`business_frame`。
