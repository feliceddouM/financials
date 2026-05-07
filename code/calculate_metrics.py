# -*- coding: utf-8 -*-
"""
calculate_metrics.py
計算衍生財務指標：ROE、股東權益等
"""

import pandas as pd
import numpy as np


def calculate_shareholders_equity(df):
    """
    計算股東權益
    股東權益 = 總資產 - 總負債
    """
    df = df.copy()
    
    # 當季股東權益
    df['shareholders_equity_q'] = (
        df['total_assets_q'] - df['total_liabilities_q']
    ).round(2)
    
    # 去年同期股東權益（用於計算平均）
    df['shareholders_equity_q_prev'] = (
        df['total_assets_q_prev'] - df['total_liabilities_q_prev']
    ).round(2)
    
    return df


def calculate_roe(df):
    """
    計算ROE (股東權益報酬率)
    ROE = 淨利 / 平均股東權益 × 100%
    
    使用年化淨利（ytd）和平均股東權益
    """
    df = df.copy()
    
    # 平均股東權益 = (期初 + 期末) / 2
    df['avg_shareholders_equity'] = (
        (df['shareholders_equity_q'] + df['shareholders_equity_q_prev']) / 2
    ).round(2)
    
    # ROE = 年化淨利 / 平均股東權益 × 100%
    # 避免除以零
    df['ROE'] = np.where(
        df['avg_shareholders_equity'] > 0,
        (df['net_income_ytd'] / df['avg_shareholders_equity'] * 100).round(2),
        None
    )
    
    return df


def calculate_all_metrics(df):
    """
    計算所有衍生指標
    
    Parameters:
    -----------
    df : pandas.DataFrame
        從parse_mops_reports.py輸出的財報資料
    
    Returns:
    --------
    pandas.DataFrame
        加入ROE等衍生指標的資料
    """
    df = df.copy()
    
    # 1. 計算股東權益
    df = calculate_shareholders_equity(df)
    
    # 2. 計算ROE
    df = calculate_roe(df)
    
    print(f"✓ 計算完成: {len(df)} 筆資料")
    print(f"  - 有效ROE: {df['ROE'].notna().sum()} 筆")
    
    return df


if __name__ == '__main__':
    # 測試用
    test_df = pd.read_csv('../data/processed/financial_metrics_2025Q3.csv')
    result = calculate_all_metrics(test_df)
    
    # 顯示範例
    sample = result[result['ROE'].notna()].head()
    print("\n範例資料:")
    print(sample[['company_id', 'company_name', 'net_income_ytd', 
                  'shareholders_equity_q', 'ROE']].to_string())
