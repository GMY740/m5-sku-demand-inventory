"""Incremental real-data market research. Baseline outputs/m5 is read-only."""
import argparse,json
from pathlib import Path
from src.market import build_market,sha256
from src.core import load_m5,make_abc_xyz,policy_backtest
from src.market_forecast import run_experiment

def safe_output(root,out):
    dest=Path(out).resolve();baseline=(root/'outputs/m5').resolve()
    if dest==baseline or baseline in dest.parents:raise ValueError('Published outputs/m5 baseline is protected')
    dest.mkdir(parents=True,exist_ok=True);return dest

def main():
    import pandas as pd
    root=Path(__file__).resolve().parent
    pa=argparse.ArgumentParser();pa.add_argument('--raw',default='data/raw');pa.add_argument('--out',default='outputs/m5_market')
    pa.add_argument('--stage',choices=['market','forecast','inventory','report','all','verify'],default='all');args=pa.parse_args()
    raw=Path(args.raw);raw=raw if raw.is_absolute() else root/raw
    out=safe_output(root,root/args.out);base=root/'outputs/m5'
    baseline={f.name:sha256(f) for f in base.iterdir() if f.is_file()}
    if args.stage in ['market','all']:
        m=build_market(raw,out,set(pd.read_csv(base/'items.csv').item_id));print(json.dumps(m,ensure_ascii=False,indent=2),flush=True)
    if args.stage in ['forecast','all']:
        items,y,c,pr,start=load_m5(raw);chosen,_=run_experiment(items,y,c,pr,start,out,base)
        print('Validation selected:',chosen,flush=True)
    if args.stage in ['inventory','all']:
        from src.market_inventory import build_inventory
        build_inventory(raw,out,base)
    if args.stage in ['report','all']:
        from src.market_report import build_market_report
        build_market_report(out,root)
    if args.stage in ['verify','all']:
        from src.market_verify import verify_market
        print(json.dumps(verify_market(out,base,raw),ensure_ascii=False,indent=2))
    assert baseline=={f.name:sha256(f) for f in base.iterdir() if f.is_file()},'Baseline changed'
    print('Published baseline SHA256 unchanged:',len(baseline),'files',flush=True)

if __name__=='__main__':main()
