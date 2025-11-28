import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 設定頁面 ---
st.set_page_config(page_title="產線戰情室", layout="wide")
st.title("🏭 產線動態儀表板")

# 初始化選取狀態
if 'selected' not in st.session_state:
    st.session_state['selected'] = None

# 確保 `前線門檻` 不會被當作可選取欄位（若先前意外被選中，清除選取）
if st.session_state.get('selected') and st.session_state['selected'][1] == '前線門檻':
    st.session_state['selected'] = None

# --- 自訂樣式：縮小 +/- 按鈕、放大數字、highlight 樣式 ---
st.markdown("""
<style>
/* 固定 +/- 按鈕為方形並置中符號，避免與左右欄位黏在一起 */
.stButton>button {font-size:12px; padding:2px 6px; min-width:30px; height:28px; display:inline-block; box-sizing:border-box; white-space:nowrap}
.stButton>button>span {line-height:28px; display:block; text-align:center}
.big-num {font-size:22px; font-weight:700;}
.stMarkdown p {margin:0; padding:0}
.big-num {padding:2px 0}
.stApp [data-testid="stVerticalBlock"] > div {padding:2px 0}
.red-highlight {background:#ffd6d6; color:#a00; font-weight:700; padding:4px 6px; border-radius:4px; display:inline-block}
.green-highlight {background:#e6ffed; color:#0a6; font-weight:700; padding:4px 6px; border-radius:4px; display:inline-block}
.threshold-highlight {background:#e6f0ff; color:#024; font-weight:800; padding:6px 8px; border-radius:6px; display:inline-block}
.muted-num {color: #666; font-weight:600;}

/* 手機響應式：窄螢幕時把按鈕縮小，數字微調 */
@media (max-width: 600px) {
    .stButton>button { font-size:10px !important; padding:0 !important; min-width:22px !important; width:26px !important; height:24px !important; }
    .stButton>button>span { line-height:24px !important; }
    .big-num { font-size:18px !important; }
    .red-highlight, .green-highlight { font-size:14px !important; padding:2px 4px !important; }
    /* 讓欄位的數字在手機上換行顯示，避免擁擠 */
    .stMarkdown p, .stMarkdown div { word-break: keep-all; }
}
</style>
""", unsafe_allow_html=True)
# --- 1. 連接 Google Sheets (當作資料庫) ---
# 這是 Streamlit 官方支援的連接器，能讀也能寫
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取現有資料 (設定 TTL 為 0 以確保每次按按鈕都拿到最新數據)
try:
    df = conn.read(worksheet="Sheet1", ttl=0)
except:
    st.error("無法連接資料庫，請檢查 Google Sheets 設定")
    st.stop()

# --- 2. 定義計算邏輯 ---
# 確保數值欄位是數字型態，避免錯誤
cols_to_check = ['組裝完', '出貨完', '前線門檻', '前線收到', '完成']
for col in cols_to_check:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 若原始 Sheet 沒有 `完成` 欄，確保存在（上面會建立為 0）
if '完成' not in df.columns:
    df['完成'] = 0
# 計算 [缺] 與 [加]
# 現在改為以 `完成` 欄位做為基準
# 缺 = 門檻 - 完成 (若小於 0 則顯示 0)
df['缺'] = df.apply(lambda x: max(0, x['前線門檻'] - x['完成']), axis=1)
# 加 = 完成 - 門檻 (若小於 0 則顯示 0)
df['加'] = df.apply(lambda x: max(0, x['完成'] - x['前線門檻']), axis=1)

# --- 3. 介面顯示與互動邏輯 ---

# 為了在手機上好按，我們不使用標準 Table，而是用卡片式或條列式佈局
# 這裡使用簡易的 Grid 系統模擬表格

# 顯示表頭（新增 `完成` 欄位）
headers = st.columns([1.5, 1, 1, 1, 1, 1, 0.8, 0.8])
with headers[0]: st.markdown("**產品**")
with headers[1]: st.markdown("組裝")
with headers[2]: st.markdown("出貨")
with headers[3]: st.markdown("門檻")
with headers[4]: st.markdown("收到")
with headers[5]: st.markdown("完成")
with headers[6]: st.markdown("🔴缺")
with headers[7]: st.markdown("🟢加")

st.divider()

# 針對每一項產品產生一行控制列
for index, row in df.iterrows():
    # 建立 8 個欄位（包含 `完成`）
    cols = st.columns([1.5, 1, 1, 1, 1, 1, 0.8, 0.8])
    
    # 產品名稱
    with cols[0]:
        st.write(f"**{row['產品']}**")
    
    # 定義按鈕功能的 Helper function
    def update_val(idx, col_name, delta):
        # 更新 DataFrame
        new_val = max(0, df.at[idx, col_name] + delta) # 防止變成負數
        df.at[idx, col_name] = new_val
        # 寫回 Google Sheets
        conn.update(worksheet="Sheet1", data=df)
        # 重新整理頁面顯示最新狀態
        st.rerun()

    def local_modify(idx, col_name, delta):
        # 僅修改本地 DataFrame，等待使用者按下「更新數據」時寫回
        new_val = max(0, df.at[idx, col_name] + delta)
        df.at[idx, col_name] = new_val
        # 立即反映 UI，但不寫回遠端
        st.experimental_rerun()

    # --- 欄位：組裝完（點選以選取） ---
    with cols[1]:
        sel_key = f"sel_組裝完_{index}"
        is_sel = st.session_state.get('selected') == (index, '組裝完')
        label = f"🔘 {row['組裝完']}" if is_sel else f"{row['組裝完']}"
        if st.button(label, key=sel_key):
            st.session_state['selected'] = (index, '組裝完')

    # --- 欄位：出貨完（點選以選取） ---
    with cols[2]:
        sel_key = f"sel_出貨完_{index}"
        is_sel = st.session_state.get('selected') == (index, '出貨完')
        label = f"🔘 {row['出貨完']}" if is_sel else f"{row['出貨完']}"
        if st.button(label, key=sel_key):
            st.session_state['selected'] = (index, '出貨完')

    # --- 欄位：前線門檻（點選以選取） ---
    with cols[3]:
        # 永遠顯示帶顏色背景的門檻數字；不提供選取按鈕（門檻通常為固定參數）
        st.markdown(f"<div class='threshold-highlight'>{row['前線門檻']}</div>", unsafe_allow_html=True)

    # --- 欄位：前線收到（點選以選取） ---
    with cols[4]:
        sel_key = f"sel_前線收到_{index}"
        is_sel = st.session_state.get('selected') == (index, '前線收到')
        label = f"🔘 {row['前線收到']}" if is_sel else f"{row['前線收到']}"
        if st.button(label, key=sel_key):
            st.session_state['selected'] = (index, '前線收到')

    # --- 欄位：完成（點選以選取） ---
    with cols[5]:
        sel_key = f"sel_完成_{index}"
        is_sel = st.session_state.get('selected') == (index, '完成')
        label = f"🔘 {row['完成']}" if is_sel else f"{row['完成']}"
        if st.button(label, key=sel_key):
            st.session_state['selected'] = (index, '完成')

    # --- 自動計算欄位 (唯讀) ---
    # 顯示缺：如果 >0 則 highlight 紅色背景，否則淡色
    with cols[6]:
        if row['缺'] > 0:
            st.markdown(f"<div class='red-highlight'>{row['缺']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='big-num muted-num'>{row['缺']}</div>", unsafe_allow_html=True)

    # 顯示加：如果 >0 則 highlight 綠色背景，否則淡色
    with cols[7]:
        if row['加'] > 0:
            st.markdown(f"<div class='green-highlight'>{row['加']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='big-num muted-num'>{row['加']}</div>", unsafe_allow_html=True)
    
    st.divider()

# 操作區：用戶先點選表格中的數字（會標示 🔘），再用下方按鈕調整數值
st.divider()
st.markdown("**操作區：選取一個欄位後，使用下方的按鈕修改（按 +/- 會立即寫回遠端）。按下「刷新數據」可重新載入 Google Sheets 的最新資料。**")
g_sel, g_minus, g_plus, g_refresh = st.columns([4,1,1,1])
sel = st.session_state.get('selected')
with g_sel:
    if sel:
        r, c = sel
        st.markdown(f"**修改中項目：** {df.at[r, '產品']} — **{c}** = **{df.at[r, c]}**")
    else:
        st.markdown("未選取任何欄位，請點表格中的數字以開始")
with g_minus:
    if st.button("➖", key="global_minus"):
        if not sel:
            st.warning("請先點選表格中的數字以選取欄位")
        else:
            # 直接寫回遠端
            update_val(sel[0], sel[1], -1)
with g_plus:
    if st.button("➕", key="global_plus"):
        if not sel:
            st.warning("請先點選表格中的數字以選取欄位")
        else:
            # 直接寫回遠端
            update_val(sel[0], sel[1], 1)
with g_refresh:
    if st.button("刷新數據", key="global_refresh"):
        # 重新載入遠端資料（script 會從頭執行並呼叫 conn.read）
        st.experimental_rerun()

# （已移除重複的全域刷新按鈕，請使用上方的「刷新數據」）
