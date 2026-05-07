# -*- coding: utf-8 -*-
"""
fetch_stock_price.py
抓取台股股價並計算本益比
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
import time


def get_tw_stock_price(stock_id, retry=3):
    """
    抓取單一台股的當前股價
    
    Parameters:
    -----------
    stock_id : str
        股票代號（例如 '2330'）
    retry : int
        重試次數
    
    Returns:
    --------
    dict
        {'price': float, 'error': str or None}
    """
    # 台股代碼格式：股號.TW（上市）或 .TWO（上櫃）
    # 先試.TW，失敗再試.TWO
    for suffix in ['.TW', '.TWO']:
        ticker = f"{stock_id}{suffix}"
        
        for attempt in range(retry):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # 嘗試多種價格欄位
                price = (
                    info.get('currentPrice') or 
                    info.get('regularMarketPrice') or 
                    info.get('previousClose')
                )
                
                if price and price > 0:
                    return {'price': round(price, 2), 'error': None}
                    
            except Exception as e:
                if attempt == retry - 1:
                    continue  # 試下一個suffix
                time.sleep(0.5)  # 短暫延遲後重試
    
    return {'price': None, 'error': 'not_found'}


def add_stock_prices(financial_df, verbose=True):
    """
    批次抓取股價並加入財報資料
    
    Parameters:
    -----------
    financial_df : pandas.DataFrame
        財報資料（需包含 company_id, eps_ytd 欄位）
    verbose : bool
        是否顯示進度
    
    Returns:
    --------
    pandas.DataFrame
        加入 stock_price, PE_ratio 欄位的資料
    """
    df = financial_df.copy()
    
    # 取得唯一的公司代號
    unique_ids = df['company_id'].unique()
    total = len(unique_ids)
    
    print(f"開始抓取 {total} 家公司股價...")
    
    # 建立股價對照表
    price_map = {}
    success_count = 0
    
    for idx, stock_id in enumerate(unique_ids, 1):
        if verbose and idx % 50 == 0:
            print(f"  進度: {idx}/{total} ({idx/total*100:.1f}%)")
        
        result = get_tw_stock_price(stock_id)
        price_map[stock_id] = result['price']
        
        if result['price'] is not None:
            success_count += 1
        
        # 避免過於頻繁請求
        if idx % 10 == 0:
            time.sleep(0.5)
    
    # 將股價加入DataFrame
    df['stock_price'] = df['company_id'].map(price_map)
    
    print(f"\n✓ 完成: {success_count}/{total} 家公司 ({success_count/total*100:.1f}%)")
    
    return df


def calculate_pe_ratio(df):
    """
    計算本益比
    P/E Ratio = 股價 / 每股盈餘（年化）
    
    Parameters:
    -----------
    df : pandas.DataFrame
        需包含 stock_price, eps_ytd 欄位
    
    Returns:
    --------
    pandas.DataFrame
        加入 PE_ratio 欄位
    """
    df = df.copy()
    
    # 本益比 = 股價 / EPS（年化）
    # 避免除以零或負數EPS
    df['PE_ratio'] = None
    
    valid_mask = (
        df['stock_price'].notna() & 
        df['eps_ytd'].notna() & 
        (df['eps_ytd'] > 0)
    )
    
    df.loc[valid_mask, 'PE_ratio'] = (
        df.loc[valid_mask, 'stock_price'] / df.loc[valid_mask, 'eps_ytd']
    ).round(2)
    
    print(f"✓ 本益比計算完成: {df['PE_ratio'].notna().sum()} 筆有效資料")
    
    return df


def add_stock_metrics(financial_df, verbose=True):
    """
    完整流程：抓股價 + 計算本益比
    
    Parameters:
    -----------
    financial_df : pandas.DataFrame
        財報資料
    verbose : bool
        是否顯示進度
    
    Returns:
    --------
    pandas.DataFrame
        加入股價與本益比的完整資料
    """
    # 1. 抓取股價
    df = add_stock_prices(financial_df, verbose=verbose)
    
    # 2. 計算本益比
    df = calculate_pe_ratio(df)
    
    return df


if __name__ == '__main__':
    # 測試用
    test_df = pd.read_csv('../data/processed/financial_metrics_2025Q3.csv')
    
    # 只測試前10家
    test_sample = test_df.head(10)
    result = add_stock_metrics(test_sample, verbose=True)
    
    print("\n範例結果:")
    print(result[['company_id', 'company_name', 'stock_price', 
                  'eps_ytd', 'PE_ratio']].to_string())
