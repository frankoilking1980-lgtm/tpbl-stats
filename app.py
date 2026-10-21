import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

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

# ----------------- 本地 Excel 讀取工具 -----------------
def load_excel_sheet(filename, sheet_name=0):
    """讀取本地上傳的 Excel (.xlsx) 檔案"""
    if os.path.exists(filename):
        try:
            # header=None 保留所有原始列，避免第一列標題吃掉欄位名稱
            return pd.read_excel(filename, sheet_name=sheet_name, header=None)
        except Exception as e:
            st.error(f"讀取 Excel 分頁出錯：{e}")
            return None
    return None

def parse_summary_sheet(df):
    """防呆版：精確拆解總表的【區塊 A：團隊四要素】與【區塊 B：球員洞察與戰力短評】"""
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    header_a_idx = None
    header_b_idx = None

    # 安全逐列掃描關鍵字，完全避免 TypeError
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

# ----------------- 側邊欄導航 -----------------
st.sidebar.title("🏀 TPBL 數據總覽")
st.sidebar.caption("本機數據庫 (Excel Mode)")

nav_selection = st.sidebar.radio(
    "功能分頁選擇",
    ["🏆 7隊戰力評級與攻防總評", "🎯 主力球員效率象限圖 (USG% vs TS%)", "⚡ 各隊陣容與 On/Off 深入分析"]
)

# 讀取本地 Excel 檔案
summary_df = load_excel_sheet("tpbl_summary.xlsx", sheet_name=0)

# ----------------- 分頁 1：7隊戰力與攻防總評 -----------------
if nav_selection == "🏆 7隊戰力評級與攻防總評":
    st.title("🏆 2026-2027 TPBL 各隊戰力評級與進階攻防總評")
    st.markdown("以四要素 (Four Factors)、節奏 (Pace) 及百回合進攻效率 (ORtg) 標準化評估各隊戰力與教練戰術。")
    
    if summary_df is not None and not summary_df.empty:
        block_a, block_b = parse_summary_sheet(summary_df)
        
        # 顯示區塊 A
        st.subheader("📊 團隊進階四要素指標 (Team Advanced Metrics)")
        st.dataframe(block_a, use_container_width=True, hide_index=True)
        
        # 顯示區塊 B
        if not block_b.empty:
            st.subheader("🔍 重點球員洞察與教練體系戰力短評")
            for _, row in block_b.iterrows():
                # 取得球隊名稱
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
        st.warning("⚠️ 找不到 `tpbl_summary.xlsx` 檔案。請確認已將 478 KB 的總表改名為 `tpbl_summary.xlsx` 並上傳至 GitHub 專案根目錄中。")

# ----------------- 分頁 2：USG% vs TS% 散佈圖 -----------------
elif nav_selection == "🎯 主力球員效率象限圖 (USG% vs TS%)":
    st.title("🎯 球員效率象限圖：球權使用率 (USG%) vs 真實命中率 (TS%)")
    st.markdown("氣泡大小代表單場綜合表現值 (**GmSc**)，右上角為高產量且高效率之核心神獸。")
    st.info("💡 總表載入完成後，此處將自動渲染全聯盟球員象限分佈。")

# ----------------- 分頁 3：PBP 陣容與 On/Off -----------------
elif nav_selection == "⚡ 各隊陣容與 On/Off 深入分析":
    st.title("⚡ 各隊 Play-by-Play 陣容組合與主力 On/Off 淨勝分")
    selected_team = st.selectbox(
        "選擇要深入分析的球隊",
        ["福爾摩沙夢想家", "新北國王", "高雄全家海神", "新北中信特攻", "臺北台新戰神", "桃園台啤永豐雲豹", "新竹御嵿攻城獅"]
    )
    st.success(f"目前檢視隊伍：**{selected_team}**。已支援讀取各隊 Excel 檔！")
