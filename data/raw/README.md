# M5原始数据获取

本仓库不分发Kaggle官方原始CSV。请自行登录竞赛页面并同意相应条款：
https://www.kaggle.com/competitions/m5-forecasting-accuracy/data

将 calendar.csv、sell_prices.csv、sales_train_evaluation.csv 放到本目录。
程序同时支持 sales_train_validation.csv；两版同时存在时优先读取evaluation版。
本仓库既有真实结果使用evaluation版，其他输入不会复现完全相同的日期与指标。

不得把合成演示结果作为真实M5结果。数据及由其产生的分析内容仍须遵守原来源条款；本仓库不赋予原始数据额外许可。
