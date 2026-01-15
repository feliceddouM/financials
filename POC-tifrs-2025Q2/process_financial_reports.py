# -*- coding: utf-8 -*-
"""
MOPS inline XBRL (HTML) quarterly parser - 改良版
根據官方名單處理指定公司的財報
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from bs4 import BeautifulSoup
import pandas as pd

def parse_number(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    s = str(text).strip()
    if s == "":
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace(",", "").replace("(", "").replace(")", "")
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if neg else val

def extract_company_meta(soup: BeautifulSoup):
    cid = cname = year = quarter = None
    for tag in soup.find_all():
        if tag.name and tag.name.lower().endswith("nonnumeric"):
            name = tag.get("name") or ""
            txt = tag.text.strip() if tag.text else ""
            if "tifrs-notes:CompanyID" in name:
                cid = txt
            elif "tifrs-notes:CompanyChineseName" in name:
                cname = txt
            elif "tifrs-notes:Year" in name:
                year = txt
            elif "tifrs-notes:Quarter" in name:
                quarter = txt
    if not (cid and year and quarter):
        title = soup.title.text if soup.title else ""
        m = re.search(r"(\d{4})Q([1-4])", title)
        if m:
            year, quarter = m.group(1), m.group(2)
        m2 = re.search(r"^\s*(\d{4})\s", title)
        if m2:
            cid = m2.group(1)
    return cid, cname, year, quarter

def extract_metrics_from_file(path: Path) -> Dict[str, Any]:
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        cid, cname, year, quarter = extract_company_meta(soup)

        rows: List[tuple] = []
        first_revenue_context = None  # 記錄第一個出現的營收context
        
        for tag in soup.find_all():
            if tag.name and tag.name.lower().endswith("nonfraction"):
                # 讀取數字和正負號屬性
                text = tag.text
                sign = tag.get("sign") or ""
                
                # 解析數字
                value = parse_number(text)
                
                # 如果有 sign="-" 屬性,將數字變成負數
                if value is not None and sign == "-":
                    value = -value
                
                concept = tag.get("name") or ""
                context = tag.get("contextref") or tag.get("contextRef") or ""
                
                # 抓第一個出現的營收context(當年當季單季)
                if concept == "ifrs-full:Revenue" and first_revenue_context is None:
                    if re.match(r'^From\d{8}To\d{8}$', context):
                        first_revenue_context = context
                
                rows.append((concept, context, value))
        
        if not first_revenue_context:
            return {"error": "no_revenue_found", "source_file": path.name, "data_quality": "failed"}
        
        quarter_ctx = first_revenue_context
        
        # 建立去年同季context
        match = re.match(r'^From(\d{8})To(\d{8})$', quarter_ctx)
        if match:
            start = match.group(1)
            end = match.group(2)
            prev_start = str(int(start[:4]) - 1) + start[4:]
            prev_end = str(int(end[:4]) - 1) + end[4:]
            prev_ctx = f"From{prev_start}To{prev_end}"
        else:
            prev_ctx = None
        
        df = pd.DataFrame(rows, columns=["concept", "context", "value"])

        def pick(concept: str, ctx: Optional[str]) -> Optional[float]:
            if not ctx:
                return None
            s = df.loc[(df["concept"] == concept) & (df["context"] == ctx), "value"]
            return float(s.iloc[0]) if len(s) else None

        revenue_concept = "ifrs-full:Revenue"
        op_inc_concept = "ifrs-full:ProfitLossFromOperatingActivities"
        profit_owners_concept = "ifrs-full:ProfitLossAttributableToOwnersOfParent"
        basic_eps_concept = "ifrs-full:BasicEarningsLossPerShare"

        result = {
            "company_id": cid,
            "company_name": cname,
            "year": year,
            "quarter": quarter,
            "quarter_context": quarter_ctx,
            "revenue_q": pick(revenue_concept, quarter_ctx),
            "revenue_prev": pick(revenue_concept, prev_ctx),
            "net_op_income_q": pick(op_inc_concept, quarter_ctx),
            "net_op_income_prev": pick(op_inc_concept, prev_ctx),
            "profit_to_owners_q": pick(profit_owners_concept, quarter_ctx),
            "profit_to_owners_prev": pick(profit_owners_concept, prev_ctx),
            "basic_eps_q": pick(basic_eps_concept, quarter_ctx),
            "basic_eps_prev": pick(basic_eps_concept, prev_ctx),
            "source_file": path.name,
        }
        
        # 驗證context是否符合預期季度
        context_warning = None
        if quarter and quarter_ctx:
            quarter_start_months = {"1": "01", "2": "04", "3": "07", "4": "10"}
            expected_month = quarter_start_months.get(quarter)
            actual_month = quarter_ctx[8:10] if len(quarter_ctx) > 10 else None
            
            if expected_month and actual_month != expected_month:
                context_warning = f"Expected Q{quarter} to start with month {expected_month}, got {actual_month}"
        
        result["context_warning"] = context_warning
        
        # 資料完整性標記
        result["data_quality"] = "complete" if all([
            result.get("revenue_q"), 
            result.get("revenue_prev")
        ]) else "incomplete"
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "source_file": path.name,
            "data_quality": "failed"
        }

def load_official_list(csv_path: str) -> Set[str]:
    """讀取官方名單,回傳股票代號集合"""
    encodings = ['big5', 'utf-8', 'cp950']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            stock_ids = set(df['公司代號'].astype(str).str.strip())
            print(f"✓ 從 {csv_path} 讀取到 {len(stock_ids)} 家公司")
            return stock_ids
        except:
            continue
    
    raise Exception(f"無法讀取CSV: {csv_path}")

def process_batch_with_whitelist(
    input_folder: str, 
    official_csv: str,
    output_csv: str = "financial_metrics.csv"
):
    """根據官方名單批次處理財報"""
    
    # 載入官方名單
    official_ids = load_official_list(official_csv)
    
    folder = Path(input_folder)
    
    # 支援 fr1 和 fr2 的合併報表
    patterns = [
        "tifrs-fr1-m1-ci-cr-*.html",
        "tifrs-fr2-m1-ci-cr-*.html"
    ]
    
    all_files = []
    for pattern in patterns:
        all_files.extend(folder.glob(pattern))
    
    # 只保留官方名單中的公司
    filtered_files = []
    for file in all_files:
        # 從檔名提取股票代號
        match = re.search(r'-(\d{4})-', file.name)
        if match and match.group(1) in official_ids:
            filtered_files.append(file)
    
    files = sorted(filtered_files)
    
    print(f"資料夾共有 {len(all_files)} 個 fr1/fr2-m1-ci-cr 檔案")
    print(f"官方名單有 {len(official_ids)} 家公司")
    print(f"配對成功: {len(files)} 個檔案")
    print(f"開始處理...\n")
    
    results = []
    success_count = 0
    failed_count = 0
    warning_count = 0
    processed_ids = set()
    
    for i, file_path in enumerate(files, 1):
        # 提取股票代號
        match = re.search(r'-(\d{4})-', file_path.name)
        if match:
            processed_ids.add(match.group(1))
        
        print(f"[{i}/{len(files)}] 處理: {file_path.name}", end=" ")
        
        result = extract_metrics_from_file(file_path)
        results.append(result)
        
        if result.get("data_quality") == "complete":
            if result.get("context_warning"):
                print("⚠ context警告")
                warning_count += 1
            else:
                print("✓")
            success_count += 1
        elif result.get("data_quality") == "incomplete":
            print("⚠ 資料不完整")
        else:
            print("✗ 失敗")
            failed_count += 1
    
    # 找出名單中但沒有處理到的公司
    not_processed = official_ids - processed_ids
    
    # 輸出CSV
    df_output = pd.DataFrame(results)
    df_output.to_csv(output_csv, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print(f"處理完成!")
    print(f"{'='*60}")
    print(f"官方名單: {len(official_ids)} 家")
    print(f"找到檔案並處理: {len(files)} 家")
    print(f"  - 成功: {success_count} 家")
    print(f"  - context警告: {warning_count} 家")
    print(f"  - 資料不完整: {len(files) - success_count - failed_count} 家")
    print(f"  - 失敗: {failed_count} 家")
    print(f"名單中但無檔案: {len(not_processed)} 家")
    print(f"實際涵蓋率: {len(files)/len(official_ids)*100:.1f}%")
    print(f"\n輸出檔案: {output_csv}")
    print(f"{'='*60}")
    
    if not_processed and len(not_processed) <= 100:
        print(f"\n未處理的公司: {sorted(not_processed)}")

if __name__ == "__main__":
    import sys
    
    # 參數: 官方CSV, HTML資料夾, 輸出檔案
    official_csv = sys.argv[1] if len(sys.argv) > 1 else "t163sb04_20251013_172201430.csv"
    input_folder = sys.argv[2] if len(sys.argv) > 2 else "../tifrs-2025Q2"
    output_file = sys.argv[3] if len(sys.argv) > 3 else "financial_metrics.csv"
    
    process_batch_with_whitelist(input_folder, official_csv, output_file)