# 正式M5数据验收清单（2026-10-16已运行）

- [x] 用户提供calendar.csv、sell_prices.csv及两版sales CSV；复制件SHA-256与源目录一致。竞赛条款由数据提供者自行遵守，本地核验不代替授权证明。
- [x] CSV已放置data/raw，未改列名和内容；本次实际使用evaluation版。
- [x] 执行python run.py --raw data/raw --store CA_1 --top-n 30 --lead-days 7，退出码0。
- [x] data_kind为M5 PUBLIC HISTORICAL SALES。
- [x] 历史2011-01-29至2016-05-22；验证2016-02-29至2016-04-24；测试2016-04-25至2016-05-22，窗口不重叠。
- [x] SKU筛选与分类仅用预验证历史2015-03-02至2016-02-28的364天。
- [x] 30个SKU的价格按销量加权覆盖率均100%，无U类。
- [x] 验证选中Ridge：WAPE 40.42%；留出测试WAPE 30.90%，没有根据测试结果倒选模型。
- [x] 独立重算分类金额、CV、ABC阈值、WAPE/MAE、各表样本量。
- [x] 订单按下单日+7天到货，逐日核验库存及在途守恒。
- [x] 核验库存汇总、PO次数、初始库存公式及策略输入公平性。
- [x] 9项pytest通过；真实看板六页与SKU/提前期/策略筛选通过程序及浏览器检查。
- [x] docs/04_resume.md已按真实输出更新；make_report.py --out outputs/m5已生成7页PDF和离线HTML，完成PDF渲染及HTML图像加载检查。
- [ ] 原算法模拟末端预测覆盖期缩短问题未修复；已在报告、简历与审计记录披露。策略结果仅作为有限窗口情景模拟。

详见audit/real_m5/真实复现验收记录.md及verification.json。
