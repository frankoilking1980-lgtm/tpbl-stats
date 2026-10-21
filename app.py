import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import re

# ----------------- 頁面全域設定 -----------------
st.set_page_config(
    page_title="TPBL 職業籃球進階數據與球探分析系統",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 解決 Matplotlib 中文字體顯示問題
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ----------------- 寬鬆模糊搜尋檔案 -----------------
def find_file_fuzzy(keyword):
    """跨平台不分大小寫、不限副檔名尋找檔案"""
    keyword_clean = keyword.lower().strip()
    for fname in os.listdir('.'):
        fname_lower = fname.lower()
        if keyword_clean in fname_lower:
            if fname_lower.endswith(('.xlsx', '.xls', '.csv')):
                return fname
    return None

def load_any_file(filepath, sheet_name=0):
    """安全載入 Excel 或 CSV"""
    if not filepath or not os.path.exists(filepath):
        return None
    try:
        if filepath.lower().endswith('.csv'):
            return pd.read_csv(filepath)
        else:
            return pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception:
        return None

# ----------------- 總表拆解解析 -----------------
def parse_summary_sheet(filepath):
    df_raw = None
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
        block_a = block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)
    else:
        block_a = df_raw.dropna(how='all', axis=1)

    if header_b_idx is not None:
        block_b = df_raw.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
        block_b.columns = [str(c).strip() for c in df_raw.iloc[header_b_idx].tolist()]
        block_b = block_b.dropna(how='all', axis=1).dropna(how='all', axis=0)
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
    return pd.DataFrame(data_rows, columns=headers)

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
        box_df.columns = [str(x).strip() for x in df.iloc[box_header_row].tolist()]
        valid_cols = []
        for col_name in box_df.columns:
            if "Unnamed" in col_name or col_name == "" or "【" in col_name:
                break
            valid_cols.append(col_name)
        box_df = box_df[valid_cols].dropna(how='all', axis=0)
    else:
        box_df = pd.DataFrame()

    return blocks, box_df

# ----------------- 取得球員母表數據 -----------------
@st.cache_data(ttl=300)
def get_master_players():
    # 尋找全聯盟進階總表
    f_master = find_file_fuzzy("進階數據與戰力評級總表")
    if f_master:
        try:
            xls = pd.ExcelFile(f_master)
            for s in xls.sheet_names:
                df = pd.read_excel(f_master, sheet_name=s)
                if '球員名' in df.columns:
                    return df
                # header=1 嘗試
                df2 = pd.read_excel(f_master, sheet_name=s, header=1)
                if '球員名' in df2.columns:
                    return df2
        except Exception:
            pass

    # 嘗試從全聯盟 CSV 載入
    f_csv = find_file_fuzzy("全聯盟球員進階數據總表")
    if f_csv:
        try:
            return pd.read_csv(f_csv)
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
# 分頁 2：USG% vs TS% 散佈圖
# =========================================================================
elif nav_selection == MENU_SCATTER:
    st.title("🎯 球員效率象限圖：球權使用率 (USG%) vs 真實命中率 (TS%)")
    st.markdown("氣泡大小代表單場綜合表現值 (**GmSc**)，右上角為高產量且高效率之核心神獸。")

    df_players = get_master_players()

    if not df_players.empty and '球員名' in df_players.columns:
        # 自動對齊欄位名稱（相容「總得分」或「得分」）
        pts_col = '總得分' if '總得分' in df_players.columns else ('得分' if '得分' in df_players.columns else None)
        
        # 轉換數值型欄位
        for col in [pts_col, 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col and col in df_players.columns:
                df_players[col] = pd.to_numeric(df_players[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        # 側邊欄滑桿過濾器
        c1, c2 = st.columns(2)
        with c1:
            min_pts = st.slider("最低場均/總得分篩選 (PTS)", min_value=0, max_value=35, value=10)
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
            fig, ax = plt.subplots(figsize=(11, 6.5), dpi=130)

            categories = [
                ('洋將', '#1f77b4', 'o'),
                ('本土', '#ff7f0e', '^'),
                ('外籍生/洋將', '#2ca02c', 's'),
                ('外籍生/華裔', '#2ca02c', 's'),
                ('洋將/歸化', '#1f77b4', 'o'),
                ('華裔/本土', '#9467bd', 'D')
            ]

            size_col = 'GmSc' if ('GmSc' in filtered.columns and filtered['GmSc'].sum() > 0) else 'EFF'

            plotted_cats = set()
            for cat, color, marker in categories:
                sub = filtered[filtered[id_col] == cat] if id_col else pd.DataFrame()
                if not sub.empty:
                    sizes = np.maximum(sub[size_col] * 14, 45) if size_col in sub.columns else 60
                    ax.scatter(sub['USG%'], sub['TS%'], s=sizes, c=color, marker=marker, alpha=0.78, edgecolors='black', linewidth=1, label=cat)
                    plotted_cats.add(cat)

            if id_col:
                other_sub = filtered[~filtered[id_col].isin(plotted_cats)]
                if not other_sub.empty:
                    sizes = np.maximum(other_sub[size_col] * 14, 45) if size_col in other_sub.columns else 60
                    ax.scatter(other_sub['USG%'], other_sub['TS%'], s=sizes, c='#7f7f7f', marker='o', alpha=0.78, edgecolors='black', linewidth=1, label='其他')

            # 標註球員名字
            for _, r in filtered.iterrows():
                name_short = str(r['球員名']).split(' ')[0]
                pt_val = r[pts_col] if pts_col else 0
                ax.annotate(f"{name_short} ({pt_val:.1f}p)", (r['USG%'], r['TS%']), xytext=(5, 5), textcoords='offset points', fontsize=9)

            avg_u = filtered['USG%'].mean()
            avg_t = filtered['TS%'].mean()
            ax.axvline(avg_u, color='darkred', linestyle=':', alpha=0.6, label=f"平均 USG% ({avg_u:.1f}%)")
            ax.axhline(avg_t, color='gray', linestyle='--', alpha=0.6, label=f"平均 TS% ({avg_t:.1f}%)")

            ax.set_title("TPBL 例行賽主力球員：球權使用率 (USG%) vs 真實命中率 (TS%)", fontsize=13, pad=12)
            ax.set_xlabel("球權使用率 USG% (在場上終結球隊進攻回合比例 %)", fontsize=11)
            ax.set_ylabel("真實命中率 TS% (綜合兩分/三分/罰球得分效率 %)", fontsize=11)
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.legend(loc='lower left', frameon=True)
            plt.tight_layout()
            st.pyplot(fig)

            with st.expander("📋 查看象限圖球員詳細數據清單", expanded=False):
                st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ 目前篩選條件下無符合球員，或數據缺少 USG%/TS% 數值。")
    else:
        st.info("💡 尚未讀取到《全聯盟球員進階數據總表》。請確認專案中已上傳該檔案。")

# =========================================================================
# 分頁 3：各隊 PBP 陣容與 On/Off 深入分析
# =========================================================================
elif nav_selection == MENU_PBP:
    st.title("⚡ 各隊 Play-by-Play 陣容組合與主力 On/Off 淨勝分")
    st.markdown("由官方逐球時間段 (Stints) 精確解析各隊【賽季累積主力 On/Off 總榜】、【賽季最佳五人陣容】與【雙洋將化學效應】。")

    team_options = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    selected_team = st.selectbox("選擇要深入分析的球隊", team_options)

    # 模糊尋找該隊伍的專屬 Excel 檔案
    # 支援「夢想家」、「國王」、「海神」等關鍵字匹配
    kw = selected_team.replace("福爾摩沙", "").replace("新北", "").replace("高雄全家", "").replace("臺北台新", "").replace("桃園台啤永豐", "").replace("新竹御嵿", "")
    target_file = find_file_fuzzy(kw) or find_file_fuzzy(selected_team)

    if target_file:
        blocks, box_df = extract_pbp_blocks(target_file)

        # 1. 顯示主力 On/Off 淨影響力總榜
        st.subheader(f"📊 {selected_team} — 主力 On/Off 淨影響力總榜")
        if 'on_off' in blocks and not blocks['on_off'].empty:
            st.dataframe(blocks['on_off'], use_container_width=True, hide_index=True)
        else:
            st.info(f"💡 {selected_team} 暫無 On/Off 統計資料（待後續賽程展開即時納入）。")

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
        st.warning(f"⚠️ 找不到 {selected_team} 的 Excel 檔案。請確認專案中包含對應名稱的 Excel 檔。")
