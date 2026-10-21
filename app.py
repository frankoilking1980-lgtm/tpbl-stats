import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
import datetime

# ----------------- 頁面全域設定 -----------------
st.set_page_config(
    page_title="TPBL 職業籃球進階數據與球探分析系統",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 徹底隱藏頂部工具列與側邊欄收合按鈕 -----------------
hide_streamlit_style = """
<style>
/* 1. 徹底拔除頂部 Header (包含三點選單、GitHub 原始碼、Deploy 按鈕) */
header, [data-testid="stHeader"] {
    display: none !important;
}

/* 2. 徹底隱藏側邊欄的收合按鈕 (<<)，讓左側選單永久鎖定展開不遺失 */
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}
[data-testid="stSidebarHeader"] button {
    display: none !important;
}
button[kind="header"] {
    display: none !important;
}

/* 3. 徹底隱藏原生頁尾與嵌入底部白框 */
footer, [data-testid="stEmbedFooter"] {
    display: none !important;
}
div[class*="viewerBadge"] {
    display: none !important;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ----------------- 時間與數值格式化工具函式 -----------------
def clean_time_display(val):
    """將被 Pandas / Excel 誤判為 Timedelta/天數的時間，校正還原回正常的 分:秒 (MM:SS)"""
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
    """將小數或字串百分比統一格式化為清晰的百分比字串 (如 44.0%)"""
    if pd.isna(val) or val == "" or str(val).strip() == "-" or str(val).strip() == "nan":
        return "0.0%"
    s = str(val).strip()
    if s.endswith('%'):
        try:
            num = float(s.replace('%', ''))
            return f"{num:.1f}%"
        except:
            return s
    try:
        f = float(s)
        if 0 < f <= 1.0:
            return f"{f * 100:.1f}%"
        else:
            return f"{f:.1f}%"
    except:
        return s

def get_ast_to_ratio(row):
    """計算或提取精確的助攻失誤比 (AST/TO)"""
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
    """生成字級放大、醒目亮綠底色標籤的 HTML 結構"""
    return f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.08);">
        <span style="font-size: 1.05rem; font-weight: 600; color: #E0E0E0;">{label}</span>
        <span style="font-size: 1.22rem; font-weight: 700; color: #00E676; background-color: rgba(0, 230, 118, 0.15); padding: 4px 14px; border-radius: 6px; letter-spacing: 0.5px;">{val}</span>
    </div>
    """

def clean_dataframe_times(df):
    """批量校正表格時間"""
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        col_str = str(col)
        if any(k in col_str for k in ['時間', 'Time', 'time', '共同時間', '累計時間']):
            df[col] = df[col].apply(clean_time_display)
    return df

def deduplicate_columns(df):
    """徹底避免 PyArrow 重複欄位報錯"""
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

def find_file_fuzzy(keyword):
    """模糊搜尋本機資料庫檔案"""
    keyword_clean = keyword.lower().strip()
    for fname in os.listdir('.'):
        fname_lower = fname.lower()
        if keyword_clean in fname_lower and fname_lower.endswith(('.xlsx', '.xls', '.csv')):
            return fname
    return None

def find_team_file(team_name):
    """精準匹配 7 隊專屬檔案"""
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
    for fname in os.listdir('.'):
        fname_lower = fname.lower()
        if any(kw.lower() in fname_lower for kw in kws) and fname_lower.endswith(('.xlsx', '.xls', '.csv')):
            return fname
    return None

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

    if row_block_a_title is not None:
        header_a_idx = row_block_a_title + 1
        end_a = row_block_b_title if row_block_b_title is not None else header_a_idx + 8
        block_a = df_raw.iloc[header_a_idx + 1 : end_a].copy()
        block_a.columns = [str(c).strip() for c in df_raw.iloc[header_a_idx].tolist()]
        block_a = clean_dataframe_times(deduplicate_columns(block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)))
    else:
        header_a_idx = None
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(v) for v in row.values if pd.notna(v)])
            if "團隊總得分" in row_str or "團隊回合數" in row_str:
                header_a_idx = idx
                break
        if header_a_idx is not None:
            block_a = df_raw.iloc[header_a_idx + 1 : header_a_idx + 8].copy()
            block_a.columns = [str(c).strip() for c in df_raw.iloc[header_a_idx].tolist()]
            block_a = clean_dataframe_times(deduplicate_columns(block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)))
        else:
            block_a = pd.DataFrame()

    if row_block_b_title is not None:
        header_b_idx = row_block_b_title + 1
        block_b = df_raw.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
        block_b.columns = [str(c).strip() for c in df_raw.iloc[header_b_idx].tolist()]
        block_b = deduplicate_columns(block_b.dropna(how='all', axis=1).dropna(how='all', axis=0))
    else:
        header_b_idx = None
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(v) for v in row.values if pd.notna(v)])
            if "高球權核心" in row_str or "高效終結者" in row_str:
                header_b_idx = idx
                break
        if header_b_idx is not None:
            block_b = df_raw.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
            block_b.columns = [str(c).strip() for c in df_raw.iloc[header_b_idx].tolist()]
            block_b = deduplicate_columns(block_b.dropna(how='all', axis=1).dropna(how='all', axis=0))
        else:
            block_b = pd.DataFrame()

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
    r_onoff, c_onoff = None, None
    r_lineup, c_lineup = None, None
    r_duo, c_duo = None, None

    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = str(df.iloc[r, c]).strip()
            if "【" in val:
                if "on/off" in val.lower() or "淨影響力" in val:
                    if r_onoff is None: r_onoff, c_onoff = r, c
                elif "五人陣容" in val:
                    if r_lineup is None: r_lineup, c_lineup = r, c
                elif "雙洋將" in val or "化學效應" in val:
                    if r_duo is None: r_duo, c_duo = r, c

    def extract_subtable(title_r, title_c):
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
        for cur_r in range(header_row_idx + 1, min(len(df), header_row_idx + 35)):
            first_val = str(df.iloc[cur_r, title_c]).strip()
            if pd.isna(df.iloc[cur_r, title_c]) or first_val == "" or first_val == "nan" or first_val.startswith("【"):
                break
            data_rows.append([df.iloc[cur_r, col_idx] for col_idx in col_indices])
            
        res = pd.DataFrame(data_rows, columns=headers)
        res = clean_dataframe_times(res)
        return deduplicate_columns(res)

    if r_onoff is not None:
        blocks['on_off'] = extract_subtable(r_onoff, c_onoff)
    if r_lineup is not None:
        blocks['lineup'] = extract_subtable(r_lineup, c_lineup)
    if r_duo is not None:
        blocks['duo'] = extract_subtable(r_duo, c_duo)

    box_header_row = None
    for r in range(min(12, len(df))):
        row_str = " ".join([str(v) for v in df.iloc[r, :8] if pd.notna(v)])
        if "球員名" in row_str and ("得分" in row_str or "出賽" in row_str):
            box_header_row = r
            break

    if box_header_row is not None:
        end_box = r_onoff if (r_onoff is not None and c_onoff == 0 and r_onoff > box_header_row) else len(df)
        box_df = df.iloc[box_header_row + 1 : end_box].copy()
        raw_headers = [str(x).strip() for x in df.iloc[box_header_row].tolist()]
        valid_cols_idx = []
        seen = set()
        for idx_h, h in enumerate(raw_headers):
            if "Unnamed" in h or h == "" or "nan" in h or "【" in h:
                break
            if h in seen:
                break
            seen.add(h)
            valid_cols_idx.append(idx_h)
            
        box_df = box_df.iloc[:, valid_cols_idx].copy()
        box_df.columns = [raw_headers[i] for i in valid_cols_idx]
        box_df = clean_dataframe_times(box_df)
        box_df = deduplicate_columns(box_df.dropna(how='all', axis=0))
    else:
        box_df = pd.DataFrame()

    return blocks, box_df

# ----------------- 取得球員母表數據 -----------------
@st.cache_data(ttl=300)
def get_master_players():
    f_master = find_file_fuzzy("進階數據與戰力評級總表")
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

    f_csv = find_file_fuzzy("全聯盟球員進階數據總表")
    if f_csv:
        try:
            return clean_dataframe_times(deduplicate_columns(pd.read_csv(f_csv)))
        except Exception:
            pass

    return pd.DataFrame()

# ----------------- 雷達圖能力值計算函式 -----------------
def calculate_radar_scores(row):
    """將球員基礎與進階數據轉換為 0-99 的戰力六邊形指標"""
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

# ----------------- 側邊欄導航設定 -----------------
st.sidebar.title("🏀 TPBL 數據總覽")

MENU_SUMMARY = "🏆 7隊戰力評級與攻防總評"
MENU_SCATTER = "🎯 主力球員效率象限圖 (USG% vs TS%)"
MENU_PBP = "⚡ 各隊 PBP 陣容與 On/Off 深入分析"
MENU_CARD = "🃏 球員戰力卡與雙人對決"
MENU_GLOSSARY = "📚 進階數據辭典與公式附錄"

nav_selection = st.sidebar.radio(
    "功能分頁選擇",
    [MENU_SUMMARY, MENU_SCATTER, MENU_PBP, MENU_CARD, MENU_GLOSSARY]
)

# =========================================================================
# 分頁 1：7 隊戰力評級與攻防總評
# =========================================================================
if nav_selection == MENU_SUMMARY:
    st.title("🏆 2026-2027 TPBL 各隊戰力評級與進階攻防總評")
    st.markdown("以四要素 (Four Factors)、節奏 (Pace) 及百回合進攻效率 (ORtg) 標準化評估各隊戰力與教練戰術。")

    sum_file = find_file_fuzzy("summary") or find_file_fuzzy("7隊戰力")
    if sum_file:
        block_a, block_b = parse_summary_sheet(sum_file)

        st.subheader("📊 團隊進階四要素指標 (Team Advanced Metrics)")
        st.dataframe(block_a, use_container_width=True, hide_index=True)

        if not block_b.empty:
            st.subheader("🔍 重點球員洞察與教練體系戰力短評")
            for _, row in block_b.iterrows():
                team_name = str(row.iloc[0]) if len(row) > 0 else "球隊"
                if team_name and team_name != "nan" and "區塊" not in team_name:
                    record = str(row.iloc[1]) if len(row) > 1 else "尚未出賽"
                    with st.expander(f"🏀 {team_name} — 戰績：{record}", expanded=True):
                        col_names = [str(c) for c in block_b.columns]
                        for c_idx, c_name in enumerate(col_names[2:], start=2):
                            val = row.iloc[c_idx] if c_idx < len(row) else ""
                            if "短評" in c_name:
                                st.info(f"**{c_name}**：\n\n{val}")
                            else:
                                st.markdown(
                                    f'<div style="margin-bottom: 8px;"><span style="font-size: 1.05rem; font-weight: bold; color: #FFFFFF;">{c_name}：</span><span style="font-size: 1.07rem; font-weight: 600; color: #00E676; background-color: rgba(0, 230, 118, 0.12); padding: 3px 10px; border-radius: 6px; display: inline-block;">{val}</span></div>',
                                    unsafe_allow_html=True
                                )
    else:
        st.warning("⚠️ 找不到總表檔案（`tpbl_summary.xlsx`）。")

# =========================================================================
# 分頁 2：USG% vs TS% 散佈圖 (Plotly 互動圖表)
# =========================================================================
elif nav_selection == MENU_SCATTER:
    st.title("🎯 球員效率象限圖：球權使用率 (USG%) vs 真實命中率 (TS%)")
    st.markdown("氣泡大小代表單場綜合表現值 (**GmSc**)，右上角為高產量且高效率之核心神獸。支援滑鼠懸停查看球員詳情與縮放。")

    df_players = get_master_players()

    if not df_players.empty and '球員名' in df_players.columns:
        pts_col = '總得分' if '總得分' in df_players.columns else ('得分' if '得分' in df_players.columns else None)
        
        for col in [pts_col, 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col and col in df_players.columns:
                df_players[col] = pd.to_numeric(df_players[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        if 'USG%' in df_players.columns and df_players['USG%'].mean() > 0 and df_players['USG%'].mean() < 1.0:
            df_players['USG%'] = df_players['USG%'] * 100.0
        if 'TS%' in df_players.columns and df_players['TS%'].mean() > 0 and df_players['TS%'].mean() < 1.0:
            df_players['TS%'] = df_players['TS%'] * 100.0

        c1, c2 = st.columns(2)
        with c1:
            min_pts = st.slider("最低得分篩選 (PTS)", min_value=0, max_value=35, value=10)
        with c2:
            id_col = '本土/洋將' if '本土/洋將' in df_players.columns else None
            id_options = ["全部"] + list(df_players[id_col].dropna().unique()) if id_col else ["全部"]
            selected_id = st.multiselect("球員身分篩選", id_options, default=["全部"])

        filtered = df_players.copy()
        if pts_col:
            filtered = filtered[filtered[pts_col] >= min_pts]
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

            fig.add_hline(y=avg_t, line_dash="dash", line_color="gray", annotation_text=f"平均 TS% ({avg_t:.1f}%)")
            fig.add_vline(x=avg_u, line_dash="dot", line_color="red", annotation_text=f"平均 USG% ({avg_u:.1f}%)")

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
        st.info("💡 尚未讀取到《全聯盟球員進階數據總表》。")

# =========================================================================
# 分頁 3：各隊 PBP 陣容與 On/Off 深入分析
# =========================================================================
elif nav_selection == MENU_PBP:
    st.title("⚡ 各隊 Play-by-Play 陣容組合與主力 On/Off 淨勝分")
    st.markdown("由官方逐球時間段 (Stints) 精確解析各隊【賽季累積主力 On/Off 總榜】、【賽季最佳五人陣容】與【雙洋將化學效應】。")

    team_options = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    selected_team = st.selectbox("選擇要深入分析的球隊", team_options)

    target_file = find_team_file(selected_team) or find_file_fuzzy(selected_team)

    if target_file:
        blocks, box_df = extract_pbp_blocks(target_file)

        # 1. 顯示主力 On/Off 淨影響力總榜
        st.subheader(f"📊 {selected_team} — 主力 On/Off 淨影響力總榜")
        if 'on_off' in blocks and not blocks['on_off'].empty:
            st.dataframe(blocks['on_off'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無 On/Off 統計資料。")

        # 2. 顯示最佳五人陣容
        st.subheader(f"🏆 {selected_team} — 最佳五人陣容 (Top Lineups)")
        if 'lineup' in blocks and not blocks['lineup'].empty:
            st.dataframe(blocks['lineup'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無五人陣容統計資料。")

        # 3. 顯示雙洋將搭配矩陣
        st.subheader(f"🤝 {selected_team} — 雙洋將化學效應矩陣")
        if 'duo' in blocks and not blocks['duo'].empty:
            st.dataframe(blocks['duo'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無雙洋將搭配資料。")

        # 4. 顯示基礎球員攻守數據
        if not box_df.empty:
            with st.expander(f"📋 查看 {selected_team} 基礎攻守數據表 (Box Score)", expanded=False):
                st.dataframe(box_df, use_container_width=True, hide_index=True)
    else:
        st.warning(f"⚠️ 找不到 {selected_team} 的 Excel 檔案。")

# =========================================================================
# 分頁 4：球員戰力卡與雙人對決 (分級選擇 + 大字號醒目排版)
# =========================================================================
elif nav_selection == MENU_CARD:
    st.title("🃏 球員戰力卡與雙雄對決 (Player Card & Head-to-Head)")
    st.markdown("依球隊輕鬆篩選球員，檢視六維戰力雷達圖與高階球探卡，並可加入另一名球員展開對照 PK。")

    df_players = get_master_players()

    if not df_players.empty and '球員名' in df_players.columns:
        all_teams = sorted(list(df_players['球隊'].dropna().unique())) if '球隊' in df_players.columns else ["全隊伍"]

        # 雙層級球員選擇列
        st.markdown("### 🔍 步驟 1：選擇主要球員（球探卡）")
        p1_col1, p1_col2 = st.columns(2)
        with p1_col1:
            p1_team = st.selectbox("🏀 主要球員所屬球隊", all_teams, index=0, key="sel_p1_team")
        with p1_col2:
            p1_player_list = df_players[df_players['球隊'] == p1_team]['球員名'].dropna().tolist() if '球隊' in df_players.columns else df_players['球員名'].dropna().tolist()
            p1_name = st.selectbox("🎯 選擇主要球員", p1_player_list, index=0, key="sel_p1_player")

        st.markdown("### ⚔️ 步驟 2：加入比較球員（可選）")
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

        # 提取資料行
        p1_row = df_players[(df_players['球隊'] == p1_team) & (df_players['球員名'] == p1_name)].iloc[0] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p1_name].iloc[0]
        p2_row = None
        if p2_name:
            p2_row = df_players[(df_players['球隊'] == p2_team) & (df_players['球員名'] == p2_name)].iloc[0] if '球隊' in df_players.columns else df_players[df_players['球員名'] == p2_name].iloc[0]

        # 計算戰力雷達數值
        categories = ['得分產量', '真實效率', '外線威脅', '組織發動', '籃板保護', '防守破壞']
        cats_closed = categories + [categories[0]]
        p1_scores = calculate_radar_scores(p1_row)
        p1_closed = p1_scores + [p1_scores[0]]

        # ----------------- 模式 A：單人球探卡模式 -----------------
        if p2_row is None:
            st.divider()
            card_col1, card_col2, card_col3, card_col4 = st.columns(4)
            pts_val = p1_row.get('總得分', p1_row.get('得分', 0))
            ts_val = format_pct(p1_row.get('TS%', '0%'))
            usg_val = format_pct(p1_row.get('USG%', '0%'))
            gmsc_val = str(p1_row.get('GmSc', p1_row.get('EFF', 0)))

            card_col1.metric("場均/總得分 (PTS)", f"{pts_val} 分")
            card_col2.metric("真實命中率 (TS%)", ts_val)
            card_col3.metric("球權使用率 (USG%)", usg_val)
            card_col4.metric("單場綜合評分 (GmSc)", gmsc_val)

            r_col1, r_col2 = st.columns([1.1, 1])
            with r_col1:
                st.subheader(f"📊 {p1_row['球員名']} — 六維戰力雷達圖")
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
                st.subheader(f"🔍 球員基本檔案與球探特徵")
                team_display = str(p1_row.get('球隊', '所屬隊伍'))
                pos_display = str(p1_row.get('位置', '位置'))
                id_display = str(p1_row.get('本土/洋將', '身分'))
                num_display = str(p1_row.get('背號', '#'))
                efg_display = format_pct(p1_row.get('eFG%', '0%'))
                tpar_display = format_pct(p1_row.get('3PAr', '0%'))
                ftr_display = format_pct(p1_row.get('FTr', '0%'))
                ast_to_display = get_ast_to_ratio(p1_row)

                # 使用放大且醒目的亮綠色標籤
                html_badges = f"""
                <div style="background-color: rgba(255,255,255,0.03); padding: 16px 20px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px;">
                    {make_stat_badge_row("所屬隊伍", team_display)}
                    {make_stat_badge_row("球衣背號 / 場上位置", f"#{num_display} / {pos_display}")}
                    {make_stat_badge_row("球員身分類別", id_display)}
                    {make_stat_badge_row("有效命中率 (eFG%)", efg_display)}
                    {make_stat_badge_row("三分出手佔比 (3PAr)", tpar_display)}
                    {make_stat_badge_row("買犯罰球比 (FTr)", ftr_display)}
                    {make_stat_badge_row("助攻失誤比 (AST/TO)", ast_to_display)}
                </div>
                """
                st.markdown(html_badges, unsafe_allow_html=True)

                note_val = p1_row.get('備註/短評', p1_row.get('備註 / 例行賽表現重點', '暫無備註'))
                st.info(f"💡 **教練與球探備註**：\n\n{note_val}")

        # ----------------- 模式 B：雙人對決 PK 模式 -----------------
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
                st.subheader("⚔️ 戰力六維度重疊對抗圖")
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
                st.subheader("📋 攻守數據正面對決表 (Tale of the Tape)")
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
        st.info("💡 尚未讀取到《全聯盟球員進階數據總表》，請確認專案中存在球員母表。")

# =========================================================================
# 分頁 5：進階數據辭典與公式附錄 (全新詳細附錄頁)
# =========================================================================
elif nav_selection == MENU_GLOSSARY:
    st.title("📚 TPBL 進階數據辭典與公式附錄 (Glossary & Formulas)")
    st.markdown("收錄職業籃球進階數據工程之計算原理、數學公式與球探判讀指引。")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 個人投籃與效率指標", 
        "⚡ 球權佔比與綜合表現", 
        "🏆 團隊四要素與攻防效率", 
        "⏱️ Play-by-Play 陣容分析"
    ])

    with tab1:
        st.header("🎯 個人投籃與得分效率 (Individual Shooting & Efficiency)")
        st.markdown(r"""
        ---
        ### 1. 有效命中率 (eFG%, Effective Field Goal Percentage)
        * **數學公式**：
        $$eFG\% = \frac{FGM + 0.5 \times 3PM}{FGA} \times 100\%$$
        * **數據意義**：傳統命中率 ($FG\%$) 的最大盲點在於將「三分球」與「兩分球」視為相同價值。有效命中率額外賦予三分球 1.5 倍的加成權重（因為三分球比兩分球多得 50% 分數）。
        * **球探判讀**：
          * 聯盟平均約為 **50% ~ 52%**。
          * 高於 **55%** 屬優質外線射手或高效禁區終結者。
          * 超過 **60%** 為頂級終結效率（如辛巴、沃許本、高效射手麥基）。

        ---
        ### 2. 真實命中率 (TS%, True Shooting Percentage)
        * **數學公式**：
        $$TS\% = \frac{PTS}{2 \times (FGA + 0.44 \times FTA)} \times 100\%$$
        * **數據意義**：衡量球員「每一次出手回合」折算後的終極得分效益（綜合兩分、三分與罰球）。
        * **為什麼係數是 0.44？**：正常情況下罰 2 球消耗 1 個進攻回合（理論係數為 0.5）。但考量到**進算加罰 (And-1)**、**三分球犯規罰 3 球**以及**技術犯規罰 1 球**不消耗回合，經 NBA 歷史大數據統計回測，乘上 **0.44** 能最精準估算罰球消耗的真實球權。
        * **球探判讀**：
          * 聯盟及格標準約為 **55%**。
          * 超過 **60%** 屬於高效率進攻武器。
          * 超過 **68%** 屬於聯盟頂級神獸（例如本季海神貝西里 $TS\% > 76\%$、國王克雷格 $TS\% > 66\%$）。

        ---
        ### 3. 三分出手佔比 (3PAr, 3-Point Attempt Rate)
        * **數學公式**：$$3PAr = \frac{3PA}{FGA} \times 100\%$$
        * **數據意義**：球員投籃出手中有多少比例是外線三分球。
        * **球探判讀**：
          * **$3PAr > 55\%$**：純外線射手或現代魔球後衛（如謝亞軒、麥基）。
          * **$3PAr < 15\%$**：傳統禁區型球員或衝擊籃下型鋒線（如高柏鎧、辛巴）。

        ---
        ### 4. 買犯罰球比 (FTr, Free Throw Attempt Rate)
        * **數學公式**：$$FTr = \frac{FTA}{FGA} \times 100\%$$
        * **數據意義**：每出手一次能換來多少次罰球機會，量化球員衝擊禁區製造犯規與對抗破壞力。
        * **球探判讀**：高於 **$40\%$** 代表極具殺傷力，國王肯刀爾與海神洛斯柯此項數據皆超過 $50\%$。
        """)

    with tab2:
        st.header("⚡ 球權佔比與綜合評分 (Usage & All-in-One Metrics)")
        st.markdown(r"""
        ---
        ### 1. 球權使用率 (USG%, Usage Percentage)
        * **數學公式**：
        $$USG\% = 100 \times \frac{(FGA + 0.44 \times FTA + TOV) \times (\text{Team\_MP} / 5)}{MP \times (\text{Team\_FGA} + 0.44 \times \text{Team\_FTA} + \text{Team\_TOV})}$$
        * **數據意義**：球員在場上時，這名球員以「投籃出手、造罰球、或失誤」終結球隊進攻回合的比例。
        * **球探判讀（戰術地位劃分）**：
          * **$USG\% \ge 28\%$**：**球隊第一戰術核心**（如林俊吉、洛斯柯、林庭謙）。
          * **$22\% \sim 27\%$**：主要先發得分點 / 第二持球副攻手（如基德、克雷格）。
          * **$< 15\%$**：底角射手、擋拆苦工或藍領綠葉。

        ---
        ### 2. 助攻失誤比 (AST/TO Ratio) 與 助攻率 (AST%)
        * **助攻失誤比**：$$\text{AST/TO} = \frac{AST}{TOV}$$
          * **球探標準**：主控後衛合格標準為 $2.0$。若高於 $3.0$（如陳振傑兩戰 0 失誤）代表控場視野極度冷靜安全。
        * **助攻率 (AST%)**：
        $$AST\% = 100 \times \frac{AST}{\left(\frac{MP}{\text{Team\_MP} / 5} \times \text{Team\_FGM}\right) - FGM}$$
          * 衡量球員在場時，隊友命中的進球有多少比例來自其助攻。

        ---
        ### 3. 單場綜合表現值 (GmSc, Game Score)
        * **數學公式 (Dean Oliver 權重模型)**：
        $$\begin{aligned}
        GmSc = & PTS + 0.4 \times FGM - 0.7 \times FGA - 0.4 \times (FTA - FTM) \\
        & + 0.7 \times OREB + 0.3 \times DREB + STL + 0.7 \times AST + 0.7 \times BLK - 0.4 \times PF - TOV
        \end{aligned}$$
        * **數據意義**：比傳統 EFF 更具統計學意義的單場評分。傳統 EFF 僅做單純加減，GmSc 給予投籃未進較輕扣分，但給予失誤重扣，並提升進攻籃板與防守阻攻之價值。
        * **球探判讀**：
          * **$10$ 分**：合格先發輪替表現。
          * **$20$ 分**：單場全明星級統治力。
          * **$30+$ 分**：單週 MVP / 統治級表現（如海神洛斯柯單場 $35.5$ 分）。

        ---
        ### 4. 戰力六維雷達圖之評分機制 (0-99 分標準化)
        * 本系統將球員的六大維度標準化為 2K 等級之 0~99 能力值：
          1. **得分產量**：以場均得分換算（基準線 $28.0$ 分為 99 滿分）。
          2. **真實效率**：以真實命中率 ($TS\%$) 換算（$72\%$ 為 99 滿分）。
          3. **外線威脅**：以三分命中數與佔比換算（場均 3.5 顆三分為 99 滿分）。
          4. **組織發動**：以助攻數與助攻失誤比換算（場均 6.0 助攻為 99 滿分）。
          5. **籃板保護**：以場均籃板數換算（場均 12.0 籃板為 99 滿分）。
          6. **防守破壞**：以抄截 ＋ 阻攻合計換算（場均 3.5 次為 99 滿分）。
        """)

    with tab3:
        st.header("🏆 團隊四要素與攻防效率 (Team Four Factors & Pace)")
        st.markdown(r"""
        ---
        ### 1. 團隊進攻回合數估算 (Possessions)
        * **數學公式**：
        $$Poss \approx \text{Team\_FGA} + 0.44 \times \text{Team\_FTA} - \text{Team\_OREB} + \text{Team\_TOV}$$
        * **邏輯拆解**：
          * 投籃出手 ($FGA$)、罰球 ($0.44 \times FTA$) 與失誤 ($TOV$) 都代表回合的結束。
          * **減去進攻籃板 ($-OREB$)**：搶到進攻籃板代表進攻回合「尚未結束並持續延續」，因此必須扣除以避免重複計算。

        ---
        ### 2. 比賽節奏 (Pace, 48 分鐘標準化)
        * **數學公式**：
        $$Pace = 48 \times \frac{Poss}{\text{Team\_MP} / 5}$$
        * **球探判讀**：
          * **$Pace > 105$**：跑轟快打旋風（如海神 $114.8$、夢想家 $104.5$）。
          * **$Pace < 98$**：半場陣地戰、重視禁區肉搏與防守壓迫（如國王 $104.6$、雲豹）。

        ---
        ### 3. 百回合進攻 / 防守 / 淨效率 (ORtg, DRtg, NetRtg)
        * **百回合進攻效率 ($ORtg$)**：$$ORtg = 100 \times \frac{\text{Team\_PTS}}{Poss}$$
        * **百回合防守效率 ($DRtg$)**：$$DRtg = 100 \times \frac{\text{Opp\_PTS}}{\text{Opp\_Poss}}$$
        * **百回合淨勝分 ($NetRtg$)**：$$NetRtg = ORtg - DRtg$$
        * **核心價值**：排除了比賽打快打慢的干擾。即使兩隊得分相同，回合數越少能拿到該分數的球隊，$ORtg$ 越高。

        ---
        ### 4. Dean Oliver 團隊籃球四要素 (Four Factors)
        NBA 數據教父 Dean Oliver 提出的決定比賽勝負四關鍵：
        1. **投籃有效命中率 (Team eFG%)**：決定進攻質量的核心（權重約 $40\%$）。
        2. **團隊失誤率 (Team TOV%)**：$$TOV\% = \frac{TOV}{FGA + 0.44 \times FTA + TOV}$$（權重約 $25\%$）。
        3. **進攻籃板爭搶率 (OREB%)**：$$\frac{\text{Team\_OREB}}{\text{Team\_OREB} + \text{Opp\_DREB}}$$（權重約 $20\%$）。
        4. **罰球率 (Team FTr)**：$$\frac{\text{Team\_FTA}}{\text{Team\_FGA}}$$（權重約 $15\%$）。
        """)

    with tab4:
        st.header("⏱️ Play-by-Play 陣容分析與 Stint 狀態機")
        st.markdown(r"""
        ---
        ### 1. 動態換人時間段 (Stint Engine) 運作原理
        * 傳統 Box Score 無法呈現「誰和誰同時在場」。
        * 狀態機從第 1 節 12:00 鎖定先發 10 人（主客各 5 人）。
        * 只要發生任何一次**換人 (Substitution)** 或**單節結束**，系統即刻切分出一個 **無換人時間段 (Stint)**。
        * 該時間段內發生的所有得分、失分、出手與回合，均精準歸屬於當下留在場上的 10 名球員。

        ---
        ### 2. 在場 / 不在場淨影響力 (On/Off Net Rating & Diff)
        * **$On\_NetRtg$**：該球員留在場上時，球隊每百回合淨勝（或淨輸）幾分。
        * **$Off\_NetRtg$**：該球員坐在板凳休息時，球隊每百回合淨勝幾分。
        * **賽季淨影響力 ($Diff$)**：
        $$Diff = On\_NetRtg - Off\_NetRtg$$
        * **球探判讀**：
          * **$Diff$ 為極大正值（如 $+5.0$ 以上）**：球隊不可或缺的真大腿（如夢想家陳振傑 $+5.6$、馬建豪 $+3.8$）。
          * **$Diff$ 為負值**：球員在場時球隊失血，或其下場時二陣替補追分效率更高。

        ---
        ### 3. 五人陣容 (5-Man Lineups) 與 雙洋將化學效應矩陣
        * **最佳五人陣容**：抓出共同上場時間 $\ge 10$ 分鐘的固定 5 人組，計算其百回合淨勝分 ($Lineup\ NetRtg$)，找出第四節終結比賽的最佳陣容。
        * **雙洋將化學效應**：評估雙外援搭檔是「內外互補拉開空間（Spacing 加成）」還是「雙中鋒塞車擠壓禁區」。
        """)
