# -*- coding: utf-8 -*-
"""
MOPS inline XBRL (HTML) quarterly parser - 擴充版
支援更多財務指標、YoY計算、合併報表+個別報表
"""

import re
from pathlib import Path
from typing import Optional, Dict, Any, Set
from bs4 import BeautifulSoup
import pandas as pd

def parse_number(text: Optional[str]) -> Optional[float]:
    """解析數字字串,處理千分位和括號負數"""
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

def to_millions(value: Optional[float]) -> Optional[float]:
    """將千元轉換為百萬元,四捨五入到小數點後2位"""
    if value is None:
        return None
    return round(value / 1000, 2)

def extract_company_meta(soup: BeautifulSoup):
    """提取公司基本資訊"""
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

def extract_by_code_and_context(soup: BeautifulSoup, code: str, context: str) -> Optional[float]:
    """
    用會計科目代號和context抓取數字
    處理 sign="-" 屬性
    """
    # 找到代號對應的那一行 <tr>
    code_td = soup.find('td', string=code)
    if not code_td:
        return None
    
    # 找到這個td的父元素(tr)
    tr = code_td.find_parent('tr')
    if not tr:
        return None
    
    # 在這一行中找所有 ix:nonFraction 標籤
    for tag in tr.find_all():
        if tag.name and 'nonfraction' in tag.name.lower():
            tag_context = tag.get('contextref') or tag.get('contextRef') or ""
            
            if tag_context == context:
                # 找到了!提取數字
                text = tag.text
                sign = tag.get('sign') or ""
                
                value = parse_number(text)
                
                # 處理負號屬性
                if value is not None and sign == "-":
                    value = -value
                
                return value
    
    return None

def build_contexts(year: str, quarter: str) -> Dict[str, str]:
    """
    根據年度和季度建立所需的contexts
    """
    # 季度起始月份
    quarter_start_months = {
        "1": ("01", "01", "03", "31"),  # Q1: 1/1-3/31
        "2": ("04", "01", "06", "30"),  # Q2: 4/1-6/30
        "3": ("07", "01", "09", "30"),  # Q3: 7/1-9/30
        "4": ("10", "01", "12", "31"),  # Q4: 10/1-12/31
    }
    
    # 累計結束月日
    ytd_end_months = {
        "1": ("03", "31"),
        "2": ("06", "30"),
        "3": ("09", "30"),
        "4": ("12", "31"),
    }
    
    if quarter not in quarter_start_months:
        return {}
    
    year_int = int(year)
    prev_year = str(year_int - 1)
    
    start_m, start_d, end_m, end_d = quarter_start_months[quarter]
    ytd_end_m, ytd_end_d = ytd_end_months[quarter]
    
    contexts = {
        # 損益表 - 單季
        'q_current': f"From{year}{start_m}{start_d}To{year}{end_m}{end_d}",
        'q_prev': f"From{prev_year}{start_m}{start_d}To{prev_year}{end_m}{end_d}",
        
        # 損益表 - 累計
        'ytd_current': f"From{year}0101To{year}{ytd_end_m}{ytd_end_d}",
        'ytd_prev': f"From{prev_year}0101To{prev_year}{ytd_end_m}{ytd_end_d}",
        
        # 資產負債表 - 時點
        'bs_current': f"AsOf{year}{end_m}{end_d}",
        'bs_prev': f"AsOf{prev_year}{end_m}{end_d}",
    }
    
    return contexts

def extract_metrics_from_file(path: Path) -> Dict[str, Any]:
    """從HTML檔案提取完整財務指標"""
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        cid, cname, year, quarter = extract_company_meta(soup)
        
        if not all([cid, year, quarter]):
            return {
                "error": "missing_metadata",
                "source_file": path.name,
                "data_quality": "failed"
            }
        
        # 判斷報表類型
        is_consolidated = "-cr-" in path.name
        report_type = "合併" if is_consolidated else "個別"
        
        # 建立contexts
        contexts = build_contexts(year, quarter)
        if not contexts:
            return {
                "error": "invalid_quarter",
                "source_file": path.name,
                "data_quality": "failed"
            }
        
        # 定義會計科目代號
        codes = {
            'revenue': '4000',
            'gross_profit': '5900',
            'operating_income': '6900',
            'net_income': '8610' if is_consolidated else '8200',  # 合併用8610,個別用8200
            'eps': '9750',
            'total_assets': '1XXX',
            'total_liabilities': '2XXX',
        }
        
        # 提取損益表數據 - 單季 (千元)
        revenue_q_raw = extract_by_code_and_context(soup, codes['revenue'], contexts['q_current'])
        revenue_q_prev_raw = extract_by_code_and_context(soup, codes['revenue'], contexts['q_prev'])
        
        gross_profit_q_raw = extract_by_code_and_context(soup, codes['gross_profit'], contexts['q_current'])
        gross_profit_q_prev_raw = extract_by_code_and_context(soup, codes['gross_profit'], contexts['q_prev'])
        
        operating_income_q_raw = extract_by_code_and_context(soup, codes['operating_income'], contexts['q_current'])
        operating_income_q_prev_raw = extract_by_code_and_context(soup, codes['operating_income'], contexts['q_prev'])
        
        net_income_q_raw = extract_by_code_and_context(soup, codes['net_income'], contexts['q_current'])
        net_income_q_prev_raw = extract_by_code_and_context(soup, codes['net_income'], contexts['q_prev'])
        
        # EPS 保持原單位(元)
        eps_q = extract_by_code_and_context(soup, codes['eps'], contexts['q_current'])
        eps_q_prev = extract_by_code_and_context(soup, codes['eps'], contexts['q_prev'])
        
        # 提取損益表數據 - 累計 (千元)
        revenue_ytd_raw = extract_by_code_and_context(soup, codes['revenue'], contexts['ytd_current'])
        revenue_ytd_prev_raw = extract_by_code_and_context(soup, codes['revenue'], contexts['ytd_prev'])
        
        gross_profit_ytd_raw = extract_by_code_and_context(soup, codes['gross_profit'], contexts['ytd_current'])
        gross_profit_ytd_prev_raw = extract_by_code_and_context(soup, codes['gross_profit'], contexts['ytd_prev'])
        
        operating_income_ytd_raw = extract_by_code_and_context(soup, codes['operating_income'], contexts['ytd_current'])
        operating_income_ytd_prev_raw = extract_by_code_and_context(soup, codes['operating_income'], contexts['ytd_prev'])
        
        net_income_ytd_raw = extract_by_code_and_context(soup, codes['net_income'], contexts['ytd_current'])
        net_income_ytd_prev_raw = extract_by_code_and_context(soup, codes['net_income'], contexts['ytd_prev'])
        
        # EPS累計 保持原單位(元)
        eps_ytd = extract_by_code_and_context(soup, codes['eps'], contexts['ytd_current'])
        eps_ytd_prev = extract_by_code_and_context(soup, codes['eps'], contexts['ytd_prev'])
        
        # 提取資產負債表數據 (千元)
        total_assets_q_raw = extract_by_code_and_context(soup, codes['total_assets'], contexts['bs_current'])
        total_assets_q_prev_raw = extract_by_code_and_context(soup, codes['total_assets'], contexts['bs_prev'])
        
        total_liabilities_q_raw = extract_by_code_and_context(soup, codes['total_liabilities'], contexts['bs_current'])
        total_liabilities_q_prev_raw = extract_by_code_and_context(soup, codes['total_liabilities'], contexts['bs_prev'])
        
        # 轉換為百萬元
        revenue_q = to_millions(revenue_q_raw)
        revenue_q_prev = to_millions(revenue_q_prev_raw)
        gross_profit_q = to_millions(gross_profit_q_raw)
        gross_profit_q_prev = to_millions(gross_profit_q_prev_raw)
        operating_income_q = to_millions(operating_income_q_raw)
        operating_income_q_prev = to_millions(operating_income_q_prev_raw)
        net_income_q = to_millions(net_income_q_raw)
        net_income_q_prev = to_millions(net_income_q_prev_raw)
        
        revenue_ytd = to_millions(revenue_ytd_raw)
        revenue_ytd_prev = to_millions(revenue_ytd_prev_raw)
        gross_profit_ytd = to_millions(gross_profit_ytd_raw)
        gross_profit_ytd_prev = to_millions(gross_profit_ytd_prev_raw)
        operating_income_ytd = to_millions(operating_income_ytd_raw)
        operating_income_ytd_prev = to_millions(operating_income_ytd_prev_raw)
        net_income_ytd = to_millions(net_income_ytd_raw)
        net_income_ytd_prev = to_millions(net_income_ytd_prev_raw)
        
        total_assets_q = to_millions(total_assets_q_raw)
        total_assets_q_prev = to_millions(total_assets_q_prev_raw)
        total_liabilities_q = to_millions(total_liabilities_q_raw)
        total_liabilities_q_prev = to_millions(total_liabilities_q_prev_raw)
        
        # 計算YoY成長率
        def calc_yoy(current, prev):
            if current is None or prev is None or prev == 0:
                return None
            return round((current - prev) / abs(prev) * 100, 2)
        
        revenue_yoy = calc_yoy(revenue_q, revenue_q_prev)
        gross_profit_yoy = calc_yoy(gross_profit_q, gross_profit_q_prev)
        operating_income_yoy = calc_yoy(operating_income_q, operating_income_q_prev)
        net_income_yoy = calc_yoy(net_income_q, net_income_q_prev)
        
        # 計算累計YoY成長率
        revenue_ytd_yoy = calc_yoy(revenue_ytd, revenue_ytd_prev)
        gross_profit_ytd_yoy = calc_yoy(gross_profit_ytd, gross_profit_ytd_prev)
        operating_income_ytd_yoy = calc_yoy(operating_income_ytd, operating_income_ytd_prev)
        net_income_ytd_yoy = calc_yoy(net_income_ytd, net_income_ytd_prev)
        
        # 計算EPS變動值 (單位:元,四捨五入到小數點後2位)
        def calc_eps_change(current, prev):
            if current is None or prev is None:
                return None
            return round(current - prev, 2)
        
        eps_change_q = calc_eps_change(eps_q, eps_q_prev)
        eps_change_ytd = calc_eps_change(eps_ytd, eps_ytd_prev)
        
        # 計算獲利率 (用原始千元數據計算,避免精度損失)
        def calc_margin(profit_raw, revenue_raw):
            if profit_raw is None or revenue_raw is None or revenue_raw == 0:
                return None
            return round(profit_raw / revenue_raw * 100, 2)
        
        gross_margin_q = calc_margin(gross_profit_q_raw, revenue_q_raw)
        gross_margin_q_prev = calc_margin(gross_profit_q_prev_raw, revenue_q_prev_raw)
        
        operating_margin_q = calc_margin(operating_income_q_raw, revenue_q_raw)
        operating_margin_q_prev = calc_margin(operating_income_q_prev_raw, revenue_q_prev_raw)
        
        net_margin_q = calc_margin(net_income_q_raw, revenue_q_raw)
        net_margin_q_prev = calc_margin(net_income_q_prev_raw, revenue_q_prev_raw)
        
        # 計算負債比 (用原始千元數據計算)
        def calc_debt_ratio(liabilities_raw, assets_raw):
            if liabilities_raw is None or assets_raw is None or assets_raw == 0:
                return None
            return round(liabilities_raw / assets_raw * 100, 2)
        
        debt_ratio_q = calc_debt_ratio(total_liabilities_q_raw, total_assets_q_raw)
        debt_ratio_q_prev = calc_debt_ratio(total_liabilities_q_prev_raw, total_assets_q_prev_raw)
        
        # 計算獲利率YoY變化 (百分點)
        def calc_change(current, prev):
            if current is None or prev is None:
                return None
            return round(current - prev, 2)
        
        gross_margin_yoy_change = calc_change(gross_margin_q, gross_margin_q_prev)
        operating_margin_yoy_change = calc_change(operating_margin_q, operating_margin_q_prev)
        net_margin_yoy_change = calc_change(net_margin_q, net_margin_q_prev)
        debt_ratio_yoy_change = calc_change(debt_ratio_q, debt_ratio_q_prev)
        
        # 組裝結果
        result = {
            # 基礎資訊
            "company_id": cid,
            "company_name": cname,
            "year": year,
            "quarter": quarter,
            "report_type": report_type,
            
            # 單季原始金額 (百萬元)
            "revenue_q": revenue_q,
            "revenue_q_prev": revenue_q_prev,
            "gross_profit_q": gross_profit_q,
            "gross_profit_q_prev": gross_profit_q_prev,
            "operating_income_q": operating_income_q,
            "operating_income_q_prev": operating_income_q_prev,
            "net_income_q": net_income_q,
            "net_income_q_prev": net_income_q_prev,
            "eps_q": eps_q,  # 元
            "eps_q_prev": eps_q_prev,  # 元
            
            # 累計原始金額 (百萬元)
            "revenue_ytd": revenue_ytd,
            "revenue_ytd_prev": revenue_ytd_prev,
            "gross_profit_ytd": gross_profit_ytd,
            "gross_profit_ytd_prev": gross_profit_ytd_prev,
            "operating_income_ytd": operating_income_ytd,
            "operating_income_ytd_prev": operating_income_ytd_prev,
            "net_income_ytd": net_income_ytd,
            "net_income_ytd_prev": net_income_ytd_prev,
            "eps_ytd": eps_ytd,  # 元
            "eps_ytd_prev": eps_ytd_prev,  # 元
            
            # EPS變動值 (元)
            "eps_change_q": eps_change_q,
            "eps_change_ytd": eps_change_ytd,
            
            # 資產負債 (百萬元)
            "total_assets_q": total_assets_q,
            "total_assets_q_prev": total_assets_q_prev,
            "total_liabilities_q": total_liabilities_q,
            "total_liabilities_q_prev": total_liabilities_q_prev,
            
            # 單季YoY成長率 (%)
            "revenue_yoy": revenue_yoy,
            "gross_profit_yoy": gross_profit_yoy,
            "operating_income_yoy": operating_income_yoy,
            "net_income_yoy": net_income_yoy,
            
            # 累計YoY成長率 (%)
            "revenue_ytd_yoy": revenue_ytd_yoy,
            "gross_profit_ytd_yoy": gross_profit_ytd_yoy,
            "operating_income_ytd_yoy": operating_income_ytd_yoy,
            "net_income_ytd_yoy": net_income_ytd_yoy,
            
            # 獲利率 (%)
            "gross_margin_q": gross_margin_q,
            "gross_margin_q_prev": gross_margin_q_prev,
            "operating_margin_q": operating_margin_q,
            "operating_margin_q_prev": operating_margin_q_prev,
            "net_margin_q": net_margin_q,
            "net_margin_q_prev": net_margin_q_prev,
            
            # 獲利率YoY變化 (百分點)
            "gross_margin_yoy_change": gross_margin_yoy_change,
            "operating_margin_yoy_change": operating_margin_yoy_change,
            "net_margin_yoy_change": net_margin_yoy_change,
            
            # 負債比 (%)
            "debt_ratio_q": debt_ratio_q,
            "debt_ratio_q_prev": debt_ratio_q_prev,
            "debt_ratio_yoy_change": debt_ratio_yoy_change,
            
            # 系統欄位
            "context_warning": None,
            "data_quality": "complete",
            "source_file": path.name,
        }
        
        # 檢查資料完整性
        critical_fields = [revenue_q, revenue_q_prev, net_income_q, net_income_q_prev]
        if not all(x is not None for x in critical_fields):
            result["data_quality"] = "incomplete"
        
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
    """根據官方名單批次處理財報 - 支援合併報表+個別報表"""
    
    # 載入官方名單
    official_ids = load_official_list(official_csv)
    
    folder = Path(input_folder)
    
    # 支援 fr1/fr2 的合併報表(cr) + 個別報表(ir)
    patterns = [
        "tifrs-fr1-m1-ci-cr-*.html",
        "tifrs-fr2-m1-ci-cr-*.html",
        "tifrs-fr1-m1-ci-ir-*.html",
        "tifrs-fr2-m1-ci-ir-*.html",
    ]
    
    all_files = []
    for pattern in patterns:
        all_files.extend(folder.glob(pattern))
    
    # 只保留官方名單中的公司
    filtered_files = []
    for file in all_files:
        match = re.search(r'-(\d{4})-', file.name)
        if match and match.group(1) in official_ids:
            filtered_files.append(file)
    
    files = sorted(filtered_files)
    
    print(f"資料夾共有 {len(all_files)} 個符合格式的檔案")
    print(f"官方名單有 {len(official_ids)} 家公司")
    print(f"配對成功: {len(files)} 個檔案")
    print(f"開始處理...\n")
    
    results = []
    success_count = 0
    incomplete_count = 0
    failed_count = 0
    processed_ids = set()
    
    for i, file_path in enumerate(files, 1):
        match = re.search(r'-(\d{4})-', file_path.name)
        if match:
            processed_ids.add(match.group(1))
        
        print(f"[{i}/{len(files)}] 處理: {file_path.name}", end=" ")
        
        result = extract_metrics_from_file(file_path)
        results.append(result)
        
        if result.get("data_quality") == "complete":
            print("✓")
            success_count += 1
        elif result.get("data_quality") == "incomplete":
            print("⚠ 資料不完整")
            incomplete_count += 1
        else:
            print("✗ 失敗")
            failed_count += 1
    
    not_processed = official_ids - processed_ids
    
    # 輸出CSV
    df_output = pd.DataFrame(results)
    
    # 按照你要求的欄位順序
    column_order = [
        "company_id", "company_name", "year", "quarter", "report_type",
        "revenue_q", "revenue_q_prev", "revenue_yoy",
        "gross_profit_q", "gross_profit_q_prev", "gross_profit_yoy",
        "operating_income_q", "operating_income_q_prev", "operating_income_yoy",
        "net_income_q", "net_income_q_prev", "net_income_yoy",
        "eps_q", "eps_q_prev", "eps_change_q",
        "revenue_ytd", "revenue_ytd_prev", "revenue_ytd_yoy",
        "gross_profit_ytd", "gross_profit_ytd_prev", "gross_profit_ytd_yoy",
        "operating_income_ytd", "operating_income_ytd_prev", "operating_income_ytd_yoy",
        "net_income_ytd", "net_income_ytd_prev", "net_income_ytd_yoy",
        "eps_ytd", "eps_ytd_prev", "eps_change_ytd",
        "total_assets_q", "total_assets_q_prev",
        "total_liabilities_q", "total_liabilities_q_prev",
        "debt_ratio_q", "debt_ratio_q_prev", "debt_ratio_yoy_change",
        "gross_margin_q", "gross_margin_q_prev", "gross_margin_yoy_change",
        "operating_margin_q", "operating_margin_q_prev", "operating_margin_yoy_change",
        "net_margin_q", "net_margin_q_prev", "net_margin_yoy_change"
    ]
    
    # 只保留存在的欄位
    existing_columns = [col for col in column_order if col in df_output.columns]
    df_output = df_output[existing_columns]
    
    df_output.to_csv(output_csv, index=False, encoding="utf-8-sig")
    
    print(f"\n{'='*60}")
    print(f"處理完成!")
    print(f"{'='*60}")
    print(f"官方名單: {len(official_ids)} 家")
    print(f"找到檔案並處理: {len(files)} 家")
    print(f"  - 成功: {success_count} 家")
    print(f"  - 資料不完整: {incomplete_count} 家")
    print(f"  - 失敗: {failed_count} 家")
    print(f"名單中但無檔案: {len(not_processed)} 家")
    print(f"實際涵蓋率: {len(files)/len(official_ids)*100:.1f}%")
    print(f"\n輸出檔案: {output_csv}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import sys
    
    # 把預設值改成Q3的
    official_csv = sys.argv[1] if len(sys.argv) > 1 else "t163sb04_20251218_15322930.csv"
    input_folder = sys.argv[2] if len(sys.argv) > 2 else "../tifrs-2025Q3"
    output_file = sys.argv[3] if len(sys.argv) > 3 else "financial_metrics_2025Q3.csv"
    
    process_batch_with_whitelist(input_folder, official_csv, output_file)