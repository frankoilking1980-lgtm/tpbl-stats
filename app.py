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

# ----------------- 工具函式 -----------------
def load_excel_raw(filepath, sheet_name=0):
    """讀取 Excel 檔案，不預設表頭以保留最完整的原始結構"""
    if os.path.exists(filepath):
        try:
            return pd.read_excel(filepath, sheet_name=sheet_name, header=None)
        except Exception:
            return None
    return None

def find_file_by_keyword(keyword):
    """根據關鍵字自動尋找專案資料夾中的對應 Excel 檔案"""
    matches = glob.glob(f"*{keyword}*.xlsx")
    if matches:
        return matches[0]
    return None

def parse_summary_sheet(df):
    """拆解 7 隊戰力總表的區塊 A 與區塊 B"""
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    header_a_idx = None
    header_b_idx = None

    for idx, row in df.iterrows():
        try:
            row_str = " ".join([str(val) for val in row.values if pd.notna(val)])
        except Exception:
            continue
            
        if "團隊總得分" in row_str or "百回合進攻效率" in row_str:
            header_a_idx = idx
        elif "高球權核心" in row_str or "戰力短評" in row_str:
            header_b_idx = idx

    # 提取區塊 A
    if header_a_idx is not None:
        end_a = header_b_idx - 1 if (header_b_idx is not None and header_b_idx > header_a_idx) else header_a_idx + 8
        block_a = df.iloc[header_a_idx + 1 : end_a].copy()
        block_a.columns = [str(c).strip() for c in df.iloc[header_a_idx].tolist()]
        block_a = block_a.dropna(how='all', axis=1).dropna(how='all', axis=0)
    else:
        block_a = df.dropna(how='all', axis=1)

    # 提取區塊 B
    if header_b_idx is not None:
        block_b = df.iloc[header_b_idx + 1 : header_b_idx + 8].copy()
        block_b.columns = [str(c).strip() for c in df.iloc[header_b_idx].tolist()]
        block_b = block_b.dropna(how='all', axis=1).dropna(how='all', axis=0)
    else:
        block_b = pd.DataFrame()

    return block_a, block_b

def extract_table_from_cell(df, r, c, max_rows=35):
    """自指定 (r, c) 座標自動提取區塊表格（同時支援水平與垂直排列排版）"""
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

def extract_pbp_blocks(df):
    """從球隊數據表中自動尋找並提取三大 PBP 進階分析表格"""
    if df is None or df.empty:
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
        
    # 提取左側傳統球員攻守數據
    box_header_row = None
    for r in range(min(10, len(df))):
        row_str = " ".join([str(v) for v in df.iloc[r, :10] if pd.notna(v)])
        if "球員名" in row_str and "得分" in row_str:
            box_header_row = r
            break
            
    if box_header_row is not None:
        end_box = r_onoff if (r_onoff is not None and c_onoff == 0 and r_onoff > box_header_row) else len(df)
        box_df = df.iloc[box_header_row + 1 : end_box].copy()
        box_df.columns = [str(x).strip() for x in df.iloc[box_header_row].tolist()]
        # 只保留基本攻守欄位（截斷至右側分隔處）
        valid_cols = []
        for col_name in box_df.columns:
            if "Unnamed" in col_name or col_name == "" or "【" in col_name:
                break
            valid_cols.append(col_name)
        box_df = box_df[valid_cols].dropna(how='all', axis=0)
    else:
        box_df = pd.DataFrame()

    return blocks, box_df

# ----------------- 全聯盟球員數據整合讀取 -----------------
@st.cache_data(ttl=300)
def load_all_players_data():
    """自動掃描所有球員數據表，彙整全聯盟球員進行象限分析"""
    # 優先嘗試讀取全聯盟球員進階總表
    master_file = find_file_by_keyword("進階數據與戰力評級總表")
    if master_file:
        try:
            xls = pd.ExcelFile(master_file)
            for sname in xls.sheet_names:
                if "球員" in sname:
                    df = pd.read_excel(master_file, sheet_name=sname)
                    if len(df) > 10 and '球員名' in df.columns:
                        return df
        except Exception:
            pass
            
    # 若無，則從各隊 Excel 的平均數據分頁中自動萃取
    team_names = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    all_dfs = []
    for tname in team_names:
        fpath = find_file_by_keyword(tname)
        if fpath:
            try:
                xls = pd.ExcelFile(fpath)
                target_sheet = 0
                for s in xls.sheet_names:
                    if "平均" in s:
                        target_sheet = s
                        break
                df_raw = pd.read_excel(fpath, sheet_name=target_sheet, header=None)
                _, b_df = extract_pbp_blocks(df_raw)
                if not b_df.empty:
                    b_df['球隊'] = tname
                    all_dfs.append(b_df)
            except Exception:
                continue
                
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

# ----------------- 側邊欄導航 -----------------
st.sidebar.title("🏀 TPBL 數據總覽")
st.sidebar.caption("本機數據庫 (Excel Local Mode)")

nav_selection = st.sidebar.radio(
    "功能分頁選擇",
    ["🏆 7隊戰力評級與攻防總評", "🎯 主力球員效率象限圖 (USG% vs TS%)", "⚡ 各隊 PBP 陣容與 On/Off 深入分析"]
)

summary_file = find_file_by_keyword("summary") or find_file_by_keyword("7隊戰力")
summary_df = load_excel_raw(summary_file, sheet_name=0) if summary_file else None

# =========================================================================
# 分頁 1：7隊戰力評級與攻防總評
# =========================================================================
if nav_selection == "🏆 7隊戰力評級與攻防總評":
    st.title("🏆 2026-2027 TPBL 各隊戰力評級與進階攻防總評")
    st.markdown("以四要素 (Four Factors)、節奏 (Pace) 及百回合進攻效率 (ORtg) 標準化評估各隊戰力與教練戰術。")
    
    if summary_df is not None and not summary_df.empty:
        block_a, block_b = parse_summary_sheet(summary_df)
        
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
        st.warning("⚠️ 找不到總表檔案。請確認專案中存在 `tpbl_summary.xlsx`。")

# =========================================================================
# 分頁 2：USG% vs TS% 散佈圖
# =========================================================================
elif nav_selection == "🎯 主力球員效率象限圖 (USG% vs TS%)":
    st.title("🎯 球員效率象限圖：球權使用率 (USG%) vs 真實命中率 (TS%)")
    st.markdown("氣泡大小代表單場綜合表現值 (**GmSc**)，右上角為高產量且高效率之核心神獸。")

    all_players = load_all_players_data()
    
    if not all_players.empty and '得分' in all_players.columns:
        df_p = all_players.copy()
        
        # 轉換數值型欄位
        for col in ['得分', 'USG%', 'TS%', 'GmSc', 'EFF']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        # 側邊欄滑桿過濾器
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_pts = st.slider("最低場均得分篩選 (PTS)", min_value=0, max_value=30, value=8)
        with col_f2:
            identity_filter = st.multiselect(
                "球員身分篩選", 
                ["全部"] + list(df_p['本土/洋將'].dropna().unique()) if '本土/洋將' in df_p.columns else ["全部"],
                default=["全部"]
            )

        filtered = df_p[df_p['得分'] >= min_pts].copy()
        if "全部" not in identity_filter and '本土/洋將' in filtered.columns:
            filtered = filtered[filtered['本土/洋將'].isin(identity_filter)]

        if not filtered.empty and 'USG%' in filtered.columns and 'TS%' in filtered.columns:
            # 確保有 GmSc 用於氣泡大小
            if 'GmSc' not in filtered.columns or filtered['GmSc'].sum() == 0:
                filtered['GmSc'] = filtered['EFF']

            fig, ax = plt.subplots(figsize=(11, 6.5), dpi=130)
            
            categories = [
                ('洋將', '#1f77b4', 'o'),
                ('本土', '#ff7f0e', '^'),
                ('外籍生/洋將', '#2ca02c', 's'),
                ('洋將/歸化', '#1f77b4', 'o'),
                ('華裔/本土', '#9467bd', 'D')
            ]
            
            plotted_cats = set()
            for cat, color, marker in categories:
                sub = filtered[filtered['本土/洋將'] == cat] if '本土/洋將' in filtered.columns else pd.DataFrame()
                if not sub.empty:
                    ax.scatter(
                        sub['USG%'], sub['TS%'],
                        s=np.maximum(sub['GmSc'] * 14, 45),
                        c=color, marker=marker, alpha=0.78, edgecolors='black', linewidth=1, label=cat
                    )
                    plotted_cats.add(cat)

            # 補齊其他未列在清單的身分
            if '本土/洋將' in filtered.columns:
                other_sub = filtered[~filtered['本土/洋將'].isin(plotted_cats)]
                if not other_sub.empty:
                    ax.scatter(
                        other_sub['USG%'], other_sub['TS%'],
                        s=np.maximum(other_sub['GmSc'] * 14, 45),
                        c='#7f7f7f', marker='o', alpha=0.78, edgecolors='black', linewidth=1, label='其他'
                    )

            # 標註球員姓名與得分
            for _, row in filtered.iterrows():
                name_short = str(row.get('球員名', '')).split(' ')[0]
                ax.annotate(
                    f"{name_short} ({row['得分']:.1f}p)",
                    (row['USG%'], row['TS%']),
                    xytext=(5, 5), textcoords='offset points', fontsize=9
                )

            avg_usg = filtered['USG%'].mean()
            avg_ts = filtered['TS%'].mean()
            ax.axvline(avg_usg, color='darkred', linestyle=':', alpha=0.6, label=f"平均 USG% ({avg_usg:.1f}%)")
            ax.axhline(avg_ts, color='gray', linestyle='--', alpha=0.6, label=f"平均 TS% ({avg_ts:.1f}%)")

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
            st.warning("⚠️ 目前球員數據中尚未計算或缺少 USG% 與 TS% 欄位。")
    else:
        st.info("💡 尚未偵測到球員明細表。請確認專案中包含各隊的球員數據 Excel 檔。")

# =========================================================================
# 分頁 3：各隊 PBP 陣容與 On/Off 深入分析
# =========================================================================
elif nav_selection == "⚡ 各隊陣容與 On/Off 深入分析":
    st.title("⚡ 各隊 Play-by-Play 陣容組合與主力 On/Off 淨勝分")
    st.markdown("由官方逐球時間段 (Stints) 精確解析各隊【賽季累積主力 On/Off 總榜】、【賽季最佳五人陣容】與【雙洋將化學效應】。")

    team_options = ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    selected_team = st.selectbox("選擇要深入分析的球隊", team_options)

    # 搜尋對應的球隊檔案
    team_file = find_file_by_keyword(selected_team)
    
    if team_file:
        xls = pd.ExcelFile(team_file)
        # 優先讀取平均數據工作表
        target_sheet = 0
        for s in xls.sheet_names:
            if "平均" in s:
                target_sheet = s
                break
                
        df_raw = pd.read_excel(team_file, sheet_name=target_sheet, header=None)
        blocks, box_df = extract_pbp_blocks(df_raw)
        
        # 1. 顯示主力 On/Off 淨影響力總榜
        st.subheader(f"📊 {selected_team} — 主力 On/Off 淨影響力總榜")
        if 'on_off' in blocks and not blocks['on_off'].empty:
            st.dataframe(blocks['on_off'], use_container_width=True, hide_index=True)
        else:
            st.info("該隊暫無 On/Off 統計資料。")
            
        # 2. 顯示最佳五人陣容
        st.subheader(f"🏆 {selected_team} — 最佳五人陣容 (Top Lineups)")
        if 'lineup' in blocks and not blocks['lineup'].empty:
            st.dataframe(blocks['lineup'], use_container_width=True, hide_index=True)
        else:
            st.info("該隊暫無五人陣容統計資料。")
            
        # 3. 顯示雙洋將搭配矩陣
        st.subheader(f"🤝 {selected_team} — 雙洋將化學效應矩陣")
        if 'duo' in blocks and not blocks['duo'].empty:
            st.dataframe(blocks['duo'], use_container_width=True, hide_index=True)
        else:
            st.info("該隊暫無雙洋將搭配資料。")
            
        # 4. 顯示基礎球員攻守數據
        if not box_df.empty:
            with st.expander("📋 查看球隊基礎攻守數據表 (Box Score)", expanded=False):
                st.dataframe(box_df, use_container_width=True, hide_index=True)
    else:
        st.warning(f"⚠️ 專案中找不到 {selected_team} 的 Excel 檔案。請確認檔名包含球隊名稱。")
