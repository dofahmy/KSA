# -*- coding: utf-8 -*-
"""Load trusted Saudi CSV rows via DATABASE_URL, no fabricated or filled sessions.
CSV headers: symbol,session_date,o,h,l,c,volume. Index symbol must be TASI.
"""
import argparse,os
import pandas as pd
from sqlalchemy import create_engine,text
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--stocks',type=Path)
ap.add_argument('--index',type=Path)
ap.add_argument('--schema-only',action='store_true')
ap.add_argument('--replace-existing',action='store_true',help='UPSERT existing symbol/date rows (default: DO NOTHING)')
a=ap.parse_args()
if not os.getenv('DATABASE_URL'):ap.error('DATABASE_URL missing')
if not a.schema_only and (not a.stocks or not a.index):ap.error('Provide --stocks and --index')
eng=create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
with eng.begin() as cn:
    for statement in Path(__file__).with_name('schema.sql').read_text(encoding='utf-8').split(';'):
        if statement.strip():cn.execute(text(statement))
if a.schema_only:print('SAUDI SCHEMA READY');raise SystemExit(0)
for file,table,is_index in ((a.stocks,'sa_tv_stocks_1d',False),(a.index,'sa_tv_indices_1d',True)):
    df=pd.read_csv(file,dtype={'symbol':str})
    req={'symbol','session_date','h','c'}
    if not req.issubset(df.columns):raise SystemExit(f'{file} missing {req-set(df.columns)}')
    df=df.copy()
    df['symbol']=df.symbol.astype(str).str.strip().str.upper()
    if is_index and not df.symbol.eq('TASI').all():raise SystemExit('Index file must contain only TASI')
    if not is_index and df.symbol.str.contains(r'\.CA$',regex=True).any():raise SystemExit('Egyptian .CA symbol found in Saudi file')
    df['session_date']=pd.to_datetime(df.session_date,errors='raise').dt.date
    for field in ('o','h','l','c','volume'):
        if field not in df:df[field]=None
        df[field]=pd.to_numeric(df[field],errors='coerce')
    if df[['symbol','session_date']].duplicated().any():raise SystemExit('Duplicate symbol/day in '+str(file))
    if df.c.isna().any() or df.c.le(0).any() or df.h.isna().any() or df.h.le(0).any():raise SystemExit('Invalid close/high '+str(file))
    if (df.h < df.c).any():raise SystemExit('High less than close: '+str(file))
    if df.volume.lt(0).any():raise SystemExit('Negative volume '+str(file))
    rows=df[['symbol','session_date','o','h','l','c','volume']].astype(object).where(pd.notna(df[['symbol','session_date','o','h','l','c','volume']]),None).to_dict('records')
    stmt=f"""INSERT INTO public.{table}(symbol,session_date,o,h,l,c,volume)
      VALUES(:symbol,:session_date,:o,:h,:l,:c,:volume)
      ON CONFLICT(symbol,session_date) DO {'UPDATE SET o=EXCLUDED.o,h=EXCLUDED.h,l=EXCLUDED.l,c=EXCLUDED.c,volume=EXCLUDED.volume' if a.replace_existing else 'NOTHING'}"""
    with eng.begin() as cn:
        for k in range(0,len(rows),1000):cn.execute(text(stmt),rows[k:k+1000])
    print(table,len(rows),'input rows processed')
print('FINISHED; no missing dates filled')
