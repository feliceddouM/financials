# -*- coding: utf-8 -*-
"""
app.py
台灣股市財報分析工具 - Streamlit 主入口
"""

import streamlit as st
from pathlib import Path
import sys

# 確保 utils 可以被各 page 引入
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title='台股財報分析',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title('📊 台股財報分析')
    st.markdown('---')

    # 資料新鮮度
    try:
        from utils.db import get_data_info, DB_PATH
        if DB_PATH.exists():
            info = get_data_info()
            st.info(
                f'**資料截至**: {info["latest_period"]}\n\n'
                f'**覆蓋公司**: {info["company_count"]:,} 家'
            )
        else:
            st.warning('尚未載入資料，請先執行資料匯入。')
            st.code('python pipeline/db_loader.py --csv your_metrics.csv', language='bash')
    except Exception as e:
        st.warning(f'資料庫連線失敗: {e}')

    st.markdown('---')
    st.markdown(
        '<small>資料來源: 公開資訊觀測站 (MOPS)<br>'
        '財務數字單位: 百萬元台幣（EPS 為元）</small>',
        unsafe_allow_html=True,
    )

# ── 首頁內容 ──────────────────────────────────────────────────────────────────
st.title('台灣上市櫃公司財報分析平台')
st.markdown("""
請從左側導航列選擇功能：

| 功能 | 說明 |
|------|------|
| 📋 **公司財務總覽** | 查詢單一公司歷史財務指標與趨勢圖 |
| 🔍 **選股篩選器** | 依財務條件篩選符合的公司 |
| ⚖️ **同業比較** | 與同產業公司財務指標對比 |
""")

st.markdown('---')

# ── 快速入門（無資料時顯示） ────────────────────────────────────────────────────
try:
    from utils.db import get_data_info, DB_PATH
    if not DB_PATH.exists():
        st.subheader('快速開始')
        st.markdown("""
        **Step 1**: 解析財報 HTML 資料夾
        ```bash
        cd financials-web
        python pipeline/parse_mops_reports.py  \\
            path/to/t163sb04.csv \\
            path/to/tifrs-2025Q3 \\
            financial_metrics_2025Q3.csv
        ```

        **Step 2**: 載入至資料庫
        ```bash
        python pipeline/db_loader.py \\
            --csv financial_metrics_2025Q3.csv \\
            --fetch-companies
        ```

        **Step 3**: 重新整理此頁面，即可開始使用！
        """)
except Exception:
    pass
