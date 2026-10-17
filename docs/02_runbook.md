# 从零开始：执行与核验操作手册

## 第一步：安装

请安装Python 3.10以上，打开PowerShell进入项目目录，执行：

```powershell
python -m pip install -r requirements.txt
```

## 第二步：先运行合成演示数据

```powershell
python run.py --demo --top-n 18
python -m pytest -q
python -m streamlit run app.py
```

看到看板醒目的 **合成演示数据** 提示，说明演示模式正常。示例数据不适用于正式简历量化成果。

## 第三步：获取官方M5数据

打开 `https://www.kaggle.com/competitions/m5-forecasting-accuracy/data`，登录并同意数据条款，下载 `calendar.csv`、`sell_prices.csv`、`sales_train_validation.csv`（或者同竞赛下的`evaluation`），放到 `data/raw/`。直接复制压缩包到该目录不行：**必须解压CSV**。

## 第四步：正式运行

```powershell
python run.py --raw data/raw --store CA_1 --top-n 30 --lead-days 7
```

控制台和 `outputs/m5/summary.json` 会出现：样本SKU数量、历史区间、验证和测试WAPE、模拟库存策略比较。若结果报错，先核查Kaggle文件是否完整、列名是否符合官方M5结构。建议先跑30个SKU，验证机器稳定后再试60或100。

## 第五步：演示看板

```powershell
python -m streamlit run app.py
```

顶部选择`m5`并切换分类、预测、补货、每日台账、局限说明。现场演示时先说明**真实历史销量≠真实企业库存**。

## 第六步：回答岗位面试

阅读 `docs/03_interview.md`，先练习2分钟的项目讲解，再练习数据来源、为何不使用未来售价、为什么Ridge未必最好、采购提前期如何约束到货、模拟结果能否声称降本等问题。

## 第七步：简历

在成功运行真实M5数据前，**不要**将演示预测误差和库存模拟满足率复制进简历。使用 `docs/04_resume.md` 中的条件模版，并根据真实输出填写。
