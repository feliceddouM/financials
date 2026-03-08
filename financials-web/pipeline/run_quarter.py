#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline/run_quarter.py
一鍵更新新季度資料：解析 HTML → 產出 CSV → 載入 SQLite

用法:
    python pipeline/run_quarter.py \\
        --html-dir /path/to/tifrs-2025Q4 \\
        --whitelist /path/to/t163sb04_new.csv \\
        --quarter 2025Q4

選項:
    --html-dir      MOPS 下載的 HTML 資料夾路徑
    --whitelist     官方公司名單 CSV（t163sb04 格式）
    --quarter       季度標籤（例如 2025Q4），用於輸出檔名
    --db            SQLite 資料庫路徑（預設: data/financials.db）
    --keep-csv      保留中間 CSV 檔案（預設: 解析完後刪除）
    --fetch-companies  從 TWSE API 更新產業資料
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_DEFAULT = PROJECT_ROOT / 'data' / 'financials.db'


def run_parser(html_dir: Path, whitelist: Path, output_csv: Path) -> bool:
    """執行 parse_mops_reports.py"""
    parser_path = Path(__file__).parent / 'parse_mops_reports.py'
    if not parser_path.exists():
        print(f'[錯誤] 找不到解析器: {parser_path}')
        print('請將 parse_mops_reports.py 複製至 pipeline/ 目錄。')
        return False

    cmd = [
        sys.executable,
        str(parser_path),
        str(whitelist),
        str(html_dir),
        str(output_csv),
    ]
    print(f'\n[Step 1] 解析財報 HTML')
    print(f'  HTML 資料夾: {html_dir}')
    print(f'  公司名單: {whitelist}')
    print(f'  輸出 CSV: {output_csv}')
    print()

    start = time.time()
    result = subprocess.run(cmd, check=False)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f'[錯誤] 解析器執行失敗（return code: {result.returncode}）')
        return False

    if not output_csv.exists():
        print(f'[錯誤] 輸出 CSV 未產生: {output_csv}')
        return False

    size_mb = output_csv.stat().st_size / 1024 / 1024
    print(f'\n[Step 1 完成] 耗時 {elapsed:.1f}s，CSV 大小 {size_mb:.1f} MB')
    return True


def run_loader(csv_path: Path, db_path: Path, fetch_companies: bool = False) -> bool:
    """執行 db_loader.py"""
    loader_path = Path(__file__).parent / 'db_loader.py'

    cmd = [sys.executable, str(loader_path), '--csv', str(csv_path), '--db', str(db_path)]
    if fetch_companies:
        cmd.append('--fetch-companies')

    print(f'\n[Step 2] 載入至資料庫')
    print(f'  CSV: {csv_path}')
    print(f'  資料庫: {db_path}')
    print()

    start = time.time()
    result = subprocess.run(cmd, check=False)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f'[錯誤] 載入器執行失敗（return code: {result.returncode}）')
        return False

    print(f'\n[Step 2 完成] 耗時 {elapsed:.1f}s')
    return True


def main():
    parser = argparse.ArgumentParser(
        description='一鍵更新新季度財報資料',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--html-dir', required=True, help='MOPS HTML 資料夾路徑')
    parser.add_argument('--whitelist', required=True, help='官方公司名單 CSV（t163sb04 格式）')
    parser.add_argument('--quarter', required=True, help='季度標籤，例如 2025Q4')
    parser.add_argument('--db', default=str(DB_DEFAULT), help='SQLite 資料庫路徑')
    parser.add_argument('--keep-csv', action='store_true', help='保留中間 CSV 檔案')
    parser.add_argument('--fetch-companies', action='store_true', help='從 TWSE API 更新產業資料')
    args = parser.parse_args()

    html_dir = Path(args.html_dir)
    whitelist = Path(args.whitelist)
    db_path = Path(args.db)
    quarter = args.quarter

    # 驗證輸入
    if not html_dir.is_dir():
        print(f'[錯誤] HTML 資料夾不存在: {html_dir}')
        sys.exit(1)
    if not whitelist.exists():
        print(f'[錯誤] 公司名單 CSV 不存在: {whitelist}')
        sys.exit(1)

    output_csv = PROJECT_ROOT / f'financial_metrics_{quarter}.csv'

    print('=' * 50)
    print(f'台股財報更新工具')
    print(f'季度: {quarter}')
    print('=' * 50)

    total_start = time.time()

    # Step 1: 解析
    if not run_parser(html_dir, whitelist, output_csv):
        sys.exit(1)

    # Step 2: 載入
    if not run_loader(output_csv, db_path, args.fetch_companies):
        sys.exit(1)

    # 清理中間檔案
    if not args.keep_csv and output_csv.exists():
        output_csv.unlink()
        print(f'\n[清理] 已刪除中間 CSV: {output_csv.name}')

    total_elapsed = time.time() - total_start
    print('\n' + '=' * 50)
    print(f'✓ {quarter} 資料更新完成！總耗時 {total_elapsed:.1f}s')
    print(f'  資料庫: {db_path}')
    print('=' * 50)
    print('\n重新整理 Streamlit 頁面即可看到最新數據。')


if __name__ == '__main__':
    main()
