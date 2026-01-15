# -*- coding: utf-8 -*-
"""
搜尋缺少的公司,統計檔名格式
"""

import pandas as pd
from pathlib import Path
import re
from collections import Counter

def find_all_formats_for_missing(missing_csv: str, html_folder: str):
    """搜尋缺少公司的所有可能HTML檔案,統計格式"""
    
    # 讀取缺少的公司清單
    try:
        missing_df = pd.read_csv(missing_csv, encoding='utf-8-sig')
        if len(missing_df) == 0:
            print("錯誤: CSV檔案是空的")
            return
    except Exception as e:
        print(f"錯誤: 無法讀取CSV - {e}")
        return
    
    missing_ids = missing_df['stock_id'].astype(str).str.strip().tolist()
    
    # 取得資料夾中所有HTML檔案
    folder = Path(html_folder)
    if not folder.exists():
        print(f"錯誤: 資料夾不存在 - {html_folder}")
        return
    
    all_html = list(folder.glob("*.html"))
    
    print(f"搜尋 {len(missing_ids)} 家缺少的公司...")
    print(f"資料夾共有 {len(all_html)} 個HTML檔案\n")
    
    # 統計找到的檔案格式
    format_counter = Counter()
    found_companies = []
    not_found_companies = []
    
    for stock_id in sorted(missing_ids):
        matching_files = []
        
        for file in all_html:
            if re.search(rf'-{stock_id}-', file.name):
                matching_files.append(file.name)
                
                # 提取格式: tifrs-fr1-m1-ci-cr
                match = re.match(r'^(tifrs-[^-]+-[^-]+-[^-]+-[^-]+)', file.name)
                if match:
                    format_pattern = match.group(1)
                    format_counter[format_pattern] += 1
        
        company_row = missing_df[missing_df['stock_id'].astype(str).str.strip() == stock_id]
        if len(company_row) > 0:
            company_name = company_row['company_name'].values[0]
            
            if matching_files:
                found_companies.append((stock_id, company_name, len(matching_files)))
            else:
                not_found_companies.append((stock_id, company_name))
    
    # 輸出統計表
    print("="*70)
    print("檔名格式統計表")
    print("="*70)
    
    if format_counter:
        print(f"\n找到的檔案格式分布:")
        for format_pattern, count in format_counter.most_common():
            print(f"  {format_pattern:<30} {count:>3} 個檔案")
    
    print(f"\n{'='*70}")
    print(f"【總結】")
    print(f"{'='*70}")
    print(f"搜尋對象: {len(missing_ids)} 家公司")
    print(f"找到其他格式: {len(found_companies)} 家 ({len(found_companies)/len(missing_ids)*100:.1f}%)")
    print(f"完全缺少: {len(not_found_companies)} 家 ({len(not_found_companies)/len(missing_ids)*100:.1f}%)")
    
    if not_found_companies:
        print(f"\n完全缺少的公司:")
        for stock_id, company_name in not_found_companies:
            print(f"  {stock_id} - {company_name}")

if __name__ == "__main__":
    import sys
    
    missing_csv = sys.argv[1] if len(sys.argv) > 1 else "missing_companies.csv"
    html_folder = sys.argv[2] if len(sys.argv) > 2 else "../tifrs-2025Q2"
    
    find_all_formats_for_missing(missing_csv, html_folder)