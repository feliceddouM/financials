# -*- coding: utf-8 -*-
"""
pages/1_company.py
公司財務總覽頁：搜尋單一公司，顯示 KPI 卡片、趨勢圖、歷史資料表。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from utils.db import load_company_list, load_company_history
from utils.format import (
    fmt_millions, fmt_pct_plain, fmt_eps,
    delta_label, color_delta,
)
from utils.charts import bar_with_yoy_line, margin_trend

st.set_page_config(page_title='公司財務總覽', page_icon='📋', layout='wide')
st.title('📋 公司財務總覽')

# ── 搜尋列 ─────────────────────────────────────────────────────────────────────
companies = load_company_list()

if companies.empty:
    st.warning('資料庫尚無資料，請先執行資料匯入。請參考首頁說明。')
    st.stop()

# 跨頁跳轉（來自篩選器）
default_label = None
if 'selected_company' in st.session_state:
    cid = st.session_state['selected_company']
    match = companies[companies['company_id'] == cid]
    if not match.empty:
        default_label = match.iloc[0]['label']

labels = companies['label'].tolist()
default_idx = labels.index(default_label) if default_label in labels else 0

col_search, col_rtype = st.columns([3, 1])
with col_search:
    selected_label = st.selectbox(
        '搜尋公司（輸入代號或名稱）',
        options=labels,
        index=default_idx,
        key='company_select',
    )
with col_rtype:
    report_type = st.radio('報表類型', ['合併', '個別'], horizontal=True)

# 解析選擇
selected_row = companies[companies['label'] == selected_label]
if selected_row.empty:
    st.error('找不到該公司')
    st.stop()

company_id = selected_row.iloc[0]['company_id']
company_name = selected_row.iloc[0]['company_name']
industry = selected_row.iloc[0]['industry_name']

st.markdown(f'**{company_name}**（{company_id}）｜{industry}')
st.markdown('---')

# ── 載入資料 ──────────────────────────────────────────────────────────────────
df = load_company_history(company_id, report_type)

# 若合併無資料，fallback 至個別
if df.empty and report_type == '合併':
    df = load_company_history(company_id, '個別')
    if not df.empty:
        st.info('此公司無合併報表，已顯示個別報表數據。')
        report_type = '個別'

if df.empty:
    st.warning(f'資料庫中找不到 **{company_name}** 的財務資料。')
    st.stop()

latest = df.iloc[-1]  # 最新一季（已按時間升序排列）


# ── KPI 卡片 ─────────────────────────────────────────────────────────────────
st.subheader(f'最新季度：{latest["year"]}Q{latest["quarter"]}')

c1, c2, c3, c4 = st.columns(4)

with c1:
    rev = latest.get('revenue_q')
    rev_yoy = latest.get('revenue_yoy')
    st.metric(
        label='單季營收',
        value=fmt_millions(rev) if rev else 'N/A',
        delta=delta_label(rev_yoy),
        delta_color=color_delta(rev_yoy),
        help='單位：百萬元台幣',
    )

with c2:
    gm = latest.get('gross_margin_q')
    gm_chg = latest.get('gross_margin_yoy_change')
    st.metric(
        label='毛利率',
        value=fmt_pct_plain(gm),
        delta=delta_label(gm_chg, unit='pp'),
        delta_color=color_delta(gm_chg),
        help='毛利率 = 毛利 / 營收',
    )

with c3:
    om = latest.get('operating_margin_q')
    om_chg = latest.get('operating_margin_yoy_change')
    st.metric(
        label='營益率',
        value=fmt_pct_plain(om),
        delta=delta_label(om_chg, unit='pp'),
        delta_color=color_delta(om_chg),
        help='營業利益率 = 營業利益 / 營收',
    )

with c4:
    eps = latest.get('eps_q')
    eps_chg = latest.get('eps_change_q')
    st.metric(
        label='EPS（單季）',
        value=fmt_eps(eps),
        delta=delta_label(eps_chg, unit='元'),
        delta_color=color_delta(eps_chg),
        help='基本每股盈餘（元）',
    )

st.markdown('---')

# ── 趨勢圖 ────────────────────────────────────────────────────────────────────
st.subheader('歷史趨勢')

col_l, col_r = st.columns(2)

with col_l:
    fig1 = bar_with_yoy_line(
        df, 'revenue_q', 'revenue_yoy',
        title='單季營收（百萬元）與 YoY%',
        bar_label='營收(百萬)',
        yoy_label='YoY%',
    )
    st.plotly_chart(fig1, use_container_width=True)

    fig3 = margin_trend(df, title='獲利率趨勢（毛利率 / 營益率 / 淨利率）')
    st.plotly_chart(fig3, use_container_width=True)

with col_r:
    fig2 = bar_with_yoy_line(
        df, 'eps_q', None,
        title='單季 EPS（元）',
        bar_label='EPS(元)',
        yoy_label='',
        bar_color='#27AE60',
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig4 = bar_with_yoy_line(
        df, 'net_income_q', 'net_income_yoy',
        title='單季淨利（百萬元）與 YoY%',
        bar_label='淨利(百萬)',
        yoy_label='YoY%',
        bar_color='#9B59B6',
    )
    st.plotly_chart(fig4, use_container_width=True)

st.markdown('---')

# ── 歷史資料表 ────────────────────────────────────────────────────────────────
st.subheader('完整歷史數據')

display_cols = {
    'period': '季度',
    'revenue_q': '營收(百萬)',
    'revenue_yoy': '營收YoY%',
    'gross_margin_q': '毛利率%',
    'operating_margin_q': '營益率%',
    'net_margin_q': '淨利率%',
    'eps_q': 'EPS(元)',
    'eps_ytd': 'EPS累計',
    'debt_ratio_q': '負債比%',
    'quality': '品質',
}

df_display = df.rename(columns=display_cols)[[c for c in display_cols.values() if c in df.rename(columns=display_cols).columns]].iloc[::-1]

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
)

# CSV 下載
csv_bytes = df.iloc[::-1].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
st.download_button(
    label='下載完整數據 CSV',
    data=csv_bytes,
    file_name=f'{company_id}_{company_name}_financial_data.csv',
    mime='text/csv',
)
