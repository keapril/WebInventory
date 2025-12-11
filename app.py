# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta, timezone

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="庫存管理系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 常數與路徑設定 ---
DATA_FILE = "inventory_data.csv"
LOG_FILE = "transaction_log.csv"
IMAGE_DIR = "images"

# 確保圖片資料夾存在
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- 3. 核心函數區 ---

def get_taiwan_time():
    """取得台灣時間 (GMT+8) 字串"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    """讀取庫存資料"""
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except:
            pass
    return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock"])

def load_log():
    """讀取紀錄資料"""
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            pass
    return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def save_log(entry):
    df_log = load_log()
    new_entry = pd.DataFrame([entry])
    df_log = pd.concat([df_log, new_entry], ignore_index=True)
    df_log.to_csv(LOG_FILE, index=False)

def save_uploaded_image(uploaded_file, sku):
    """儲存上傳的圖片並回傳檔名"""
    if uploaded_file is None:
        return None
    file_ext = os.path.splitext(uploaded_file.name)[1]
    new_filename = f"{sku}{file_ext}"
    save_path = os.path.join(IMAGE_DIR, new_filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return new_filename

# --- 4. 主程式介面 ---

def main():
    with st.sidebar:
        st.title("庫存管理系統")
        st.write("使用者：管理員 (Admin)")
        st.markdown("---")
        page = st.radio("功能選單", [
            "庫存查詢", 
            "入庫作業", 
            "出庫作業", 
            "品項維護", 
            "異動紀錄"
        ])

    if page == "庫存查詢":
        page_search()
    elif page == "入庫作業":
        page_operation("入庫")
    elif page == "出庫作業":
        page_operation("出庫")
    elif page == "品項維護":
        page_maintenance()
    elif page == "異動紀錄":
        page_reports()

# --- 各頁面子程式 ---

def page_search():
    st.subheader("庫存查詢")
    search_term = st.text_input("請輸入 SKU 或 品名關鍵字")
    
    if search_term:
        df = load_data()
        mask = df['SKU'].astype(str).str.contains(search_term, case=False, na=False) | \
               df['Name'].astype(str).str.contains(search_term, case=False, na=False)
        result = df[mask]
        
        if not result.empty:
            for _, row in result.iterrows():
                with st.container():
                    st.markdown("---")
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        img_name = row['ImageFile']
                        if pd.notna(img_name) and str(img_name).strip() != "":
                            img_path = os.path.join(IMAGE_DIR, str(img_name))
                            if os.path.exists(img_path) and os.path.isfile(img_path):
                                st.image(img_path, width=300)
                            else:
                                st.warning(f"[!] 找不到圖片檔案: {img_name}")
                        else:
                            st.info("未上傳圖片")
                    with c2:
                        st.subheader(row['Name'])
                        st.text(f"SKU: {row['SKU']}")
                        st.text(f"分類: {row['Category']}")
                        st.metric("目前庫存", row['Stock'])
        else:
            st.info("查無資料")

def page_operation(op_type):
    st.subheader(f"{op_type}作業")
    
    if "scan_input" not in st.session_state:
        st.session_state.scan_input = ""

    c1, c2 = st.columns([1, 3])
    qty = c1.number_input(f"{op_type}數量", min_value=1, value=1)
    
    def on_scan():
        sku_code = st.session_state.scan_box
        if sku_code:
            process_stock(sku_code, qty, op_type)
            st.session_state.scan_box = "" 

    st.text_input("請掃描條碼 (掃描後自動執行)", key="scan_box", on_change=on_scan)

def process_stock(sku, qty, op_type):
    df = load_data()
    match = df[df['SKU'] == sku]
    
    if not match.empty:
        idx = match.index[0]
        current_stock = df.at[idx, 'Stock']
        name = df.at[idx, 'Name']
        
        if op_type == "入庫":
            new_stock = current_stock + qty
        else:
            new_stock = current_stock - qty
            
        df.at[idx, 'Stock'] = new_stock
        save_data(df)
        
        # 使用台灣時間
        log = {
            "Time": get_taiwan_time(),
            "User": "Admin",
            "Type": op_type,
            "SKU": sku,
            "Name": name,
            "Quantity": qty,
            "Note": "掃碼作業"
        }
        save_log(log)
        
        st.success(f"[V] {name} {op_type} {qty} 成功！ (庫存變為: {new_stock})")
    else:
        st.error(f"[X] 找不到此 SKU: {sku}")

def page_maintenance():
    st.subheader("品項維護")
    
    tab_new, tab_edit, tab_img = st.tabs(["新增商品", "編輯庫存總表", "🖼️ 圖片更換專區"])
    
    # Tab 1: 新增
    with tab_new:
        with st.form("new_prod"):
            c1, c2, c3 = st.columns(3)
            i_code = c1.text_input("編碼 (Code)")
            i_cat = c2.text_input("分類 (Category)")
            i_num = c3.text_input("號碼 (Number)")
            i_name = st.text_input("品名")
            i_file = st.file_uploader("上傳圖片 (選用)", type=["jpg", "png", "jpeg"])
            i_stock = st.number_input("初始庫存", 0)
            
            if st.form_submit_button("儲存商品"):
                sku = f"{i_code}-{i_cat}-{i_num}"
                if i_code and i_name:
                    df = load_data()
                    fname = None
                    if i_file:
                        fname = save_uploaded_image(i_file, sku)
                    
                    if sku in df['SKU'].values:
                        st.warning("SKU 已存在，將更新資料...")
                        if fname: df.loc[df['SKU']==sku, 'ImageFile'] = fname
                        df.loc[df['SKU']==sku, ['Code','Category','Number','Name']] = [i_code,i_cat,i_num,i_name]
                    else:
                        new_row = pd.DataFrame([{
                            "SKU":sku, "Code":i_code, "Category":i_cat, 
                            "Number":i_num, "Name":i_name, 
                            "ImageFile":fname, "Stock":i_stock
                        }])
                        df = pd.concat([df, new_row], ignore_index=True)
                    
                    save_data(df)
                    st.success(f"已儲存: {sku}")
                else:
                    st.error("錯誤：編碼與品名為必填欄位")
                    
    # Tab 2: 編輯
    with tab_edit:
        st.caption("提示：點擊表格內容可直接修改，修改完畢請記得按「儲存修改」。")
        df = load_data()
        edited = st.data_editor(df, num_rows="dynamic", key="main_editor")
        if st.button("儲存修改"):
            save_data(edited)
            st.success("表格資料已更新！")
            time.sleep(1)
            st.rerun()

    # Tab 3: 圖片更換
    with tab_img:
        st.subheader("更換現有商品圖片")
        df_current = load_data()
        
        if df_current.empty:
            st.info("目前沒有任何商品資料。")
        else:
            sku_list = df_current['SKU'].unique().tolist()
            selected_sku_for_img = st.selectbox("請選擇要更換圖片的商品 SKU", sku_list, key="sku_img_select")
            
            if selected_sku_for_img:
                item_row = df_current[df_current['SKU'] == selected_sku_for_img].iloc[0]
                st.write(f"您選擇了： **{item_row['Name']}**")
                
                col_old, col_new = st.columns(2)
                
                with col_old:
                    st.write("📍 目前的圖片：")
                    current_img_name = item_row['ImageFile']
                    if pd.notna(current_img_name) and str(current_img_name).strip() != "":
                        current_img_path = os.path.join(IMAGE_DIR, str(current_img_name))
                        if os.path.exists(current_img_path) and os.path.isfile(current_img_path):
                            st.image(current_img_path, width=250)
                        else:
                            st.warning(f"找不到原始檔案: {current_img_name}")
                    else:
                        st.info("無圖片")

                with col_new:
                    st.write("📤 上傳新圖片以替換：")
                    new_img_file = st.file_uploader("選擇新圖片", type=["jpg", "png", "jpeg"], key="new_img_uploader")
                    
                    if new_img_file:
                        if st.button("✅ 確認更換圖片", key="confirm_img_change"):
                            new_filename = save_uploaded_image(new_img_file, selected_sku_for_img)
                            df_current.loc[df_current['SKU'] == selected_sku_for_img, 'ImageFile'] = new_filename
                            save_data(df_current)
                            st.success(f"成功更新！")
                            time.sleep(1.5)
                            st.rerun()

def page_reports():
    st.subheader("異動紀錄 (台灣時間)")
    df_log = load_log()
    
    filter_sku = st.text_input("篩選 SKU", key="log_sku")
    if filter_sku:
        df_log = df_log[df_log['SKU'].str.contains(filter_sku, case=False, na=False)]
        
    st.dataframe(df_log.sort_values(by="Time", ascending=False))
    
    csv = df_log.to_csv(index=False).encode('utf-8-sig')
    st.download_button("下載 CSV 報表", csv, "inventory_log.csv", "text/csv")

if __name__ == "__main__":
    main()
