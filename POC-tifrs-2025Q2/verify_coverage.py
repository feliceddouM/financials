# -*- coding: utf-8 -*-
"""
驗證財報處理涵蓋率
根據觀測站匯總報表名單,檢查哪些公司有對應的HTML檔案並成功解析
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Set
import re

def load_official_list(csv_path: str) -> pd.DataFrame:
    """讀取觀測站匯總報表,提取公司清單"""
    # 嘗試不同編碼
    encodings = ['big5', 'utf-8', 'cp950']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            print(f"✓ 成功用 {encoding} 編碼讀取CSV")
            break
        except:
            continue
    else:
        raise Exception("無法讀取CSV檔案")
    
    # 提取公司代號和名稱
    company_list = df[['公司代號', '公司名稱']].copy()
    company_list.columns = ['stock_id', 'company_name']
    
    # 轉換股票代號為字串,確保格式一致
    company_list['stock_id'] = company_list['stock_id'].astype(str).str.strip()
    
    print(f"✓ 從CSV讀取到 {len(company_list)} 家公司")
    
    return company_list

def find_available_html_files(html_folder: str, pattern: str = "tifrs-fr1-m1-ci-cr") -> Set[str]:
    """找出資料夾中所有符合格式的HTML檔案對應的公司代號"""
    folder = Path(html_folder)
    
    # 列出所有HTML檔案
    all_html_files = list(folder.glob("*.html"))
    
    stock_ids = set()
    for file in all_html_files:
        # 嚴格驗證檔名格式: tifrs-fr1-m1-ci-cr-XXXX-2025Q2.html
        # 必須完全匹配這個格式
        match = re.match(rf'^{re.escape(pattern)}-(\d{{4}})-\d{{4}}Q[1-4]\.html$', file.name)
        if match:
            stock_ids.add(match.group(1))
    
    print(f"✓ 找到 {len(stock_ids)} 個 {pattern} 格式的HTML檔案")
    print(f"  (資料夾共有 {len(all_html_files)} 個HTML檔案)")
    
    return stock_ids

def compare_coverage(official_list: pd.DataFrame, available_ids: Set[str]) -> Dict:
    """比對官方名單和實際可處理的檔案"""
    official_ids = set(official_list['stock_id'].values)
    
    # 計算交集和差集
    matched = official_ids & available_ids
    missing = official_ids - available_ids
    extra = available_ids - official_ids
    
    # 準備報告
    result = {
        'total_official': len(official_ids),
        'total_available': len(available_ids),
        'matched_count': len(matched),
        'missing_count': len(missing),
        'extra_count': len(extra),
        'matched_ids': sorted(matched),
        'missing_ids': sorted(missing),
        'extra_ids': sorted(extra)
    }
    
    # 提取缺少檔案的公司詳細資訊
    missing_companies = official_list[official_list['stock_id'].isin(missing)].copy()
    result['missing_companies'] = missing_companies
    
    return result

def print_report(result: Dict):
    """印出驗證報告"""
    print("\n" + "="*60)
    print("涵蓋率驗證報告")
    print("="*60)
    
    print(f"\n【總覽】")
    print(f"觀測站官方名單: {result['total_official']} 家公司")
    print(f"本機HTML檔案: {result['total_available']} 個檔案")
    print(f"成功配對: {result['matched_count']} 家")
    print(f"涵蓋率: {result['matched_count']/result['total_official']*100:.1f}%")
    
    if result['missing_count'] > 0:
        print(f"\n【缺少的公司】共 {result['missing_count']} 家")
        print("前20家:")
        df_missing = result['missing_companies'].head(20)
        for _, row in df_missing.iterrows():
            print(f"  {row['stock_id']} - {row['company_name']}")
        
        if result['missing_count'] > 20:
            print(f"  ... 還有 {result['missing_count'] - 20} 家")
    
    if result['extra_count'] > 0:
        print(f"\n【多餘的檔案】共 {result['extra_count']} 個")
        print("(這些檔案不在官方名單中,可能是其他類型的公司)")
        print(f"前10個: {', '.join(list(result['extra_ids'])[:10])}")
    
    print("\n" + "="*60)

def save_missing_list(result: Dict, output_file: str = "missing_companies.csv"):
    """儲存缺少的公司清單"""
    if result['missing_count'] > 0:
        result['missing_companies'].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 缺少的公司清單已儲存至: {output_file}")

if __name__ == "__main__":
    import sys
    
    # 預設路徑已調整為你的資料夾結構
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "t163sb04_20251013_172201430.csv"
    html_folder = sys.argv[2] if len(sys.argv) > 2 else "../tifrs-2025Q2"  
    
    print("開始驗證涵蓋率...")
    print(f"CSV檔案: {csv_path}")
    print(f"HTML資料夾: {html_folder}\n")
    
    # 載入官方名單
    official_list = load_official_list(csv_path)
    
    # 找出可用的HTML檔案(只找 tifrs-fr1-m1-ci-cr 格式)
    available_ids = find_available_html_files(html_folder)
    
    # 比對並產生報告
    result = compare_coverage(official_list, available_ids)
    print_report(result)
    
    # 儲存缺少的公司清單
    save_missing_list(result)