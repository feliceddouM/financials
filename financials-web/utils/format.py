# -*- coding: utf-8 -*-
"""
utils/format.py
數字格式化、顏色標示工具。
"""


def fmt_millions(val, unit: str = '百萬', decimals: int = 0) -> str:
    """格式化百萬元數字"""
    if val is None:
        return 'N/A'
    try:
        v = float(val)
        if abs(v) >= 1_000_000:
            return f'{v / 1_000_000:.{decimals}f}T {unit}'
        if abs(v) >= 1_000:
            return f'{v / 1_000:.{decimals}f}B {unit}'
        return f'{v:,.{decimals}f} {unit}'
    except (TypeError, ValueError):
        return 'N/A'


def fmt_pct(val, decimals: int = 1, suffix: str = '%') -> str:
    """格式化百分比"""
    if val is None:
        return 'N/A'
    try:
        return f'{float(val):+.{decimals}f}{suffix}'
    except (TypeError, ValueError):
        return 'N/A'


def fmt_pct_plain(val, decimals: int = 1) -> str:
    """格式化百分比（不含+號）"""
    if val is None:
        return 'N/A'
    try:
        return f'{float(val):.{decimals}f}%'
    except (TypeError, ValueError):
        return 'N/A'


def fmt_eps(val) -> str:
    """格式化 EPS"""
    if val is None:
        return 'N/A'
    try:
        return f'NT${float(val):+.2f}'
    except (TypeError, ValueError):
        return 'N/A'


def color_delta(val, positive_is_good: bool = True) -> str:
    """
    根據數值正負回傳顏色字串（用於 st.metric）
    正值 → 'normal' (綠色箭頭)
    負值 → 'inverse' (紅色箭頭)
    """
    if val is None:
        return 'off'
    try:
        v = float(val)
        if abs(v) < 0.01:
            return 'off'
        if positive_is_good:
            return 'normal' if v > 0 else 'inverse'
        else:
            return 'inverse' if v > 0 else 'normal'
    except (TypeError, ValueError):
        return 'off'


def delta_label(val, unit: str = '%', decimals: int = 1) -> str | None:
    """產生 st.metric 的 delta 顯示文字"""
    if val is None:
        return None
    try:
        v = float(val)
        return f'{v:+.{decimals}f}{unit}'
    except (TypeError, ValueError):
        return None


def pct_color_css(val, low: float = 20.0, high: float = 40.0) -> str:
    """
    根據百分比數值回傳背景顏色 CSS（用於表格高亮）
    val < low  → 淡紅
    val > high → 淡綠
    中間       → 白色
    """
    if val is None:
        return ''
    try:
        v = float(val)
        if v >= high:
            return 'background-color: #d4f5d4'
        if v < low:
            return 'background-color: #ffd4d4'
        return ''
    except (TypeError, ValueError):
        return ''


def yoy_color_css(val, threshold: float = 0.0) -> str:
    """YoY 顏色"""
    if val is None:
        return ''
    try:
        v = float(val)
        if v > threshold:
            return 'background-color: #d4f5d4'
        if v < threshold:
            return 'background-color: #ffd4d4'
        return ''
    except (TypeError, ValueError):
        return ''
