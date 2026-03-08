# -*- coding: utf-8 -*-
"""
db_loader.py
將 parse_mops_reports.py 的輸出 CSV 載入至 SQLite 資料庫。
支援 upsert（重複執行不重複新增），並自動建立/更新 companies 表。

用法:
    python pipeline/db_loader.py --csv path/to/financial_metrics.csv
    python pipeline/db_loader.py --csv metrics_2025Q2.csv --csv metrics_2025Q3.csv
    python pipeline/db_loader.py --fetch-companies   # 從 TWSE API 抓取產業資料
"""

import argparse
import sqlite3
import json
import sys
from pathlib import Path

import pandas as pd
import requests

DB_PATH = Path(__file__).parent.parent / 'data' / 'financials.db'

# TWSE 上市公司名單（含產業別）公開 API
TWSE_API = 'https://openapi.twse.com.tw/v1/opendata/t51sb01'
# TPEx 上櫃公司名單
TPEX_API = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_companies_in_category'

# 產業代碼對應表（備援用，當 API 不可用時依股票代號範圍推斷）
INDUSTRY_RANGE_MAP = [
    (range(1100, 1200), '水泥工業'),
    (range(1200, 1300), '食品工業'),
    (range(1300, 1400), '塑膠工業'),
    (range(1400, 1500), '紡織纖維'),
    (range(1500, 1600), '電機機械'),
    (range(1600, 1700), '電器電纜'),
    (range(1700, 1800), '化學工業'),
    (range(1800, 1900), '玻璃陶瓷'),
    (range(1900, 2000), '造紙工業'),
    (range(2000, 2100), '鋼鐵工業'),
    (range(2100, 2200), '橡膠工業'),
    (range(2200, 2300), '汽車工業'),
    (range(2300, 2500), '半導體業'),
    (range(2500, 2600), '電腦及週邊設備業'),
    (range(2600, 2700), '光電業'),
    (range(2700, 2800), '通信網路業'),
    (range(2800, 2900), '電子零組件業'),
    (range(2900, 3000), '電子通路業'),
    (range(3000, 3100), '資訊服務業'),
    (range(3100, 3300), '其他電子業'),
    (range(5800, 6000), '百貨零售'),
    (range(6000, 7000), '觀光事業'),
    (range(2881, 2900), '金融業'),
    (range(2800, 2882), '金融業'),
]


def get_industry_by_code(company_id: str) -> str:
    """依股票代號範圍推斷產業（備援）"""
    try:
        cid = int(company_id)
        for r, name in INDUSTRY_RANGE_MAP:
            if cid in r:
                return name
    except (ValueError, TypeError):
        pass
    return '其他'


def init_db(db_path: Path) -> sqlite3.Connection:
    """建立資料庫與資料表（若不存在）"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id    TEXT PRIMARY KEY,
            company_name  TEXT,
            industry_code TEXT DEFAULT '',
            industry_name TEXT DEFAULT '其他',
            market        TEXT DEFAULT 'TWSE',
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS financial_metrics (
            id                              INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id                      TEXT NOT NULL,
            company_name                    TEXT,
            year                            TEXT NOT NULL,
            quarter                         TEXT NOT NULL,
            report_type                     TEXT NOT NULL,

            revenue_q                       REAL,
            revenue_q_prev                  REAL,
            revenue_yoy                     REAL,
            gross_profit_q                  REAL,
            gross_profit_q_prev             REAL,
            gross_profit_yoy                REAL,
            operating_income_q              REAL,
            operating_income_q_prev         REAL,
            operating_income_yoy            REAL,
            net_income_q                    REAL,
            net_income_q_prev               REAL,
            net_income_yoy                  REAL,
            eps_q                           REAL,
            eps_q_prev                      REAL,
            eps_change_q                    REAL,

            revenue_ytd                     REAL,
            revenue_ytd_prev                REAL,
            revenue_ytd_yoy                 REAL,
            gross_profit_ytd                REAL,
            gross_profit_ytd_prev           REAL,
            gross_profit_ytd_yoy            REAL,
            operating_income_ytd            REAL,
            operating_income_ytd_prev       REAL,
            operating_income_ytd_yoy        REAL,
            net_income_ytd                  REAL,
            net_income_ytd_prev             REAL,
            net_income_ytd_yoy              REAL,
            eps_ytd                         REAL,
            eps_ytd_prev                    REAL,
            eps_change_ytd                  REAL,

            total_assets_q                  REAL,
            total_assets_q_prev             REAL,
            total_liabilities_q             REAL,
            total_liabilities_q_prev        REAL,
            debt_ratio_q                    REAL,
            debt_ratio_q_prev               REAL,
            debt_ratio_yoy_change           REAL,

            gross_margin_q                  REAL,
            gross_margin_q_prev             REAL,
            gross_margin_yoy_change         REAL,
            operating_margin_q              REAL,
            operating_margin_q_prev         REAL,
            operating_margin_yoy_change     REAL,
            net_margin_q                    REAL,
            net_margin_q_prev               REAL,
            net_margin_yoy_change           REAL,

            quality                         TEXT DEFAULT 'complete',
            source_file                     TEXT,
            loaded_at                       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(company_id, year, quarter, report_type)
        );

        CREATE INDEX IF NOT EXISTS idx_fm_company  ON financial_metrics(company_id);
        CREATE INDEX IF NOT EXISTS idx_fm_period   ON financial_metrics(year, quarter);
        CREATE INDEX IF NOT EXISTS idx_fm_quality  ON financial_metrics(quality);
    """)
    conn.commit()
    return conn


def load_csv(csv_path: Path, conn: sqlite3.Connection) -> tuple[int, int]:
    """載入一份 CSV 至資料庫，回傳 (inserted, skipped) 筆數"""
    for enc in ('utf-8-sig', 'utf-8', 'big5', 'cp950'):
        try:
            df = pd.read_csv(csv_path, encoding=enc, dtype={'company_id': str})
            break
        except Exception:
            continue
    else:
        raise RuntimeError(f'無法讀取 CSV: {csv_path}')

    # 只保留有效資料（排除 fail）
    df = df[df.get('quality', 'complete') != 'fail'].copy()

    # 重命名 file → source_file（若存在）
    if 'file' in df.columns:
        df = df.rename(columns={'file': 'source_file'})

    # 確保 company_id 為字串
    df['company_id'] = df['company_id'].astype(str).str.strip()

    # 定義資料表欄位（不含 id, loaded_at）
    db_cols = [
        'company_id', 'company_name', 'year', 'quarter', 'report_type',
        'revenue_q', 'revenue_q_prev', 'revenue_yoy',
        'gross_profit_q', 'gross_profit_q_prev', 'gross_profit_yoy',
        'operating_income_q', 'operating_income_q_prev', 'operating_income_yoy',
        'net_income_q', 'net_income_q_prev', 'net_income_yoy',
        'eps_q', 'eps_q_prev', 'eps_change_q',
        'revenue_ytd', 'revenue_ytd_prev', 'revenue_ytd_yoy',
        'gross_profit_ytd', 'gross_profit_ytd_prev', 'gross_profit_ytd_yoy',
        'operating_income_ytd', 'operating_income_ytd_prev', 'operating_income_ytd_yoy',
        'net_income_ytd', 'net_income_ytd_prev', 'net_income_ytd_yoy',
        'eps_ytd', 'eps_ytd_prev', 'eps_change_ytd',
        'total_assets_q', 'total_assets_q_prev',
        'total_liabilities_q', 'total_liabilities_q_prev',
        'debt_ratio_q', 'debt_ratio_q_prev', 'debt_ratio_yoy_change',
        'gross_margin_q', 'gross_margin_q_prev', 'gross_margin_yoy_change',
        'operating_margin_q', 'operating_margin_q_prev', 'operating_margin_yoy_change',
        'net_margin_q', 'net_margin_q_prev', 'net_margin_yoy_change',
        'quality', 'source_file',
    ]

    # 只取 CSV 中存在的欄位
    keep = [c for c in db_cols if c in df.columns]
    df_insert = df[keep].copy()

    cols_str = ', '.join(keep)
    placeholders = ', '.join(['?'] * len(keep))
    sql = f'INSERT OR REPLACE INTO financial_metrics ({cols_str}) VALUES ({placeholders})'

    inserted = 0
    skipped = 0
    for _, row in df_insert.iterrows():
        values = [None if pd.isna(v) else v for v in row.values]
        try:
            conn.execute(sql, values)
            inserted += 1
        except Exception:
            skipped += 1

    conn.commit()

    # 更新 companies 表（只補新公司，不覆蓋已有產業資料）
    for _, row in df[['company_id', 'company_name']].drop_duplicates().iterrows():
        cid = str(row['company_id']).strip()
        cname = row.get('company_name', '')
        industry = get_industry_by_code(cid)
        conn.execute("""
            INSERT INTO companies (company_id, company_name, industry_name)
            VALUES (?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                company_name = excluded.company_name
        """, (cid, cname, industry))
    conn.commit()

    return inserted, skipped


def fetch_twse_companies(conn: sqlite3.Connection) -> int:
    """從 TWSE 公開 API 抓取上市公司產業資料，更新 companies 表"""
    print('正在從 TWSE 抓取上市公司產業資料...')
    try:
        resp = requests.get(TWSE_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'  TWSE API 失敗: {e}')
        return 0

    updated = 0
    for item in data:
        cid = str(item.get('公司代號', '')).strip()
        cname = str(item.get('公司名稱', '')).strip()
        industry_name = str(item.get('產業別', '')).strip() or get_industry_by_code(cid)
        if not cid:
            continue
        conn.execute("""
            INSERT INTO companies (company_id, company_name, industry_name, market)
            VALUES (?, ?, ?, 'TWSE')
            ON CONFLICT(company_id) DO UPDATE SET
                company_name  = excluded.company_name,
                industry_name = excluded.industry_name,
                market        = 'TWSE',
                updated_at    = CURRENT_TIMESTAMP
        """, (cid, cname, industry_name))
        updated += 1

    conn.commit()
    print(f'  已更新 {updated} 家上市公司')
    return updated


def print_summary(conn: sqlite3.Connection):
    """印出資料庫摘要"""
    cur = conn.execute("""
        SELECT year, quarter, report_type, quality, COUNT(*) as cnt
        FROM financial_metrics
        GROUP BY year, quarter, report_type, quality
        ORDER BY year DESC, quarter DESC, report_type, quality
    """)
    rows = cur.fetchall()
    print('\n=== 資料庫摘要 ===')
    print(f'{"年度":>4} {"季":>2} {"類型":>4} {"品質":>10} {"筆數":>6}')
    print('-' * 35)
    for r in rows:
        print(f'{r[0]:>4} Q{r[1]:>1} {r[2]:>4} {r[3]:>10} {r[4]:>6}')

    total = conn.execute('SELECT COUNT(*) FROM financial_metrics').fetchone()[0]
    companies = conn.execute('SELECT COUNT(DISTINCT company_id) FROM financial_metrics').fetchone()[0]
    print(f'\n總計: {total} 筆，涵蓋 {companies} 家公司')


def main():
    parser = argparse.ArgumentParser(description='載入財報 CSV 至 SQLite')
    parser.add_argument('--csv', action='append', help='CSV 檔案路徑（可多次指定）')
    parser.add_argument('--db', default=str(DB_PATH), help='SQLite 資料庫路徑')
    parser.add_argument('--fetch-companies', action='store_true', help='從 TWSE API 抓取產業資料')
    args = parser.parse_args()

    db_path = Path(args.db)
    conn = init_db(db_path)
    print(f'資料庫: {db_path}')

    if args.fetch_companies:
        fetch_twse_companies(conn)

    if args.csv:
        for csv_file in args.csv:
            p = Path(csv_file)
            if not p.exists():
                print(f'找不到檔案: {p}')
                continue
            print(f'\n載入: {p.name}')
            inserted, skipped = load_csv(p, conn)
            print(f'  新增/更新: {inserted} 筆，略過: {skipped} 筆')

    print_summary(conn)
    conn.close()


if __name__ == '__main__':
    main()
