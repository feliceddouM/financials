# -*- coding: utf-8 -*-
"""
utils/charts.py
可複用的 Plotly 圖表函式。
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


_COLORS = {
    'bar_main': '#4C72B0',
    'bar_prev': '#C0C0C0',
    'line_yoy': '#DD8452',
    'positive': '#27AE60',
    'negative': '#E74C3C',
    'neutral': '#95A5A6',
}

_LAYOUT = dict(
    font=dict(family='Arial, sans-serif', size=12),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(orientation='h', y=-0.15),
)


def bar_with_yoy_line(
    df: pd.DataFrame,
    bar_col: str,
    yoy_col: str,
    title: str,
    bar_label: str = '金額(百萬)',
    yoy_label: str = 'YoY %',
    bar_color: str = None,
) -> go.Figure:
    """
    雙軸圖：長條（金額）+ 折線（YoY%）
    df 需有 period 欄位作為 x 軸。
    """
    if df.empty:
        return go.Figure().update_layout(title=title, **_LAYOUT)

    bar_color = bar_color or _COLORS['bar_main']

    fig = go.Figure()

    # 長條圖（左軸）
    bar_colors = []
    for v in df[bar_col]:
        if pd.isna(v):
            bar_colors.append(_COLORS['neutral'])
        elif v >= 0:
            bar_colors.append(bar_color)
        else:
            bar_colors.append(_COLORS['negative'])

    fig.add_trace(go.Bar(
        name=bar_label,
        x=df['period'],
        y=df[bar_col],
        marker_color=bar_colors,
        yaxis='y1',
    ))

    # YoY 折線（右軸）
    if yoy_col in df.columns:
        yoy_colors = [
            _COLORS['positive'] if (not pd.isna(v) and v > 0)
            else (_COLORS['negative'] if (not pd.isna(v) and v < 0)
                  else _COLORS['neutral'])
            for v in df[yoy_col]
        ]
        fig.add_trace(go.Scatter(
            name=yoy_label,
            x=df['period'],
            y=df[yoy_col],
            mode='lines+markers',
            line=dict(color=_COLORS['line_yoy'], width=2),
            marker=dict(color=yoy_colors, size=8),
            yaxis='y2',
        ))

    fig.update_layout(
        title=title,
        yaxis=dict(title=bar_label, showgrid=True, gridcolor='#f0f0f0'),
        yaxis2=dict(
            title=yoy_label,
            overlaying='y',
            side='right',
            showgrid=False,
            zeroline=True,
            zerolinecolor='#cccccc',
        ),
        hovermode='x unified',
        **_LAYOUT,
    )
    return fig


def margin_trend(df: pd.DataFrame, title: str = '獲利率趨勢') -> go.Figure:
    """三率折線圖：毛利率、營益率、淨利率"""
    if df.empty:
        return go.Figure().update_layout(title=title, **_LAYOUT)

    fig = go.Figure()
    metrics = [
        ('gross_margin_q', '毛利率', '#2ECC71'),
        ('operating_margin_q', '營益率', '#3498DB'),
        ('net_margin_q', '淨利率', '#9B59B6'),
    ]
    for col, name, color in metrics:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                name=name,
                x=df['period'],
                y=df[col],
                mode='lines+markers',
                line=dict(color=color, width=2),
                marker=dict(size=7),
            ))

    fig.add_hline(y=0, line_dash='dash', line_color='#cccccc')
    fig.update_layout(
        title=title,
        yaxis=dict(title='%', showgrid=True, gridcolor='#f0f0f0'),
        hovermode='x unified',
        **_LAYOUT,
    )
    return fig


def radar_chart(
    companies: list[dict],
    metrics: list[tuple[str, str]],
    title: str = '同業雷達圖',
) -> go.Figure:
    """
    雷達圖比較多家公司。
    companies: [{'name': '台積電', 'values': [80, 90, 75, ...]}]
    metrics: [('gross_margin_q', '毛利率'), ...]
    """
    fig = go.Figure()
    metric_labels = [m[1] for m in metrics] + [metrics[0][1]]  # 閉合

    colors = px.colors.qualitative.Set2

    for i, comp in enumerate(companies):
        vals = comp['values'] + [comp['values'][0]]  # 閉合
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=metric_labels,
            fill='toself',
            name=comp['name'],
            line=dict(color=colors[i % len(colors)]),
            opacity=0.7,
        ))

    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        **_LAYOUT,
    )
    return fig


def horizontal_bar(
    df: pd.DataFrame,
    value_col: str,
    label_col: str,
    title: str,
    highlight_id: str = None,
    unit: str = '%',
) -> go.Figure:
    """
    水平長條圖，依數值排序，可高亮特定公司。
    """
    if df.empty:
        return go.Figure().update_layout(title=title, **_LAYOUT)

    df_sorted = df.copy().dropna(subset=[value_col]).sort_values(value_col)

    colors = []
    for _, row in df_sorted.iterrows():
        if highlight_id and str(row.get('company_id', '')) == str(highlight_id):
            colors.append('#E74C3C')
        elif row[value_col] >= 0:
            colors.append(_COLORS['bar_main'])
        else:
            colors.append(_COLORS['negative'])

    fig = go.Figure(go.Bar(
        x=df_sorted[value_col],
        y=df_sorted[label_col],
        orientation='h',
        marker_color=colors,
        text=[f'{v:.1f}{unit}' for v in df_sorted[value_col]],
        textposition='outside',
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(title=unit, showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(tickfont=dict(size=11)),
        **_LAYOUT,
    )
    return fig
