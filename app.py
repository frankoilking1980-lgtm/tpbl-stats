import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
import datetime
import json

# ----------------- 頁面全域設定 (100% 滿版排版) -----------------
st.set_page_config(
    page_title="TPBL 職業籃球進階數據與球探分析系統",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- 頂部導航與主題基礎 CSS -----------------
base_style = """
<style>
header, [data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
footer, [data-testid="stEmbedFooter"] {display: none !important;}
div[class*="viewerBadge"] {display: none !important;}

[data-testid="stSidebar"] {display: none !important;}
[data-testid="stSidebarCollapseButton"] {display: none !important;}
[data-testid="collapsedControl"] {display: none !important;}

div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
    display: none !important;
}

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
st.markdown(base_style, unsafe_allow_html=True)

# ----------------- 賽季階段與外觀主題切換列 -----------------
stage_mapping = {
    "🔥 2026-2027 季前熱身賽": ["data/preseason2026", "preseason2026", "."],
    "🏆 2026-2027 例行賽": ["data/season2026", "season2026", "."],
    "📜 2025-2026 例行賽": ["data/season2025", "season2025", "."],
    "⚔️ 2025-2026 季後挑戰賽": ["data/playin2025", "playin2025", "."],
    "⚔️ 2025-2026 季後賽": ["data/playoff2025", "playoff2025", "."],
    "🏆 2025-2026 冠軍賽": ["data/final20252026", "final20252026", "."]
}

col_sel_season, col_sel_theme, _ = st.columns([1.3, 0.9, 2])
with col_sel_season:
    stage_selection = st.selectbox(
        "選擇賽季階段",
        options=list(stage_mapping.keys()),
        index=0,
        label_visibility="collapsed"
    )

with col_sel_theme:
    theme_choice = st.radio(
        "外觀主題切換",
        ["🌙 深色", "☀️ 淺色"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

is_light = (theme_choice == "☀️ 淺色")
plotly_template = "plotly_white" if is_light else "plotly_dark"
active_dirs = stage_mapping[stage_selection]

# ----------------- 動態外觀主題樣式注入 -----------------
if is_light:
    theme_css = """
    <style>
    .stApp { background-color: #F8F9FA !important; color: #1A1A1A !important; }
    h1, h2, h3, h4, h5, h6, p, span, label { color: #1A1A1A !important; }
    div[data-testid="stRadio"] > div { background: rgba(0, 0, 0, 0.04) !important; border: 1px solid rgba(0, 0, 0, 0.1) !important; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] { background-color: rgba(0, 0, 0, 0.03) !important; border: 1px solid rgba(0, 0, 0, 0.08) !important; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] p { color: #333333 !important; }
    @media (min-width: 768px) {
        div[data-testid="stRadio"] { width: 100% !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important; flex-direction: row !important; justify-content: space-between !important;
            width: 100% !important; gap: 12px !important; padding: 8px 12px !important; border-radius: 14px !important;
            margin-bottom: 20px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            flex: 1 1 0 !important; display: flex !important; justify-content: center !important; align-items: center !important;
            padding: 12px 10px !important; border-radius: 9px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] p { font-size: 1.12rem !important; font-weight: 600 !important; }
    }
    @media (max-width: 767px) {
        div[data-testid="stRadio"] { width: 100% !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: grid !important; grid-template-columns: repeat(2, 1fr) !important; gap: 8px !important;
            background: transparent !important; padding: 0 !important; border: none !important; margin-bottom: 16px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:last-child { grid-column: span 2 !important; }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            display: flex !important; justify-content: center !important; align-items: center !important;
            padding: 10px 6px !important; border-radius: 8px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] p { font-size: 0.92rem !important; font-weight: 600 !important; }
    }
    </style>
    """
else:
    theme_css = """
    <style>
    .stApp { background-color: #0E1117 !important; color: #FFFFFF !important; }
    h1, h2, h3, h4, h5, h6, p, span, label { color: #FFFFFF !important; }
    div[data-testid="stRadio"] > div { background: rgba(255, 255, 203, 0.03) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] { background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] p { color: #FFFFFF !important; }
    @media (min-width: 768px) {
        div[data-testid="stRadio"] { width: 100% !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: flex !important; flex-direction: row !important; justify-content: space-between !important;
            width: 100% !important; gap: 12px !important; padding: 8px 12px !important; border-radius: 14px !important;
            margin-bottom: 20px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            flex: 1 1 0 !important; display: flex !important; justify-content: center !important; align-items: center !important;
            padding: 12px 10px !important; border-radius: 9px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] p { font-size: 1.12rem !important; font-weight: 600 !important; }
    }
    @media (max-width: 767px) {
        div[data-testid="stRadio"] { width: 100% !important; }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            display: grid !important; grid-template-columns: repeat(2, 1fr) !important; gap: 8px !important;
            background: transparent !important; padding: 0 !important; border: none !important; margin-bottom: 16px !important;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] > label:last-child { grid-column: span 2 !important; }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            display: flex !important; justify-content: center !important; align-items: center !important;
            padding: 10px 6px !important; border-radius: 8px !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] p { font-size: 0.92rem !important; font-weight: 600 !important; }
    }
    </style>
    """
st.markdown(theme_css, unsafe_allow_html=True)

# ----------------- 全域 UI 色彩與容器變數 -----------------
card_bg = "rgba(0, 0, 0, 0.03)" if is_light else "rgba(255, 255, 255, 0.03)"
card_border = "rgba(0, 0, 0, 0.1)" if is_light else "rgba(255, 255, 255, 0.1)"
card_box_bg = "rgba(0, 0, 0, 0.02)" if is_light else "rgba(255, 255, 255, 0.03)"
table_wrapper_bg = "rgba(0, 0, 0, 0.02)" if is_light else "rgba(255, 255, 255, 0.02)"
text_title_c = "#111111" if is_light else "#EEEEEE"
text_sub_c = "#777777" if is_light else "#888888"

# ----------------- 工具函式 -----------------
def clean_time_display(val):
    if pd.isna(val):
        return ""
    if isinstance(val, (pd.Timedelta, datetime.timedelta)):
        tot_sec = int(val.total_seconds())
        if tot_sec < 3600:
            return f"{tot_sec // 60:02d}:{tot_sec % 60:02d}"
        else:
            return f"{tot_sec // 3600:02d}:{(tot_sec % 3600) // 60:02d}"
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
    m_hms = re.match(r'^00:(\d+):(\d+)$', val_str)
    if m_hms:
        return f"{int(m_hms.group(1)):02d}:{int(m_hms.group(2)):02d}"
    m_hms2 = re.match(r'^(\d+):(\d+):00$', val_str)
    if m_hms2:
        return f"{int(m_hms2.group(1)):02d}:{int(m_hms2.group(2)):02d}"
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
    text_c = "#333333" if is_light else "#E0E0E0"
    border_c = "rgba(0,0,0,0.06)" if is_light else "rgba(255,255,255,0.08)"
    return f'<div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid {border_c};"><span style="font-size: 1.05rem; font-weight: 600; color: {text_c};">{label}</span><span style="font-size: 1.22rem; font-weight: 700; color: #00E676; background-color: rgba(0, 230, 118, 0.15); padding: 4px 14px; border-radius: 6px; letter-spacing: 0.5px;">{val}</span></div>'

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

def find_file_in_folders(candidate_dirs, keyword):
    keyword_clean = keyword.lower().strip()
    for d in candidate_dirs:
        if os.path.exists(d):
            for fname in os.listdir(d):
                fname_lower = fname.lower()
                if keyword_clean in fname_lower and fname_lower.endswith(('.xlsx', '.xls', '.csv', '.json')):
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

team_color_map = {
    "新北國王": "#FFC107",
    "福爾摩沙夢想家": "#00E676",
    "高雄全家海神": "#00B0FF",
    "新北中信特攻": "#FFD600",
    "臺北台新戰神": "#FF5252",
    "桃園台啤永豐雲豹": "#AB47BC",
    "新竹御嵿攻城獅": "#EA80FC"
}

def render_bi_bar(label, val_away, val_home, is_pct=False, higher_is_better=True):
    def parse_stat(v):
        s = str(v).strip().replace('%', '').replace('+', '')
        if '/' in s:
            try:
                return float(s.split('/')[0])
            except:
                return 0.0
        try:
            return float(s)
        except:
            return 0.0

    num_a = parse_stat(val_away)
    num_h = parse_stat(val_home)
    
    tot = (num_a + num_h) if (num_a + num_h) > 0 else 1.0
    pct_a = min(100.0, max(8.0, (num_a / tot) * 100.0))
    pct_h = min(100.0, max(8.0, (num_h / tot) * 100.0))
    
    lose_bar_color = "#BDBDBD" if is_light else "#616161"
    
    if higher_is_better:
        color_a = "#00E676" if num_a > num_h else lose_bar_color
        color_h = "#00E676" if num_h > num_a else lose_bar_color
    else:
        color_a = "#00E676" if num_a < num_h else lose_bar_color
        color_h = "#00E676" if num_h < num_a else lose_bar_color

    disp_a = f"{val_away:.1f}%" if is_pct and isinstance(val_away, (int, float)) else str(val_away)
    disp_h = f"{val_home:.1f}%" if is_pct and isinstance(val_home, (int, float)) else str(val_home)
    
    label_c = "#444" if is_light else "#BBB"
    
    return f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; font-size: 0.95rem;"><div style="width: 16%; text-align: right; font-weight: 700; color: {color_a}; font-size: 1.05rem;">{disp_a}</div><div style="width: 26%; display: flex; justify-content: flex-end; padding-right: 8px;"><div style="width: {pct_a:.1f}%; background: {color_a}; height: 8px; border-radius: 4px;"></div></div><div style="width: 32%; text-align: center; color: {label_c}; font-weight: 600; white-space: nowrap; font-size: 0.9rem;">{label}</div><div style="width: 26%; display: flex; justify-content: flex-start; padding-left: 8px;"><div style="width: {pct_h:.1f}%; background: {color_h}; height: 8px; border-radius: 4px;"></div></div><div style="width: 16%; text-align: left; font-weight: 700; color: {color_h}; font-size: 1.05rem;">{disp_h}</div></div>'

def split_lineup_and_pairs(df_lineup):
    if df_lineup is None or df_lineup.empty:
        return pd.DataFrame(), pd.DataFrame()
    col0 = df_lineup.columns[0]
    split_idx = None
    for idx, r in df_lineup.iterrows():
        val = str(r[col0]).strip()
        if "核心搭檔" in val or "Key Pairs" in val:
            split_idx = idx
            break
    if split_idx is not None:
        df_5man = df_lineup.loc[:split_idx - 1].copy()
        df_pairs = df_lineup.loc[split_idx + 1:].copy()
    else:
        def is_pair(val):
            cnt = str(val).count('+')
            return cnt == 1 or cnt == 2
        mask_pairs = df_lineup[col0].apply(is_pair)
        df_5man = df_lineup[~mask_pairs].copy()
        df_pairs = df_lineup[mask_pairs].copy()

    df_5man = df_5man.dropna(subset=[col0]).dropna(how='all', axis=1)
    df_pairs = df_pairs.dropna(subset=[col0]).dropna(how='all', axis=1)
    return df_5man, df_pairs

# ----------------- 精確單場工作表抽取器 (已整合 WOWY 與單場欄位過濾) -----------------
def extract_single_game_data(filepath, sheet_name, game_id="", game_date=""):
    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, ""
    try:
        xls = pd.ExcelFile(filepath)
        all_sheets = xls.sheet_names
        matched_sheet = None

        if sheet_name in all_sheets:
            matched_sheet = sheet_name

        if not matched_sheet:
            clean_target = re.sub(r'[\s\.\-_/]', '', sheet_name).lower()
            for s in all_sheets:
                if re.sub(r'[\s\.\-_/]', '', s).lower() == clean_target:
                    matched_sheet = s
                    break

        if not matched_sheet:
            gid = game_id.lower().strip() if game_id else ""
            date_clean = re.sub(r'^(2025|2026|2027)[\.\-_/]', '', game_date).strip() if game_date else ""
            for s in all_sheets:
                s_lower = s.lower()
                has_id = (gid in s_lower) if gid else False
                has_date = (game_date in s) or (date_clean in s.replace('/', '.').replace('-', '.')) if date_clean else False
                if has_id and has_date:
                    matched_sheet = s
                    break

        if not matched_sheet and game_id:
            gid = game_id.lower().strip()
            for s in all_sheets:
                words = re.split(r'[\s\.\-_/]', s.lower())
                if "vs" in s.lower() and gid in words:
                    matched_sheet = s
                    break

        if not matched_sheet and game_date:
            date_clean = re.sub(r'^(2025|2026|2027)[\.\-_/]', '', game_date).strip()
            for s in all_sheets:
                if "vs" in s.lower() and (game_date in s or (date_clean and date_clean in s.replace('/', '.').replace('-', '.'))):
                    matched_sheet = s
                    break

        if not matched_sheet:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, ""

        df = pd.read_excel(filepath, sheet_name=matched_sheet, header=None)
        
        header_r = None
        for r in range(min(8, len(df))):
            vals = [str(x).strip() for x in df.iloc[r, :8].dropna().tolist()]
            if any(k in vals for k in ["球員名", "球員", "Player"]):
                header_r = r
                break
                
        if header_r is None:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, matched_sheet

        # 1. 抽取單場 Box score 並過濾不必要顯示的欄位
        box_cols = []
        box_col_idxs = []
        for c in range(0, min(36, len(df.columns))):
            h = str(df.iloc[header_r, c]).strip()
            if not h or h == "nan" or h.startswith("Unnamed"):
                break
            box_cols.append(h)
            box_col_idxs.append(c)

        box_rows = []
        for r in range(header_r + 1, len(df)):
            c0 = str(df.iloc[r, 0]).strip() if len(df.columns) > 0 and pd.notna(df.iloc[r, 0]) else ""
            c1 = str(df.iloc[r, 1]).strip() if len(df.columns) > 1 and pd.notna(df.iloc[r, 1]) else ""
            
            if not c1 or c1 == "nan":
                break
                
            row_identity = f"{c0} {c1}"
            if any(k in row_identity for k in ['合計', '總計', 'TEAM', '團隊', 'Team', '名球員', '全隊']):
                continue
                
            box_rows.append([df.iloc[r, ci] for ci in box_col_idxs])

        box_df = pd.DataFrame(box_rows, columns=box_cols)
        box_df = clean_dataframe_times(deduplicate_columns(box_df))

        # 過濾單場不需顯示之欄位（在台年資、出賽、投籃熱區、備註）
        drop_keywords = ['在台年資', '出賽', '投籃熱區', '表現重點', '備註']
        keep_cols = [c for c in box_df.columns if not any(k in c for k in drop_keywords)]
        box_df = box_df[keep_cols]

        # 2. 提取右側陣容、On/Off 表與對位交鋒 (WOWY) 表
        def extract_sub(start_c):
            if start_c is None or start_c >= len(df.columns):
                return pd.DataFrame()
            cols = []
            c_idxs = []
            for c in range(start_c, len(df.columns)):
                h = str(df.iloc[header_r, c]).strip()
                if not h or h == "nan" or h.startswith("Unnamed"):
                    break
                cols.append(h)
                c_idxs.append(c)
            if not cols:
                return pd.DataFrame()
            data = []
            for r in range(header_r + 1, len(df)):
                v = df.iloc[r, c_idxs[0]]
                if pd.isna(v) or str(v).strip() == "" or str(v) == "nan":
                    break
                data.append([df.iloc[r, ci] for ci in c_idxs])
            res = pd.DataFrame(data, columns=cols)
            return clean_dataframe_times(deduplicate_columns(res))

        onoff_c, lineup_c, wowy_c = None, None, None
        start_scan = max(box_col_idxs) + 1 if box_col_idxs else 16
        for c in range(start_scan, len(df.columns)):
            val_r2 = str(df.iloc[header_r - 1, c]).strip() if header_r > 0 else ""
            val_r3 = str(df.iloc[header_r, c]).strip()
            if "On/Off" in val_r2 or "on/off" in val_r3.lower() or ("在場時間" in val_r3 and onoff_c is None):
                if onoff_c is None:
                    onoff_c = c if val_r3 in ["球員名", "球員"] else (c-1 if df.iloc[header_r, c-1] in ["球員名", "球員"] else c)
            if "陣容" in val_r2 or "陣容" in val_r3:
                if lineup_c is None:
                    lineup_c = c
            if any(k in val_r2 for k in ["對位", "WOWY", "交鋒"]) or any(k in val_r3 for k in ["對位", "WOWY", "交鋒"]):
                if wowy_c is None:
                    wowy_c = c

        onoff_df = extract_sub(onoff_c) if onoff_c else pd.DataFrame()
        lineup_df = extract_sub(lineup_c) if lineup_c else pd.DataFrame()
        wowy_df = extract_sub(wowy_c) if wowy_c else pd.DataFrame()

        # 3. 累加團隊統計
        team_stats = {}
        alias_map = {
            '得分': ['得分', '總得分', 'PTS'],
            '投籃命中': ['投籃命中', 'FGM'],
            '投籃出手': ['投籃出手', 'FGA'],
            '三分命中': ['三分命中', '3PM'],
            '三分出手': ['三分出手', '3PA'],
            '罰球命中': ['罰球命中', 'FTM'],
            '罰球出手': ['罰球出手', 'FTA'],
            '進攻籃板': ['進攻籃板', 'OREB', '前場籃板'],
            '防守籃板': ['防守籃板', 'DREB', '後場籃板'],
            '籃板': ['籃板', 'REB', '總籃板'],
            '助攻': ['助攻', 'AST'],
            '抄截': ['抄截', 'STL'],
            '阻攻': ['阻攻', 'BLK'],
            '失誤': ['失誤', 'TOV', 'TO'],
            '犯規': ['犯規', 'PF']
        }

        for stat_key, candidates in alias_map.items():
            matched_c = next((c for c in candidates if c in box_df.columns), None)
            if matched_c:
                team_stats[stat_key] = float(pd.to_numeric(box_df[matched_c], errors='coerce').fillna(0).sum())
            else:
                team_stats[stat_key] = 0.0

        if team_stats.get('防守籃板', 0.0) == 0.0 and team_stats.get('籃板', 0.0) > 0 and team_stats.get('進攻籃板', 0.0) > 0:
            team_stats['防守籃板'] = max(0.0, team_stats['籃板'] - team_stats['進攻籃板'])

        return box_df, onoff_df, lineup_df, wowy_df, team_stats, matched_sheet
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, ""

# ----------------- 總表拆解解析 -----------------
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

# ----------------- 提取各隊專屬 PBP 表格 -----------------
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
    has_vertical_brackets = False
    for r in range(len(df)):
        for c in range(min(5, len(df.columns))):
            v = str(df.iloc[r, c]).strip()
            if v.startswith("【") and any(k in v for k in ["on/off", "淨影響力", "五人陣容", "雙洋將", "陣容"]):
                has_vertical_brackets = True
                break
        if has_vertical_brackets:
            break

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
            res = clean_dataframe_times(deduplicate_columns(res))
            return res

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
            box_df = clean_dataframe_times(deduplicate_columns(box_df))
        else:
            box_df = pd.DataFrame()
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
            res = clean_dataframe_times(deduplicate_columns(res))
            return res

        box_df = extract_horizontal_subtable(0)

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

        lineup_c = None
        for c in range(5, len(row_headers)):
            if "五人陣容" in row_headers[c]:
                lineup_c = c
                break
        if lineup_c is not None:
            blocks['lineup'] = extract_horizontal_subtable(lineup_c)

        duo_c = None
        for c in range(5, len(row_headers)):
            if "洋將搭檔" in row_headers[c] or "雙洋將" in row_headers[c]:
                duo_c = c
                break
        if duo_c is not None:
            blocks['duo'] = extract_horizontal_subtable(duo_c)

    return blocks, box_df

# ----------------- 取得球員母表數據 (自動合併進階與平均數據表) -----------------
@st.cache_data(ttl=300)
def get_master_players(candidate_dirs):
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

    f_csv = find_file_in_folders(candidate_dirs, "全聯盟球員進階數據總表")
    if f_csv:
        try:
            return clean_dataframe_times(deduplicate_columns(pd.read_csv(f_csv)))
        except Exception:
            pass

    all_team_dfs = []
    teams = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    for t_name in teams:
        tf = find_team_file_in_folders(candidate_dirs, team_name=t_name)
        if tf:
            try:
                xls = pd.ExcelFile(tf)
                target_sheet = next((s for s in xls.sheet_names if "進階" in s), None)
                avg_sheet = next((s for s in xls.sheet_names if "平均" in s), None)
                
                if target_sheet:
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
                        t_df = deduplicate_columns(t_df)
                        if '球員名' in t_df.columns:
                            t_df['球員名'] = t_df['球員名'].astype(str).str.strip()
                            t_df = t_df[t_df['球員名'] != 'nan'].dropna(subset=['球員名'])
                            if '出賽' in t_df.columns:
                                t_df = t_df.dropna(subset=['出賽'])
                        if '球隊' not in t_df.columns or t_df['球隊'].isna().all():
                            t_df['球隊'] = t_name

                        # 同步讀取「平均數據」工作表，補齊籃板、助攻、抄截、阻攻與球探備註
                        if avg_sheet:
                            raw_avg = pd.read_excel(tf, sheet_name=avg_sheet, header=None)
                            h_avg_idx = None
                            for r in range(min(6, len(raw_avg))):
                                r_vals = [str(x).strip() for x in raw_avg.iloc[r].dropna().tolist()]
                                if "球員名" in r_vals and ("出賽" in r_vals or "背號" in r_vals):
                                    h_avg_idx = r
                                    break
                            if h_avg_idx is not None:
                                avg_cols, avg_c_idxs = [], []
                                for c_i, h_val in enumerate(raw_avg.iloc[h_avg_idx].tolist()):
                                    h_str = str(h_val).strip()
                                    if not h_str or h_str == "nan" or h_str.startswith("Unnamed"):
                                        break
                                    avg_cols.append(h_str)
                                    avg_c_idxs.append(c_i)
                                avg_df = raw_avg.iloc[h_avg_idx + 1:, avg_c_idxs].copy()
                                avg_df.columns = avg_cols
                                avg_df = deduplicate_columns(avg_df)
                                if '球員名' in avg_df.columns:
                                    avg_df['球員名'] = avg_df['球員名'].astype(str).str.strip()
                                    avg_df = avg_df.dropna(subset=['球員名']).drop_duplicates(subset=['球員名'])
                                    missing_cols = ['球員名'] + [c for c in avg_df.columns if c not in t_df.columns]
                                    t_df = pd.merge(t_df, avg_df[missing_cols], on='球員名', how='left')

                        all_team_dfs.append(t_df)
            except Exception:
                continue

    if all_team_dfs:
        combined = pd.concat(all_team_dfs, ignore_index=True)
        return clean_dataframe_times(deduplicate_columns(combined))

    return pd.DataFrame()

# ----------------- 雷達圖能力值計算函式 -----------------
def calculate_radar_scores(row):
    pts = 0.0
    for pc in ['場均得分', 'PPG', '總得分', '得分', 'PTS']:
        if pc in row and pd.notna(row[pc]):
            try:
                pts_val = float(str(row[pc]).replace('%', ''))
                if pc in ['場均得分', 'PPG']:
                    pts = pts_val
                else:
                    games = float(row.get('出賽', row.get('場次', 1)))
                    pts = pts_val / games if games > 0 else pts_val
                break
            except:
                pass
    score_pts = min(99, max(15, (pts / 28.0) * 85 + 14))

    ts_val = str(row.get('TS%', '0')).replace('%', '')
    try:
        ts = float(ts_val)
        if ts < 1.0 and ts > 0: ts = ts * 100.0
    except:
        ts = 50.0
    score_eff = min(99, max(15, ((ts - 40.0) / 32.0) * 85 + 14))

    tpm = float(pd.to_numeric(str(row.get('三分命中', 0)).replace('%', ''), errors='coerce') or 0.0)
    score_3p = min(99, max(15, (tpm / 3.5) * 85 + 14))

    ast = float(pd.to_numeric(str(row.get('助攻', 0)).replace('%', ''), errors='coerce') or 0.0)
    score_ast = min(99, max(15, (ast / 6.0) * 85 + 14))

    reb = float(pd.to_numeric(str(row.get('籃板', 0)).replace('%', ''), errors='coerce') or 0.0)
    score_reb = min(99, max(15, (reb / 12.0) * 85 + 14))

    stl = float(pd.to_numeric(str(row.get('抄截', 0)).replace('%', ''), errors='coerce') or 0.0)
    blk = float(pd.to_numeric(str(row.get('阻攻', 0)).replace('%', ''), errors='coerce') or 0.0)
    stocks = stl + blk
    score_def = min(99, max(15, (stocks / 3.5) * 85 + 14))

    return [round(score_pts, 1), round(score_eff, 1), round(score_3p, 1), round(score_ast, 1), round(score_reb, 1), round(score_def, 1)]

# =========================================================================
# 頁首橫幅
# =========================================================================
banner_sub_c = "#666666" if is_light else "#9E9E9E"
st.markdown(
    f"""
    <div style="text-align: center; margin-top: -24px; margin-bottom: 12px;">
        <h1 style="font-size: 2.2rem; margin-bottom: 6px; letter-spacing: 1px;">🏀 TPBL 職業籃球進階數據與球探分析系統</h1>
        <p style="color: {banner_sub_c}; font-size: 1.05rem; margin: 0;">即時戰力、進階四要素、On/Off 陣容與球員效率象限分析</p>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# 頂部導航列 (Top Navigation Bar) - 6 大核心分頁
# =========================================================================
MENU_SUMMARY = "🏆 7隊戰力評級"
MENU_SCATTER = "🎯 主力效率象限圖"
MENU_GAME = "📅 逐場賽事覆盤"
MENU_PBP = "⚡ 各隊 PBP 陣容與 On/Off"
MENU_CARD = "🃏 球員戰力卡與對決"
MENU_GLOSSARY = "📚 進階數據辭典"

nav_selection = st.radio(
    "導航選單",
    [MENU_SUMMARY, MENU_SCATTER, MENU_GAME, MENU_PBP, MENU_CARD, MENU_GLOSSARY],
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
                    m_dash = re.search(r'(\d+)\s*[-－/]\s*(\d+)', val_str)
                    if m_dash:
                        wins = float(m_dash.group(1))
                        losses = float(m_dash.group(2))
                        tot = wins + losses
                        return wins / tot if tot > 0 else 0.0
                    return 0.0

                df_display['_win_sort'] = df_display['戰績'].apply(extract_win_pct)
                df_display = df_display.sort_values(by='_win_sort', ascending=False).drop(columns=['_win_sort'])

            # 防呆修正：自動將 0.423 等小數格式化為 42.3% 百分比顯示
            pct_cols = ['團隊命中率%', '團隊三分出手比 (Team 3PAr)', '團隊有效命中率 (Team eFG%)', '團隊失誤率 (Team TOV%)']
            for c in pct_cols:
                if c in df_display.columns:
                    df_display[c] = df_display[c].apply(format_pct)

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
                                badge_text_c = "#111111" if is_light else "#FFFFFF"
                                st.markdown(
                                    f'<div style="margin-bottom: 8px;"><span style="font-size: 1.05rem; font-weight: bold; color: {badge_text_c};">{c_name}：</span><span style="font-size: 1.25rem; font-weight: 600; color: #00E676; background-color: rgba(0, 230, 118, 0.12); padding: 3px 10px; border-radius: 6px; display: inline-block;">{val}</span></div>',
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
        pts_col = None
        for c in df_players.columns:
            if c in ['場均得分', 'PPG']:
                pts_col = c
                break
            elif c in ['總得分', '得分', 'PTS']:
                pts_col = c
                break

        id_col = None
        for c in df_players.columns:
            if any(k in str(c) for k in ['身分', '本土', '洋將', '身份']):
                id_col = c
                break

        games_col = None
        for gc in ['出賽', '場次', '出賽場次', 'Games', 'GP']:
            if gc in df_players.columns:
                games_col = gc
                break

        for col in [pts_col, games_col, 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col and col in df_players.columns:
                df_players[col] = pd.to_numeric(df_players[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0.0)

        if pts_col in ['場均得分', 'PPG']:
            df_players['場均得分'] = pd.to_numeric(df_players[pts_col], errors='coerce').fillna(0.0).round(1)
        elif games_col and pts_col:
            g_s = pd.to_numeric(df_players[games_col], errors='coerce').fillna(1.0).replace(0, 1.0)
            p_s = pd.to_numeric(df_players[pts_col], errors='coerce').fillna(0.0)
            df_players['場均得分'] = (p_s / g_s).round(1)
        elif pts_col:
            df_players['場均得分'] = pd.to_numeric(df_players[pts_col], errors='coerce').fillna(0.0).round(1)
        else:
            df_players['場均得分'] = 0.0

        # 針對每位球員獨立防呆校正，若以小數存入（如 0.25）自動轉換為 25.0
        def fix_pct_val(val):
            if val <= 0: return 0.0
            if val <= 1.0: return round(val * 100.0, 1)
            return round(val, 1)

        if 'USG%' in df_players.columns:
            df_players['USG%'] = df_players['USG%'].apply(fix_pct_val)
        if 'TS%' in df_players.columns:
            df_players['TS%'] = df_players['TS%'].apply(fix_pct_val)

        c1, c2 = st.columns(2)
        with c1:
            min_ppg = st.slider("最低場均得分篩選 (PPG)", min_value=0.0, max_value=30.0, value=8.0, step=0.5)
        with c2:
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
                    'USG%': ':.1f',
                    'TS%': ':.1f',
                    size_col: ':.1f',
                    '氣泡大小': False
                },
                template=plotly_template
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

            quad_text_color = "rgba(0,0,0,0.4)" if is_light else "rgba(255,255,255,0.4)"
            quadrant_annotations = [
                dict(x=avg_u + 6, y=avg_t + 18, text="🔥 第一象限：高產高效核心", showarrow=False, font=dict(size=13, color=quad_text_color)),
                dict(x=avg_u - 6, y=avg_t + 18, text="🎯 第二象限：高效終結者", showarrow=False, font=dict(size=13, color=quad_text_color)),
                dict(x=avg_u - 6, y=avg_t - 15, text="🛡️ 第三象限：角色球員/低迷區", showarrow=False, font=dict(size=13, color=quad_text_color)),
                dict(x=avg_u + 6, y=avg_t - 15, text="⚠️ 第四象限：低效強攻區", showarrow=False, font=dict(size=13, color=quad_text_color))
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
# 分頁 3：單場賽事實況與進階數據覆盤 (Game Breakdown)
# =========================================================================
elif nav_selection == MENU_GAME:
    st.subheader(f"📅 {stage_selection} — 單場賽事實況與進階數據覆盤 (Game Breakdown)")
    st.markdown("以官方逐球紀錄為基底，深度解析兩隊單場【進階四要素雙向對決】、【關鍵五人陣容】、【核心雙人搭檔】與【球員單場進階 Box Score】。")

    sched_file = find_file_in_folders(active_dirs, "schedule.json")
    schedule_data = []
    if sched_file and os.path.exists(sched_file):
        try:
            with open(sched_file, "r", encoding="utf-8") as f_json:
                schedule_data = json.load(f_json)
        except Exception:
            pass

    if not schedule_data:
        st.info(f"💡 {stage_selection} 暫無可用的賽程索引（請確認 `{active_dirs[0]}/schedule.json` 檔案存在且格式正確）。")
    else:
        game_labels = [
            f"{g.get('game_id', '')} ｜ {g.get('date', '')} ｜ {g.get('away_team', '')} {g.get('away_score', '')} : {g.get('home_score', '')} {g.get('home_team', '')} ({g.get('status', 'FINAL')})"
            for g in schedule_data
        ]
        
        selected_game_label = st.selectbox("選擇要覆盤的比賽場次", game_labels, index=0)
        selected_idx = game_labels.index(selected_game_label)
        cur_game = schedule_data[selected_idx]
        
        away_team = cur_game.get('away_team', '')
        home_team = cur_game.get('home_team', '')
        away_score = int(cur_game.get('away_score', 0))
        home_score = int(cur_game.get('home_score', 0))
        
        away_sheet = cur_game.get('away_sheet') or cur_game.get('sheet_name', '')
        home_sheet = cur_game.get('home_sheet') or cur_game.get('sheet_name', '')
        cur_game_id = cur_game.get('game_id', '')
        cur_game_date = cur_game.get('date', '')

        away_file = find_team_file_in_folders(active_dirs, away_team)
        home_file = find_team_file_in_folders(active_dirs, home_team)

        box_away, onoff_away, lineup_away, wowy_away, stats_away, matched_away_sheet = extract_single_game_data(away_file, away_sheet, cur_game_id, cur_game_date)
        box_home, onoff_home, lineup_home, wowy_home, stats_home, matched_home_sheet = extract_single_game_data(home_file, home_sheet, cur_game_id, cur_game_date)

        if stats_away.get('得分', 0) > 0:
            away_score = int(stats_away['得分'])
        if stats_home.get('得分', 0) > 0:
            home_score = int(stats_home['得分'])

        color_away = "#00E676" if away_score > home_score else ("#222" if is_light else "#FFF")
        color_home = "#00E676" if home_score > away_score else ("#222" if is_light else "#FFF")
        
        team_a_official = team_color_map.get(away_team, "#00E676")
        team_h_official = team_color_map.get(home_team, "#00E676")

        st.markdown(f"""
        <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; padding: 22px 16px; margin: 12px 0 24px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                <div style="flex: 1.2;">
                    <div style="color: {text_sub_c}; font-size: 0.95rem; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.5px;">客隊 (AWAY)</div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: {text_title_c}; margin-bottom: 4px;">{away_team}</div>
                    <div style="font-size: 3.4rem; font-weight: 900; color: {color_away}; line-height: 1.1;">{away_score}</div>
                </div>
                <div style="flex: 1.0; padding: 0 10px;">
                    <div style="display: inline-block; background: rgba(0, 230, 118, 0.2); color: #00E676; padding: 6px 18px; border-radius: 20px; font-weight: 800; font-size: 1.15rem; letter-spacing: 1px; margin-bottom: 8px; border: 1px solid rgba(0, 230, 118, 0.3);">{cur_game.get('status', 'FINAL')}</div>
                    <div style="color: {text_title_c}; font-size: 2.3rem; font-weight: 900; letter-spacing: 2px; line-height: 1.1; margin-bottom: 4px;">{cur_game.get('game_id')}</div>
                    <div style="color: {text_sub_c}; font-size: 1.1rem; font-weight: 600; letter-spacing: 0.5px;">{cur_game.get('date')} {cur_game.get('time', '')}</div>
                </div>
                <div style="flex: 1.2;">
                    <div style="color: {text_sub_c}; font-size: 0.95rem; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.5px;">主隊 (HOME)</div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: {text_title_c}; margin-bottom: 4px;">{home_team}</div>
                    <div style="font-size: 3.4rem; font-weight: 900; color: {color_home}; line-height: 1.1;">{home_score}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if box_away.empty and box_home.empty:
            st.warning(f"⚠️ 找不到該場次的工作表（請確認各隊 Excel 中是否包含對應工作表）。")
        else:
            st.caption(f"🔍 數據來源工作表核對 ｜ 客隊：`{matched_away_sheet}` ｜ 主隊：`{matched_home_sheet}`")

            fga_a, fta_a, oreb_a, dreb_a, tov_a, fgm_a, tpm_a, tpa_a = (
                stats_away.get('投籃出手', 0), stats_away.get('罰球出手', 0), stats_away.get('進攻籃板', 0),
                stats_away.get('防守籃板', 0), stats_away.get('失誤', 0), stats_away.get('投籃命中', 0),
                stats_away.get('三分命中', 0), stats_away.get('三分出手', 0)
            )
            fga_h, fta_h, oreb_h, dreb_h, tov_h, fgm_h, tpm_h, tpa_h = (
                stats_home.get('投籃出手', 0), stats_home.get('罰球出手', 0), stats_home.get('進攻籃板', 0),
                stats_home.get('防守籃板', 0), stats_home.get('失誤', 0), stats_home.get('投籃命中', 0),
                stats_home.get('三分命中', 0), stats_home.get('三分出手', 0)
            )
            
            efg_a = (fgm_a + 0.5 * tpm_a) / fga_a if fga_a > 0 else 0.0
            efg_h = (fgm_h + 0.5 * tpm_h) / fga_h if fga_h > 0 else 0.0
            
            poss_a = fga_a + 0.44 * fta_a - oreb_a + tov_a
            poss_h = fga_h + 0.44 * fta_h - oreb_h + tov_h
            poss_game = (poss_a + poss_h) / 2.0 if (poss_a + poss_h) > 0 else 100.0
            
            ortg_a = 100.0 * (away_score / poss_a) if poss_a > 0 else 0.0
            ortg_h = 100.0 * (home_score / poss_h) if poss_h > 0 else 0.0
            
            tov_pct_a = (tov_a / (fga_a + 0.44 * fta_a + tov_a)) if (fga_a + 0.44 * fta_a + tov_a) > 0 else 0.0
            tov_pct_h = (tov_h / (fga_h + 0.44 * fta_h + tov_h)) if (fga_h + 0.44 * fta_h + tov_h) > 0 else 0.0
            
            orb_pct_a = oreb_a / (oreb_a + dreb_h) if (oreb_a + dreb_h) > 0 else 0.0
            orb_pct_h = oreb_h / (oreb_h + dreb_a) if (oreb_h + dreb_a) > 0 else 0.0
            
            tpar_a = tpa_a / fga_a if fga_a > 0 else 0.0
            tpar_h = tpa_h / fga_h if fga_h > 0 else 0.0
            ftr_a = fta_a / fga_a if fga_a > 0 else 0.0
            ftr_h = fta_h / fga_h if fga_h > 0 else 0.0

            st.markdown("#### ⚔️ 兩隊進階四要素與攻防效率雙向對決")
            
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0 16px 0; border-bottom: 2px solid {card_border}; margin-bottom: 18px;">
                <div style="width: 42%; text-align: right; padding-right: 14px;">
                    <span style="font-size: 1.65rem; font-weight: 900; color: {team_a_official}; letter-spacing: 1px;">{away_team}</span>
                    <span style="color: {text_sub_c}; font-size: 0.95rem; margin-left: 6px; font-weight: 600;">(客)</span>
                </div>
                <div style="width: 16%; text-align: center; color: {text_sub_c}; font-size: 1.15rem; font-weight: 900; letter-spacing: 2px;">
                    VS
                </div>
                <div style="width: 42%; text-align: left; padding-left: 14px;">
                    <span style="font-size: 1.65rem; font-weight: 900; color: {team_h_official}; letter-spacing: 1px;">{home_team}</span>
                    <span style="color: {text_sub_c}; font-size: 0.95rem; margin-left: 6px; font-weight: 600;">(主)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            bars_html = "".join([
                render_bi_bar("百回合進攻效率 (ORtg)", f"{ortg_a:.1f}", f"{ortg_h:.1f}", higher_is_better=True),
                render_bi_bar("百回合防守效率 (DRtg)", f"{ortg_h:.1f}", f"{ortg_a:.1f}", higher_is_better=False),
                render_bi_bar("真實進攻回合 (Poss)", f"{poss_a:.1f}", f"{poss_h:.1f}", higher_is_better=True),
                render_bi_bar("有效命中率 (eFG%)", f"{efg_a*100:.1f}%", f"{efg_h*100:.1f}%", higher_is_better=True),
                render_bi_bar("團隊失誤率 (TOV%)", f"{tov_pct_a*100:.1f}%", f"{tov_pct_h*100:.1f}%", higher_is_better=False),
                render_bi_bar("進攻籃板爭搶率 (ORB%)", f"{orb_pct_a*100:.1f}%", f"{orb_pct_h*100:.1f}%", higher_is_better=True),
                render_bi_bar("三分出手佔比 (3PAr)", f"{tpar_a*100:.1f}%", f"{tpar_h*100:.1f}%", higher_is_better=True),
                render_bi_bar("買犯罰球比 (FTr)", f"{ftr_a*100:.1f}%", f"{ftr_h*100:.1f}%", higher_is_better=True),
                render_bi_bar("投籃命中 (FGM/FGA)", f"{int(fgm_a)}/{int(fga_a)}", f"{int(fgm_h)}/{int(fga_h)}", higher_is_better=True),
                render_bi_bar("三分命中 (3PM/3PA)", f"{int(tpm_a)}/{int(tpa_a)}", f"{int(tpm_h)}/{int(tpa_h)}", higher_is_better=True),
                render_bi_bar("罰球命中 (FTM/FTA)", f"{int(stats_away.get('罰球命中', 0))}/{int(fta_a)}", f"{int(stats_home.get('罰球命中', 0))}/{int(fta_h)}", higher_is_better=True),
            ])

            table_wrapper_bg = "rgba(0, 0, 0, 0.02)" if is_light else "rgba(255, 255, 255, 0.02)"
            st.markdown(f'<div style="background: {table_wrapper_bg}; padding: 18px 22px; border-radius: 12px; border: 1px solid {card_border}; margin-bottom: 26px;">{bars_html}</div>', unsafe_allow_html=True)

            lineup_5man_away, pairs_away = split_lineup_and_pairs(lineup_away)
            lineup_5man_home, pairs_home = split_lineup_and_pairs(lineup_home)

            st.markdown("#### 🏆 單場關鍵五人陣容對抗 (Top 5-Man Lineups)")
            col_l_a, col_l_h = st.columns(2)
            with col_l_a:
                st.markdown(f"**客隊：{away_team} 主要五人陣容**")
                if not lineup_5man_away.empty:
                    st.dataframe(lineup_5man_away, use_container_width=True, hide_index=True)
                else:
                    st.info(f"💡 {away_team} 本場暫無五人陣容細部統計。")

            with col_l_h:
                st.markdown(f"**主隊：{home_team} 主要五人陣容**")
                if not lineup_5man_home.empty:
                    st.dataframe(lineup_5man_home, use_container_width=True, hide_index=True)
                else:
                    st.info(f"💡 {home_team} 本場暫無五人陣容細部統計。")

            if not pairs_away.empty or not pairs_home.empty:
                st.markdown("#### 🤝 單場核心雙人搭檔效益 (Key Pairs Chemistry)")
                col_p_a, col_p_h = st.columns(2)
                with col_p_a:
                    st.markdown(f"**客隊：{away_team} 核心搭檔**")
                    if not pairs_away.empty:
                        st.dataframe(pairs_away, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"💡 {away_team} 本場暫無雙人搭檔統計。")

                with col_p_h:
                    st.markdown(f"**主隊：{home_team} 核心搭檔**")
                    if not pairs_home.empty:
                        st.dataframe(pairs_home, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"💡 {home_team} 本場暫重雙人搭檔統計。")

            # 渲染單場關鍵焦點對位與戰術交鋒 (WOWY)
            if not wowy_away.empty or not wowy_home.empty:
                st.markdown("#### 🎯 單場關鍵焦點對位與戰術交鋒 (WOWY)")
                col_w_a, col_w_h = st.columns(2)
                with col_w_a:
                    st.markdown(f"**客隊: {away_team} 焦點對位**")
                    if not wowy_away.empty:
                        # 將對位情境項目設為索引，排版會更乾淨；或直接傳入 wowy_away
                        st.table(wowy_away.set_index(wowy_away.columns[0]))
                    else:
                        st.info(f"💡 {away_team} 本場暫無對位分析。")

                with col_w_h:
                    st.markdown(f"**主隊: {home_team} 焦點對位**")
                    if not wowy_home.empty:
                        st.table(wowy_home.set_index(wowy_home.columns[0]))
                    else:
                        st.info(f"💡 {home_team} 本場暫無對位分析。")

            st.markdown("#### 📋 兩隊球員單場進階攻守數據 (Single-Game Box Score)")
            pinned_box_config = {
                "背號": st.column_config.TextColumn("背號", pinned=True),
                "球員名": st.column_config.TextColumn("球員名", pinned=True)
            }

            col_box_a, col_box_h = st.columns(2)
            with col_box_a:
                st.markdown(f'<div style="font-size: 1.15rem; font-weight: 700; color: {team_a_official}; margin-bottom: 8px;">🏀 客隊：{away_team} 球員單場攻守</div>', unsafe_allow_html=True)
                if not box_away.empty:
                    st.dataframe(box_away, use_container_width=True, hide_index=True, height=540, column_config=pinned_box_config)
                else:
                    st.info(f"💡 {away_team} 本場球員攻守數據載入失敗。")

            with col_box_h:
                st.markdown(f'<div style="font-size: 1.15rem; font-weight: 700; color: {team_h_official}; margin-bottom: 8px;">🏀 主隊：{home_team} 球員單場攻守</div>', unsafe_allow_html=True)
                if not box_home.empty:
                    st.dataframe(box_home, use_container_width=True, hide_index=True, height=540, column_config=pinned_box_config)
                else:
                    st.info(f"💡 {home_team} 本場球員攻守數據載入失敗。")

# =========================================================================
# 分頁 4：各隊 PBP 陣容與 On/Off 深入分析
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
            
            table_border_c = "rgba(0,0,0,0.1)" if is_light else "rgba(255,255,255,0.08)"
            table_head_bg = "rgba(0,0,0,0.03)" if is_light else "rgba(255,255,255,0.04)"
            table_body_border = "rgba(0,0,0,0.05)" if is_light else "rgba(255,255,255,0.05)"
            table_text_dim = "#777" if is_light else "#9E9E9E"
            table_text_main = "#222" if is_light else "#E0E0E0"
            table_text_desc = "#111" if is_light else "#FFFFFF"

            html = [
                f'<div style="overflow-x: auto; width: 100%; border: 1px solid {table_border_c}; border-radius: 8px; margin-bottom: 20px;">',
                f'<table style="width: 100%; border-collapse: collapse; font-size: 0.95rem; background-color: {table_wrapper_bg}; text-align: left;">',
                f'<thead><tr style="border-bottom: 1px solid {table_border_c}; background-color: {table_head_bg};">'
            ]
            for i, h in enumerate(headers):
                if i < len(headers) - 1:
                    html.append(f'<th style="padding: 10px 14px; white-space: nowrap; width: 1%; color: {table_text_dim}; font-weight: 600;">{h}</th>')
                else:
                    html.append(f'<th style="padding: 10px 14px; color: {table_text_dim}; font-weight: 600;">{h}</th>')
            html.append('</tr></thead><tbody>')
            
            for _, row in df_duo.iterrows():
                html.append(f'<tr style="border-bottom: 1px solid {table_body_border};">')
                for i, h in enumerate(headers):
                    val = str(row[h]).strip() if pd.notna(row[h]) else ""
                    if i < len(headers) - 1:
                        val_display = val
                        if "NetRtg" in h or "(+/-)" in h:
                            if val.startswith("+"):
                                val_display = f'<span style="color: #00E676; font-weight: 600;">{val}</span>'
                            elif val.startswith("-"):
                                val_display = f'<span style="color: #FF5252; font-weight: 600;">{val}</span>'
                        html.append(f'<td style="padding: 10px 14px; white-space: nowrap; width: 1%; color: {table_text_main};">{val_display}</td>')
                    else:
                        html.append(f'<td style="padding: 10px 14px; color: {table_text_desc}; line-height: 1.5;">{val}</td>')
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
# 分頁 5：球員戰力卡與雙人對決
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
            if not p1_player_list:
                st.warning("⚠️ 該球隊暫無可用球員名單")
                p1_name = None
            else:
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

        p1_match = df_players[(df_players['球隊'] == p1_team) & (df_players['球員名'] == p1_name)] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p1_name]
        p1_row = p1_match.iloc[0] if not p1_match.empty else None
        p2_row = None
        if p2_name:
            p2_match = df_players[(df_players['球隊'] == p2_team) & (df_players['球員名'] == p2_name)] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p2_name]
            p2_row = p2_match.iloc[0] if not p2_match.empty else None

        if p1_row is None:
            st.warning('⚠️ 查無此球員資料，請重新選擇。')
        else:
            categories = ['得分產量', '真實效率', '外線威脅', '組織發動', '籃板保護', '防守破壞']
            cats_closed = categories + [categories[0]]
            p1_scores = calculate_radar_scores(p1_row)
            p1_closed = p1_scores + [p1_scores[0]]

            if p2_row is None:
                st.divider()
                card_col1, card_col2, card_col3, card_col4 = st.columns(4)

                games_cnt = float(pd.to_numeric(str(p1_row.get('出賽', p1_row.get('場次', 1))), errors='coerce') or 1.0)
                games_cnt = 1.0 if games_cnt <= 0 else games_cnt

                raw_pts = 0.0
                for pc in ['場均得分', 'PPG', '總得分', '得分', 'PTS']:
                    if pc in p1_row and pd.notna(p1_row[pc]):
                        try:
                            raw_pts = float(str(p1_row[pc]).replace('%', ''))
                            break
                        except:
                            pass

                if '場均得分' in p1_row or 'PPG' in p1_row:
                    ppg_val = raw_pts
                    tot_pts = raw_pts * games_cnt
                else:
                    tot_pts = raw_pts
                    ppg_val = tot_pts / games_cnt

                raw_gmsc = float(pd.to_numeric(str(p1_row.get('GmSc', p1_row.get('EFF', 0))), errors='coerce') or 0.0)
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
                    radar_grid_c = 'rgba(0, 0, 0, 0.12)' if is_light else 'rgba(255, 255, 255, 0.15)'
                    radar_text_c = '#222222' if is_light else '#FFFFFF'
                    fig_single.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor=radar_grid_c),
                            angularaxis=dict(gridcolor=radar_grid_c, tickfont=dict(size=13, color=radar_text_c)),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        template=plotly_template,
                        height=460,
                        margin=dict(l=30, r=30, t=20, b=20)
                    )
                    st.plotly_chart(fig_single, use_container_width=True)

                with r_col2:
                    st.markdown(f"#### 🔍 球員基本檔案與球探特徵")
                    team_display = str(p1_row.get('球隊', '所屬隊伍'))
                    pos_display = str(p1_row.get('位置', '位置'))
                    id_display = str(p1_row.get('本土/洋將', p1_row.get('身分', p1_row.get('身份', '身分'))))
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
                    card_box_bg = "rgba(0,0,0,0.02)" if is_light else "rgba(255,255,255,0.03)"
                    st.markdown(f'<div style="background-color: {card_box_bg}; padding: 16px 20px; border-radius: 10px; border: 1px solid {card_border}; margin-bottom: 12px;">{rows_html}</div>', unsafe_allow_html=True)

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
                        <p style="margin: 4px 0 0 0; color: {text_sub_c};">{p1_row.get('球隊', '')} | #{p1_row.get('背號', '')} | {p1_row.get('位置', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with pk_c2:
                    st.markdown(f"""
                    <div style="background-color: rgba(255, 145, 0, 0.1); border-left: 5px solid #FF9100; padding: 12px; border-radius: 6px;">
                        <h3 style="margin: 0; color: #FF9100;">🟠 {p2_row['球員名']}</h3>
                        <p style="margin: 4px 0 0 0; color: {text_sub_c};">{p2_row.get('球隊', '')} | #{p2_row.get('背號', '')} | {p2_row.get('位置', '')}</p>
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
                    radar_grid_c = 'rgba(0, 0, 0, 0.12)' if is_light else 'rgba(255, 255, 255, 0.15)'
                    radar_text_c = '#222222' if is_light else '#FFFFFF'
                    fig_dual.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor=radar_grid_c),
                            angularaxis=dict(gridcolor=radar_grid_c, tickfont=dict(size=13, color=radar_text_c)),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        template=plotly_template,
                        height=460,
                        margin=dict(l=30, r=30, t=30, b=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig_dual, use_container_width=True)

                with dual_col2:
                    st.markdown("#### 📋 攻守數據正面對決表 (Tale of the Tape)")

                    def get_ppg(r):
                        g = float(pd.to_numeric(str(r.get('出賽', r.get('場次', 1))), errors='coerce') or 1.0)
                        g = 1.0 if g <= 0 else g
                        for pc in ['場均得分', 'PPG']:
                            if pc in r and pd.notna(r[pc]):
                                return float(str(r[pc]).replace('%', ''))
                        for pc in ['總得分', '得分', 'PTS']:
                            if pc in r and pd.notna(r[pc]):
                                return float(str(r[pc]).replace('%', '')) / g
                        return 0.0

                    p1_ppg = get_ppg(p1_row)
                    p2_ppg = get_ppg(p2_row)

                    compare_metrics = [
                        ('場均得分 (PPG)', f"{p1_ppg:.1f}", f"{p2_ppg:.1f}"),
                        ('出賽場次', p1_row.get('出賽', p1_row.get('場次', 0)), p2_row.get('出賽', p2_row.get('場次', 0))),
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
                        ('綜合評分 (GmSc)', p1_row.get('GmSc', p1_row.get('EFF', 0)), p2_row.get('GmSc', p2_row.get('EFF', 0)))
                    ]

                    cmp_df = pd.DataFrame(compare_metrics, columns=['指標項目', f"🟢 {p1_row['球員名']}", f"🟠 {p2_row['球員名']}"])
                    st.dataframe(cmp_df, use_container_width=True, hide_index=True)
                    st.caption("💡 提示：可切換不同球員組合，觀察不同體系後衛或禁區長人之間的風格差異。")
    else:
        st.info("💡 尚未讀取到球員數據母表。")

# =========================================================================
# 分頁 6：進階數據辭典與公式附錄
# =========================================================================
elif nav_selection == MENU_GLOSSARY:
    st.subheader("📚 TPBL 進階數據辭典與公式附錄 (Glossary & Formulas)")
    st.markdown("收錄職業籃球進階數據工程之計算原理、數學公式、球探判讀指引與體系洞察。")

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
* **數據意義**：傳統命中率 ($FG\%$) 將三分球與兩分球視為同等價值，有效命中率將三分球額外賦予 1.5 倍的得分權重，真實反映外線投射的期望回報。
* **球探判讀標準**：
  * **$> 60.0\%$**：聯盟頂級禁區終結者（如高柏鎧）/ 高效外線終結點（如沃許本、迪亞洛）。
  * **$53.0\% \sim 58.0\%$**：聯盟優質先發得分點。
  * **$< 48.0\%$**：出手效率偏低，多為受迫性出手或外線把握度不足。

---
### 2. 真實命中率 (TS%, True Shooting Percentage)
* **數學公式**：
$$TS\% = \frac{PTS}{2 \times (FGA + 0.44 \times FTA)} \times 100\%$$
* **數據意義**：衡量每次終結回合（綜合兩分球、三分球與罰球）的終極得分效率，是現代籃球評估得分手最權威的單一指標。
* **為什麼罰球係數是 0.44？**：技術犯規罰球、And-1（進球加罰）與三分犯規（罰 3 球）不會消耗完整的進攻回合，經大數據回歸精確折算後，每次罰球出手平均消耗約 0.44 個回合。
* **球探判讀標準**：
  * **$> 60.0\%$**：高產高效神獸（如德魯 64.2%、沃許本 62.0%、迪亞洛 63.3%）。
  * **$53.0\% \sim 58.0\%$**：聯盟合格主力水平。
  * **$< 50.0\%$**：低效進攻區，球隊應適度限縮其自主強攻比重。

---
### 3. 三分出手佔比 (3PAr) 與 買犯罰球比 (FTr)
* **三分出手佔比 (3PAr, 3-Point Attempt Rate)**：
$$3PAr = \frac{3PA}{FGA} \times 100\%$$
  * **判讀**：衡量球員進攻空間屬性。$> 50\%$ 為純魔球外線砲塔（如霍爾曼、湯普金斯）；$< 20\%$ 為傳統禁區肉搏型長人。
* **買犯罰球比 (FTr, Free Throw Rate)**：
$$FTr = \frac{FTA}{FGA} \times 100\%$$
  * **判讀**：衡量衝擊禁區與製造犯規的殺傷力。$> 40\%$ 代表極具禁區破壞力，能造成對手犯規麻煩並站上罰球線穩健取分。
        """)

    with tab2:
        st.markdown(r"""
### 1. 球權使用率 (USG%, Usage Percentage)
* **數學公式**：
$$USG\% = 100 \times \frac{(FGA + 0.44 \times FTA + TOV) \times (\text{Team\_MP} / 5)}{MP \times (\text{Team\_FGA} + 0.44 \times \text{Team\_FTA} + \text{Team\_TOV})}$$
* **數據意義**：衡量一名球員在場時，球隊所有以「出手、罰球、失誤」結束的回合中，由該球員親自終結的比例。
* **戰術地位判讀**：
  * **$\ge 30.0\%$**：球隊絕對第一持球核心（如克羅馬 36.9%、威力斯 36.5%、杰倫 35.8%）。
  * **$22.0\% \sim 28.0\%$**：主要先發得分點 / 第二持球副攻手（如阿巴西 26.0%、高國豪 24.2%）。
  * **$< 18.0\%$**：功能型角色球員、底角射手或防守大鎖。

---
### 2. 單場綜合表現值 (GmSc, Game Score)
* **數學公式**：
$$GmSc = PTS + 0.4 \times FGM - 0.7 \times FGA - 0.4 \times (FTA - FTM) + 0.7 \times OREB + 0.3 \times DREB + STL + 0.7 \times AST + 0.7 \times BLK - 0.4 \times PF - TOV$$
* **數據意義**：由進階數據鼻祖 John Hollinger 提出，將得分、籃板、助攻、抄截、火鍋與各項命中/失誤加權整合為單一線性數值，評估每場比賽的綜合產出。
* **球探判讀標準 (場均值)**：
  * **$> 18.0$**：年度 MVP 競爭者 / 聯盟第一檔洋將（如德魯、克羅馬）。
  * **$12.0 \sim 17.0$**：全明星級先發核心（如阿巴西、高錦瑋、沃許本）。
  * **$8.0 \sim 11.0$**：合格主力輪替陣容。
  * **$< 5.0$**：板凳替補或邊緣輪替球員。

---
### 3. 助攻失誤比 (AST/TO) 與 組織影響力
* **數學公式**：
$$AST/TO = \frac{AST}{TOV}$$
* **數據意義**：衡量控球後衛與進攻發動機的傳球決策質量與失誤控制能力。
* **球探判讀標準**：
  * **$> 2.50$**：頂級指揮官，出色的傳導穩定性且鮮少送出失誤。
  * **$1.80 \sim 2.40$**：合格的主力控球水平。
  * **$< 1.30$**：傳球風險過高或持球過於黏球，容易被對手打出快速反擊。
        """)

    with tab3:
        st.markdown(r"""
### 1. 進階四要素 (Dean Oliver's Four Factors)
現代籃球數據分析最著名的「四大決勝要素」，攻防兩端權重佔比如下：
1. **有效命中率 (eFG%, 權重 40%)**：投籃準星與得分期望值，為贏球最核心要素。
2. **失誤率 (TOV%, 權重 25%)**：每百回合失誤次數，保護球權即保護進攻機會。
3. **進攻籃板率 (OREB%, 權重 20%)**：前場籃板衝搶能力，爭取二次進攻機會。
4. **買犯罰球率 (FTr, 權重 15%)**：製造犯規站上罰球線的頻率與殺傷力。

---
### 2. 團隊進攻回合數 (Poss) 與 比賽節奏 (Pace)
* **回合數估算公式**：
$$Poss \approx Team\_FGA + 0.44 \times Team\_FTA - Team\_OREB + Team\_TOV$$
* **比賽節奏 (Pace, 48 分鐘標準化回合數)**：
$$Pace = 48 \times \frac{Poss}{Team\_MP / 5}$$
* **戰術節奏判讀**：
  * **$Pace > 103.0$**：快節奏跑轟球風（主打快速推進與早攻，轉換進攻比例高）。
  * **$97.0 \sim 102.0$**：聯盟標準攻防節奏。
  * **$< 96.0$**：陣地戰導向體系（強調半場戰術執行、高位擋拆與低位肉搏）。

---
### 3. 百回合進攻 / 防守 / 淨效率 (ORtg / DRtg / NetRtg)
* **百回合進攻效率 (ORtg, Offensive Rating)**：
$$ORtg = 100 \times \frac{Team\_PTS}{Poss}$$
  * 衡量每 100 個進攻回合的真實得分能力。超過 **115.0** 屬聯盟頂尖進攻強隊。
* **百回合防守效率 (DRtg, Defensive Rating)**：
$$DRtg = 100 \times \frac{Opp\_PTS}{Opp\_Poss}$$
  * 衡量每 100 個防守回合的失分控制能力。低於 **100.0** 屬聯盟第一線鐵血防守強隊。
* **百回合淨效率 (NetRtg, Net Rating)**：
$$NetRtg = ORtg - DRtg$$
  * 剔除比賽節奏（Pace）干擾後，球隊攻防戰力的真實淨勝分體現。
        """)

    with tab4:
        st.markdown(r"""
### 1. Play-by-Play (PBP) Stint 狀態機運作原理
* **逐球時間段 (Stint)**：系統即時追蹤場上 10 人名單，只要場上發生**「任一球員替換」**或**「單節結束」**，狀態機即自動切分出一個封閉時間段。
* 該時間段內產生的所有得分、失分、出手、籃板與回合數，100% 精準歸屬於當時在場的特定陣容。

---
### 2. 主力 On/Off 淨影響力指標體系
衡量單一主力球員在場與下場時，球隊攻防戰力的真實落差：
* **On ORtg / On DRtg / On NetRtg**：該球員**在場上時**，球隊每百回合的得分、失分與淨勝分。
* **Off NetRtg**：該球員**在板凳休息時**，球隊每百回合的淨勝分。
* **賽季淨影響力 (Net Diff)**：
$$Diff = On\_NetRtg - Off\_NetRtg$$
  * **$Diff > +10.0$**：球隊真核基石，在場時大幅贏分、退場時球隊體系嚴重失血（不可替代性極高）。
  * **$Diff \approx 0.0$**：替補陣容銜接穩定，體系不因該球員輪休而產生劇烈波動。
  * **$Diff < -5.0$**：該球員在場時防守破口或進攻停滯，反而替補陣容效率更高。

---
### 3. 最佳五人陣容與雙洋將化學效應矩陣
* **最佳五人陣容 (Top Lineups)**：
  * 篩選整季**累計同場出賽時間最長**之主力配置，評估在具有足夠樣本數（Sample Size）下的實質戰術效益。
* **雙洋將化學效應矩陣 (Duo Chemistry)**：
  * TPBL 採雙洋將同場制，雙外援的空間搭配、擋拆默契與禁區護框互補性，直接決定球隊攻防上限。
  * 藉由雙人共同在場時間（Minutes）、累計正負分（+/-）與 Lineup NetRtg，找出教練團最具統治力的外援決勝組合。
        """)
