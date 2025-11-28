import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 設定頁面 ---
st.set_page_config(page_title="產線戰情室", layout="wide")
st.title("🏭 產線動態儀表板")

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
cols_to_check = ['組裝完', '出貨完', '前線門檻', '前線收到']
for col in cols_to_check:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# 計算 [缺] 與 [加]
# 缺 = 門檻 - 收到 (若小於 0 則顯示 0)
df['缺'] = df.apply(lambda x: max(0, x['前線門檻'] - x['前線收到']), axis=1)
# 加 = 收到 - 門檻 (若小於 0 則顯示 0)
df['加'] = df.apply(lambda x: max(0, x['前線收到'] - x['前線門檻']), axis=1)

# --- 3. 介面顯示與互動邏輯 ---

# 為了在手機上好按，我們不使用標準 Table，而是用卡片式或條列式佈局
# 這裡使用簡易的 Grid 系統模擬表格

# 顯示表頭
headers = st.columns([1.5, 1, 1, 1, 1, 0.8, 0.8])
with headers[0]: st.markdown("**產品**")
with headers[1]: st.markdown("組裝")
with headers[2]: st.markdown("出貨")
with headers[3]: st.markdown("門檻")
with headers[4]: st.markdown("收到")
with headers[5]: st.markdown("🔴缺")
with headers[6]: st.markdown("🟢加")

st.divider()

# 針對每一項產品產生一行控制列
for index, row in df.iterrows():
    # 建立 7 個欄位
    cols = st.columns([1.5, 1, 1, 1, 1, 0.8, 0.8])
    
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

    # --- 欄位：組裝完 ---
    with cols[1]:
        st.write(f"{row['組裝完']}")
        c1, c2 = st.columns(2)
        if c1.button("➕", key=f"as_p_{index}"): update_val(index, '組裝完', 1)
        if c2.button("➖", key=f"as_m_{index}"): update_val(index, '組裝完', -1)

    # --- 欄位：出貨完 ---
    with cols[2]:
        st.write(f"{row['出貨完']}")
        c1, c2 = st.columns(2)
        if c1.button("➕", key=f"sh_p_{index}"): update_val(index, '出貨完', 1)
        if c2.button("➖", key=f"sh_m_{index}"): update_val(index, '出貨完', -1)

    # --- 欄位：前線門檻 ---
    with cols[3]:
        st.write(f"{row['前線門檻']}")
        c1, c2 = st.columns(2)
        if c1.button("➕", key=f"th_p_{index}"): update_val(index, '前線門檻', 1)
        if c2.button("➖", key=f"th_m_{index}"): update_val(index, '前線門檻', -1)

    # --- 欄位：前線收到 ---
    with cols[4]:
        st.write(f"{row['前線收到']}")
        c1, c2 = st.columns(2)
        if c1.button("➕", key=f"rc_p_{index}"): update_val(index, '前線收到', 1)
        if c2.button("➖", key=f"rc_m_{index}"): update_val(index, '前線收到', -1)

    # --- 自動計算欄位 (唯讀) ---
    with cols[5]:
        st.markdown(f"<span style='color:red; font-weight:bold'>{row['缺']}</span>", unsafe_allow_html=True)
    
    with cols[6]:
        st.markdown(f"<span style='color:green; font-weight:bold'>{row['加']}</span>", unsafe_allow_html=True)
    
    st.divider()

# 手動刷新按鈕 (雖然按任何按鈕都會刷新，但有時候別人更新了你需要手動刷)
if st.button("🔄 刷新即時數據"):
    st.rerun()
