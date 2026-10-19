"""Chinese business labels for dashboard copies; source data remain unchanged."""
import numpy as np
import pandas as pd

CATEGORY_NAMES={'FOODS':'食品','HOUSEHOLD':'家庭用品','HOBBIES':'兴趣用品'}
STATE_NAMES={'CA':'加利福尼亚州 CA','TX':'得克萨斯州 TX','WI':'威斯康星州 WI'}
METHOD_NAMES={'seasonal_naive_7':'周同期预测','moving_mean_28':'28日均值预测','ridge':'Ridge基础模型','ridge_price_history':'Ridge历史价格模型'}
POLICY_NAMES={'weekly_cover':'定期补货策略','rop':'订货点策略','abc_xyz':'分类安全库存策略'}
FIELD_NAMES={
'cat_id':'商品品类','dept_id':'商品部门','state_id':'州','store_id':'门店','item_id':'商品编号',
'units':'销售数量（件）','sales_value':'销售金额（美元）','priced_units':'已匹配价格的销售数量（件）','value_share':'销售金额占比','unit_share':'销售数量占比',
'priced_unit_coverage':'销量价格匹配率','price_coverage':'商品匹配率的门店均值','observed_days':'统计天数（天）','days':'统计天数（天）','store_count':'门店数（家）','stores':'门店数（家）',
'units_per_day':'日均销售数量（件/日）','units_per_store_day':'单店日均销量（件/店·日）','value_per_day':'日均销售金额（美元/日）','value_per_store_day':'单店日均销售金额（美元/店·日）',
'category_unit_share':'销售数量占比','category_value_share':'销售金额占比','department_value_share_in_store':'门店内部门销售金额占比',
'period':'统计期间','period_start':'期间开始日期','period_end':'期间结束日期','date':'日期','origin':'预测起始日期','d_idx':'历史日序号','month_of_year':'月份','weekday':'星期序号',
'weekly_cv':'需求波动系数','median_weekly_demand_cv':'需求波动系数中位数','price_cv':'价格波动系数','median_price_cv':'价格波动系数中位数','series_count':'商品—门店销售组合数',
'price_changes':'价格变化次数','total_changes':'价格变化总次数','full_weeks':'完整零售周数','weeks':'有效完整零售周数',
'zero_day_share':'零销售天数占比','first_price_date':'首次记录价格日期','pre_first_price_zero_days':'首价记录前零销售天数（天）','pre_first_price_positive_units':'首价记录前销售数量（件）','post_first_price_missing_days':'首价记录后缺价天数（天）','missing_price_sales_units':'未匹配价格的销售数量（件）',
'recent_56_daily':'最近56天日均销售数量（件/日）','previous_56_daily':'前一阶段56天日均销售数量（件/日）','earlier_56_daily':'再前一阶段56天日均销售数量（件/日）',
'recent_change':'最近阶段销售数量变化率','sustained_decline':'是否连续下降','same_dates_prior_year_daily':'去年同期日均销售数量（件/日）','yoy_daily_change':'日均销售数量同比变化率',
'abc':'销售金额分类','xyz':'需求波动分类','abc_xyz':'商品综合分类','high_volume':'是否高销售数量商品','high_value':'是否重点金额商品','high_volatility':'是否高需求波动商品','recommendation':'采购与运营建议',
'history_units':'历史销售数量（件）','history_value':'历史销售金额（美元）','stage':'评估阶段','method':'预测模型','wape':'加权绝对误差率 WAPE','mae':'平均绝对误差 MAE（件/商品·日）','evaluated_item_days':'评估样本量（商品·日）','actual_units':'实际销售数量（件）','observed_units':'实际销售数量（件）','actual':'实际销售数量（件）','prediction':'预测销售数量（件）',
'method_ridge':'基础预测模型','method_price':'价格预测模型','wape_ridge':'基础模型 WAPE','wape_price':'价格模型 WAPE','mae_ridge':'基础模型 MAE（件/商品·日）','mae_price':'价格模型 MAE（件/商品·日）','evaluated_item_days_ridge':'基础模型样本量（商品·日）','evaluated_item_days_price':'价格模型样本量（商品·日）','actual_units_ridge':'基础模型实际销售数量（件）','actual_units_price':'价格模型实际销售数量（件）','wape_change_pp':'WAPE变化（百分点）','mae_change':'MAE变化（件/商品·日）',
'wm_yr_wk':'零售周编号','sell_price':'零售价格（美元/件）','old_price':'调整前价格（美元/件）','new_price':'调整后价格（美元/件）','price_change':'价格变化率','comparable':'是否满足前后比较条件','reason':'前后比较条件说明','pre_units_per_day':'调整前日均销售数量（件/日）','post_units_per_day':'调整后日均销售数量（件/日）','sales_change':'日均销售数量变化率','event_share':'节日天数占比','snap_share':'SNAP适用天数占比','event_share_change':'节日天数占比变化（百分点）','snap_share_change':'SNAP适用天数占比变化（百分点）','partial_log_correlation':'价格与销售数量相关系数','status':'价格关联分析适用性',
'policy':'模拟补货策略','lead_days':'模拟采购提前期（天）','simulation_fill_rate':'模拟需求满足率','demand_units':'作为模拟需求的历史销售数量（件）','fulfilled_units':'模拟需求满足数量（件）','lost_units':'模拟缺货数量（件）','avg_ending_on_hand':'模拟日均期末库存（件）','total_ordered_units':'模拟订货数量（件）','po_events':'模拟订货事件数（次）','terminal_on_hand':'评价期末模拟在手库存（件）','terminal_pipeline':'评价期末模拟在途库存（件）',
'day_index':'历史日序号','day':'模拟日序号','initial_units':'模拟初始库存（件）','arrivals':'模拟到货数量（件）','demand':'作为模拟需求的历史销售数量（件）','fulfilled':'模拟需求满足数量（件）','lost':'模拟缺货数量（件）','ordered':'模拟订货数量（件）','ending_on_hand':'模拟期末库存（件）','in_transit':'模拟在途库存（件）','reorder_point':'模拟订货点（件）','safety_stock':'模拟安全库存（件）','opening_on_hand':'模拟期初在手库存（件）','inventory_position':'模拟库存位置（件）','target_stock':'模拟目标库存（件）','forecast_lead_units':'提前期内预测销售数量（件）','forecast_target_units':'补货覆盖期内预测销售数量（件）','forecast_days':'需求预测覆盖天数（天）','target_coverage_days':'补货目标覆盖天数（天）','order_arrival_date':'模拟订单预计到货日期',
'file':'官方数据文件','size':'文件大小（字节）','sha256':'文件校验值 SHA-256','relative_demand_index':'相对需求指数','total':'全样本销售数量（件）','days_all':'全样本统计天数（天）'
}
PERCENT_FIELDS={'value_share','unit_share','priced_unit_coverage','price_coverage','category_unit_share','category_value_share','department_value_share_in_store','zero_day_share','recent_change','yoy_daily_change','wape','wape_ridge','wape_price','price_change','sales_change','event_share','snap_share','simulation_fill_rate'}
PP_FIELDS={'event_share_change','snap_share_change'}
VALUE_NAMES={**CATEGORY_NAMES,**METHOD_NAMES,**POLICY_NAMES,'validation':'验证期','test':'测试期','eligible':'满足分析条件','insufficient_variation_or_sales':'价格变化或销售记录不足','no_residual_variation':'控制因素后差异不足','isolated_4_week_windows':'前后各4个完整周，各侧价格稳定','edge_missing_or_other_price_changes':'期间不完整、缺价或存在其他价格变化'}

def percent(value):
    if isinstance(value,str) and value.endswith('%'):return value
    return f'{float(value):.2%}' if pd.notna(value) and np.isfinite(float(value)) else '—'

def business_frame(frame,overrides=None):
    """Translate a display/export copy; never modify the calculation frame."""
    d=frame.copy(deep=True)
    for col in d.columns:
        if col in PERCENT_FIELDS:d[col]=d[col].map(percent)
        elif col in PP_FIELDS:d[col]=d[col].map(lambda v:f'{v*100:+.2f}' if pd.notna(v) else '—')
        elif pd.api.types.is_bool_dtype(d[col]):d[col]=d[col].map({True:'是',False:'否'})
        elif pd.api.types.is_object_dtype(d[col]) or pd.api.types.is_string_dtype(d[col]) or isinstance(d[col].dtype,pd.CategoricalDtype):
            d[col]=d[col].map(lambda v:VALUE_NAMES.get(v,v) if isinstance(v,str) else v)
    labels={**FIELD_NAMES,**(overrides or {})}
    return d.rename(columns=labels)
