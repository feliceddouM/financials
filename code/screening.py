# -*- coding: utf-8 -*-
"""
screening.py
選股邏輯：Quality + Value 策略
"""

import pandas as pd
import numpy as np


def calculate_industry_benchmarks(df, industry_col='industry'):
    """
    計算產業指標
    - ROE中位數（每個產業）
    - 本益比平均（每個產業）
    
    Parameters:
    -----------
    df : pandas.DataFrame
        需包含 industry, ROE, PE_ratio 欄位
    industry_col : str
        產業欄位名稱
    
    Returns:
    --------
    pandas.DataFrame
        加入 industry_median_roe, industry_avg_pe 欄位
    """
    df = df.copy()
    
    # 計算每個產業的ROE中位數
    industry_roe = df.groupby(industry_col)['ROE'].median().to_dict()
    df['industry_median_roe'] = df[industry_col].map(industry_roe)
    
    # 計算每個產業的本益比平均
    industry_pe = df.groupby(industry_col)['PE_ratio'].mean().to_dict()
    df['industry_avg_pe'] = df[industry_col].map(industry_pe)
    
    print(f"✓ 產業指標計算完成: {len(industry_roe)} 個產業")
    
    return df


def apply_quality_filter(df):
    """
    品質篩選
    1. ROE > 產業中位數
    2. 負債比率 < 60%
    3. 營收年增率 > 0%
    
    Parameters:
    -----------
    df : pandas.DataFrame
        需包含相關欄位
    
    Returns:
    --------
    pandas.DataFrame
        符合品質標準的公司
    """
    df = df.copy()
    
    # 篩選條件
    quality_mask = (
        df['ROE'].notna() &
        df['industry_median_roe'].notna() &
        (df['ROE'] > df['industry_median_roe']) &  # ROE > 產業中位數
        (df['debt_ratio_q'] < 60) &                 # 負債比率 < 60%
        (df['revenue_yoy'] > 0)                     # 營收成長 > 0%
    )
    
    result = df[quality_mask].copy()
    
    print(f"✓ 品質篩選: {len(result)}/{len(df)} 家公司符合")
    
    return result


def apply_value_filter(df):
    """
    估值篩選
    本益比 < 產業平均 × 0.85（有15%折價空間）
    
    Parameters:
    -----------
    df : pandas.DataFrame
        需包含 PE_ratio, industry_avg_pe
    
    Returns:
    --------
    pandas.DataFrame
        符合估值標準的公司
    """
    df = df.copy()
    
    # 篩選條件
    value_mask = (
        df['PE_ratio'].notna() &
        df['industry_avg_pe'].notna() &
        (df['PE_ratio'] < df['industry_avg_pe'] * 0.85)  # PE < 產業均值 × 0.85
    )
    
    result = df[value_mask].copy()
    
    print(f"✓ 估值篩選: {len(result)}/{len(df)} 家公司符合")
    
    return result


def calculate_signal_score(df):
    """
    計算AI訊號評分
    
    評分標準：
    - ROE improvement > 20%: +2分
    - 淨利年增率 > 50%: +2分
    - 毛利率 improvement > 10%: +1分
    - 營收加速成長（連續2季）: +1分（暫時簡化為營收成長>20%）
    - 本益比折價 > 20%: +1分
    
    總分：
    - ≥4分: ⭐⭐⭐ 強力訊號
    - 2-3分: ⭐⭐ 值得關注
    - <2分: 無標註
    """
    df = df.copy()
    df['signal_score'] = 0
    
    # 1. ROE improvement > 20%
    # ROE_improvement = (ROE_當期 - ROE_去年同期) / ROE_去年同期 × 100%
    # 暫時簡化：只看當期ROE是否顯著高於產業中位數
    roe_improvement_mask = (
        df['ROE'].notna() & 
        df['industry_median_roe'].notna() &
        (df['ROE'] > df['industry_median_roe'] * 1.2)  # 高於產業中位數20%
    )
    df.loc[roe_improvement_mask, 'signal_score'] += 2
    
    # 2. 淨利年增率 > 50%
    high_growth_mask = df['net_income_yoy'] > 50
    df.loc[high_growth_mask, 'signal_score'] += 2
    
    # 3. 毛利率 improvement > 10%
    # gross_margin_yoy_change 已經是百分點變化
    margin_improvement_mask = df['gross_margin_yoy_change'] > 2  # 毛利率提升2個百分點以上
    df.loc[margin_improvement_mask, 'signal_score'] += 1
    
    # 4. 營收高速成長（簡化為 > 20%）
    revenue_growth_mask = df['revenue_yoy'] > 20
    df.loc[revenue_growth_mask, 'signal_score'] += 1
    
    # 5. 本益比折價 > 20%（PE < 產業均值 × 0.8）
    deep_value_mask = (
        df['PE_ratio'].notna() &
        df['industry_avg_pe'].notna() &
        (df['PE_ratio'] < df['industry_avg_pe'] * 0.8)
    )
    df.loc[deep_value_mask, 'signal_score'] += 1
    
    # 訊號強度分類
    df['signal_strength'] = '無'
    df.loc[df['signal_score'] >= 4, 'signal_strength'] = '⭐⭐⭐'
    df.loc[(df['signal_score'] >= 2) & (df['signal_score'] < 4), 'signal_strength'] = '⭐⭐'
    
    print(f"✓ 訊號評分完成:")
    print(f"  - ⭐⭐⭐: {(df['signal_strength'] == '⭐⭐⭐').sum()} 家")
    print(f"  - ⭐⭐: {(df['signal_strength'] == '⭐⭐').sum()} 家")
    
    return df


def screen_stocks(df, industry_col='industry'):
    """
    完整選股流程
    
    Parameters:
    -----------
    df : pandas.DataFrame
        完整的財報+股價資料
        需包含：industry, ROE, debt_ratio_q, revenue_yoy, PE_ratio等欄位
    industry_col : str
        產業欄位名稱
    
    Returns:
    --------
    pandas.DataFrame
        符合Quality+Value標準的公司，按訊號強度排序
    """
    print("=" * 50)
    print("開始選股篩選")
    print("=" * 50)
    
    # 0. 計算產業指標
    df = calculate_industry_benchmarks(df, industry_col)
    
    # 1. 品質篩選
    quality_stocks = apply_quality_filter(df)
    
    # 2. 估值篩選
    final_stocks = apply_value_filter(quality_stocks)
    
    # 3. 計算訊號評分
    final_stocks = calculate_signal_score(final_stocks)
    
    # 4. 排序（訊號強度 > ROE）
    final_stocks = final_stocks.sort_values(
        by=['signal_score', 'ROE'], 
        ascending=[False, False]
    ).reset_index(drop=True)
    
    print("=" * 50)
    print(f"✓ 篩選完成: 共 {len(final_stocks)} 家公司符合標準")
    print("=" * 50)
    
    return final_stocks


def get_screening_summary(screened_df):
    """
    產生篩選結果摘要
    
    Returns:
    --------
    dict
        統計資訊
    """
    summary = {
        'total_companies': len(screened_df),
        'strong_signals': (screened_df['signal_strength'] == '⭐⭐⭐').sum(),
        'moderate_signals': (screened_df['signal_strength'] == '⭐⭐').sum(),
        'avg_roe': screened_df['ROE'].mean(),
        'avg_pe': screened_df['PE_ratio'].mean(),
        'industries': screened_df['industry'].nunique() if 'industry' in screened_df.columns else 0
    }
    
    return summary


if __name__ == '__main__':
    # 測試用
    # 需要先有完整資料：財報 + ROE + 股價 + 產業分類
    test_df = pd.read_csv('../data/processed/complete_data_with_industry.csv')
    
    result = screen_stocks(test_df)
    
    print("\n篩選結果範例（前10家）:")
    display_cols = [
        'company_id', 'company_name', 'industry', 'signal_strength',
        'ROE', 'PE_ratio', 'revenue_yoy', 'debt_ratio_q'
    ]
    print(result[display_cols].head(10).to_string())
    
    # 摘要
    summary = get_screening_summary(result)
    print("\n摘要統計:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
