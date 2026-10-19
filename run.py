"""One-command reproducible entry point.

Examples:
 python run.py --demo
 python run.py --raw data/raw --top-n 60 --store CA_1
"""
import argparse
import json
from pathlib import Path
from src.core import build_full_project
from src.demo_data import build_demo

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true',help='Generate/use synthetic M5-format example data')
    parser.add_argument('--raw',default='data/raw',help='Real Kaggle M5 files directory')
    parser.add_argument('--top-n',type=int,default=30)
    parser.add_argument('--store',default='CA_1')
    parser.add_argument('--lead-days',type=int,default=7)
    parser.add_argument('--out',default=None)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    raw=(root/'data/demo') if args.demo else Path(args.raw)
    if not raw.is_absolute():raw=root/raw
    if args.demo and not (raw/'sales_train_validation.csv').exists():build_demo(raw)
    out=(root/('outputs/demo' if args.demo else 'outputs/m5_market/core_reproduction')) if args.out is None else Path(args.out)
    summary,_=build_full_project(raw,out,args.store,args.top_n,source='demo' if args.demo else 'm5',lead_days=args.lead_days)
    print(json.dumps({k:summary[k] for k in ['data_kind','sku_count','history_days','selected_forecast_method','validation_wape','test_wape','inventory_results']},ensure_ascii=False,indent=2))
    print('Saved results in:',out)
