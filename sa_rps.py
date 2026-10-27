# -*- coding: utf-8 -*-
"""Shared RS math: TASI comparator, exact original eight color rules."""
import numpy as np
import pandas as pd
def compute(stock, index, lookback=50, smooth=7, gray=50):
    x = stock.merge(index, on='session_date', how='inner', validate='one_to_one').sort_values('session_date').reset_index(drop=True)
    if x.empty: return x
    s=x['c'].astype(float); b=x['bc'].astype(float)
    # Pine: first smooth current AND lagged input price by SMA7.
    ss=s.rolling(smooth,min_periods=smooth).mean()
    bb=b.rolling(smooth,min_periods=smooth).mean()
    x['rps']=ss/ss.shift(lookback) - bb/bb.shift(lookback)
    x['gray_sma50']=x.rps.rolling(gray,min_periods=gray).mean()
    x['above_gray']=(x.rps > x.gray_sma50)
    x['cross_up']=(x.rps > x.gray_sma50) & (x.rps.shift(1)<=x.gray_sma50.shift(1))
    x['cross_down']=(x.rps < x.gray_sma50) & (x.rps.shift(1)>=x.gray_sma50.shift(1))
    # Original Pine: AssetBull and CompareBull are 50-session performance signs,
    # computed on SMA7-smoothed prices with no log returns and no ATR normalization.
    asset_bull=ss/ss.shift(lookback)>1
    compare_bull=bb/bb.shift(lookback)>1
    outperform=x.rps>0
    underperform=x.rps<0
    # Preserve all eight Pine states. Condition order matches original Pine exactly.
    states=np.select([
      (~asset_bull)&(~compare_bull)&outperform,
      asset_bull&(~compare_bull)&outperform,
      asset_bull&compare_bull&outperform,
      (~asset_bull)&compare_bull&outperform,
      asset_bull&compare_bull&underperform,
      (~asset_bull)&compare_bull&underperform,
      (~asset_bull)&(~compare_bull)&underperform,
      asset_bull&(~compare_bull)&underperform,
    ], ['ROP','IOP','LOP','LAOP','RUP','IUP','LUP','LAUP'],default='NEUTRAL')
    x['pine_color_code']=states
    x.loc[x.rps.isna(),'pine_color_code']='WARMUP'
    x['rps_minus_gray']=x.rps-x.gray_sma50
    x['date']=x.session_date.dt.strftime('%Y-%m-%d')
    return x

