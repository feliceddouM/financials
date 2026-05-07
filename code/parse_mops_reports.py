# -*- coding: utf-8 -*-
# MOPS inline XBRL 季報解析器
# 動態讀取 scale/unitRef 屬性,一次掃描建立查詢表

import re
import sys
import itertools
from pathlib import Path
from collections import namedtuple, Counter
from bs4 import BeautifulSoup
import pandas as pd

# ── 常數 ──────────────────────────────────────────────
Ctx = namedtuple('Ctx', ['q_cur', 'q_prv', 'ytd_cur', 'ytd_prv', 'bs_cur', 'bs_prv'])

_STRIP_CHARS = str.maketrans('', '', ',() ')


# ── 數值工具 ──────────────────────────────────────────

def clean_num(txt):
    # 清理數字文字: 千分位逗號、括號負號
    if not txt:
        return None
    s = txt.strip()
    if not s:
        return None
    is_neg = (s[0] == '(' and s[-1] == ')')
    s = s.translate(_STRIP_CHARS)
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if is_neg else n


def read_tag_value(tag):
    # 讀取 ix:nonFraction 的實際數值與單位
    # 回傳 (actual_value, unitRef字串)
    raw = clean_num(tag.text)
    if raw is None:
        return None, ''
    if tag.get('sign', '') == '-':
        raw = -raw
    try:
        exp = int(tag.get('scale', '0'))
    except ValueError:
        exp = 0
    actual = raw * (10 ** exp)
    unit = tag.get('unitRef') or tag.get('unitref') or ''
    return actual, unit


def to_mm(val, unit):
    # 轉百萬元 (EPS不轉)
    if val is None:
        return None
    if unit == 'EarningsPerShare':
        return round(val, 2)
    return round(val / 1_000_000, 2)


def yoy(cur, prv):
    # 年增率 %
    if cur is None or prv is None or prv == 0:
        return None
    return round((cur - prv) / abs(prv) * 100, 2)


def pct(numer, denom):
    # 百分比
    if numer is None or denom is None or denom == 0:
        return None
    return round(numer / denom * 100, 2)


def diff(a, b):
    # 差值
    if a is None or b is None:
        return None
    return round(a - b, 2)


# ── 元資料 ────────────────────────────────────────────

def get_company_info(soup):
    # 從 ix:hidden 讀公司代號/名稱/年度/季度
    info = {'cid': None, 'cname': None, 'yr': None, 'qtr': None}
    mapping = {
        'CompanyID': 'cid',
        'CompanyChineseName': 'cname',
        'Year': 'yr',
        'Quarter': 'qtr',
    }
    for tag in soup.find_all(re.compile(r'nonnumeric$', re.I)):
        nm = tag.get('name', '')
        for suffix, key in mapping.items():
            if suffix in nm:
                info[key] = (tag.text or '').strip()
                break

    # 備援: 從 <title> 取
    if not (info['cid'] and info['yr'] and info['qtr']):
        title = soup.title.text if soup.title else ''
        m = re.search(r'(\d{4})Q([1-4])', title)
        if m:
            info['yr'], info['qtr'] = m.group(1), m.group(2)
        m2 = re.search(r'^\s*(\d{4})\s', title)
        if m2 and not info['cid']:
            info['cid'] = m2.group(1)

    return info


# ── Context 字串 ──────────────────────────────────────

def make_ctx_strings(yr, qtr):
    # 產生六組 contextRef 字串
    bounds = {
        '1': ('0101', '0331'),
        '2': ('0401', '0630'),
        '3': ('0701', '0930'),
        '4': ('1001', '1231'),
    }
    if qtr not in bounds:
        return None
    start_md, end_md = bounds[qtr]
    pyr = str(int(yr) - 1)
    return Ctx(
        q_cur=f'From{yr}{start_md}To{yr}{end_md}',
        q_prv=f'From{pyr}{start_md}To{pyr}{end_md}',
        ytd_cur=f'From{yr}0101To{yr}{end_md}',
        ytd_prv=f'From{pyr}0101To{pyr}{end_md}',
        bs_cur=f'AsOf{yr}{end_md}',
        bs_prv=f'AsOf{pyr}{end_md}',
    )


# ── 核心: 一次掃描建表 ───────────────────────────────

_CODE_RE = re.compile(r'^[0-9X]{4}$')

def scan_all_values(soup):
    # 一次走訪所有 ix:nonFraction,建立 (代號, context) -> (實際值, 單位)
    lookup = {}
    for tag in soup.find_all(re.compile(r'nonfraction$', re.I)):
        ctx = tag.get('contextRef') or tag.get('contextref') or ''
        if not ctx:
            continue
        tr = tag.find_parent('tr')
        if not tr:
            continue
        # 找同一行的會計代號 td
        code = None
        for td in tr.find_all('td'):
            txt = td.get_text(strip=True)
            if _CODE_RE.match(txt):
                code = txt
                break
        if not code:
            continue
        val, unit = read_tag_value(tag)
        key = (code, ctx)
        if key not in lookup:
            lookup[key] = (val, unit)
    return lookup


def grab(lookup, code, ctx):
    # 查表取值,自動轉百萬元
    pair = lookup.get((code, ctx))
    if pair is None:
        return None
    return to_mm(pair[0], pair[1])


def grab_raw(lookup, code, ctx):
    # 查表取原始值 (計算比率用)
    pair = lookup.get((code, ctx))
    if pair is None:
        return None
    return pair[0]


# ── 單檔解析 ──────────────────────────────────────────

def parse_one_file(fpath):
    # 解析一份財報 HTML,回傳 dict
    try:
        html = fpath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            html = fpath.read_text(encoding='big5', errors='replace')
        except Exception as e:
            return {'err': str(e), 'file': fpath.name, 'quality': 'fail'}
    except Exception as e:
        return {'err': str(e), 'file': fpath.name, 'quality': 'fail'}

    soup = BeautifulSoup(html, 'html.parser')
    meta = get_company_info(soup)

    if not (meta['cid'] and meta['yr'] and meta['qtr']):
        return {'err': 'meta_missing', 'file': fpath.name, 'quality': 'fail'}

    ctx = make_ctx_strings(meta['yr'], meta['qtr'])
    if ctx is None:
        return {'err': 'bad_quarter', 'file': fpath.name, 'quality': 'fail'}

    is_cr = '-cr-' in fpath.name
    rpt = '合併' if is_cr else '個別'

    # 會計科目代號
    C_REV   = '4000'
    C_GP    = '5900'
    C_OI    = '6900'
    C_NI    = '8610' if is_cr else '8200'
    C_EPS   = '9750'
    C_ASSET = '1XXX'
    C_LIAB  = '2XXX'

    tbl = scan_all_values(soup)

    # ---- 取值 (百萬元) ----

    # 單季
    rev_cur = grab(tbl, C_REV, ctx.q_cur)
    rev_prv = grab(tbl, C_REV, ctx.q_prv)
    gp_cur  = grab(tbl, C_GP,  ctx.q_cur)
    gp_prv  = grab(tbl, C_GP,  ctx.q_prv)
    oi_cur  = grab(tbl, C_OI,  ctx.q_cur)
    oi_prv  = grab(tbl, C_OI,  ctx.q_prv)
    ni_cur  = grab(tbl, C_NI,  ctx.q_cur)
    ni_prv  = grab(tbl, C_NI,  ctx.q_prv)
    eps_cur = grab(tbl, C_EPS, ctx.q_cur)
    eps_prv = grab(tbl, C_EPS, ctx.q_prv)

    # 累計
    rev_ytd_cur = grab(tbl, C_REV, ctx.ytd_cur)
    rev_ytd_prv = grab(tbl, C_REV, ctx.ytd_prv)
    gp_ytd_cur  = grab(tbl, C_GP,  ctx.ytd_cur)
    gp_ytd_prv  = grab(tbl, C_GP,  ctx.ytd_prv)
    oi_ytd_cur  = grab(tbl, C_OI,  ctx.ytd_cur)
    oi_ytd_prv  = grab(tbl, C_OI,  ctx.ytd_prv)
    ni_ytd_cur  = grab(tbl, C_NI,  ctx.ytd_cur)
    ni_ytd_prv  = grab(tbl, C_NI,  ctx.ytd_prv)
    eps_ytd_cur = grab(tbl, C_EPS, ctx.ytd_cur)
    eps_ytd_prv = grab(tbl, C_EPS, ctx.ytd_prv)

    # 資產負債
    ast_cur = grab(tbl, C_ASSET, ctx.bs_cur)
    ast_prv = grab(tbl, C_ASSET, ctx.bs_prv)
    lia_cur = grab(tbl, C_LIAB,  ctx.bs_cur)
    lia_prv = grab(tbl, C_LIAB,  ctx.bs_prv)

    # ---- 原始值 (比率計算用) ----
    rev_cur_raw = grab_raw(tbl, C_REV, ctx.q_cur)
    rev_prv_raw = grab_raw(tbl, C_REV, ctx.q_prv)
    gp_cur_raw  = grab_raw(tbl, C_GP,  ctx.q_cur)
    gp_prv_raw  = grab_raw(tbl, C_GP,  ctx.q_prv)
    oi_cur_raw  = grab_raw(tbl, C_OI,  ctx.q_cur)
    oi_prv_raw  = grab_raw(tbl, C_OI,  ctx.q_prv)
    ni_cur_raw  = grab_raw(tbl, C_NI,  ctx.q_cur)
    ni_prv_raw  = grab_raw(tbl, C_NI,  ctx.q_prv)
    ast_cur_raw = grab_raw(tbl, C_ASSET, ctx.bs_cur)
    ast_prv_raw = grab_raw(tbl, C_ASSET, ctx.bs_prv)
    lia_cur_raw = grab_raw(tbl, C_LIAB,  ctx.bs_cur)
    lia_prv_raw = grab_raw(tbl, C_LIAB,  ctx.bs_prv)

    # ---- 組裝結果 ----
    row = {}

    # 基本資料
    row['company_id']   = meta['cid']
    row['company_name'] = meta['cname']
    row['year']         = meta['yr']
    row['quarter']      = meta['qtr']
    row['report_type']  = rpt

    # 單季金額 (百萬元, EPS為元)
    row['revenue_q']              = rev_cur
    row['revenue_q_prev']         = rev_prv
    row['gross_profit_q']         = gp_cur
    row['gross_profit_q_prev']    = gp_prv
    row['operating_income_q']     = oi_cur
    row['operating_income_q_prev']= oi_prv
    row['net_income_q']           = ni_cur
    row['net_income_q_prev']      = ni_prv
    row['eps_q']                  = eps_cur
    row['eps_q_prev']             = eps_prv

    # 累計金額
    row['revenue_ytd']              = rev_ytd_cur
    row['revenue_ytd_prev']         = rev_ytd_prv
    row['gross_profit_ytd']         = gp_ytd_cur
    row['gross_profit_ytd_prev']    = gp_ytd_prv
    row['operating_income_ytd']     = oi_ytd_cur
    row['operating_income_ytd_prev']= oi_ytd_prv
    row['net_income_ytd']           = ni_ytd_cur
    row['net_income_ytd_prev']      = ni_ytd_prv
    row['eps_ytd']                  = eps_ytd_cur
    row['eps_ytd_prev']             = eps_ytd_prv

    # EPS 變動
    row['eps_change_q']   = diff(eps_cur, eps_prv)
    row['eps_change_ytd'] = diff(eps_ytd_cur, eps_ytd_prv)

    # 資產負債 (百萬元)
    row['total_assets_q']           = ast_cur
    row['total_assets_q_prev']      = ast_prv
    row['total_liabilities_q']      = lia_cur
    row['total_liabilities_q_prev'] = lia_prv

    # 單季 YoY %
    row['revenue_yoy']          = yoy(rev_cur, rev_prv)
    row['gross_profit_yoy']     = yoy(gp_cur, gp_prv)
    row['operating_income_yoy'] = yoy(oi_cur, oi_prv)
    row['net_income_yoy']       = yoy(ni_cur, ni_prv)

    # 累計 YoY %
    row['revenue_ytd_yoy']          = yoy(rev_ytd_cur, rev_ytd_prv)
    row['gross_profit_ytd_yoy']     = yoy(gp_ytd_cur, gp_ytd_prv)
    row['operating_income_ytd_yoy'] = yoy(oi_ytd_cur, oi_ytd_prv)
    row['net_income_ytd_yoy']       = yoy(ni_ytd_cur, ni_ytd_prv)

    # 獲利率 % (用原始值算)
    gm_cur = pct(gp_cur_raw, rev_cur_raw)
    gm_prv = pct(gp_prv_raw, rev_prv_raw)
    om_cur = pct(oi_cur_raw, rev_cur_raw)
    om_prv = pct(oi_prv_raw, rev_prv_raw)
    nm_cur = pct(ni_cur_raw, rev_cur_raw)
    nm_prv = pct(ni_prv_raw, rev_prv_raw)

    row['gross_margin_q']      = gm_cur
    row['gross_margin_q_prev'] = gm_prv
    row['operating_margin_q']      = om_cur
    row['operating_margin_q_prev'] = om_prv
    row['net_margin_q']        = nm_cur
    row['net_margin_q_prev']   = nm_prv

    # 獲利率變化 (百分點)
    row['gross_margin_yoy_change']     = diff(gm_cur, gm_prv)
    row['operating_margin_yoy_change'] = diff(om_cur, om_prv)
    row['net_margin_yoy_change']       = diff(nm_cur, nm_prv)

    # 負債比 %
    dr_cur = pct(lia_cur_raw, ast_cur_raw)
    dr_prv = pct(lia_prv_raw, ast_prv_raw)
    row['debt_ratio_q']          = dr_cur
    row['debt_ratio_q_prev']     = dr_prv
    row['debt_ratio_yoy_change'] = diff(dr_cur, dr_prv)

    # 品質
    critical = [rev_cur, rev_prv, ni_cur, ni_prv]
    row['quality'] = 'complete' if all(v is not None for v in critical) else 'incomplete'
    row['file'] = fpath.name

    return row


# ── 批次處理 ──────────────────────────────────────────

def load_whitelist(csv_path):
    # 讀官方公司名單
    for enc in ('big5', 'cp950', 'utf-8'):
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            ids = set(df['company_id'].astype(str).str.strip())
            print(f'[名單] 讀取 {len(ids)} 家 ({enc})')
            return ids
        except Exception:
            pass
    raise RuntimeError(f'無法讀取: {csv_path}')


def run_batch(folder_path, csv_path, out_path):
    # 批次解析全部財報
    wl = load_whitelist(csv_path)
    base = Path(folder_path)

    globs = [
        'tifrs-fr1-m1-ci-cr-*.html',
        'tifrs-fr2-m1-ci-cr-*.html',
        'tifrs-fr1-m1-ci-ir-*.html',
        'tifrs-fr2-m1-ci-ir-*.html',
    ]
    pool = sorted(itertools.chain.from_iterable(base.glob(g) for g in globs))

    targets = []
    for f in pool:
        m = re.search(r'-(\d{4})-', f.name)
        if m and m.group(1) in wl:
            targets.append(f)

    print(f'[檔案] 符合格式: {len(pool)}, 名單內: {len(targets)}')

    rows = []
    stats = Counter()
    seen_ids = set()

    for idx, fp in enumerate(targets, 1):
        m = re.search(r'-(\d{4})-', fp.name)
        if m:
            seen_ids.add(m.group(1))
        print(f'  {idx}/{len(targets)} {fp.name}', end=' ')
        r = parse_one_file(fp)
        rows.append(r)
        q = r.get('quality', 'fail')
        stats[q] += 1
        print(f'[{q}]')

    # 寫出 CSV
    df = pd.DataFrame(rows)
    col_order = [
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
    ]
    keep = [c for c in col_order if c in df.columns]
    df[keep].to_csv(out_path, index=False, encoding='utf-8-sig')

    missing = wl - seen_ids
    print(f'\n--- 完成 ---')
    print(f'處理: {len(targets)} 檔')
    for k in ('complete', 'incomplete', 'fail'):
        print(f'  {k}: {stats[k]}')
    print(f'名單未涵蓋: {len(missing)} 家')
    print(f'涵蓋率: {len(seen_ids) / len(wl) * 100:.1f}%')
    print(f'輸出: {out_path}')


# ── 設定路徑（改成你的實際路徑）──
CSV_PATH = 't163sb04_20251218_15322930.csv'   # 公司名單
DIR_PATH = '../tifrs-2025Q3'                   # HTML 財報資料夾
OUT_PATH = 'financial_metrics_2025Q3.csv'  # 輸出

run_batch(DIR_PATH, CSV_PATH, OUT_PATH)
