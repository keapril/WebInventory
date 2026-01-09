
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Product, LogEntry, Page, LogType } from './types';
import { 
  Package, Inbox, Send, Wrench, History, 
  Search, Box, Info, Trash2, 
  AlertTriangle, MapPin, Tag, Sparkles, 
  Plus, Edit, Image as ImageIcon, RotateCcw, Save, X, Layers, Upload, Camera, ExternalLink, Github, Globe, Hash, Calendar, ListPlus, Calculator
} from 'lucide-react';
import { HeroScene } from './components/QuantumScene';

// --- SYSTEM CONFIGURATION ---
const SYSTEM_CONFIG = {
  TEXT_DB_PATH: "product-system-900c4.firebasestorage.app",
  IMAGE_DB_PATH: "pub-12069eb186dd414482e689701534d8d5.r2.dev",
  GITHUB_URL: "https://github.com/keapril/WebInventory",
  OFFICIAL_URL: "https://webfce.streamlit.app/",
  VERSION: "2.5.0-Quantum"
};

// Helper to resolve image URLs
const resolveImageUrl = (path: string) => {
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('data:')) return path;
  return `https://${SYSTEM_CONFIG.IMAGE_DB_PATH}/${path}`;
};

// --- MOCK DATA ---
const initialProducts: Product[] = [
  { SKU: "EQ-NC-001", Code: "EQ", Category: "儀器", Number: "001", Name: "高精度示波器", ImageFile: "https://images.unsplash.com/photo-1599468652316-24c615886618?w=400", Stock: 5, Location: "北辦", SN: "SN-A123", WarrantyStart: "2023-01-15", WarrantyEnd: "2025-01-14", Accessories: "電源線x1, 探頭x2" },
  { SKU: "CS-PP-002", Code: "CS", Category: "耗材", Number: "002", Name: "5ml 移液管", ImageFile: "https://images.unsplash.com/photo-1633638423438-2ab37c1d41ac?w=400", Stock: 200, Location: "中辦", SN: "", WarrantyStart: null, WarrantyEnd: null, Accessories: "" },
];

const initialLogs: LogEntry[] = [
  { Time: "2024-07-20 10:05:32", User: "Admin", Type: "入庫", SKU: "EQ-NC-001", Name: "高精度示波器", Quantity: 2, Note: "系統初始化" },
];

// --- UTILS ---
const getCurrentTimestamp = () => new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }).replace(/\//g, '-');

const checkWarrantyStatus = (warrantyEnd: string | null) => {
    if (!warrantyEnd) return { status: '正常', text: 'N/A' };
    const endDate = new Date(warrantyEnd);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const daysLeft = Math.ceil((endDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    if (daysLeft < 0) return { status: '已過期', text: `過期 ${Math.abs(daysLeft)} 天` };
    if (daysLeft <= 30) return { status: '即將到期', text: `剩 ${daysLeft} 天` };
    return { status: '正常', text: `剩 ${daysLeft} 天` };
};

// --- COMPONENTS ---

const Sidebar: React.FC<{ currentPage: Page; setPage: (page: Page) => void }> = ({ currentPage, setPage }) => {
    const menuItems: { id: Page; name: string; icon: React.ReactNode }[] = [
        { id: 'overview', name: '總覽查詢', icon: <Package size={18}/> },
        { id: 'inbound', name: '入庫作業', icon: <Inbox size={18}/> },
        { id: 'outbound', name: '出庫作業', icon: <Send size={18}/> },
        { id: 'maintenance', name: '資料維護', icon: <Wrench size={18}/> },
        { id: 'logs', name: '異動紀錄', icon: <History size={18}/> },
    ];

    return (
        <aside className="w-64 glass border-r border-gold/10 flex flex-col flex-shrink-0 z-20">
            <div className="h-20 flex items-center px-8 gap-3">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white shadow-lg shadow-primary/30">
                  <Sparkles size={18} />
                </div>
                <h1 className="text-xl font-serif font-bold text-stone-800 tracking-tight">WebInventory</h1>
            </div>
            
            <nav className="flex-1 px-4 py-4 space-y-1">
                {menuItems.map(item => (
                    <button
                        key={item.id}
                        onClick={() => setPage(item.id)}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl transition-all ${currentPage === item.id ? 'bg-primary text-white shadow-md shadow-primary/20' : 'text-stone-500 hover:bg-stone-100/50 hover:text-stone-800'}`}
                    >
                        {item.icon}
                        <span>{item.name}</span>
                    </button>
                ))}
            </nav>

            <div className="px-6 py-8 space-y-4 border-t border-gold/5">
                <div className="flex items-center gap-2 text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-2">
                   <ExternalLink size={12} /> 外部資源連結
                </div>
                <a href={SYSTEM_CONFIG.GITHUB_URL} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-xs text-stone-500 hover:text-primary transition-colors group">
                    <Github size={16} className="group-hover:scale-110 transition-transform"/>
                    <span>GitHub 專案源碼</span>
                </a>
                <a href={SYSTEM_CONFIG.OFFICIAL_URL} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-xs text-stone-500 hover:text-primary transition-colors group">
                    <Globe size={16} className="group-hover:scale-110 transition-transform"/>
                    <span>正式版網站 (Streamlit)</span>
                </a>
                
                <div className="mt-4 p-3 bg-stone-100/50 rounded-xl border border-gold/5">
                   <div className="flex items-center gap-2 text-emerald-600 mb-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                      <span className="text-[9px] font-bold uppercase tracking-widest">Database Connected</span>
                   </div>
                   <p className="text-[8px] text-stone-400 font-mono truncate">{SYSTEM_CONFIG.TEXT_DB_PATH}</p>
                </div>
            </div>
        </aside>
    );
};

// --- DATA MAINTENANCE PAGE ---

const LabelInput: React.FC<{ label: string; icon: React.ReactNode; children: React.ReactNode }> = ({ label, icon, children }) => (
  <div className="space-y-1.5">
    <label className="flex items-center gap-2 text-[11px] font-bold text-stone-500 uppercase tracking-wider ml-1">
      {icon} {label}
    </label>
    {children}
  </div>
);

const MaintenancePage: React.FC<{
  onAdd: (p: Product) => void,
  onReset: () => void,
  editingProduct: Product | null,
  clearEditing: () => void,
  productsList: Product[]
}> = ({ onAdd, onReset, editingProduct, clearEditing, productsList }) => {
  const [subPage, setSubPage] = useState<'add' | 'edit' | 'reset'>('add');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    code: '', category: '', number: '', name: '', sn: '', location: '北辦', stock: 1,
    hasWarranty: false, warrantyStart: '', warrantyEnd: '', 
    accName: '', accQty: 1, imagePreview: ''
  });
  const [accessories, setAccessories] = useState<{name: string, qty: number}[]>([]);

  // Effect to load editing data
  useEffect(() => {
    if (editingProduct) {
      setSubPage('add'); // Reuse the form
      setForm({
        code: editingProduct.Code,
        category: editingProduct.Category,
        number: editingProduct.Number,
        name: editingProduct.Name,
        sn: editingProduct.SN || '',
        location: editingProduct.Location,
        stock: editingProduct.Stock,
        hasWarranty: !!editingProduct.WarrantyEnd,
        warrantyStart: editingProduct.WarrantyStart || '',
        warrantyEnd: editingProduct.WarrantyEnd || '',
        accName: '',
        accQty: 1,
        imagePreview: editingProduct.ImageFile
      });
      // Parse accessories string
      if (editingProduct.Accessories) {
        const accs = editingProduct.Accessories.split(', ').map(a => {
           const parts = a.split('x');
           return { name: parts[0], qty: parseInt(parts[1]) || 1 };
        });
        setAccessories(accs);
      } else {
        setAccessories([]);
      }
    }
  }, [editingProduct]);

  const generatedSKU = useMemo(() => {
    if (!form.code && !form.category && !form.number) return "SKU-PREVIEW-000";
    return `${form.code || '??'}-${form.category || '??'}-${form.number || '??'}`.toUpperCase();
  }, [form.code, form.category, form.number]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setForm(prev => ({ ...prev, imagePreview: reader.result as string }));
      };
      reader.readAsDataURL(file);
    }
  };

  const addAccessory = () => {
    if (!form.accName) return;
    setAccessories([...accessories, { name: form.accName, qty: form.accQty }]);
    setForm({ ...form, accName: '', accQty: 1 });
  };

  const removeAccessory = (index: number) => {
    setAccessories(accessories.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    if (!form.code || !form.category || !form.number || !form.name) {
      alert("請填寫基本必要欄位 (編碼、分類、編號、名稱)");
      return;
    }
    const accString = accessories.map(a => `${a.name}x${a.qty}`).join(', ');
    
    onAdd({
      SKU: generatedSKU, Code: form.code, Category: form.category, Number: form.number, Name: form.name,
      ImageFile: form.imagePreview, Stock: form.stock, Location: form.location, SN: form.sn,
      WarrantyStart: form.hasWarranty ? form.warrantyStart : null,
      WarrantyEnd: form.hasWarranty ? form.warrantyEnd : null,
      Accessories: accString
    });

    setForm({
      code: '', category: '', number: '', name: '', sn: '', location: '北辦', stock: 1,
      hasWarranty: false, warrantyStart: '', warrantyEnd: '', 
      accName: '', accQty: 1, imagePreview: ''
    });
    setAccessories([]);
    clearEditing();
    alert(`產品 ${generatedSKU} 已成功建立/更新`);
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-20">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Wrench className="text-primary" size={20} />
            <span className="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">System Configuration</span>
          </div>
          <h2 className="text-4xl font-serif font-bold text-stone-800">
            {editingProduct ? '編輯品項' : '資料維護'}
          </h2>
          <p className="text-sm text-stone-400 font-medium mt-1">
            {editingProduct ? `正在修改: ${editingProduct.SKU}` : '管理產品主檔、SKU 編碼與配件標籤'}
          </p>
        </div>
        <div className="flex gap-1 bg-stone-100/80 backdrop-blur p-1.5 rounded-2xl border border-gold/10 shadow-inner">
          <button onClick={() => { clearEditing(); setSubPage('add'); }} className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${subPage === 'add' ? 'bg-white text-primary shadow-md' : 'text-stone-400 hover:text-stone-600'}`}>
            <Plus size={14} /> 新增/編輯
          </button>
          <button onClick={() => setSubPage('edit')} className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${subPage === 'edit' ? 'bg-white text-stone-800 shadow-md' : 'text-stone-400 hover:text-stone-600'}`}>
            <ListPlus size={14} /> 清單選取
          </button>
          <button onClick={() => setSubPage('reset')} className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${subPage === 'reset' ? 'bg-white text-rose-500 shadow-md' : 'text-stone-400 hover:text-stone-600'}`}>
            <RotateCcw size={14} /> 重置緩存
          </button>
        </div>
      </header>

      {subPage === 'add' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="glass border border-gold/10 p-8 rounded-[2.5rem] shadow-xl shadow-stone-200/20 space-y-8">
              {/* Image & SKU Preview Row */}
              <div className="flex flex-col md:flex-row items-center gap-8 pb-8 border-b border-gold/5">
                <div className="relative group w-40 h-40 rounded-[2rem] bg-stone-50 border-2 border-dashed border-gold/20 overflow-hidden flex items-center justify-center transition-all hover:border-primary/50">
                  {form.imagePreview ? (
                    <img src={resolveImageUrl(form.imagePreview)} className="w-full h-full object-cover" />
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-stone-300">
                      <Camera size={32} />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Upload Photo</span>
                    </div>
                  )}
                  <input type="file" ref={fileInputRef} onChange={handleImageUpload} className="hidden" accept="image/*" />
                  <button onClick={() => fileInputRef.current?.click()} className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 backdrop-blur-[2px]">
                    <div className="flex flex-col items-center text-white gap-2">
                      <Upload size={24}/>
                      <span className="text-[10px] font-bold uppercase tracking-widest">更換圖片</span>
                    </div>
                  </button>
                </div>
                
                <div className="flex-1 space-y-4">
                  <div className="p-4 bg-stone-50 rounded-2xl border border-gold/5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">SKU Generation Preview</span>
                      {editingProduct && (
                        <span className="text-[9px] font-bold px-2 py-0.5 bg-amber-100 text-amber-600 rounded-full">編輯模式</span>
                      )}
                    </div>
                    <div className="text-2xl font-mono font-bold text-primary tracking-wider">{generatedSKU}</div>
                  </div>
                  <p className="text-xs text-stone-400 leading-relaxed">更換圖片後，請務必按下下方的同步按鈕，系統會自動上傳至 R2 物件儲存空間並更新連結。</p>
                </div>
              </div>

              {/* Input Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <LabelInput label="編碼 (Code)" icon={<Hash size={12}/>}>
                  <input type="text" placeholder="例: EQ" value={form.code} onChange={e => setForm({...form, code: e.target.value.toUpperCase()})} className="input" />
                </LabelInput>
                <LabelInput label="分類 (Category)" icon={<Layers size={12}/>}>
                  <input type="text" placeholder="例: NC" value={form.category} onChange={e => setForm({...form, category: e.target.value.toUpperCase()})} className="input" />
                </LabelInput>
                <LabelInput label="編號 (Number)" icon={<Calculator size={12}/>}>
                  <input type="text" placeholder="例: 001" value={form.number} onChange={e => setForm({...form, number: e.target.value})} className="input" />
                </LabelInput>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <LabelInput label="產品名稱" icon={<Tag size={12}/>}>
                  <input type="text" placeholder="請輸入產品全稱" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="input" />
                </LabelInput>
                <LabelInput label="S/N 序號" icon={<Info size={12}/>}>
                  <input type="text" placeholder="如有序號請填寫" value={form.sn} onChange={e => setForm({...form, sn: e.target.value})} className="input" />
                </LabelInput>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <LabelInput label="存放位置" icon={<MapPin size={12}/>}>
                  <select value={form.location} onChange={e => setForm({...form, location: e.target.value})} className="input">
                    <option>北辦</option><option>中辦</option><option>南辦</option><option>醫院</option><option>客戶端</option>
                  </select>
                </LabelInput>
                <LabelInput label="庫存量" icon={<Box size={12}/>}>
                  <input type="number" min="0" value={form.stock} onChange={e => setForm({...form, stock: parseInt(e.target.value) || 0})} className="input" />
                </LabelInput>
              </div>

              {/* Warranty Section */}
              <div className="pt-6 border-t border-gold/5">
                <label className="flex items-center gap-3 cursor-pointer group mb-4">
                  <div className={`w-5 h-5 rounded border-2 transition-all flex items-center justify-center ${form.hasWarranty ? 'bg-primary border-primary' : 'border-stone-200 group-hover:border-primary/50'}`}>
                    {form.hasWarranty && <X size={14} className="text-white rotate-45" />}
                  </div>
                  <input type="checkbox" checked={form.hasWarranty} onChange={e => setForm({...form, hasWarranty: e.target.checked})} className="hidden" />
                  <span className="text-sm font-bold text-stone-600">啟用合約/保固日期設定</span>
                </label>
                
                <AnimatePresence>
                  {form.hasWarranty && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-6 overflow-hidden">
                      <LabelInput label="保固開始" icon={<Calendar size={12}/>}>
                        <input type="date" value={form.warrantyStart} onChange={e => setForm({...form, warrantyStart: e.target.value})} className="input" />
                      </LabelInput>
                      <LabelInput label="保固結束" icon={<Calendar size={12}/>}>
                        <input type="date" value={form.warrantyEnd} onChange={e => setForm({...form, warrantyEnd: e.target.value})} className="input" />
                      </LabelInput>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex gap-4">
                 {editingProduct && (
                   <button onClick={() => { clearEditing(); setForm({...form, code:'', category:'', number:'', name:''}); }} className="px-8 py-5 rounded-[1.5rem] font-bold text-stone-400 hover:bg-stone-100 transition-all">取消編輯</button>
                 )}
                 <button onClick={handleSave} className="flex-1 bg-primary text-white py-5 rounded-[1.5rem] font-bold shadow-xl shadow-primary/20 flex items-center justify-center gap-3 hover:bg-gold-dark hover:scale-[1.01] transition-all active:scale-[0.99]">
                  <Save size={20} /> 同步至雲端文字資料庫
                </button>
              </div>
            </div>
          </div>

          {/* Sidebar Area: Accessory Tags */}
          <div className="space-y-6">
            <div className="glass border border-gold/10 p-8 rounded-[2.5rem] shadow-xl shadow-stone-200/10">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xs font-bold text-stone-500 uppercase tracking-[0.2em] flex items-center gap-2">
                  <ListPlus size={14} className="text-primary"/> 配件標籤清單
                </h3>
                <span className="bg-stone-100 text-stone-500 text-[10px] font-bold px-2 py-0.5 rounded-full">{accessories.length}</span>
              </div>
              
              <div className="space-y-4">
                <div className="space-y-3">
                  <input type="text" placeholder="輸入配件名稱..." value={form.accName} onChange={e => setForm({...form, accName: e.target.value})} className="input bg-white/80" />
                  <div className="flex gap-2">
                    <input type="number" min="1" value={form.accQty} onChange={e => setForm({...form, accQty: parseInt(e.target.value) || 1})} className="input w-24 bg-white/80" />
                    <button onClick={addAccessory} className="flex-1 bg-stone-800 text-white rounded-xl text-xs font-bold hover:bg-stone-700 transition-colors">加入標籤</button>
                  </div>
                </div>

                <div className="pt-4 border-t border-gold/5 min-h-[200px] flex flex-wrap gap-2 content-start">
                  {accessories.length > 0 ? (
                    accessories.map((acc, i) => (
                      <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} key={i} className="group bg-white pl-3 pr-2 py-2 rounded-xl flex items-center gap-3 border border-gold/10 text-xs font-bold shadow-sm hover:border-primary/30 transition-all">
                        <span className="text-stone-700">{acc.name}</span>
                        <span className="text-primary px-1.5 py-0.5 bg-gold/5 rounded-md">x{acc.qty}</span>
                        <button onClick={() => removeAccessory(i)} className="text-stone-300 hover:text-rose-500 transition-colors">
                          <X size={14} />
                        </button>
                      </motion.div>
                    ))
                  ) : (
                    <div className="w-full flex flex-col items-center justify-center py-12 text-stone-300 gap-2 italic">
                       <Tag size={24} className="opacity-20" />
                       <p className="text-[10px] font-bold tracking-widest uppercase">No accessories added</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : subPage === 'edit' ? (
        <div className="max-w-4xl mx-auto space-y-6">
           <div className="glass p-8 rounded-[2.5rem] border border-gold/10 shadow-xl">
              <h3 className="text-xl font-serif font-bold text-stone-800 mb-6">選取產品進行編輯</h3>
              <div className="space-y-3">
                 {productsList.map(p => (
                   <button key={p.SKU} onClick={() => { setSubPage('add'); clearEditing(); onAdd(p); /* Just a hack to trigger parent state if needed, but we'll use local trigger */ }} className="w-full flex items-center gap-4 p-4 rounded-2xl bg-white hover:bg-stone-50 border border-gold/5 transition-all text-left group">
                      <div className="w-12 h-12 rounded-xl overflow-hidden shrink-0 border border-stone-100">
                        <img src={resolveImageUrl(p.ImageFile)} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1">
                         <div className="font-bold text-stone-800">{p.Name}</div>
                         <div className="text-xs font-mono text-stone-400">{p.SKU}</div>
                      </div>
                      <Edit size={16} className="text-stone-300 group-hover:text-primary transition-colors"/>
                   </button>
                 ))}
              </div>
           </div>
        </div>
      ) : (
        <div className="glass p-16 rounded-[3rem] text-center border border-gold/10 shadow-2xl space-y-8 max-w-2xl mx-auto">
          <div className="w-24 h-24 bg-rose-50 rounded-[2rem] flex items-center justify-center mx-auto text-rose-500 shadow-inner">
            <RotateCcw size={40} />
          </div>
          <div>
            <h3 className="text-2xl font-serif font-bold text-stone-800">重置本地與雲端緩存？</h3>
            <p className="text-sm text-stone-400 mt-3 leading-relaxed max-w-sm mx-auto">這項操作將清空當前瀏覽器的模擬緩存，並還原回初始設定狀態。此動作無法復原。</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
             <button onClick={() => setSubPage('add')} className="px-10 py-4 rounded-2xl font-bold text-stone-500 hover:bg-stone-50 transition-all">取消操作</button>
             <button onClick={onReset} className="bg-rose-600 text-white px-12 py-4 rounded-2xl font-bold shadow-xl shadow-rose-200 hover:bg-rose-700 hover:scale-105 transition-all">確認重置資料庫</button>
          </div>
        </div>
      )}
    </div>
  );
}

// --- APP CORE ---

const App: React.FC = () => {
    const [page, setPage] = useState<Page>('overview');
    const [products, setProducts] = useState<Product[]>(initialProducts);
    const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);

    const addProduct = useCallback((p: Product) => {
      setProducts(prev => {
        const exists = prev.find(item => item.SKU === p.SKU);
        if (exists) {
          return prev.map(item => item.SKU === p.SKU ? p : item);
        }
        return [p, ...prev];
      });
      setLogs(prev => [{ Time: getCurrentTimestamp(), User: 'Admin', Type: '新增', SKU: p.SKU, Name: p.Name, Quantity: p.Stock, Note: '建立/更新品項' }, ...prev]);
    }, []);

    const triggerEdit = (p: Product) => {
      setEditingProduct(p);
      setPage('maintenance');
    };

    const resetDatabase = () => {
      setProducts(initialProducts);
      setLogs(initialLogs);
      setPage('overview');
    };

    return (
        <div className="h-screen w-screen flex bg-background font-sans relative overflow-hidden">
            <div className="absolute inset-0 z-0 opacity-[0.04]"><HeroScene /></div>
            <Sidebar currentPage={page} setPage={setPage} />
            <main className="flex-1 overflow-y-auto relative z-10 p-8 md:p-12">
                <AnimatePresence mode='wait'>
                    <motion.div key={page} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.3 }}>
                        {page === 'overview' && <OverviewPage products={products} onEdit={triggerEdit} />}
                        {page === 'maintenance' && (
                          <MaintenancePage 
                            onAdd={addProduct} 
                            onReset={resetDatabase} 
                            editingProduct={editingProduct} 
                            clearEditing={() => setEditingProduct(null)}
                            productsList={products}
                          />
                        )}
                        {page === 'logs' && <LogsPage logs={logs} />}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
};

const OverviewPage: React.FC<{ products: Product[], onEdit: (p: Product) => void }> = ({ products, onEdit }) => (
    <div className="space-y-10 max-w-6xl mx-auto">
        <header>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-1 h-1 rounded-full bg-primary"></div>
              <span className="text-[10px] font-bold text-primary uppercase tracking-[0.3em]">Live Inventory Tracking</span>
            </div>
            <h2 className="text-4xl font-serif font-bold text-stone-800">庫存總覽</h2>
            <p className="text-sm text-stone-400 mt-1">當前全區域儀器與消耗品即時狀態</p>
        </header>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {products.map(p => (
                <motion.div whileHover={{ y: -5 }} key={p.SKU} className="relative glass p-5 rounded-[2rem] border border-gold/10 flex items-center gap-5 shadow-sm hover:shadow-xl hover:shadow-stone-200/40 transition-all group">
                    {/* Edit Overlay Button */}
                    <button 
                      onClick={(e) => { e.stopPropagation(); onEdit(p); }}
                      className="absolute top-4 right-4 p-2 bg-white/80 rounded-full border border-gold/10 text-stone-400 hover:text-primary hover:bg-white shadow-sm opacity-0 group-hover:opacity-100 transition-all scale-90 hover:scale-110"
                      title="編輯此產品資料"
                    >
                      <Edit size={14} />
                    </button>

                    <div className="w-20 h-20 rounded-2xl bg-stone-100 overflow-hidden border border-gold/5 shrink-0 group-hover:scale-105 transition-transform">
                        <img src={resolveImageUrl(p.ImageFile)} className="w-full h-full object-cover" onError={(e) => (e.currentTarget.src = 'https://via.placeholder.com/150')} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                           <span className="px-2 py-0.5 rounded-md bg-stone-100 text-stone-400 text-[9px] font-bold uppercase tracking-wider">{p.Location}</span>
                           <span className={`text-[9px] font-bold ${checkWarrantyStatus(p.WarrantyEnd).status === '正常' ? 'text-emerald-500' : 'text-rose-500'}`}>
                             {checkWarrantyStatus(p.WarrantyEnd).status}
                           </span>
                        </div>
                        <h4 className="font-bold text-stone-800 truncate text-base">{p.Name}</h4>
                        <p className="text-[10px] text-stone-400 font-mono tracking-wider">{p.SKU}</p>
                    </div>
                    <div className="text-right pl-2 border-l border-gold/5">
                        <span className="text-2xl font-bold text-primary tabular-nums leading-none block">{p.Stock}</span>
                        <p className="text-[8px] text-stone-400 uppercase font-bold tracking-widest mt-1">Units</p>
                    </div>
                </motion.div>
            ))}
        </div>
    </div>
);

const LogsPage: React.FC<{ logs: LogEntry[] }> = ({ logs }) => (
    <div className="max-w-6xl mx-auto space-y-10">
        <header>
            <h2 className="text-4xl font-serif font-bold text-stone-800">操作日誌</h2>
            <p className="text-sm text-stone-400 mt-1">所有進出庫、系統修改之完整異動紀錄</p>
        </header>
        <div className="glass rounded-[2.5rem] border border-gold/10 overflow-hidden shadow-2xl shadow-stone-200/10">
            <table className="w-full text-sm text-left">
                <thead className="bg-stone-50/80 border-b border-gold/10 text-stone-400 font-bold uppercase tracking-[0.15em] text-[10px]">
                    <tr>
                      <th className="px-8 py-5">時間節點 (Time)</th>
                      <th className="px-8 py-5">品項名稱 (Product)</th>
                      <th className="px-8 py-5">作業類型 (Type)</th>
                      <th className="px-8 py-5 text-right">數量 (Qty)</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-stone-100/50">
                    {logs.map((log, i) => (
                        <tr key={i} className="hover:bg-white/60 transition-colors group">
                            <td className="px-8 py-5 font-mono text-stone-400 text-xs">{log.Time}</td>
                            <td className="px-8 py-5">
                               <div className="font-bold text-stone-800">{log.Name}</div>
                               <div className="text-[10px] text-stone-400 font-mono mt-0.5">{log.SKU}</div>
                            </td>
                            <td className="px-8 py-5">
                               <span className={`px-3 py-1 rounded-full text-[10px] font-bold tracking-wider ${
                                 log.Type === '入庫' ? 'bg-emerald-50 text-emerald-600' : 
                                 log.Type === '出庫' ? 'bg-rose-50 text-rose-600' : 
                                 'bg-stone-100 text-stone-600'
                               }`}>{log.Type}</span>
                            </td>
                            <td className="px-8 py-5 text-right font-bold text-stone-700 group-hover:text-primary transition-colors">{log.Quantity}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {logs.length === 0 && (
              <div className="py-20 text-center text-stone-300 font-serif italic">No logs recorded yet.</div>
            )}
        </div>
    </div>
);

export default App;
