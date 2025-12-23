# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
import json
import time
from PIL import Image
from datetime import datetime

# Firebase 相關套件
import firebase_admin
from firebase_admin import credentials, firestore, storage

# --- 1. 系統設定 ---
st.set_page_config(
    page_title="庫存管理系統 (修正版)",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Firebase 初始化 (單例模式) ---
if not firebase_admin._apps:
    # 這裡假設您的 secrets 設定正確
    try:
        key_dict = json.loads(st.secrets["firebase"]["text_key"])
        cred = credentials.Certificate(key_dict)
        bucket_name = f"{key_dict['project_id']}.appspot.com"
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
    except Exception as e:
        st.error(f"Firebase 初始化失敗: {e}")
        st.stop()

db = firestore.client()
bucket = storage.bucket()

COLLECTION_NAME = "products"

# --- 3. 資料庫操作函式 ---

def load_data_snapshot():
    """
    從 Firestore 讀取資料，同時回傳 DataFrame 和原始的所有 ID (Set)
    用於後續比對刪除
    """
    docs = db.collection(COLLECTION_NAME).stream()
    data = []
    original_ids = set()

    for doc in docs:
        d = doc.to_dict()
        sku = doc.id
        original_ids.add(sku)
        
        data.append({
            "SKU": sku, 
            "Code": d.get("code", ""),
            "Category": d.get("categoryName", ""),
            "Number": d.get("number", ""),
            "Name": d.get("name", ""),
            "ImageFile": d.get("imageFile", ""),
            "Stock": d.get("stock", 0),
            "Location": d.get("location", ""),
            "SN": d.get("sn", ""),
            "Spec": d.get("spec", ""),
            "UDI": d.get("udi", "")
        })
    
    if not data:
        return pd.DataFrame(columns=["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "Spec", "UDI"]), original_ids
    
    return pd.DataFrame(data), original_ids

def save_data_row(row):
    """更新單筆資料到 Firestore"""
    data_dict = {
        "code": row.get("Code", ""),
        "categoryName": row.get("Category", ""),
        "number": row.get("Number", ""),
        "name": row.get("Name", ""),
        "imageFile": row.get("ImageFile", ""),
        "stock": row.get("Stock", 0),
        "location": row.get("Location", ""),
        "sn": row.get("SN", ""),
        "spec": row.get("Spec", ""),
        "udi": row.get("UDI", ""),
        "updatedAt": firestore.SERVER_TIMESTAMP
    }
    # 使用 SKU 當作 Document ID
    db.collection(COLLECTION_NAME).document(str(row["SKU"])).set(data_dict, merge=True)

def delete_data_row(sku):
    """從 Firestore 刪除資料"""
    db.collection(COLLECTION_NAME).document(str(sku)).delete()

def upload_image_to_firebase(uploaded_file, sku):
    """上傳圖片"""
    if uploaded_file is None:
        return None
    
    file_ext = uploaded_file.name.split('.')[-1]
    blob_name = f"images/{sku}-{int(time.time())}.{file_ext}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
    blob.make_public()
    return blob.public_url

# --- 4. 介面邏輯 ---

st.title("☁️ 雲端庫存管理系統 (修正版)")

# 初始化 Session State 用於暫存原始 ID
if 'original_ids' not in st.session_state:
    st.session_state.original_ids = set()

menu = st.sidebar.radio("前往", ["庫存總覽", "新增商品", "圖片管理"])

if menu == "庫存總覽":
    st.subheader("📦 目前庫存")
    
    # 讀取資料
    df, original_ids = load_data_snapshot()
    # 將原始 ID 存入 session_state 以便儲存時比對
    st.session_state.original_ids = original_ids

    # 搜尋過濾
    search_term = st.text_input("🔍 搜尋 (名稱/代碼/規格)", "")
    if search_term:
        df = df[
            df["Name"].str.contains(search_term, case=False, na=False) |
            df["Code"].str.contains(search_term, case=False, na=False) |
            df["Spec"].str.contains(search_term, case=False, na=False)
        ]

    # 顯示可編輯表格
    edited_df = st.data_editor(
        df,
        key="inventory_editor",
        num_rows="dynamic",
        column_config={
            # 重要修正：鎖定 SKU 欄位，避免使用者修改導致資料重複
            "SKU": st.column_config.TextColumn("SKU (不可改)", disabled=True),
            "ImageFile": st.column_config.ImageColumn("圖片預覽"),
            "Stock": st.column_config.NumberColumn("數量", min_value=0, step=1),
        },
        use_container_width=True
    )

    if st.button("💾 儲存變更"):
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. 處理資料更新與新增
            total_rows = len(edited_df)
            current_skus = set()
            
            for i, row in edited_df.iterrows():
                if not pd.isna(row["SKU"]) and str(row["SKU"]).strip() != "":
                    sku_str = str(row["SKU"])
                    current_skus.add(sku_str)
                    save_data_row(row)
                
                if total_rows > 0:
                    progress_bar.progress((i + 1) / total_rows)
            
            # 2. 處理資料刪除 (重要修正)
            # 找出「原始有」但「現在沒有」的 SKU
            deleted_skus = st.session_state.original_ids - current_skus
            
            if deleted_skus:
                status_text.text(f"正在刪除 {len(deleted_skus)} 筆資料...")
                for sku in deleted_skus:
                    delete_data_row(sku)
            
            st.success(f"✅ 同步完成！更新/新增 {len(edited_df)} 筆，刪除 {len(deleted_skus)} 筆。")
            time.sleep(1.5)
            st.rerun()
            
        except Exception as e:
            st.error(f"儲存過程發生錯誤: {e}")

elif menu == "新增商品":
    st.subheader("➕ 新增商品")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU (唯一編號)*", help="請輸入唯一識別碼，建立後不可修改")
        code = c2.text_input("產品代碼")
        name = st.text_input("品名*")
        category = c1.text_input("分類")
        spec = c2.text_input("規格")
        stock = st.number_input("初始數量", min_value=0, value=1)
        
        uploaded_img = st.file_uploader("商品圖片", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("新增"):
            # 檢查 SKU 是否已存在 (簡單防呆)
            doc_ref = db.collection(COLLECTION_NAME).document(sku)
            if doc_ref.get().exists:
                st.error(f"錯誤：SKU '{sku}' 已存在，請使用其他編號。")
            elif not sku or not name:
                st.error("SKU 和 品名 為必填！")
            else:
                image_url = ""
                if uploaded_img:
                    with st.spinner("圖片上傳中..."):
                        image_url = upload_image_to_firebase(uploaded_img, sku)
                
                new_data = {
                    "SKU": sku, "Code": code, "Name": name, 
                    "Category": category, "Spec": spec, 
                    "Stock": stock, "ImageFile": image_url,
                    "Number": "", "Location": "", "SN": "", "UDI": ""
                }
                save_data_row(new_data)
                st.success(f"已新增：{name}")
                time.sleep(1)
                st.rerun()

elif menu == "圖片管理":
    st.subheader("🖼️ 圖片更換")
    df, _ = load_data_snapshot() # 重用函式
    
    sku_to_edit = st.selectbox("選擇商品", df["SKU"].unique())
    
    if sku_to_edit:
        item = df[df["SKU"] == sku_to_edit].iloc[0]
        st.write(f"目前商品：**{item['Name']}** ({item['SKU']})")
        
        if item["ImageFile"]:
            st.image(item["ImageFile"], width=200, caption="目前圖片")
        else:
            st.info("尚無圖片")
            
        new_img = st.file_uploader("上傳新圖片", type=["png", "jpg"])
        if new_img and st.button("確認更換"):
            with st.spinner("上傳中..."):
                url = upload_image_to_firebase(new_img, sku_to_edit)
                db.collection(COLLECTION_NAME).document(str(sku_to_edit)).update({"imageFile": url})
            
            st.success("圖片更新完成！")
            time.sleep(1)
            st.rerun()
