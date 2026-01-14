# -*- coding: utf-8 -*-
"""
清除 Firebase Storage 的舊圖片連結
執行後所有 Firebase Storage 的圖片 URL 會被清空
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

def is_firebase_storage_url(url):
    """檢查是否為 Firebase Storage URL"""
    if not url:
        return False
    return "storage.googleapis.com" in url or "firebasestorage.app" in url

def clear_firebase_images():
    """清除所有 Firebase Storage 的圖片連結"""
    print("=" * 50)
    print("開始清除 Firebase Storage 圖片連結")
    print("=" * 50)
    
    db = init_firebase()
    docs = db.collection(COLLECTION_NAME).stream()
    
    total = 0
    cleared = 0
    skipped = 0
    
    for doc in docs:
        total += 1
        data = doc.to_dict()
        image_url = data.get('imageFile', '')
        
        print(f"\n[{total}] {doc.id}")
        print(f"  目前圖片: {image_url[:80]}..." if len(image_url) > 80 else f"  目前圖片: {image_url}")
        
        if is_firebase_storage_url(image_url):
            # 清空 Firebase Storage URL
            db.collection(COLLECTION_NAME).document(doc.id).update({
                'imageFile': ''
            })
            print(f"  ✅ 已清除 Firebase Storage 連結")
            cleared += 1
        else:
            print(f"  ⏭️ 跳過（不是 Firebase Storage 或已清空）")
            skipped += 1
    
    print("\n" + "=" * 50)
    print("清除完成！")
    print(f"  總計: {total}")
    print(f"  已清除: {cleared}")
    print(f"  跳過: {skipped}")
    print("=" * 50)
    print("\n提示：請到 Streamlit 重新上傳圖片")

if __name__ == "__main__":
    # 確認操作
    print("\n⚠️  警告：此操作將清除所有 Firebase Storage 的圖片連結")
    print("   (Cloudflare R2 的圖片連結不會被影響)")
    confirm = input("\n確定要繼續嗎？(輸入 yes 確認): ")
    
    if confirm.lower() == "yes":
        clear_firebase_images()
    else:
        print("❌ 已取消操作")
