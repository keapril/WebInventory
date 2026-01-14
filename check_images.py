# -*- coding: utf-8 -*-
"""
檢查 Firestore 中所有產品的圖片狀態
"""

import json
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase 設定
FIREBASE_KEY_PATH = "product-system-900c4-firebase-adminsdk-fbsvc-305a38d463.json"
COLLECTION_NAME = "instrument_consumables"

def init_firebase():
    """初始化 Firebase"""
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def check_images():
    """檢查所有產品的圖片狀態"""
    print("=" * 80)
    print("檢查 Firestore 圖片狀態")
    print("=" * 80)
    
    db = init_firebase()
    docs = db.collection(COLLECTION_NAME).stream()
    
    r2_images = []
    firebase_images = []
    no_images = []
    
    for doc in docs:
        data = doc.to_dict()
        sku = doc.id
        name = data.get('name', 'N/A')
        image_url = data.get('imageFile', '')
        
        if not image_url:
            no_images.append({'SKU': sku, 'Name': name})
        elif 'r2.dev' in image_url or 'r2.cloudflarestorage.com' in image_url:
            r2_images.append({'SKU': sku, 'Name': name, 'URL': image_url})
        elif 'firebasestorage' in image_url or 'storage.googleapis.com' in image_url:
            firebase_images.append({'SKU': sku, 'Name': name, 'URL': image_url})
        else:
            no_images.append({'SKU': sku, 'Name': name, 'URL': image_url})
    
    # 顯示統計
    print(f"\n📊 統計總覽")
    print(f"  ✅ Cloudflare R2 圖片: {len(r2_images)}")
    print(f"  ⚠️ Firebase Storage 圖片: {len(firebase_images)}")
    print(f"  ❌ 無圖片: {len(no_images)}")
    
    # 顯示 R2 圖片
    if r2_images:
        print(f"\n✅ Cloudflare R2 圖片 ({len(r2_images)} 筆)")
        print("-" * 80)
        for item in r2_images[:10]:  # 只顯示前 10 筆
            print(f"  SKU: {item['SKU']}")
            print(f"  名稱: {item['Name']}")
            print(f"  URL: {item['URL'][:80]}...")
            print()
        if len(r2_images) > 10:
            print(f"  ... 還有 {len(r2_images) - 10} 筆")
    
    # 顯示無圖片
    if no_images:
        print(f"\n❌ 無圖片 ({len(no_images)} 筆)")
        print("-" * 80)
        for item in no_images[:10]:
            print(f"  SKU: {item['SKU']}")
            print(f"  名稱: {item['Name']}")
            print()
        if len(no_images) > 10:
            print(f"  ... 還有 {len(no_images) - 10} 筆")
    
    # 顯示 Firebase Storage 圖片（舊的）
    if firebase_images:
        print(f"\n⚠️ Firebase Storage 圖片 ({len(firebase_images)} 筆) - 需要遷移或清除")
        print("-" * 80)
        for item in firebase_images[:5]:
            print(f"  SKU: {item['SKU']}")
            print(f"  名稱: {item['Name']}")
            print()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_images()
