# -*- coding: utf-8 -*-
"""
utils/db.py
SQLite 資料庫連線與常用查詢 helper。
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent.parent / 'data' / 'financials.db'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=3600)
def load_all_metrics(report_type: str = '合併') -> pd.DataFrame:
    """
    一次性載入全量財務指標至 pandas DataFrame（in-memory cache）。
    Screener 所有篩選操作都在這個 DataFrame 上做，不重複查 DB。
    """
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            fm.*,
            COALESCE(c.industry_name, '其他') AS industry_name,
            COALESCE(c.market, 'TWSE') AS market
        FROM financial_metrics fm
        LEFT JOIN companies c ON fm.company_id = c.company_id
        WHERE fm.quality != 'fail'
          AND fm.report_type = ?
        ORDER BY fm.year DESC, fm.quarter DESC, fm.revenue_q DESC NULLS LAST
    """, conn, params=(report_type,))
    conn.close()
    df['company_id'] = df['company_id'].astype(str)
    return df


@st.cache_data(ttl=3600)
def load_company_list() -> pd.DataFrame:
    """
    載入公司列表供搜尋框使用。
    回傳含 label 欄位（'代號 公司名稱'）的 DataFrame。
    """
    conn = get_connection()
    df = pd.read_sql("""
        SELECT DISTINCT
            fm.company_id,
            fm.company_name,
            COALESCE(c.industry_name, '其他') AS industry_name,
            COALESCE(c.market, 'TWSE') AS market
        FROM financial_metrics fm
        LEFT JOIN companies c ON fm.company_id = c.company_id
        WHERE fm.quality != 'fail'
        ORDER BY fm.company_id
    """, conn)
    conn.close()
    df['company_id'] = df['company_id'].astype(str)
    df['label'] = df['company_id'] + '  ' + df['company_name'].fillna('')
    return df


@st.cache_data(ttl=3600)
def load_company_history(company_id: str, report_type: str = '合併') -> pd.DataFrame:
    """載入單一公司所有季度資料，按時間排序"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT * FROM financial_metrics
        WHERE company_id = ?
          AND report_type = ?
          AND quality != 'fail'
        ORDER BY year ASC, quarter ASC
    """, conn, params=(company_id, report_type))
    conn.close()
    if not df.empty:
        df['period'] = df['year'] + 'Q' + df['quarter']
    return df


@st.cache_data(ttl=3600)
def load_peers(company_id: str, year: str, quarter: str,
               report_type: str = '合併', limit: int = 20) -> pd.DataFrame:
    """載入同產業公司的指定季度數據"""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT fm.*, c.industry_name, c.market
        FROM financial_metrics fm
        JOIN companies c ON fm.company_id = c.company_id
        WHERE c.industry_name = (
            SELECT COALESCE(cc.industry_name, '其他')
            FROM companies cc WHERE cc.company_id = ?
        )
        AND fm.year = ?
        AND fm.quarter = ?
        AND fm.report_type = ?
        AND fm.quality != 'fail'
        ORDER BY fm.revenue_q DESC NULLS LAST
        LIMIT ?
    """, conn, params=(company_id, year, quarter, report_type, limit))
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_data_info() -> dict:
    """取得資料庫基本資訊（最新季度、公司數）"""
    if not DB_PATH.exists():
        return {'latest_period': 'N/A', 'company_count': 0}
    conn = get_connection()
    row = conn.execute("""
        SELECT
            MAX(year || 'Q' || quarter) AS latest_period,
            COUNT(DISTINCT company_id) AS company_count
        FROM financial_metrics
        WHERE quality = 'complete'
    """).fetchone()
    conn.close()
    if row:
        return {'latest_period': row[0] or 'N/A', 'company_count': row[1] or 0}
    return {'latest_period': 'N/A', 'company_count': 0}


@st.cache_data(ttl=3600)
def get_available_periods() -> list[str]:
    """取得資料庫中所有可用的期別，由新到舊"""
    if not DB_PATH.exists():
        return []
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT year || 'Q' || quarter AS period
        FROM financial_metrics
        WHERE quality != 'fail'
        ORDER BY period DESC
    """).fetchall()
    conn.close()
    return [r[0] for r in rows]


@st.cache_data(ttl=3600)
def get_industry_list() -> list[str]:
    """取得所有產業別清單"""
    if not DB_PATH.exists():
        return []
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT COALESCE(c.industry_name, '其他') AS industry_name
        FROM financial_metrics fm
        LEFT JOIN companies c ON fm.company_id = c.company_id
        WHERE fm.quality != 'fail'
        ORDER BY industry_name
    """).fetchall()
    conn.close()
    return [r[0] for r in rows]
