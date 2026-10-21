import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
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

# 解決 Matplotlib 中文字體顯示問題（若有備用靜態繪圖需求）
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ----------------- 時間校正與安全工具函式 -----------------
def clean_time_display(val):
    """將被 Pandas / Excel 誤判為 Timedelta/天數的時間，校正還原回正常的 分:秒 (MM:SS)"""
    if pd.isna(val):
        return ""
        
    # 若被讀成 Timedelta 物件 (如 42 hours 41 mins 被自動進位為 1 day 18:41:00)
    if isinstance(val, (pd.Timedelta, datetime.timedelta)):
        tot_sec = val.total_seconds()
        orig_mins = int(tot_sec // 3600)
        orig_secs = int((tot_sec % 3600) // 60)
        return f"{orig_mins:02d}:{orig_secs:02d}"
    
    val_str = str(val).strip()
    
    # 處理字串型態的 "1 day, 18:41:00" 或 "2 days, 22:46:00"
    m_day = re.match(r'(\d+)\s*days?,?\s*(\d+):(\d+)(?::(\d+))?', val_str)
    if m_day:
        days = int(m_day.group(1))
        hours = int(m_day.group(2))
        mins = int(m_day.group(3))
        orig_mins = days * 24 + hours
        orig_secs = mins
        return f"{orig_mins:02d}:{orig_secs:02d}"
        
    # 處理 Google Sheets 匯出的 ISO 時間字串 (如 PT35H44M00.000S)
    m_pt = re.match(r'PT(\d+)H(\d+)M', val_str)
    if m_pt:
        return f"{int(m_pt.group(1)):02d}:{int(m_pt.group(2)):02d}"
    
    # 處理 "42:41:00" 或 "10:08:00" (去除末尾多餘的 :00 秒數)
    m_hms = re.match(r'^(\d+):(\d+):00$', val_str)
    if m_hms:
        return f"{int(m_hms.group(1)):02d}:{int(m_hms.group(2)):02d}"
        
    return val_str

def clean_dataframe_times(df):
    """掃描表格中所有與時間相關的欄位，批量套用時間校正"""
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        col_str = str(col)
        if any(k in col_str for k in ['時間', 'Time', 'time', '共同時間', '累計時間']):
            df[col] = df[col].apply(clean_time_display)
    return df

def deduplicate_columns(df):
    """徹底避免 PyArrow 拋出 Duplicate column names found 錯誤"""
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
    """跨平台不分大小寫尋找檔案"""
    keyword_clean = keyword.lower().strip()
    for fname in os.listdir('.'):
        fname_lower = fname.lower()
        if keyword_clean in fname_lower and fname_lower.endswith(('.xlsx', '.xls', '.csv')):
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

    header_a_idx = None
    header_b_idx = None

    for idx, row in df_raw.iterrows():
        row_str = " ".join([str(v) for v in row.values if pd.notna(v)])
        if "團隊總得分" in row_str or "百回合進攻效率" in row_str:
            header_a_idx = idx
        elif "高球權核心" in row_str or "戰力短評" in row_str:
            header_b_idx = idx

    if header_a_idx is not None:
        end_a = header_b_idx - 1 if (header_b_idx is not None and header_b_idx > header_a_idx) else header_a_idx + 8
        block_a = df_raw.iloc[header_a_idx + 1 : end_a].copy()
        block_a.columns = [str(c).strip() for c in df_raw.iloc[header_a_idx].tolist()]
        block_a = clean_dataframe_times(deduplicate_columns(block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)))
    else:
        block_a = clean_dataframe_times(deduplicate_columns(df_raw.dropna(how='all', axis=1)))

    if header_b_idx is not None:
        block_b = df_raw.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
        block_b.columns = [str(c).strip() for c in df_raw.iloc[header_b_idx].tolist()]
        block_b = deduplicate_columns(block_b.dropna(how='all', axis=1).dropna(how='all', axis=0))
    else:
        block_b = pd.DataFrame()

    return block_a, block_b

# ----------------- 提取各隊專屬 PBP 表格 -----------------
def extract_table_from_cell(df, r, c, max_rows=35):
    if r is None or c is None or r >= len(df):
        return pd.DataFrame()
    header_row = r + 1
    if header_row >= len(df):
        return pd.DataFrame()
    headers = []
    col_indices = []
    for cur_c in range(c, len(df.columns)):
        val = df.iloc[header_row, cur_c]
        if pd.isna(val) or str(val).strip() == "" or str(val).startswith("Unnamed"):
            break
        headers.append(str(val).strip())
        col_indices.append(cur_c)
    if not headers:
        return pd.DataFrame()
    data_rows = []
    for cur_r in range(header_row + 1, min(len(df), header_row + 1 + max_rows)):
        first_val = str(df.iloc[cur_r, c]).strip()
        if pd.isna(df.iloc[cur_r, c]) or first_val == "" or first_val == "nan" or first_val.startswith("【"):
            break
        data_rows.append([df.iloc[cur_r, col_idx] for col_idx in col_indices])
    res = pd.DataFrame(data_rows, columns=headers)
    res = clean_dataframe_times(res)
    return deduplicate_columns(res)

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
            val = str(df.iloc[r, c])
            if "On/Off" in val or "淨影響力總榜" in val:
                r_onoff, c_onoff = r, c
            elif "最佳五人陣容" in val or "五人陣容" in val:
                r_lineup, c_lineup = r, c
            elif "雙洋將" in val or "洋將搭檔" in val:
                r_duo, c_duo = r, c

    if r_onoff is not None:
        blocks['on_off'] = extract_table_from_cell(df, r_onoff, c_onoff)
    if r_lineup is not None:
        blocks['lineup'] = extract_table_from_cell(df, r_lineup, c_lineup)
    if r_duo is not None:
        blocks['duo'] = extract_table_from_cell(df, r_duo, c_duo)

    # 提取傳統攻守數據
    box_header_row = None
    for r in range(min(12, len(df))):
        row_str = " ".join([str(v) for v in df.iloc[r, :8] if pd.notna(v)])
        if "球員名" in row_str and ("得分" in row_str or "出賽" in row_str):
            box_header_row = r
            break

    if box_header_row is not None:
        end_box = r_onoff if (r_onoff is not None and c_onoff == 0 and r_onoff > box_header_row) else len(df)
        box_df = df.iloc[box_header_row + 1 : end_box].copy()
        
        # 欄位截取與去重
        raw_headers = [str(x).strip() for x in df.iloc[box_header_row].tolist()]
        valid_cols_idx = []
        seen_headers = set()
        for idx_h, h in enumerate(raw_headers):
            if "Unnamed" in h or h == "" or "nan" in h or "【" in h:
                break
            if h in seen_headers:
                break
            seen_headers.add(h)
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

# ----------------- 側邊欄導航設定 -----------------
st.sidebar.title("🏀 TPBL 數據總覽")
st.sidebar.caption("本機數據庫 (Excel Local Mode)")

MENU_SUMMARY = "🏆 7隊戰力評級與攻防總評"
MENU_SCATTER = "🎯 主力球員效率象限圖 (USG% vs TS%)"
MENU_PBP = "⚡ 各隊 PBP 陣容與 On/Off 深入分析"

nav_selection = st.sidebar.radio(
    "功能分頁選擇",
    [MENU_SUMMARY, MENU_SCATTER, MENU_PBP]
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
                                st.markdown(f"**{c_name}**：`{val}`")
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
        
        # 轉換數值型欄位
        for col in [pts_col, 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col and col in df_players.columns:
                df_players[col] = pd.to_numeric(df_players[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        # 自動百分比校正（若小於 1 則自動乘以 100）
        if df_players['USG%'].mean() > 0 and df_players['USG%'].mean() < 1.0:
            df_players['USG%'] = df_players['USG%'] * 100.0
        if df_players['TS%'].mean() > 0 and df_players['TS%'].mean() < 1.0:
            df_players['TS%'] = df_players['TS%'] * 100.0

        # 過濾控制項
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

            # 簡稱供標籤顯示
            filtered['簡稱'] = filtered['球員名'].apply(lambda x: str(x).split(' ')[0])

            # 使用 Plotly 繪製互動散佈圖（徹底避免 Matplotlib 中文方塊問題）
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

            # 平均十字參考輔助線
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

    # 模糊尋找該隊伍的專屬 Excel 檔案
    kw = selected_team.replace("福爾摩沙", "").replace("新北", "").replace("高雄全家", "").replace("臺北台新", "").replace("桃園台啤永豐", "").replace("新竹御嵿", "")
    target_file = find_file_fuzzy(kw) or find_file_fuzzy(selected_team)

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
