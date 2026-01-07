# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont
import io

# --- 1. 網頁基礎設定 (v7.2 日期型別修復版) ---
st.set_page_config(
    page_title="庫存管理系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS: 無印良品風 (淺灰、深灰字、極簡)
st.markdown("""
    <style>
    /* 全站背景 */
    .stApp {
        background-color: #F9F9F9;
        color: #333333;
        font-family: "Helvetica Neue", Helvetica, "PingFang TC", "Microsoft JhengHei", sans-serif;
    }
    
    /* 側邊欄 - 淺灰底深灰字 */
    section[data-testid="stSidebar"] {
        background-color: #F0F2F6;
        color: #31333F;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p {
        color: #31333F !important;
    }
    
    /* 標題 */
    h1, h2, h3 {
        color: #2C3E50;
        font-weight: 600;
    }
    
    /* 數據卡片 */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        text-align: center;
    }
    .metric-label {
        color: #7F8C8D;
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #2C3E50;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* 狀態標籤 */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-right: 5px;
        margin-bottom: 3px;
        border: 1px solid transparent;
    }
    .badge-gray { background-color: #F5F5F5; color: #666; border-color: #DDD; }
    .badge-green { background-color: #E8F5E9; color: #2E7D32; border-color: #C8E6C9; }
    .badge-red { background-color: #FFEBEE; color: #C62828; border-color: #FFCDD2; }
    .badge-blue { background-color: #E3F2FD; color: #1565C0; border-color: #BBDEFB; }
    .badge-gold { background-color: #FFFDE7; color: #F57F17; border-color: #FFF9C4; }
    
    /* 輸入框與按鈕 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stDateInput input {
        border-radius: 4px;
        border: 1px solid #CCC;
    }
    div.stButton > button {
        background-color: #5D6D7E;
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5rem 1rem;
        transition: background 0.3s;
    }
    div.stButton > button:hover {
        background-color: #34495E;
    }
    
    /* Radio Button 優化 */
    .stRadio > div { flex-direction: column; gap: 5px; }
    .stRadio label {
        background-color: transparent;
        padding: 5px 10px;
        border-radius: 4px;
        color: #31333F !important;
    }
    .stRadio label:hover {
        background-color: #E0E4E8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 常數與路徑設定 ---
DATA_FILE = "inventory_data.csv"
LOG_FILE = "transaction_log.csv"
IMAGE_DIR = "images"

# 確保圖片目錄存在
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# --- 3. 核心函數區 ---

def get_taiwan_time():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    # 定義完整欄位，包含 SN 和保固
    default_cols = ["SKU", "Code", "Category", "Number", "Name", "ImageFile", "Stock", "Location", "SN", "WarrantyStart", "WarrantyEnd"]
    
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # 補齊欄位
            for col in default_cols:
                if col not in df.columns:
                    df[col] = ""
            
            # 轉換為字串避免錯誤，Location 與 SN 保持字串
            df["Location"] = df["Location"].fillna("").astype(str)
            df["SN"] = df["SN"].fillna("").astype(str)
            
            # [關鍵修正] 日期欄位處理
            # 1. 先強制轉為 datetime，錯誤變 NaT
            df["WarrantyStart"] = pd.to_datetime(df["WarrantyStart"], errors='coerce')
            df["WarrantyEnd"] = pd.to_datetime(df["WarrantyEnd"], errors='coerce')
            
            # 2. 為了 st.data_editor 的 DateColumn，我們需要把 NaT 轉為 None，
            #    且保留 datetime 物件 (Streamlit 會自動處理顯示)
            #    注意：不需要轉回字串，直接給 datetime 物件是最好的
            
            return df
        except Exception as e:
            st.error(f"資料讀取錯誤: {e}")
            pass
            
    return pd.DataFrame(columns=default_cols)

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            pass
    return pd.DataFrame(columns=["Time", "User", "Type", "SKU", "Name", "Quantity", "Note"])

def save_data(df):
    # [關鍵修正] 儲存前將日期轉回字串格式 YYYY-MM-DD，避免 CSV 存成 Timestamp 物件導致下次讀取困難
    df_to_save = df.copy()
    
    # 處理 WarrantyStart
    if "WarrantyStart" in df_to_save.columns:
        df_to_save["WarrantyStart"] = df_to_save["WarrantyStart"].apply(
            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and hasattr(x, 'strftime') else ""
        )
        
    # 處理 WarrantyEnd
    if "WarrantyEnd" in df_to_save.columns:
        df_to_save["WarrantyEnd"] = df_to_save["WarrantyEnd"].apply(
            lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) and hasattr(x, 'strftime') else ""
        )
    
    df_to_save.to_csv(DATA_FILE, index=False)

def save_log(entry):
    df_log = load_log()
    new_entry = pd.DataFrame([entry])
    df_log = pd.concat([df_log, new_entry], ignore_index=True)
    df_log.to_csv(LOG_FILE, index=False)

def save_uploaded_image(uploaded_file, sku):
    if uploaded_file is None:
        return None
    # 取得副檔名
    file_ext = os.path.splitext(uploaded_file.name)[1]
    # 建立新檔名 (SKU + 副檔名)
    new_filename = f"{sku}{file_ext}"
    
    # 儲存到 images 資料夾
    save_path = os.path.join(IMAGE_DIR, new_filename)
    try:
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return new_filename
    except Exception as e:
        st.error(f"圖片儲存失敗: {e}")
        return None

# --- [圖片生成函數] ---
def generate_inventory_image(df_result):
    card_width = 800
    card_height = 220
    padding = 20
    header_height = 80
    
    total_height = header_height + (len(df_result) * (card_height + padding)) + padding
    img_width = card_width + (padding * 2)
    
    img = Image.new('RGB', (img_width, total_height), color='#FFFFFF')
    draw = ImageDraw.Draw(img)
    
    # 使用預設字體
    try:
        font_default = ImageFont.load_default()
    except:
        pass 
    
    # Header
    draw.rectangle([0, 0, img_width, header_height], fill='#2C3E50')
    draw.text((padding, 30), f"INVENTORY REPORT - {datetime.now().strftime('%Y-%m-%d')}", fill='white')

    y_offset = header_height + padding
    
    for _, row in df_result.iterrows():
        # 卡片框
        draw.rectangle([padding, y_offset, padding + card_width, y_offset + card_height], outline='#CCCCCC', width=1)
        
        # 圖片
        img_path = None
        if pd.notna(row['ImageFile']) and str(row['ImageFile']).strip():
            full_path = os.path.join(IMAGE_DIR, str(row['ImageFile']))
            if os.path.exists(full_path):
                img_path = full_path
        
        if img_path:
            try:
                prod_img = Image.open(img_path).convert('RGB')
                prod_img.thumbnail((150, 150))
                img.paste(prod_img, (padding + 20, y_offset + 25))
            except:
                pass
        else:
            draw.rectangle([padding + 20, y_offset + 25, padding + 170, y_offset + 175], fill='#F0F0F0')
            draw.text((padding + 60, y_offset + 90), "No Image", fill='#888')

        # 文字
        text_x = padding + 200
        text_y = y_offset + 30
        
        draw.text((text_x, text_y), f"NAME: {row['Name']}", fill='black')
        text_y += 30
        draw.text((text_x, text_y), f"SKU: {row['SKU']} | CAT: {row['Category']}", fill='#555')
        text_y += 25
        
        stock_info = f"STOCK: {row['Stock']}"
        draw.text((text_x, text_y), stock_info, fill='red' if row['Stock'] <= 5 else 'green')
        text_y += 25
        
        if row['Location']:
            draw.text((text_x, text_y), f"LOC: {row['Location']}", fill='blue')
            text_y += 25
            
        # 日期轉字串顯示
        war_end_str = ""
        if pd.notna(row['WarrantyEnd']):
            if hasattr(row['WarrantyEnd'], 'strftime'):
                war_end_str = row['WarrantyEnd'].strftime('%Y-%m-%d')
            else:
                war_end_str = str(row['WarrantyEnd'])

        if row['SN'] or war_end_str:
            info = f"S/N: {row['SN']}  Warranty: {war_end_str}"
            draw.text((text_x, text_y), info, fill='#E67E22')

        y_offset += card_height + padding

    return img

# --- 4. 主程式介面 ---

def main():
    with st.sidebar:
        st.title("📦 庫存管理系統")
        st.write("v7.2 日期型別修復版")
        st.markdown("---")
        
        page = st.radio("功能選單", [
            "📊 總覽與查詢", 
            "📥 入庫作業", 
            "📤 出庫作業", 
            "🛠️ 資料維護", 
            "📋 異動紀錄"
        ])
        st.markdown("---")

    # 頁面路由
    if "總覽" in page:
        page_search()
    elif "入庫" in page:
        page_operation("入庫")
    elif "出庫" in page:
        page_operation("出庫")
    elif "維護" in page:
        page_maintenance()
    elif "紀錄" in page:
        page_reports()

# --- 各頁面子程式 ---

def page_search():
    st.header("📊 庫存總覽")
    df = load_data()
    
    # 數據看板
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>總品項數</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    with c2:
        low_stock = len(df[df['Stock'] <= 5])
        st.markdown(f"<div class='metric-card'><div class='metric-label'>低庫存警示</div><div class='metric-value' style='color:#C62828;'>{low_stock}</div></div>", unsafe_allow_html=True)
    with c3:
        total_qty = df['Stock'].sum()
        st.markdown(f"<div class='metric-card'><div class='metric-label'>庫存總數量</div><div class='metric-value'>{total_qty}</div></div>", unsafe_allow_html=True)
    
    st.write("")
    st.subheader("🔍 搜尋庫存")
    
    col_search, col_action = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("輸入關鍵字", key="search_input", placeholder="搜尋 SKU / 品名 / 地點 / S/N...")
    
    if search_term:
        # 搜尋前轉字串
        mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        result = df[mask]
    else:
        result = df
    
    with col_action:
        st.write("") 
        if st.button("📥 匯出查詢結果圖", use_container_width=True):
            with st.spinner("圖片生成中..."):
                img = generate_inventory_image(result)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.download_button(label="下載 PNG 圖片", data=byte_im, file_name="inventory_report.png", mime="image/png", use_container_width=True)

    st.write("")
    
    if not result.empty:
        st.caption(f"共找到 {len(result)} 筆資料")
        
        for _, row in result.iterrows():
            # 徽章準備
            badges = []
            if row['Stock'] <= 5: badges.append(f"<span class='badge badge-red'>庫存: {row['Stock']}</span>")
            else: badges.append(f"<span class='badge badge-green'>庫存: {row['Stock']}</span>")
            
            if row['Location']: badges.append(f"<span class='badge badge-blue'>📍 {row['Location']}</span>")
            
            # SN 與 保固 (有值才顯示)
            if row['SN']: badges.append(f"<span class='badge badge-gray'>S/N: {row['SN']}</span>")
            
            if pd.notna(row['WarrantyEnd']):
                try:
                    # 注意：現在 row['WarrantyEnd'] 是 datetime 或 NaT
                    today = datetime.now()
                    if row['WarrantyEnd'] >= today:
                        days = (row['WarrantyEnd'] - today).days
                        badges.append(f"<span class='badge badge-gold'>🛡️ 保固內 (剩{days}天)</span>")
                    else:
                        badges.append(f"<span class='badge badge-red'>⚠️ 已過保</span>")
                except: pass
            
            badges_html = "".join(badges)

            # 圖片直接顯示
            with st.container():
                st.markdown(f"""
                <div style="background:white; border:1px solid #EEE; border-radius:8px; padding:15px; margin-bottom:10px;">
                    <div style="display:flex; gap:20px;">
                """, unsafe_allow_html=True)
                
                c_img, c_info = st.columns([1, 4])
                
                with c_img:
                    img_shown = False
                    if pd.notna(row['ImageFile']) and str(row['ImageFile']).strip():
                        # 使用 os.path.abspath 確保路徑正確
                        img_path = os.path.abspath(os.path.join(IMAGE_DIR, str(row['ImageFile'])))
                        
                        if os.path.exists(img_path):
                            try:
                                st.image(img_path, use_container_width=True)
                                img_shown = True
                            except Exception:
                                st.caption("❌ 圖片損壞")
                        else:
                            st.caption(f"⚠️ 檔案遺失")
                    
                    if not img_shown:
                        st.caption("無圖片")
                
                with c_info:
                    st.markdown(f"""
                        <div style="font-size:1.2rem; font-weight:bold; color:#333; margin-bottom:5px;">{row['Name']}</div>
                        <div style="margin-bottom:8px;">{badges_html}</div>
                        <div style="font-size:0.9rem; color:#666;">
                            <b>SKU:</b> {row['SKU']} &nbsp;|&nbsp; 
                            <b>分類:</b> {row['Category']} &nbsp;|&nbsp; 
                            <b>號碼:</b> {row['Number']}
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
    else: 
        st.info("沒有找到相關資料。")

def page_operation(op_type):
    st.header(f"{op_type}作業")
    
    if "scan_input" not in st.session_state: st.session_state.scan_input = ""
    
    col_q, col_s = st.columns([1, 2])
    with col_q: qty = st.number_input("數量", min_value=1, value=1)
    
    def on_scan():
        if st.session_state.scan_box:
            process_stock(st.session_state.scan_box, qty, op_type)
            st.session_state.scan_box = ""
    
    st.text_input("請掃描條碼或輸入 SKU", key="scan_box", on_change=on_scan)

def process_stock(sku, qty, op_type):
    df = load_data()
    match = df[df['SKU'] == sku]
    if not match.empty:
        idx = match.index[0]
        curr = df.at[idx, 'Stock']
        new = curr + qty if op_type == "入庫" else curr - qty
        df.at[idx, 'Stock'] = new
        save_data(df)
        save_log({"Time":get_taiwan_time(), "User":"Admin", "Type":op_type, "SKU":sku, "Name":df.at[idx,'Name'], "Quantity":qty, "Note":"App"})
        st.toast(f"✅ {op_type}成功！", icon="✨")
        st.success(f"已更新 **{df.at[idx,'Name']}** 庫存為: {new}")
    else: st.error(f"找不到 SKU: {sku}")

def page_maintenance():
    st.header("🛠️ 資料維護")
    
    tab1, tab2, tab3 = st.tabs(["＋ 新增項目", "📝 編輯表格", "🖼️ 更換圖片"])
    
    df_opt = load_data()
    exist_locs = sorted([str(x) for x in df_opt['Location'].unique() if pd.notna(x) and str(x).strip() != ""])
    all_locs = sorted(list(set(["北", "中", "南", "高"] + exist_locs)))

    # === Tab 1: 新增 ===
    with tab1:
        st.subheader("1. 基本資料")
        c1, c2 = st.columns(2)
        i_code = c1.text_input("編碼 (Code)")
        i_cat = c2.text_input("分類 (Category)")
        c3, c4 = st.columns(2)
        i_num = c3.text_input("號碼 (Number)")
        i_name = c4.text_input("品名 (Name)")
        
        # --- 儀器專屬欄位 ---
        st.subheader("2. 規格與保固 (選填)")
        st.info("💡 如果是耗材，以下欄位留空即可")
        c_sn, c_war = st.columns(2)
        i_sn = c_sn.text_input("S/N (產品序號)")
        
        with c_war:
            enable_warranty = st.checkbox("設定保固日期?")
            if enable_warranty:
                cw1, cw2 = st.columns(2)
                i_w_start = cw1.date_input("保固開始日", value=datetime.today())
                i_w_end = cw2.date_input("保固結束日", value=datetime.today() + timedelta(days=365))
            else:
                i_w_start = None
                i_w_end = None
        
        st.subheader("3. 庫存與地點")
        col_loc_main, col_loc_sub = st.columns([1, 2])
        main_loc = col_loc_main.selectbox("區域選擇", ["北", "中", "南", "高", "醫院"])
        
        hospital_name = ""
        with col_loc_sub:
            if main_loc == "醫院":
                hospital_name = st.text_input("輸入醫院名稱", placeholder="例如：台大")
            else:
                st.text_input("區域鎖定", value=main_loc, disabled=True)
        
        i_stock = st.number_input("初始庫存", 0, value=1)
        i_file = st.file_uploader("商品圖片", type=["jpg", "png"])
        
        if st.button("確認新增", use_container_width=True):
            final_loc = f"醫院-{hospital_name}" if main_loc == "醫院" and hospital_name.strip() else main_loc
            if main_loc == "醫院" and not hospital_name.strip():
                st.error("請輸入醫院名稱")
                st.stop()

            sku = f"{i_code}-{i_cat}-{i_num}"
            
            # 日期轉字串 (如果有啟用的話)
            fw_s = i_w_start.strftime('%Y-%m-%d') if i_w_start else ""
            fw_e = i_w_end.strftime('%Y-%m-%d') if i_w_end else ""

            if i_code and i_name:
                df = load_data()
                fname = save_uploaded_image(i_file, sku) if i_file else None
                new_data = {
                    "SKU": sku, "Code": i_code, "Category": i_cat, "Number": i_num, 
                    "Name": i_name, "ImageFile": fname, "Stock": i_stock, 
                    "Location": final_loc, "SN": i_sn, 
                    "WarrantyStart": fw_s, "WarrantyEnd": fw_e
                }
                
                # 轉 DataFrame 並確保日期格式 (Timestamp)
                new_row_df = pd.DataFrame([new_data])
                new_row_df["WarrantyStart"] = pd.to_datetime(new_row_df["WarrantyStart"], errors='coerce')
                new_row_df["WarrantyEnd"] = pd.to_datetime(new_row_df["WarrantyEnd"], errors='coerce')

                if sku in df['SKU'].values:
                    st.warning("SKU 已存在，將更新資料")
                    if fname: df.loc[df['SKU']==sku, 'ImageFile'] = fname
                    
                    df.loc[df['SKU']==sku, 'Code'] = i_code
                    df.loc[df['SKU']==sku, 'Category'] = i_cat
                    df.loc[df['SKU']==sku, 'Number'] = i_num
                    df.loc[df['SKU']==sku, 'Name'] = i_name
                    df.loc[df['SKU']==sku, 'Location'] = final_loc
                    df.loc[df['SKU']==sku, 'SN'] = i_sn
                    
                    # 更新日期 (確保是 Timestamp)
                    if fw_s: df.loc[df['SKU']==sku, 'WarrantyStart'] = pd.to_datetime(fw_s)
                    if fw_e: df.loc[df['SKU']==sku, 'WarrantyEnd'] = pd.to_datetime(fw_e)
                else:
                    df = pd.concat([df, new_row_df], ignore_index=True)
                
                save_data(df)
                st.success(f"新增成功: {sku}")
            else: st.error("編碼與品名為必填")

    # === Tab 2: 編輯表格 ===
    with tab2:
        df = load_data()
        col_cfg = {
            "Location": st.column_config.SelectboxColumn("地點", width="medium", options=all_locs),
            "WarrantyStart": st.column_config.DateColumn("保固開始", format="YYYY-MM-DD"),
            "WarrantyEnd": st.column_config.DateColumn("保固結束", format="YYYY-MM-DD"),
            "SN": st.column_config.TextColumn("S/N (序號)"),
            "ImageFile": st.column_config.TextColumn("圖片檔名", disabled=True)
        }
        edited = st.data_editor(df, num_rows="dynamic", key="main_editor", use_container_width=True, column_config=col_cfg)
        if st.button("儲存表格變更"):
            save_data(edited)
            st.success("表格已更新")
            time.sleep(1)
            st.rerun()

    # === Tab 3: 換圖 ===
    with tab3:
        df_cur = load_data()
        if not df_cur.empty:
            sel = st.selectbox("選擇商品更換圖片", df_cur['SKU'].unique())
            if sel:
                row = df_cur[df_cur['SKU'] == sel].iloc[0]
                st.info(f"正在更換: **{row['Name']}**")
                f = st.file_uploader("選擇新圖片", type=["jpg","png"])
                if f and st.button("上傳並更換"):
                    fname = save_uploaded_image(f, sel)
                    df_cur.loc[df_cur['SKU']==sel, 'ImageFile'] = fname
                    save_data(df_cur)
                    st.success("圖片更新成功")
                    time.sleep(1)
                    st.rerun()

def page_reports():
    st.header("📋 異動紀錄")
    df = load_log()
    if not df.empty:
        st.dataframe(df.sort_values(by="Time", ascending=False), use_container_width=True)
        st.download_button("下載 CSV", df.to_csv(index=False).encode('utf-8-sig'), "log.csv", "text/csv")
    else: st.info("無紀錄")

if __name__ == "__main__":
    main()
