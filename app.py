import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
import datetime

# ----------------- 頁面全域設定 (100% 滿版排版) -----------------
st.set_page_config(
    page_title="TPBL 職業籃球進階數據與球探分析系統",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- 頂部現代風格：電腦/手機雙端完全自適應 CSS -----------------
top_nav_style = """
<style>
/* 1. 徹底隱藏原生 Header、工具列、頁尾與嵌入白條 */
header, [data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
footer, [data-testid="stEmbedFooter"] {display: none !important;}
div[class*="viewerBadge"] {display: none !important;}

/* 2. 徹底關閉左側邊欄，釋放 100% 畫面空間 */
[data-testid="stSidebar"] {display: none !important;}
[data-testid="stSidebarCollapseButton"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}

/* 3. 隱藏 st.radio 頂部的提示標題 */
div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
    display: none !important;
}

/* ========================================================= */
/* 【電腦螢幕專屬樣式：寬度 >= 768px】                      */
/* ========================================================= */
@media (min-width: 768px) {
    div[data-testid="stRadio"] {
        width: 100% !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        width: 100% !important;
        gap: 12px !important;
        background: rgba(255, 255, 255, 0.03) !important;
        padding: 8px 12px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        margin-bottom: 20px !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        flex: 1 1 0 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 12px 10px !important;
        border-radius: 9px !important;
        cursor: pointer !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] p {
        font-size: 1.12rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }
}

/* ========================================================= */
/* 【手機螢幕專屬樣式：寬度 < 768px】                       */
/* ========================================================= */
@media (max-width: 767px) {
    div[data-testid="stRadio"] {
        width: 100% !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 8px !important;
        background: transparent !important;
        padding: 0 !important;
        border: none !important;
        margin-bottom: 16px !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:last-child {
        grid-column: span 2 !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background-color: rgba(255, 255, 255, 0.06) !important;
        padding: 10px 6px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] p {
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        margin: 0 !important;
        text-align: center !important;
    }
}

/* 4. 通用：滑鼠懸停與選中高亮效果 */
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background-color: rgba(0, 230, 118, 0.15) !important;
    border-color: #00E676 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background-color: rgba(0, 230, 118, 0.18) !important;
    border-color: #00E676 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {
    color: #00E676 !important;
    font-weight: 700 !important;
}
</style>
"""
st.markdown(top_nav_style, unsafe_allow_html=True)

# ----------------- 時間與數值格式化工具函式 -----------------
def clean_time_display(val):
    if pd.isna(val):
        return ""
    if isinstance(val, (pd.Timedelta, datetime.timedelta)):
        tot_sec = val.total_seconds()
        orig_mins = int(tot_sec // 3600)
        orig_secs = int((tot_sec % 3600) // 60)
        return f"{orig_mins:02d}:{orig_secs:02d}"
    val_str = str(val).strip()
    m_day = re.match(r'(\d+)\s*days?,?\s*(\d+):(\d+)(?::(\d+))?', val_str)
    if m_day:
        days = int(m_day.group(1))
        hours = int(m_day.group(2))
        mins = int(m_day.group(3))
        orig_mins = days * 24 + hours
        orig_secs = mins
        return f"{orig_mins:02d}:{orig_secs:02d}"
    m_pt = re.match(r'PT(\d+)H(\d+)M', val_str)
    if m_pt:
        return f"{int(m_pt.group(1)):02d}:{int(m_pt.group(2)):02d}"
    m_hms = re.match(r'^(\d+):(\d+):00$', val_str)
    if m_hms:
        return f"{int(m_hms.group(1)):02d}:{int(m_hms.group(2)):02d}"
    return val_str

def format_pct(val):
    if pd.isna(val) or val == "" or str(val).strip() == "-" or str(val).strip() == "nan":
        return "0.0%"
    s = str(val).strip()
    if s.endswith('%'):
        try:
            return f"{float(s.replace('%', '')):.1f}%"
        except:
            return s
    try:
        f = float(s)
        return f"{f * 100:.1f}%" if 0 < f <= 1.0 else f"{f:.1f}%"
    except:
        return s

def get_ast_to_ratio(row):
    if 'AST/TO' in row and pd.notna(row['AST/TO']) and str(row['AST/TO']).strip() != "":
        val = str(row['AST/TO']).strip()
        try:
            return f"{float(val):.2f}"
        except:
            return val
    try:
        ast = float(row.get('助攻', 0))
        tov = float(row.get('失誤', 0))
        if tov == 0:
            return f"{ast:.1f} (無失誤)" if ast > 0 else "0.00"
        return f"{ast / tov:.2f}"
    except:
        return "0.00"

def make_stat_badge_row(label, val):
    return f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.08);"><span style="font-size: 1.05rem; font-weight: 600; color: #E0E0E0;">{label}</span><span style="font-size: 1.22rem; font-weight: 700; color: #00E676; background-color: rgba(0, 230, 118, 0.15); padding: 4px 14px; border-radius: 6px; letter-spacing: 0.5px;">{val}</span></div>'

def clean_dataframe_times(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        col_str = str(col)
        if any(k in col_str for k in ['時間', 'Time', 'time', '共同時間', '累計時間']):
            df[col] = df[col].apply(clean_time_display)
    return df

def deduplicate_columns(df):
    if df is None or df.empty:
        return df
    cols = [str(c).strip() for c in df.columns]
    cols = [f"Col_{i}" if c == "" or c == "nan" or "Unnamed" in c else c for i, c in enumerate(cols)]
    seen = {}
    new_cols = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols
    return df

# ----------------- 支援資料夾分流的智慧找檔函式 -----------------
def find_file_in_folders(candidate_dirs, keyword):
    keyword_clean = keyword.lower().strip()
    for d in candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                fname_lower = fname.lower()
                if keyword_clean in fname_lower and fname_lower.endswith(('.xlsx', '.xls', '.csv')):
                    return os.path.join(d, fname)
    return None

def find_team_file_in_folders(candidate_dirs, team_name):
    team_keywords = {
        "福爾摩沙夢想家": ["夢想家", "福爾摩沙"],
        "新北國王": ["國王"],
        "高雄全家海神": ["海神", "全家"],
        "新北中信特攻": ["特攻", "中信"],
        "臺北台新戰神": ["戰神", "台新"],
        "桃園台啤永豐雲豹": ["雲豹", "台啤", "永豐"],
        "新竹御嵿攻城獅": ["攻城獅", "攻城", "御嵿"]
    }
    kws = team_keywords.get(team_name, [team_name])
    for d in candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                fname_lower = fname.lower()
                if any(kw.lower() in fname_lower for kw in kws) and fname_lower.endswith(('.xlsx', '.xls', '.csv')):
                    return os.path.join(d, fname)
    return None

# ----------------- 總表拆解解析 (自動探測表頭，相容各種註釋行) -----------------
def parse_summary_sheet(filepath):
    try:
        if filepath.lower().endswith('.csv'):
            df_raw = pd.read_csv(filepath, header=None)
        else:
            df_raw = pd.read_excel(filepath, sheet_name=0, header=None)
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    if df_raw is None or df_raw.empty:
        return pd.DataFrame(), pd.DataFrame()

    row_block_a_title = None
    row_block_b_title = None

    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)])
        if "【區塊 A" in row_str or "區塊 A" in row_str:
            row_block_a_title = idx
        elif "【區塊 B" in row_str or "區塊 B" in row_str:
            row_block_b_title = idx

    # 解析區塊 A：往下自動尋找含有「球隊名稱」或「團隊總得分」的正確表頭列
    block_a = pd.DataFrame()
    if row_block_a_title is not None:
        header_a_idx = None
        search_end = row_block_b_title if row_block_b_title is not None else row_block_a_title + 5
        for r in range(row_block_a_title + 1, min(len(df_raw), search_end)):
            row_str = " ".join([str(v) for v in df_raw.iloc[r].values if pd.notna(v)])
            if "球隊名稱" in row_str or "團隊總得分" in row_str or "戰績" in row_str:
                header_a_idx = r
                break
        
        if header_a_idx is not None:
            end_a = row_block_b_title if row_block_b_title is not None else header_a_idx + 8
            block_a = df_raw.iloc[header_a_idx + 1 : end_a].copy()
            block_a.columns = [str(c).strip() for c in df_raw.iloc[header_a_idx].tolist()]
            block_a = clean_dataframe_times(deduplicate_columns(block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)))

    # 解析區塊 B：往下自動尋找含有「高球權核心」或「戰力短評」的正確表頭列
    block_b = pd.DataFrame()
    if row_block_b_title is not None:
        header_b_idx = None
        for r in range(row_block_b_title + 1, min(len(df_raw), row_block_b_title + 5)):
            row_str = " ".join([str(v) for v in df_raw.iloc[r].values if pd.notna(v)])
            if "球隊名稱" in row_str or "高球權核心" in row_str or "短評" in row_str:
                header_b_idx = r
                break
                
        if header_b_idx is not None:
            block_b = df_raw.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
            block_b.columns = [str(c).strip() for c in df_raw.iloc[header_b_idx].tolist()]
            block_b = deduplicate_columns(block_b.dropna(how='all', axis=1).dropna(how='all', axis=0))

    return block_a, block_b

# ----------------- 提取各隊專屬 PBP 表格 (雙模智慧解析：相容例行賽縱向與熱身賽橫向) -----------------
def extract_pbp_blocks(filepath):
    if not filepath or not os.path.exists(filepath):
        return {}, pd.DataFrame()
    try:
        xls = pd.ExcelFile(filepath)
        target_sheet = 0
        for s in xls.sheet_names:
            if "平均" in s or "pbp" in s.lower() or "陣容" in s:
                target_sheet = s
                break
        df = pd.read_excel(filepath, sheet_name=target_sheet, header=None)
    except Exception:
        return {}, pd.DataFrame()

    blocks = {}
    
    # 判斷是「縱向垂直排版（例行賽）」還是「橫向並排（熱身賽）」
    has_vertical_brackets = False
    for r in range(len(df)):
        for c in range(min(5, len(df.columns))):
            v = str(df.iloc[r, c]).strip()
            if v.startswith("【") and any(k in v for k in ["on/off", "淨影響力", "五人陣容", "雙洋將", "陣容"]):
                has_vertical_brackets = True
                break
        if has_vertical_brackets:
            break

    # =========================================================
    # 模式 A：縱向垂直排版（例行賽標準格式）
    # =========================================================
    if has_vertical_brackets:
        r_onoff, c_onoff = None, None
        r_lineup, c_lineup = None, None
        r_duo, c_duo = None, None

        for r in range(len(df)):
            for c in range(min(5, len(df.columns))):
                val = str(df.iloc[r, c]).strip()
                if val.startswith("【"):
                    if "on/off" in val.lower() or "淨影響力" in val:
                        if r_onoff is None: r_onoff, c_onoff = r, c
                    elif "五人陣容" in val:
                        if r_lineup is None: r_lineup, c_lineup = r, c
                    elif "雙洋將" in val or "化學效應" in val or "洋將搭檔" in val:
                        if r_duo is None: r_duo, c_duo = r, c

        def extract_vertical_subtable(title_r, title_c):
            if title_r is None or title_c is None:
                return pd.DataFrame()
            header_row_idx = title_r + 1
            if header_row_idx >= len(df):
                return pd.DataFrame()
            headers = []
            col_indices = []
            for cur_c in range(title_c, len(df.columns)):
                h_val = df.iloc[header_row_idx, cur_c]
                if pd.isna(h_val) or str(h_val).strip() == "" or str(h_val).startswith("Unnamed") or str(h_val) == "nan":
                    break
                headers.append(str(h_val).strip())
                col_indices.append(cur_c)
            if not headers:
                return pd.DataFrame()
            data_rows = []
            for cur_r in range(header_row_idx + 1, min(len(df), header_row_idx + 40)):
                first_val = str(df.iloc[cur_r, title_c]).strip()
                if pd.isna(df.iloc[cur_r, title_c]) or first_val == "" or first_val == "nan" or first_val.startswith("【"):
                    break
                data_rows.append([df.iloc[cur_r, col_idx] for col_idx in col_indices])
            res = pd.DataFrame(data_rows, columns=headers)
            res = clean_dataframe_times(res)
            return deduplicate_columns(res)

        if r_onoff is not None:
            blocks['on_off'] = extract_vertical_subtable(r_onoff, c_onoff)
        if r_lineup is not None:
            blocks['lineup'] = extract_vertical_subtable(r_lineup, c_lineup)
        if r_duo is not None:
            blocks['duo'] = extract_vertical_subtable(r_duo, c_duo)

        box_header_row = None
        for r in range(min(12, len(df))):
            row_str = " ".join([str(v) for v in df.iloc[r, :8] if pd.notna(v)])
            if "球員名" in row_str and ("得分" in row_str or "出賽" in row_str or "背號" in row_str):
                box_header_row = r
                break
        if box_header_row is not None:
            end_box = r_onoff if (r_onoff is not None and c_onoff == 0 and r_onoff > box_header_row) else len(df)
            raw_headers = [str(x).strip() for x in df.iloc[box_header_row].tolist()]
            valid_cols_idx = []
            seen = set()
            for idx_h, h in enumerate(raw_headers):
                if "Unnamed" in h or h == "" or "nan" in h or "【" in h or (idx_h > 5 and h in seen):
                    break
                seen.add(h)
                valid_cols_idx.append(idx_h)
            box_df = df.iloc[box_header_row + 1 : end_box, valid_cols_idx].copy()
            box_df.columns = [raw_headers[i] for i in valid_cols_idx]
            box_df = clean_dataframe_times(box_df)
            box_df = deduplicate_columns(box_df.dropna(how='all', axis=0))
        else:
            box_df = pd.DataFrame()

    # =========================================================
    # 模式 B：橫向並排排版（熱身賽格式）
    # =========================================================
    else:
        header_r = None
        for r in range(min(10, len(df))):
            row_str = " ".join([str(v) for v in df.iloc[r, :10] if pd.notna(v)])
            if "球員名" in row_str and ("背號" in row_str or "出賽" in row_str):
                header_r = r
                break
        
        if header_r is None:
            return {}, pd.DataFrame()

        row_headers = [str(df.iloc[header_r, c]).strip() if pd.notna(df.iloc[header_r, c]) else "" for c in range(len(df.columns))]

        def extract_horizontal_subtable(start_c):
            if start_c is None or start_c >= len(row_headers):
                return pd.DataFrame()
            cols = []
            col_idxs = []
            for c in range(start_c, len(row_headers)):
                h = row_headers[c]
                if not h or h == "nan" or h.startswith("Unnamed"):
                    break
                cols.append(h)
                col_idxs.append(c)
            if not cols:
                return pd.DataFrame()
            data = []
            for r in range(header_r + 1, len(df)):
                val = df.iloc[r, col_idxs[0]]
                if pd.isna(val) or str(val).strip() == "" or str(val) == "nan":
                    break
                data.append([df.iloc[r, ci] for ci in col_idxs])
            res = pd.DataFrame(data, columns=cols)
            res = clean_dataframe_times(res)
            return deduplicate_columns(res)

        # 1. 抓取 Box Score（由第 0 欄開始）
        box_df = extract_horizontal_subtable(0)

        # 2. 抓取 On/Off（定位第二個「球員名」所在欄位）
        onoff_c = None
        for c in range(5, len(row_headers)):
            if "On_ORtg" in row_headers[c] or "累計在場時間" in row_headers[c]:
                onoff_c = c - 1 if (c > 0 and row_headers[c-1] == "球員名") else c
                break
            elif "淨影響力" in row_headers[c]:
                for back_c in range(c, max(0, c - 8), -1):
                    if row_headers[back_c] == "球員名":
                        onoff_c = back_c
                        break
                if onoff_c is not None:
                    break
        if onoff_c is not None:
            blocks['on_off'] = extract_horizontal_subtable(onoff_c)

        # 3. 抓取五人陣容（定位「五人陣容組合」所在欄位）
        lineup_c = None
        for c in range(5, len(row_headers)):
            if "五人陣容" in row_headers[c]:
                lineup_c = c
                break
        if lineup_c is not None:
            blocks['lineup'] = extract_horizontal_subtable(lineup_c)

        # 4. 抓取雙洋將化學效應（定位「洋將搭檔」或「雙洋將」所在欄位）
        duo_c = None
        for c in range(5, len(row_headers)):
            if "洋將搭檔" in row_headers[c] or "雙洋將" in row_headers[c]:
                duo_c = c
                break
        if duo_c is not None:
            blocks['duo'] = extract_horizontal_subtable(duo_c)

    return blocks, box_df

# ----------------- 取得球員母表數據 (優先讀取總表，若無則自動從 7 隊合併) -----------------
@st.cache_data(ttl=300)
def get_master_players(candidate_dirs):
    # 1. 優先檢查是否已有獨立總表
    f_master = find_file_in_folders(candidate_dirs, "進階數據與戰力評級總表")
    if f_master:
        try:
            xls = pd.ExcelFile(f_master)
            for s in xls.sheet_names:
                df = pd.read_excel(f_master, sheet_name=s)
                if '球員名' in df.columns:
                    return clean_dataframe_times(deduplicate_columns(df))
                df2 = pd.read_excel(f_master, sheet_name=s, header=1)
                if '球員名' in df2.columns:
                    return clean_dataframe_times(deduplicate_columns(df2))
        except Exception:
            pass

    # 2. 若無獨立總表，自動掃描 7 隊專屬表並即時聚合《球員進階數據》
    all_team_dfs = []
    teams = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    for t_name in teams:
        tf = find_team_file_in_folders(candidate_dirs, t_name)
        if tf:
            try:
                xls = pd.ExcelFile(tf)
                target_sheet = None
                for s in xls.sheet_names:
                    if "進階" in s:
                        target_sheet = s
                        break
                if target_sheet:
                    # 探測標頭列（通常在第 3 或第 4 列）
                    raw_adv = pd.read_excel(tf, sheet_name=target_sheet, header=None)
                    header_idx = None
                    for r in range(min(6, len(raw_adv))):
                        row_vals = [str(x).strip() for x in raw_adv.iloc[r].dropna().tolist()]
                        if "球員名" in row_vals and ("出賽" in row_vals or "背號" in row_vals):
                            header_idx = r
                            break
                    if header_idx is not None:
                        t_df = raw_adv.iloc[header_idx + 1:].copy()
                        t_df.columns = [str(x).strip() for x in raw_adv.iloc[header_idx].tolist()]
                        t_df = t_df.dropna(subset=['球員名', '出賽'])
                        if '球隊' not in t_df.columns or t_df['球隊'].isna().all():
                            t_df['球隊'] = t_name
                        all_team_dfs.append(t_df)
            except Exception:
                continue

    if all_team_dfs:
        combined = pd.concat(all_team_dfs, ignore_index=True)
        return clean_dataframe_times(deduplicate_columns(combined))

    return pd.DataFrame()

# ----------------- 雷達圖能力值計算函式 -----------------
def calculate_radar_scores(row):
    pts = float(row.get('總得分', row.get('得分', 0)))
    games = float(row.get('出賽', 1))
    pts_pg = pts / games if games > 0 else pts
    score_pts = min(99, max(15, (pts_pg / 28.0) * 85 + 14))

    ts_val = str(row.get('TS%', '0')).replace('%', '')
    try:
        ts = float(ts_val)
        if ts < 1.0 and ts > 0: ts = ts * 100.0
    except:
        ts = 50.0
    score_eff = min(99, max(15, ((ts - 40.0) / 32.0) * 85 + 14))

    tpm = float(row.get('三分命中', 0)) / (games if games > 0 else 1)
    score_3p = min(99, max(15, (tpm / 3.5) * 85 + 14))

    ast = float(row.get('助攻', 0)) / (games if games > 0 else 1)
    score_ast = min(99, max(15, (ast / 6.0) * 85 + 14))

    reb = float(row.get('籃板', 0)) / (games if games > 0 else 1)
    score_reb = min(99, max(15, (reb / 12.0) * 85 + 14))

    stocks = (float(row.get('抄截', 0)) + float(row.get('阻攻', 0))) / (games if games > 0 else 1)
    score_def = min(99, max(15, (stocks / 3.5) * 85 + 14))

    return [round(score_pts, 1), round(score_eff, 1), round(score_3p, 1), round(score_ast, 1), round(score_reb, 1), round(score_def, 1)]

# =========================================================================
# 頁首橫幅
# =========================================================================
st.markdown(
    """
    <div style="text-align: center; margin-top: -30px; margin-bottom: 12px;">
        <h1 style="font-size: 2.2rem; margin-bottom: 6px; letter-spacing: 1px;">🏀 TPBL 職業籃球進階數據與球探分析系統</h1>
        <p style="color: #9E9E9E; font-size: 1.05rem; margin: 0;">即時戰力、進階四要素、On/Off 陣容與球員效率象限分析</p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# 賽季階段切換下拉選單 (Season Selector - Dropdown)
# =========================================================================
stage_mapping = {
    "🏆 2026-2027 例行賽": ["data/season2026", "season2026", "."],
    "🔥 2026-2027 季前熱身賽": ["data/preseason2026", "preseason2026", "."],
    "📜 2025-2026 例行賽": ["data/season2025", "season2025", "."]
}

sel_col1, _ = st.columns([1.3, 3])
with sel_col1:
    stage_selection = st.selectbox(
        "選擇賽季階段",
        options=list(stage_mapping.keys()),
        index=0,
        label_visibility="collapsed"
    )

active_dirs = stage_mapping[stage_selection]

# =========================================================================
# 頂部導航列 (Top Navigation Bar)
# =========================================================================
MENU_SUMMARY = "🏆 7隊戰力評級"
MENU_SCATTER = "🎯 主力效率象限圖"
MENU_PBP = "⚡ 各隊 PBP 陣容與 On/Off"
MENU_CARD = "🃏 球員戰力卡與對決"
MENU_GLOSSARY = "📚 進階數據辭典"

nav_selection = st.radio(
    "導航選單",
    [MENU_SUMMARY, MENU_SCATTER, MENU_PBP, MENU_CARD, MENU_GLOSSARY],
    horizontal=True,
    label_visibility="collapsed"
)

# =========================================================================
# 分頁 1：7 隊戰力評級與攻防總評
# =========================================================================
if nav_selection == MENU_SUMMARY:
    st.subheader(f"🏆 {stage_selection} — 各隊戰力評級與進階攻防總評")
    st.markdown("以四要素 (Four Factors)、節奏 (Pace) 及百回合進攻效率 (ORtg) 標準化評估各隊戰力與教練戰術。")

    sum_file = find_file_in_folders(active_dirs, "summary") or find_file_in_folders(active_dirs, "戰力評級總表")
    if sum_file:
        block_a, block_b = parse_summary_sheet(sum_file)

        st.markdown("#### 📊 團隊進階四要素指標 (Team Advanced Metrics)")
        if not block_a.empty:
            df_display = block_a.copy()
            # 若有「戰績」欄位，提取勝場數計算勝率以利正確排序
            if '戰績' in df_display.columns:
                def extract_win_pct(val):
                    val_str = str(val).strip()
                    m = re.search(r'(\d+)\s*勝', val_str)
                    if m:
                        wins = float(m.group(1))
                        m_loss = re.search(r'(\d+)\s*敗', val_str)
                        losses = float(m_loss.group(1)) if m_loss else 0.0
                        tot = wins + losses
                        return wins / tot if tot > 0 else 0.0
                    return 0.0

                df_display['_win_sort'] = df_display['戰績'].apply(extract_win_pct)
                # 預設依勝率由大到小排序
                df_display = df_display.sort_values(by='_win_sort', ascending=False).drop(columns=['_win_sort'])

            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.dataframe(block_a, use_container_width=True, hide_index=True)

        if not block_b.empty:
            st.markdown("#### 🔍 重點球員洞察與教練體系戰力短評")
            for _, row in block_b.iterrows():
                team_name = str(row.iloc[0]) if len(row) > 0 else "球隊"
                if team_name and team_name != "nan" and "區塊" not in team_name:
                    record = str(row.iloc[1]) if len(row) > 1 else "出賽"
                    with st.expander(f"🏀 {team_name} — 戰績：{record}", expanded=True):
                        col_names = [str(c) for c in block_b.columns]
                        for c_idx, c_name in enumerate(col_names[2:], start=2):
                            val = row.iloc[c_idx] if c_idx < len(row) else ""
                            if "短評" in c_name:
                                st.info(f"**{c_name}**：\n\n{val}")
                            else:
                                st.markdown(
                                    f'<div style="margin-bottom: 8px;"><span style="font-size: 1.05rem; font-weight: bold; color: #FFFFFF;">{c_name}：</span><span style="font-size: 1.25rem; font-weight: 600; color: #00E676; background-color: rgba(0, 230, 118, 0.12); padding: 3px 10px; border-radius: 6px; display: inline-block;">{val}</span></div>',
                                    unsafe_allow_html=True
                                )
    else:
        st.warning(f"⚠️ 找不到該階段的總表檔案（請確認已將總表放進 `{active_dirs[0]}` 或根目錄）。")

# =========================================================================
# 分頁 2：USG% vs TS% 散佈圖 (Plotly 互動圖表)
# =========================================================================
elif nav_selection == MENU_SCATTER:
    st.subheader(f"🎯 {stage_selection} — 主力球員效率象限圖：球權使用率 (USG%) vs 真實命中率 (TS%)")
    st.markdown("氣泡大小代表單場綜合表現值 (**GmSc**)，右上角為高產量且高效率之核心神獸。")

    df_players = get_master_players(active_dirs)

    if not df_players.empty and '球員名' in df_players.columns:
        pts_col = '總得分' if '總得分' in df_players.columns else ('得分' if '得分' in df_players.columns else None)
        games_col = '出賽' if '出賽' in df_players.columns else ('場次' if '場次' in df_players.columns else None)
        
        for col in [pts_col, games_col, 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col and col in df_players.columns:
                df_players[col] = pd.to_numeric(df_players[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        # 計算場均得分 (PPG)，若無出賽場次則 fallback 回原始得分
        if games_col and pts_col:
            df_players['出賽數'] = df_players[games_col].replace(0, 1)
            df_players['場均得分'] = (df_players[pts_col] / df_players['出賽數']).round(1)
        elif pts_col:
            df_players['場均得分'] = df_players[pts_col]
        else:
            df_players['場均得分'] = 0.0

        if 'USG%' in df_players.columns and df_players['USG%'].mean() > 0 and df_players['USG%'].mean() < 1.0:
            df_players['USG%'] = df_players['USG%'] * 100.0
        if 'TS%' in df_players.columns and df_players['TS%'].mean() > 0 and df_players['TS%'].mean() < 1.0:
            df_players['TS%'] = df_players['TS%'] * 100.0

        c1, c2 = st.columns(2)
        with c1:
            # 改為場均得分 (PPG) 滑桿，預設 8.0 分，間隔 0.5 分
            min_ppg = st.slider("最低場均得分篩選 (PPG)", min_value=0.0, max_value=30.0, value=8.0, step=0.5)
        with c2:
            id_col = '本土/洋將' if '本土/洋將' in df_players.columns else None
            id_options = ["全部"] + list(df_players[id_col].dropna().unique()) if id_col else ["全部"]
            selected_id = st.multiselect("球員身分篩選", id_options, default=["全部"])

        filtered = df_players.copy()
        filtered = filtered[filtered['場均得分'] >= min_ppg]
        if id_col and "全部" not in selected_id:
            filtered = filtered[filtered[id_col].isin(selected_id)]

        if not filtered.empty and 'USG%' in filtered.columns and 'TS%' in filtered.columns:
            size_col = 'GmSc' if ('GmSc' in filtered.columns and filtered['GmSc'].sum() > 0) else 'EFF'
            filtered['氣泡大小'] = np.maximum(filtered[size_col], 5)
            filtered['簡稱'] = filtered['球員名'].apply(lambda x: str(x).split(' ')[0])

            fig = px.scatter(
                filtered,
                x='USG%',
                y='TS%',
                size='氣泡大小',
                color=id_col if id_col else None,
                text='簡稱',
                hover_name='球員名',
                hover_data={
                    '場均得分': ':.1f',
                    pts_col: True,
                    'USG%': ':.1f',
                    'TS%': ':.1f',
                    size_col: ':.1f',
                    '氣泡大小': False
                },
                template='plotly_dark'
            )

            avg_u = filtered['USG%'].mean()
            avg_t = filtered['TS%'].mean()

            fig.add_hline(
                y=avg_t, 
                line_dash="dash", 
                line_color="#00E5FF", 
                line_width=2,
                annotation_text=f" 主力平均 TS% ({avg_t:.1f}%)", 
                annotation_position="bottom right",
                annotation_font=dict(size=12, color="#00E5FF")
            )
            fig.add_vline(
                x=avg_u, 
                line_dash="dash", 
                line_color="#FFD700", 
                line_width=2,
                annotation_text=f" 主力平均 USG% ({avg_u:.1f}%)", 
                annotation_position="top left",
                annotation_font=dict(size=12, color="#FFD700")
            )

            quadrant_annotations = [
                dict(x=avg_u + 6, y=avg_t + 18, text="🔥 第一象限：高產高效核心", showarrow=False, font=dict(size=13, color="rgba(255,255,255,0.4)")),
                dict(x=avg_u - 6, y=avg_t + 18, text="🎯 第二象限：高效終結者", showarrow=False, font=dict(size=13, color="rgba(255,255,255,0.4)")),
                dict(x=avg_u - 6, y=avg_t - 15, text="🛡️ 第三象限：角色球員/低迷區", showarrow=False, font=dict(size=13, color="rgba(255,255,255,0.4)")),
                dict(x=avg_u + 6, y=avg_t - 15, text="⚠️ 第四象限：低效強攻區", showarrow=False, font=dict(size=13, color="rgba(255,255,255,0.4)"))
            ]
            for annot in quadrant_annotations:
                fig.add_annotation(annot)

            fig.update_traces(textposition='top center')
            fig.update_layout(
                xaxis_title="球權使用率 USG% (%)",
                yaxis_title="真實命中率 TS% (%)",
                legend_title="球員身分",
                height=650
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 查看象限圖球員詳細數據清單", expanded=False):
                st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ 目前篩選條件下無符合球員。")
    else:
        st.info("💡 尚未讀取到球員進階數據母表。")

# =========================================================================
# 分頁 3：各隊 PBP 陣容與 On/Off 深入分析
# =========================================================================
elif nav_selection == MENU_PBP:
    st.subheader(f"⚡ {stage_selection} — 各隊 Play-by-Play 陣容組合與主力 On/Off 淨勝分")
    st.markdown("由逐球時間段 (Stints) 精確解析各隊【主力 On/Off 總榜】、【賽季最佳五人陣容】與【雙洋將化學效應】。")

    team_options = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    selected_team = st.selectbox("選擇要深入分析的球隊", team_options)

    target_file = find_team_file_in_folders(active_dirs, selected_team)

    if target_file:
        blocks, box_df = extract_pbp_blocks(target_file)

        st.markdown(f"#### 📊 {selected_team} — 主力 On/Off 淨影響力總榜")
        if 'on_off' in blocks and not blocks['on_off'].empty:
            st.dataframe(blocks['on_off'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無 On/Off 統計資料。")

        st.markdown(f"#### 🏆 {selected_team} — 最佳五人陣容 (Top Lineups)")
        if 'lineup' in blocks and not blocks['lineup'].empty:
            st.dataframe(blocks['lineup'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無五人陣容統計資料。")

        st.markdown(f"#### 🤝 {selected_team} — 雙洋將化學效應矩陣")
        if 'duo' in blocks and not blocks['duo'].empty:
            df_duo = blocks['duo'].copy()
            headers = list(df_duo.columns)
            
            # 自適應原生表格：前段數據緊湊貼合 (width: 1%)，後段建議自動展開鋪滿
            html = [
                '<div style="overflow-x: auto; width: 100%; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; margin-bottom: 20px;">',
                '<table style="width: 100%; border-collapse: collapse; font-size: 0.95rem; background-color: rgba(255,255,255,0.02); text-align: left;">',
                '<thead><tr style="border-bottom: 1px solid rgba(255,255,255,0.12); background-color: rgba(255,255,255,0.04);">'
            ]
            for i, h in enumerate(headers):
                if i < len(headers) - 1:
                    html.append(f'<th style="padding: 10px 14px; white-space: nowrap; width: 1%; color: #9E9E9E; font-weight: 600;">{h}</th>')
                else:
                    html.append(f'<th style="padding: 10px 14px; color: #9E9E9E; font-weight: 600;">{h}</th>')
            html.append('</tr></thead><tbody>')
            
            for _, row in df_duo.iterrows():
                html.append('<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">')
                for i, h in enumerate(headers):
                    val = str(row[h]).strip() if pd.notna(row[h]) else ""
                    if i < len(headers) - 1:
                        val_display = val
                        if "NetRtg" in h or "(+/-)" in h:
                            if val.startswith("+"):
                                val_display = f'<span style="color: #00E676; font-weight: 600;">{val}</span>'
                            elif val.startswith("-"):
                                val_display = f'<span style="color: #FF5252; font-weight: 600;">{val}</span>'
                        html.append(f'<td style="padding: 10px 14px; white-space: nowrap; width: 1%; color: #E0E0E0;">{val_display}</td>')
                    else:
                        html.append(f'<td style="padding: 10px 14px; color: #FFFFFF; line-height: 1.5;">{val}</td>')
                html.append('</tr>')
            html.append('</tbody></table></div>')
            st.markdown("".join(html), unsafe_allow_html=True)
        else:
            st.info(f"💡 {selected_team} 暫無雙洋將搭配資料。")

        if not box_df.empty:
            with st.expander(f"📋 查看 {selected_team} 基礎攻守數據表 (Box Score)", expanded=False):
                st.dataframe(box_df, use_container_width=True, hide_index=True)
    else:
        st.warning(f"⚠️ 找不到 {selected_team} 的專屬數據檔案。")

# =========================================================================
# 分頁 4：球員戰力卡與雙人對決
# =========================================================================
elif nav_selection == MENU_CARD:
    st.subheader(f"🃏 {stage_selection} — 球員戰力卡與雙雄對決 (Player Card & Head-to-Head)")
    st.markdown("依球隊篩選球員，檢視六維戰力雷達圖與高階球探卡，並可加入另一名球員展開對照 PK。")

    df_players = get_master_players(active_dirs)

    if not df_players.empty and '球員名' in df_players.columns:
        all_teams = sorted(list(df_players['球隊'].dropna().unique())) if '球隊' in df_players.columns else ["全隊伍"]

        st.markdown("##### 🔍 步驟 1：選擇主要球員（球探卡）")
        p1_col1, p1_col2 = st.columns(2)
        with p1_col1:
            p1_team = st.selectbox("🏀 主要球員所屬球隊", all_teams, index=0, key="sel_p1_team")
        with p1_col2:
            p1_player_list = df_players[df_players['球隊'] == p1_team]['球員名'].dropna().tolist() if '球隊' in df_players.columns else df_players['球員名'].dropna().tolist()
            p1_name = st.selectbox("🎯 選擇主要球員", p1_player_list, index=0, key="sel_p1_player")

        st.markdown("##### ⚔️ 步驟 2：加入比較球員（可選）")
        p2_col1, p2_col2 = st.columns(2)
        with p2_col1:
            p2_team_options = ["無（單人球探卡模式）"] + all_teams
            p2_team = st.selectbox("🏀 比較球員所屬球隊", p2_team_options, index=0, key="sel_p2_team")
        with p2_col2:
            if p2_team != "無（單人球探卡模式）":
                p2_player_list = df_players[df_players['球隊'] == p2_team]['球員名'].dropna().tolist() if '球隊' in df_players.columns else df_players['球員名'].dropna().tolist()
                if p1_team == p2_team and p1_name in p2_player_list and len(p2_player_list) > 1:
                    p2_player_list = [p for p in p2_player_list if p != p1_name]
                p2_name = st.selectbox("👤 選擇比較球員", p2_player_list, index=0, key="sel_p2_player")
            else:
                st.info("💡 尚未選擇第二位球員，目前維持「單人球探卡」模式。")
                p2_name = None

        p1_row = df_players[(df_players['球隊'] == p1_team) & (df_players['球員名'] == p1_name)].iloc[0] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p1_name].iloc[0]
        p2_row = None
        if p2_name:
            p2_row = df_players[(df_players['球隊'] == p2_team) & (df_players['球員名'] == p2_name)].iloc[0] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p2_name].iloc[0]

        categories = ['得分產量', '真實效率', '外線威脅', '組織發動', '籃板保護', '防守破壞']
        cats_closed = categories + [categories[0]]
        p1_scores = calculate_radar_scores(p1_row)
        p1_closed = p1_scores + [p1_scores[0]]

        if p2_row is None:
            st.divider()
            card_col1, card_col2, card_col3, card_col4 = st.columns(4)
            
            # 計算場均與總累計
            games_cnt = float(p1_row.get('出賽', 1))
            games_cnt = 1.0 if games_cnt <= 0 else games_cnt
            
            tot_pts = float(p1_row.get('總得分', p1_row.get('得分', 0)))
            ppg_val = tot_pts / games_cnt
            
            raw_gmsc = float(p1_row.get('GmSc', p1_row.get('EFF', 0)))
            # 若原始 GmSc 大於 50，代表是整季累計值，換算為場均 GmSc
            gmsc_pg = raw_gmsc / games_cnt if raw_gmsc > 45 else raw_gmsc
            
            ts_val = format_pct(p1_row.get('TS%', '0%'))
            usg_val = format_pct(p1_row.get('USG%', '0%'))

            card_col1.metric("場均得分 (PPG)", f"{ppg_val:.1f} 分", delta=f"整季累計 {int(tot_pts)} 分" if tot_pts > 40 else None)
            card_col2.metric("真實命中率 (TS%)", ts_val)
            card_col3.metric("球權使用率 (USG%)", usg_val)
            card_col4.metric("場均綜合評分 (GmSc)", f"{gmsc_pg:.1f}", delta=f"整季累積 {raw_gmsc:.1f}" if raw_gmsc > 45 else None)

            r_col1, r_col2 = st.columns([1.1, 1])
            with r_col1:
                st.markdown(f"#### 📊 {p1_row['球員名']} — 六維戰力雷達圖")
                fig_single = go.Figure()
                fig_single.add_trace(go.Scatterpolar(
                    r=p1_closed,
                    theta=cats_closed,
                    fill='toself',
                    name=str(p1_row['球員名']),
                    line_color='#00E676',
                    fillcolor='rgba(0, 230, 118, 0.28)'
                ))
                fig_single.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='rgba(255, 255, 255, 0.15)'),
                        angularaxis=dict(gridcolor='rgba(255, 255, 255, 0.15)', tickfont=dict(size=13, color='#FFFFFF')),
                        bgcolor='rgba(0,0,0,0)'
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    template='plotly_dark',
                    height=460,
                    margin=dict(l=30, r=30, t=20, b=20)
                )
                st.plotly_chart(fig_single, use_container_width=True)

            with r_col2:
                st.markdown(f"#### 🔍 球員基本檔案與球探特徵")
                team_display = str(p1_row.get('球隊', '所屬隊伍'))
                pos_display = str(p1_row.get('位置', '位置'))
                id_display = str(p1_row.get('本土/洋將', '身分'))
                num_display = str(p1_row.get('背號', '#'))
                efg_display = format_pct(p1_row.get('eFG%', '0%'))
                tpar_display = format_pct(p1_row.get('3PAr', '0%'))
                ftr_display = format_pct(p1_row.get('FTr', '0%'))
                ast_to_display = get_ast_to_ratio(p1_row)

                rows_html = "".join([
                    make_stat_badge_row("所屬隊伍", team_display),
                    make_stat_badge_row("球衣背號 / 場上位置", f"#{num_display} / {pos_display}"),
                    make_stat_badge_row("球員身分類別", id_display),
                    make_stat_badge_row("有效命中率 (eFG%)", efg_display),
                    make_stat_badge_row("三分出手佔比 (3PAr)", tpar_display),
                    make_stat_badge_row("買犯罰球比 (FTr)", ftr_display),
                    make_stat_badge_row("助攻失誤比 (AST/TO)", ast_to_display)
                ])
                html_badges = f'<div style="background-color: rgba(255,255,255,0.03); padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px;">{rows_html}</div>'
                st.markdown(html_badges, unsafe_allow_html=True)

                note_val = p1_row.get('備註/短評', p1_row.get('備註 / 例行賽表現重點', p1_row.get('備註 / 熱身賽表現重點', '暫無備註')))
                st.info(f"💡 **教練與球探備註**：\n\n{note_val}")

        else:
            p2_scores = calculate_radar_scores(p2_row)
            p2_closed = p2_scores + [p2_scores[0]]

            st.divider()
            pk_c1, pk_c2 = st.columns(2)
            with pk_c1:
                st.markdown(f"""
                <div style="background-color: rgba(0, 230, 118, 0.1); border-left: 5px solid #00E676; padding: 12px; border-radius: 6px;">
                    <h3 style="margin: 0; color: #00E676;">🟢 {p1_row['球員名']}</h3>
                    <p style="margin: 4px 0 0 0; color: #BBB;">{p1_row.get('球隊', '')} | #{p1_row.get('背號', '')} | {p1_row.get('位置', '')} ({p1_row.get('本土/洋將', '')})</p>
                </div>
                """, unsafe_allow_html=True)
            with pk_c2:
                st.markdown(f"""
                <div style="background-color: rgba(255, 145, 0, 0.1); border-left: 5px solid #FF9100; padding: 12px; border-radius: 6px;">
                    <h3 style="margin: 0; color: #FF9100;">🟠 {p2_row['球員名']}</h3>
                    <p style="margin: 4px 0 0 0; color: #BBB;">{p2_row.get('球隊', '')} | #{p2_row.get('背號', '')} | {p2_row.get('位置', '')} ({p2_row.get('本土/洋將', '')})</p>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            dual_col1, dual_col2 = st.columns([1.1, 1])

            with dual_col1:
                st.markdown("#### ⚔️ 戰力六維度重疊對抗圖")
                fig_dual = go.Figure()
                fig_dual.add_trace(go.Scatterpolar(
                    r=p1_closed,
                    theta=cats_closed,
                    fill='toself',
                    name=str(p1_row['球員名']),
                    line_color='#00E676',
                    fillcolor='rgba(0, 230, 118, 0.22)'
                ))
                fig_dual.add_trace(go.Scatterpolar(
                    r=p2_closed,
                    theta=cats_closed,
                    fill='toself',
                    name=str(p2_row['球員名']),
                    line_color='#FF9100',
                    fillcolor='rgba(255, 145, 0, 0.22)'
                ))
                fig_dual.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor='rgba(255, 255, 255, 0.15)'),
                        angularaxis=dict(gridcolor='rgba(255, 255, 255, 0.15)', tickfont=dict(size=13, color='#FFFFFF')),
                        bgcolor='rgba(0,0,0,0)'
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    template='plotly_dark',
                    height=460,
                    margin=dict(l=30, r=30, t=30, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_dual, use_container_width=True)

            with dual_col2:
                st.markdown("#### 📋 攻守數據正面對決表 (Tale of the Tape)")
                compare_metrics = [
                    ('得分', p1_row.get('總得分', p1_row.get('得分', 0)), p2_row.get('總得分', p2_row.get('得分', 0))),
                    ('真實命中率 (TS%)', format_pct(p1_row.get('TS%', '0%')), format_pct(p2_row.get('TS%', '0%'))),
                    ('有效命中率 (eFG%)', format_pct(p1_row.get('eFG%', '0%')), format_pct(p2_row.get('eFG%', '0%'))),
                    ('球權使用率 (USG%)', format_pct(p1_row.get('USG%', '0%')), format_pct(p2_row.get('USG%', '0%'))),
                    ('三分出手比 (3PAr)', format_pct(p1_row.get('3PAr', '0%')), format_pct(p2_row.get('3PAr', '0%'))),
                    ('買犯罰球比 (FTr)', format_pct(p1_row.get('FTr', '0%')), format_pct(p2_row.get('FTr', '0%'))),
                    ('助攻失誤比 (AST/TO)', get_ast_to_ratio(p1_row), get_ast_to_ratio(p2_row)),
                    ('籃板', p1_row.get('籃板', 0), p2_row.get('籃板', 0)),
                    ('助攻', p1_row.get('助攻', 0), p2_row.get('助攻', 0)),
                    ('抄截', p1_row.get('抄截', 0), p2_row.get('抄截', 0)),
                    ('阻攻', p1_row.get('阻攻', 0), p2_row.get('阻攻', 0)),
                    ('單場綜合 (GmSc)', p1_row.get('GmSc', p1_row.get('EFF', 0)), p2_row.get('GmSc', p2_row.get('EFF', 0)))
                ]
                
                cmp_df = pd.DataFrame(compare_metrics, columns=['指標項目', f"🟢 {p1_row['球員名']}", f"🟠 {p2_row['球員名']}"])
                st.dataframe(cmp_df, use_container_width=True, hide_index=True)
                
                st.caption("💡 提示：可切換不同球員組合，觀察不同體系後衛或禁區長人之間的風格差異。")
    else:
        st.info("💡 尚未讀取到球員數據母表。")

# =========================================================================
# 分頁 5：進階數據辭典與公式附錄
# =========================================================================
elif nav_selection == MENU_GLOSSARY:
    st.subheader("📚 TPBL 進階數據辭典與公式附錄 (Glossary & Formulas)")
    st.markdown("收錄職業籃球進階數據工程之計算原理、數學公式與球探判讀指引。")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 個人投籃與效率指標", 
        "⚡ 球權佔比與綜合表現", 
        "🏆 團隊四要素與攻防效率", 
        "⏱️ Play-by-Play 陣容分析"
    ])

    with tab1:
        st.markdown(r"""
        ### 1. 有效命中率 (eFG%, Effective Field Goal Percentage)
        * **數學公式**：
        $$eFG\% = \frac{FGM + 0.5 \times 3PM}{FGA} \times 100\%$$
        * **數據意義**：傳統命中率 ($FG\%$) 將三分球與兩分球視為相同價值，有效命中率額外賦予三分球 1.5 倍加成權重。
        * **球探判讀**：聯盟平均約 **50% ~ 52%**；超過 **55%** 為優異射手，超過 **60%** 為頂尖終結者。

        ---
        ### 2. 真實命中率 (TS%, True Shooting Percentage)
        * **數學公式**：
        $$TS\% = \frac{PTS}{2 \times (FGA + 0.44 \times FTA)} \times 100\%$$
        * **數據意義**：衡量每次出手回合的終極得分效益（綜合兩分、三分與罰球）。
        * **為什麼係數是 0.44？**：扣除 And-1、三分犯規與技術犯規後的大數據精確回合折算係數。
        * **球探判讀**：及格線 **55%**；超過 **60%** 為優質得分點；超過 **68%** 屬聯盟頂級神獸。

        ---
        ### 3. 三分出手佔比 (3PAr) 與 買犯罰球比 (FTr)
        * $$3PAr = \frac{3PA}{FGA} \times 100\% \quad (3PAr > 55\% \text{ 為魔球射手})$$
        * $$FTr = \frac{FTA}{FGA} \times 100\% \quad (FTr > 40\% \text{ 具強烈禁區破壞力})$$
        """)

    with tab2:
        st.markdown(r"""
        ### 1. 球權使用率 (USG%, Usage Percentage)
        * **數學公式**：
        $$USG\% = 100 \times \frac{(FGA + 0.44 \times FTA + TOV) \times (\text{Team\_MP} / 5)}{MP \times (\text{Team\_FGA} + 0.44 \times \text{Team\_FTA} + \text{Team\_TOV})}$$
        * **戰術地位判讀**：
          * **$USG\% \ge 28\%$**：球隊第一戰術核心（如林俊吉、洛斯柯、林庭謙）。
          * **$22\% \sim 27\%$**：主要先發得分點 / 第二持球副攻手。
          * **$< 15\%$**：藍領苦工、底角射手。

        ---
        ### 2. 單場綜合表現值 (GmSc, Game Score)
        * **數學公式**：
        $$\begin{aligned}
        GmSc = & PTS + 0.4 \times FGM - 0.7 \times FGA - 0.4 \times (FTA - FTM) \\
        & + 0.7 \times OREB + 0.3 \times DREB + STL + 0.7 \times AST + 0.7 \times BLK - 0.4 \times PF - TOV
        \end{aligned}$$
        * **球探標準**：10 分為合格輪替；20 分為全明星統治力；30 分以上為 MVP 級表現。
        """)

    with tab3:
        st.markdown(r"""
        ### 1. 團隊進攻回合數 (Poss) 與 比賽節奏 (Pace)
        * $$Poss \approx \text{Team\_FGA} + 0.44 \times \text{Team\_FTA} - \text{Team\_OREB} + \text{Team\_TOV}$$
        * $$Pace = 48 \times \frac{Poss}{\text{Team\_MP} / 5}$$
        * **節奏判讀**：$Pace > 105$ 為跑轟快攻隊伍（如海神）；$Pace < 98$ 為半場陣地戰體系。

        ---
        ### 2. 百回合進攻 / 防守 / 淨效率 (ORtg / DRtg / NetRtg)
        * $$ORtg = 100 \times \frac{\text{Team\_PTS}}{Poss}, \quad DRtg = 100 \times \frac{\text{Opp\_PTS}}{\text{Opp\_Poss}}$$
        * $$NetRtg = ORtg - DRtg$$
        """)

    with tab4:
        st.markdown(r"""
        ### 1. Play-by-Play Stint 狀態機運作原理
        * 逐球紀錄追蹤場上 10 人名單。遇任何換人或單節結束即切分無換人時間段 (Stint)。
        * 該區段內的所有攻守數據精準歸屬於該套陣容。

        ---
        ### 2. 主力 On/Off 淨影響力 (Diff)
        * $$Diff = On\_NetRtg - Off\_NetRtg$$
        * **判讀**：正值越大代表不可替代性越強；負值代表其在場時球隊失血或替補追分更高效。
        """)
