# -*- coding: utf-8 -*-
"""
pages/3_peers.py
同業比較：選定公司後自動載入同產業公司，進行財務指標對比。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np

from utils.db import load_company_list, load_peers, get_available_periods, load_all_metrics
from utils.charts import radar_chart, horizontal_bar

st.set_page_config(page_title='同業比較', page_icon='⚖️', layout='wide')
st.title('⚖️ 同業比較')

# ── 載入基礎資料 ──────────────────────────────────────────────────────────────
companies = load_company_list()
periods = get_available_periods()

if companies.empty or not periods:
    st.warning('資料庫尚無資料，請先執行資料匯入。請參考首頁說明。')
    st.stop()

# ── 選擇設定 ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    # 跨頁跳轉支援
    default_label = None
    if 'selected_company' in st.session_state:
        cid = st.session_state['selected_company']
        match = companies[companies['company_id'] == cid]
        if not match.empty:
            default_label = match.iloc[0]['label']

    labels = companies['label'].tolist()
    default_idx = labels.index(default_label) if default_label in labels else 0

    selected_label = st.selectbox(
        '選擇主要公司',
        options=labels,
        index=default_idx,
    )

with col2:
    selected_period = st.selectbox('比較期別', options=periods, index=0)
    year, quarter = selected_period[:4], selected_period[5]

with col3:
    report_type = st.radio('報表類型', ['合併', '個別'], horizontal=True)

# 解析選擇
selected_row = companies[companies['label'] == selected_label]
if selected_row.empty:
    st.error('找不到該公司')
    st.stop()

target_id = selected_row.iloc[0]['company_id']
target_name = selected_row.iloc[0]['company_name']
target_industry = selected_row.iloc[0]['industry_name']

st.markdown(f'**主要公司**: {target_name}（{target_id}）｜產業: {target_industry}')

# ── 手動新增比較公司 ──────────────────────────────────────────────────────────
with st.expander('手動新增跨產業比較公司（最多 5 家）'):
    extra_labels = st.multiselect(
        '新增公司',
        options=[l for l in labels if l != selected_label],
        max_selections=5,
        key='extra_peers',
    )

extra_ids = []
for lbl in extra_labels:
    row = companies[companies['label'] == lbl]
    if not row.empty:
        extra_ids.append(row.iloc[0]['company_id'])

st.markdown('---')

# ── 載入同業數據 ──────────────────────────────────────────────────────────────
df_peers = load_peers(target_id, year, quarter, report_type, limit=20)

# 加入手動新增的公司
if extra_ids:
    df_all_metrics = load_all_metrics(report_type)
    df_extra = df_all_metrics[
        (df_all_metrics['company_id'].isin(extra_ids)) &
        (df_all_metrics['year'] == year) &
        (df_all_metrics['quarter'] == quarter)
    ]
    df_peers = pd.concat([df_peers, df_extra], ignore_index=True).drop_duplicates(subset='company_id')

if df_peers.empty:
    # fallback: 從全量資料中找同產業
    df_all_metrics = load_all_metrics(report_type)
    df_peers = df_all_metrics[
        (df_all_metrics['industry_name'] == target_industry) &
        (df_all_metrics['year'] == year) &
        (df_all_metrics['quarter'] == quarter)
    ].copy()

if df_peers.empty:
    st.warning(f'找不到 {target_industry} 在 {selected_period} 的同業數據。')
    st.stop()

# 確保目標公司在列表中
if target_id not in df_peers['company_id'].values:
    df_all_metrics = load_all_metrics(report_type)
    target_row = df_all_metrics[
        (df_all_metrics['company_id'] == target_id) &
        (df_all_metrics['year'] == year) &
        (df_all_metrics['quarter'] == quarter)
    ]
    df_peers = pd.concat([target_row, df_peers], ignore_index=True).drop_duplicates(subset='company_id')

peer_count = len(df_peers)
st.caption(f'同業比較範圍：{peer_count} 家公司（含目標公司）')

# ── 比較表格 ──────────────────────────────────────────────────────────────────
st.subheader('財務指標比較表')

compare_cols = [
    'company_id', 'company_name',
    'gross_margin_q', 'gross_margin_yoy_change',
    'operating_margin_q', 'operating_margin_yoy_change',
    'net_margin_q',
    'revenue_yoy', 'net_income_yoy',
    'eps_q', 'eps_ytd',
    'debt_ratio_q',
]
show_cols = [c for c in compare_cols if c in df_peers.columns]
df_table = df_peers[show_cols].copy()

# 計算產業中位數
numeric_cols = df_table.select_dtypes(include='number').columns.tolist()
median_row = {c: df_table[c].median() for c in numeric_cols}
median_row['company_id'] = '──'
median_row['company_name'] = '產業中位數'
df_table = pd.concat([df_table, pd.DataFrame([median_row])], ignore_index=True)

rename_map = {
    'company_id': '代號',
    'company_name': '公司',
    'gross_margin_q': '毛利率%',
    'gross_margin_yoy_change': '毛利pp',
    'operating_margin_q': '營益率%',
    'operating_margin_yoy_change': '營益pp',
    'net_margin_q': '淨利率%',
    'revenue_yoy': '營收YoY%',
    'net_income_yoy': '淨利YoY%',
    'eps_q': 'EPS季',
    'eps_ytd': 'EPS累計',
    'debt_ratio_q': '負債比%',
}
df_table = df_table.rename(columns=rename_map)

def highlight_target(row):
    """高亮目標公司列"""
    if str(row.get('代號', '')) == str(target_id):
        return ['background-color: #dbeafe'] * len(row)
    if row.get('代號', '') == '──':
        return ['background-color: #f5f5dc; font-weight: bold'] * len(row)
    return [''] * len(row)

float_cols = [c for c in df_table.columns if df_table[c].dtype in ['float64', 'float32']]

styled = (
    df_table.style
    .apply(highlight_target, axis=1)
    .format({c: '{:.1f}' for c in float_cols if c in df_table.columns}, na_rep='N/A')
)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ── 圖表比較 ──────────────────────────────────────────────────────────────────
st.markdown('---')
st.subheader('視覺化比較')

tab_radar, tab_bar = st.tabs(['雷達圖', '指標長條圖'])

# 定義雷達指標（轉換為百分位排名）
radar_metrics = [
    ('gross_margin_q', '毛利率'),
    ('operating_margin_q', '營益率'),
    ('net_margin_q', '淨利率'),
    ('revenue_yoy', '營收YoY'),
    ('eps_q', 'EPS'),
]

with tab_radar:
    df_radar = df_peers.copy()
    valid_metrics = [(col, lbl) for col, lbl in radar_metrics if col in df_radar.columns]

    if len(valid_metrics) >= 3:
        # 計算百分位排名（0-100）
        for col, _ in valid_metrics:
            df_radar[f'{col}_pct'] = df_radar[col].rank(pct=True, na_option='bottom') * 100

        # 準備雷達圖資料
        radar_companies = []
        # 目標公司
        target_data = df_radar[df_radar['company_id'] == target_id]
        if not target_data.empty:
            row = target_data.iloc[0]
            radar_companies.append({
                'name': f'{target_name}（目標）',
                'values': [float(row.get(f'{col}_pct', 50)) for col, _ in valid_metrics],
            })
        # 同業（最多前 5 名）
        df_others = df_radar[df_radar['company_id'] != target_id].head(5)
        for _, r in df_others.iterrows():
            radar_companies.append({
                'name': str(r.get('company_name', r['company_id'])),
                'values': [float(r.get(f'{col}_pct', 50)) for col, _ in valid_metrics],
            })

        fig_radar = radar_chart(
            radar_companies,
            valid_metrics,
            title=f'{target_name} vs 同業（百分位排名）',
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.caption('雷達圖數值為各指標在同業中的百分位排名（越高越好）')
    else:
        st.info('資料不足，無法繪製雷達圖。')

with tab_bar:
    bar_metric = st.selectbox('選擇比較指標', options=[
        ('gross_margin_q', '毛利率 %'),
        ('operating_margin_q', '營益率 %'),
        ('net_margin_q', '淨利率 %'),
        ('revenue_yoy', '營收 YoY %'),
        ('net_income_yoy', '淨利 YoY %'),
        ('eps_q', 'EPS（元）'),
        ('debt_ratio_q', '負債比 %'),
    ], format_func=lambda x: x[1])

    col_key, col_label = bar_metric

    if col_key in df_peers.columns:
        df_bar = df_peers[['company_id', 'company_name', col_key]].dropna(subset=[col_key])
        df_bar['label'] = df_bar['company_name'].fillna(df_bar['company_id'])

        fig_bar = horizontal_bar(
            df_bar,
            value_col=col_key,
            label_col='label',
            title=f'{col_label} — 同業比較',
            highlight_id=target_id,
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption(f'紅色標示為目標公司：{target_name}')
    else:
        st.info(f'資料中無 {col_label} 欄位。')
