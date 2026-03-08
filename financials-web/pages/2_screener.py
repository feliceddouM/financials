# -*- coding: utf-8 -*-
"""
pages/2_screener.py
選股篩選器：依財務指標條件篩選公司，支援跨頁跳轉至公司總覽。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from utils.db import load_all_metrics, get_available_periods, get_industry_list

st.set_page_config(page_title='選股篩選器', page_icon='🔍', layout='wide')
st.title('🔍 選股篩選器')

# ── 載入資料 ──────────────────────────────────────────────────────────────────
periods = get_available_periods()
industries = get_industry_list()

if not periods:
    st.warning('資料庫尚無資料，請先執行資料匯入。請參考首頁說明。')
    st.stop()

# ── 側欄篩選器 ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('篩選條件')

    # 期別
    selected_period = st.selectbox('期別', options=periods, index=0)
    year, quarter = selected_period[:4], selected_period[5]

    # 報表類型
    report_type = st.radio('報表類型', ['合併', '個別'], horizontal=True)

    st.markdown('---')

    # 預設組合
    st.markdown('**快速預設**')
    preset_cols = st.columns(2)
    with preset_cols[0]:
        preset_growth = st.button('高毛利穩成長', use_container_width=True,
                                   help='毛利率>40%, 營收YoY>10%')
    with preset_cols[1]:
        preset_turnaround = st.button('轉機股', use_container_width=True,
                                       help='淨利YoY>50%, 營收YoY>0%')

    st.markdown('---')
    st.markdown('**獲利率 (%)**')

    gm_min = st.slider('毛利率 最低', -100, 100, 0, key='gm_min')
    om_min = st.slider('營益率 最低', -100, 100, 0, key='om_min')
    nm_min = st.slider('淨利率 最低', -100, 100, -50, key='nm_min')

    st.markdown('**成長率 YoY (%)**')
    rev_yoy_min = st.slider('營收 YoY 最低', -100, 500, -100, key='rev_yoy_min')
    ni_yoy_min = st.slider('淨利 YoY 最低', -500, 2000, -500, key='ni_yoy_min')

    st.markdown('**EPS（元）**')
    eps_min = st.number_input('EPS 最低', value=-999.0, step=0.5, key='eps_min')

    st.markdown('**負債比 (%)**')
    debt_max = st.slider('負債比 最高', 0, 100, 100, key='debt_max')

    st.markdown('**產業別**')
    selected_industries = st.multiselect(
        '選擇產業（空白=全部）',
        options=industries,
        default=[],
        key='industries',
    )

    st.markdown('**資料品質**')
    complete_only = st.checkbox('只顯示 complete', value=True, key='complete_only')

    st.markdown('---')
    if st.button('重置所有篩選', use_container_width=True):
        for k in ['gm_min', 'om_min', 'nm_min', 'rev_yoy_min',
                  'ni_yoy_min', 'eps_min', 'debt_max', 'industries', 'complete_only']:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

# 處理預設組合
if preset_growth:
    st.session_state['gm_min'] = 40
    st.session_state['rev_yoy_min'] = 10
    st.rerun()
if preset_turnaround:
    st.session_state['ni_yoy_min'] = 50
    st.session_state['rev_yoy_min'] = 0
    st.rerun()

# ── 篩選邏輯 ──────────────────────────────────────────────────────────────────
df_all = load_all_metrics(report_type)

# 篩選期別
mask = (df_all['year'] == year) & (df_all['quarter'] == quarter)
df = df_all[mask].copy()

# 獲利率
if gm_min > -100:
    df = df[df['gross_margin_q'].notna() & (df['gross_margin_q'] >= gm_min)]
if om_min > -100:
    df = df[df['operating_margin_q'].notna() & (df['operating_margin_q'] >= om_min)]
if nm_min > -100:
    df = df[df['net_margin_q'].notna() & (df['net_margin_q'] >= nm_min)]

# 成長率
if rev_yoy_min > -100:
    df = df[df['revenue_yoy'].notna() & (df['revenue_yoy'] >= rev_yoy_min)]
if ni_yoy_min > -500:
    df = df[df['net_income_yoy'].notna() & (df['net_income_yoy'] >= ni_yoy_min)]

# EPS
if eps_min > -999:
    df = df[df['eps_q'].notna() & (df['eps_q'] >= eps_min)]

# 負債比
if debt_max < 100:
    df = df[df['debt_ratio_q'].notna() & (df['debt_ratio_q'] <= debt_max)]

# 產業別
if selected_industries:
    df = df[df['industry_name'].isin(selected_industries)]

# 資料品質
if complete_only:
    df = df[df['quality'] == 'complete']

# ── 結果區域 ──────────────────────────────────────────────────────────────────
result_count = len(df)
col_title, col_dl = st.columns([3, 1])

with col_title:
    color = 'green' if result_count > 0 else 'red'
    st.markdown(
        f'**{selected_period} {report_type}報表** — 找到 '
        f'<span style="color:{color};font-size:1.3em;font-weight:bold">{result_count}</span> 家公司',
        unsafe_allow_html=True,
    )

with col_dl:
    if result_count > 0:
        csv_bytes = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label='下載結果 CSV',
            data=csv_bytes,
            file_name=f'screener_{selected_period}.csv',
            mime='text/csv',
        )

if result_count == 0:
    st.warning('沒有符合條件的公司，請放寬篩選條件。')
    st.stop()

# ── 顯示欄位設定 ──────────────────────────────────────────────────────────────
display_cols = [
    'company_id', 'company_name', 'industry_name',
    'revenue_q', 'revenue_yoy',
    'gross_margin_q', 'gross_margin_yoy_change',
    'operating_margin_q', 'operating_margin_yoy_change',
    'net_margin_q',
    'net_income_yoy',
    'eps_q', 'eps_ytd',
    'debt_ratio_q',
    'quality',
]
show_cols = [c for c in display_cols if c in df.columns]
df_show = df[show_cols].copy().sort_values('revenue_q', ascending=False)

rename_map = {
    'company_id': '代號',
    'company_name': '公司',
    'industry_name': '產業',
    'revenue_q': '營收(百萬)',
    'revenue_yoy': '營收YoY%',
    'gross_margin_q': '毛利率%',
    'gross_margin_yoy_change': '毛利pp',
    'operating_margin_q': '營益率%',
    'operating_margin_yoy_change': '營益pp',
    'net_margin_q': '淨利率%',
    'net_income_yoy': '淨利YoY%',
    'eps_q': 'EPS季',
    'eps_ytd': 'EPS累計',
    'debt_ratio_q': '負債比%',
    'quality': '品質',
}
df_show = df_show.rename(columns=rename_map)

# 設定表格顏色（YoY 欄位）
def style_df(df_s):
    styled = df_s.style

    def color_yoy(val):
        if pd.isna(val):
            return ''
        return 'background-color: #d4f5d4' if float(val) > 0 else 'background-color: #ffd4d4'

    def color_pct(val):
        if pd.isna(val):
            return ''
        v = float(val)
        if v >= 40:
            return 'background-color: #d4f5d4'
        if v < 10:
            return 'background-color: #ffd4d4'
        return ''

    yoy_cols = [c for c in ['營收YoY%', '毛利pp', '營益pp', '淨利YoY%'] if c in df_s.columns]
    pct_cols = [c for c in ['毛利率%', '營益率%', '淨利率%'] if c in df_s.columns]

    for col in yoy_cols:
        styled = styled.applymap(color_yoy, subset=[col])
    for col in pct_cols:
        styled = styled.applymap(color_pct, subset=[col])

    # 數值格式化
    float_cols = [c for c in df_s.columns if df_s[c].dtype in ['float64', 'float32']]
    styled = styled.format(
        {c: '{:.1f}' for c in float_cols if c in df_s.columns},
        na_rep='N/A',
    )
    return styled

st.dataframe(
    style_df(df_show),
    use_container_width=True,
    hide_index=True,
    height=500,
)

# ── 跨頁跳轉 ──────────────────────────────────────────────────────────────────
st.markdown('---')
st.markdown('**點擊公司代號查看詳細財務總覽：**')

jump_cols = st.columns(min(8, result_count))
for i, (_, row) in enumerate(df_show.head(16).iterrows()):
    with jump_cols[i % 8]:
        cid = str(row.get('代號', ''))
        cname = str(row.get('公司', ''))
        if st.button(f'{cid}\n{cname}', key=f'jump_{cid}', use_container_width=True):
            st.session_state['selected_company'] = cid
            st.switch_page('pages/1_company.py')
