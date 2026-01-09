
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
  Plus, Edit, Image as ImageIcon, RotateCcw, Save, X, Layers, Upload, Camera, ExternalLink, Github, Globe, Hash, Calendar, ListPlus, Calculator, Loader2, Cloud, RefreshCw, Bot, SendHorizonal, MessageCircle
} from 'lucide-react';
import { HeroScene } from './components/QuantumScene';
import { GoogleGenAI } from "@google/genai";

// --- SYSTEM CONFIGURATION ---
const SYSTEM_CONFIG = {
  FIREBASE_URL: "https://product-system-900c4-default-rtdb.firebaseio.com", 
  IMAGE_DB_PATH: "pub-12069eb186dd414482e689701534d8d5.r2.dev",
  GITHUB_URL: "https://github.com/keapril/WebInventory",
  OFFICIAL_URL: "https://webfce.streamlit.app/",
  VERSION: "2.8.0-AI-Integrated"
};

// Helper to resolve image URLs
const resolveImageUrl = (path: string) => {
  if (!path) return 'https://via.placeholder.com/400?text=No+Image';
  if (path.startsWith('http') || path.startsWith('data:')) return path;
  return `https://${SYSTEM_CONFIG.IMAGE_DB_PATH}/${path}`;
};

const getCurrentTimestamp = () => new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }).replace(/\//g, '-');

// --- AI CHAT COMPONENT ---
const AIChat: React.FC<{ products: Product[] }> = ({ products }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{role: 'user' | 'ai', text: string}[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isTyping]);

  const handleAskAI = async () => {
    if (!input.trim() || isTyping) return;
    
    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsTyping(true);

    try {
      const apiKey = process.env.API_KEY;
      if (!apiKey) {
        setTimeout(() => {
          setMessages(prev => [...prev, { role: 'ai', text: "哎呀！偵測不到 GEMINI_API_KEY。請在 Vercel 設定中加入金鑰，我才能幫您分析數據。目前我暫時無法回答您的問題喔！" }]);
          setIsTyping(false);
        }, 1000);
        return;
      }

      const ai = new GoogleGenAI({ apiKey });
      const context = JSON.stringify(products.map(p => ({ SKU: p.SKU, Name: p.Name, Stock: p.Stock, Location: p.Location })));
      
      const response = await ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: userMsg,
        config: {
          systemInstruction: `妳是一位專業的庫存管理助手。以下是目前的即時庫存數據：${context}。請根據這些數據回答使用者的問題。如果數據中找不到，請委婉告知。請使用繁體中文回答，語氣親切專業。`,
          temperature: 0.7,
        }
      });

      setMessages(prev => [...prev, { role: 'ai', text: response.text || "抱歉，我現在有點混亂，請再問一次。" }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'ai', text: "連線 AI 服務時發生錯誤，請檢查您的 API 金鑰是否正確。" }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="mb-4 w-80 md:w-96 glass border border-gold/20 rounded-[2rem] shadow-2xl overflow-hidden flex flex-col"
            style={{ height: '500px' }}
          >
            <div className="p-4 bg-primary text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot size={20} />
                <span className="font-bold text-sm tracking-wide">AI 智慧助手</span>
              </div>
              <button onClick={() => setIsOpen(false)}><X size={20}/></button>
            </div>
            
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-stone-50/30">
              {messages.length === 0 && (
                <div className="text-center py-10 px-6">
                  <Bot size={40} className="mx-auto text-primary/30 mb-3" />
                  <p className="text-stone-400 text-xs font-serif italic">我是您的量子庫存助手，您可以問我有關庫存的任何問題！</p>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-xs font-medium shadow-sm ${
                    m.role === 'user' ? 'bg-primary text-white' : 'bg-white border border-gold/10 text-stone-700'
                  }`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                   <div className="bg-white border border-gold/10 px-4 py-2 rounded-2xl flex items-center gap-1">
                      <div className="w-1 h-1 bg-primary rounded-full animate-bounce"></div>
                      <div className="w-1 h-1 bg-primary rounded-full animate-bounce delay-75"></div>
                      <div className="w-1 h-1 bg-primary rounded-full animate-bounce delay-150"></div>
                   </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-gold/10 bg-white">
              <div className="flex gap-2">
                <input 
                  type="text" 
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAskAI()}
                  placeholder="詢問庫存狀況..." 
                  className="flex-1 bg-stone-100 border-none rounded-xl px-4 py-2 text-xs focus:ring-1 focus:ring-primary"
                />
                <button 
                  onClick={handleAskAI}
                  className="p-2 bg-primary text-white rounded-xl hover:bg-gold-dark transition-colors shadow-lg shadow-primary/20"
                >
                  <SendHorizonal size={18} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 bg-primary text-white rounded-full shadow-2xl shadow-primary/40 flex items-center justify-center relative group overflow-hidden"
      >
        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
        <Bot size={28} className="relative z-10" />
        {!isOpen && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 rounded-full border-2 border-white animate-pulse"></span>
        )}
      </motion.button>
    </div>
  );
};

// --- SIDEBAR COMPONENT ---
const Sidebar: React.FC<{ currentPage: Page; setPage: (page: Page) => void; isSyncing: boolean }> = ({ currentPage, setPage, isSyncing }) => {
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

            <div className="px-6 py-6 space-y-4 border-t border-gold/5">
                <div className="flex items-center gap-2 text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-2">
                   <Cloud size={12} /> Cloud Infrastructure
                </div>
                <div className="p-3 bg-stone-100/50 rounded-xl border border-gold/5 overflow-hidden">
                   <p className="text-[8px] text-stone-400 font-mono truncate">{SYSTEM_CONFIG.FIREBASE_URL}</p>
                   <div className="flex items-center justify-between mt-2">
                      <p className="text-[8px] text-emerald-600 font-bold uppercase flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Online
                      </p>
                      {isSyncing && <RefreshCw size={10} className="text-primary animate-spin" />}
                   </div>
                </div>
                <div className="text-[9px] text-stone-400 font-bold text-center">v{SYSTEM_CONFIG.VERSION}</div>
            </div>
        </aside>
    );
};

const LabelInput: React.FC<{ label: string; icon: React.ReactNode; children: React.ReactNode }> = ({ label, icon, children }) => (
  <div className="space-y-1.5">
    <label className="flex items-center gap-2 text-[11px] font-bold text-stone-500 uppercase tracking-wider ml-1">
      {icon} {label}
    </label>
    {children}
  </div>
);

// --- MAINTENANCE PAGE ---
const MaintenancePage: React.FC<{
  onSave: (p: Product) => Promise<void>,
  editingProduct: Product | null,
  clearEditing: () => void,
  setEditingProduct: (p: Product) => void,
  productsList: Product[],
  isSaving: boolean
}> = ({ onSave, editingProduct, clearEditing, setEditingProduct, productsList, isSaving }) => {
  const [subPage, setSubPage] = useState<'add' | 'edit'>('add');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    code: '', category: '', number: '', name: '', sn: '', location: '北辦', stock: 1,
    hasWarranty: false, warrantyStart: '', warrantyEnd: '', 
    accName: '', accQty: 1, imagePreview: ''
  });
  const [accessories, setAccessories] = useState<{name: string, qty: number}[]>([]);

  useEffect(() => {
    if (editingProduct) {
      setSubPage('add');
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
      if (editingProduct.Accessories) {
        const accs = editingProduct.Accessories.split(', ').filter(Boolean).map(a => {
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

  const submitForm = async () => {
    if (!form.code || !form.category || !form.number || !form.name) {
      alert("請填寫基本必要欄位 (編碼、分類、編號、名稱)");
      return;
    }
    const accString = accessories.map(a => `${a.name}x${a.qty}`).join(', ');
    
    await onSave({
      SKU: generatedSKU, Code: form.code, Category: form.category, Number: form.number, Name: form.name,
      ImageFile: form.imagePreview, Stock: form.stock, Location: form.location, SN: form.sn,
      WarrantyStart: form.hasWarranty ? form.warrantyStart : null,
      WarrantyEnd: form.hasWarranty ? form.warrantyEnd : null,
      Accessories: accString
    });

    if (!editingProduct) {
      setForm({
        code: '', category: '', number: '', name: '', sn: '', location: '北辦', stock: 1,
        hasWarranty: false, warrantyStart: '', warrantyEnd: '', 
        accName: '', accQty: 1, imagePreview: ''
      });
      setAccessories([]);
    }
    clearEditing();
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-20">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Wrench className="text-primary" size={20} />
            <span className="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Maintenance Terminal</span>
          </div>
          <h2 className="text-4xl font-serif font-bold text-stone-800">
            {editingProduct ? '編輯品項/更換圖片' : '資料維護'}
          </h2>
          <p className="text-sm text-stone-400 font-medium mt-1">針對已建檔產品進行資訊更新與雲端同步</p>
        </div>
        <div className="flex gap-1 bg-stone-100/80 backdrop-blur p-1.5 rounded-2xl border border-gold/10 shadow-inner">
          <button onClick={() => { clearEditing(); setSubPage('add'); }} className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${subPage === 'add' ? 'bg-white text-primary shadow-md' : 'text-stone-400 hover:text-stone-600'}`}>
            <Plus size={14} /> 新增/編輯
          </button>
          <button onClick={() => setSubPage('edit')} className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${subPage === 'edit' ? 'bg-white text-stone-800 shadow-md' : 'text-stone-400 hover:text-stone-600'}`}>
            <ListPlus size={14} /> 選項切換
          </button>
        </div>
      </header>

      {subPage === 'add' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="glass border border-gold/10 p-8 rounded-[2.5rem] shadow-xl shadow-stone-200/20 space-y-8">
              
              <div className="flex flex-col md:flex-row items-center gap-8 pb-8 border-b border-gold/5">
                <div className="relative group w-48 h-48 rounded-[2.5rem] bg-stone-50 border-2 border-dashed border-gold/20 overflow-hidden flex items-center justify-center transition-all hover:border-primary/50">
                  {form.imagePreview ? (
                    <img src={resolveImageUrl(form.imagePreview)} className="w-full h-full object-cover" />
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-stone-300">
                      <Camera size={40} />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Empty Image</span>
                    </div>
                  )}
                  <input type="file" ref={fileInputRef} onChange={handleImageUpload} className="hidden" accept="image/*" />
                  <button onClick={() => fileInputRef.current?.click()} className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 backdrop-blur-[2px]">
                    <div className="flex flex-col items-center text-white gap-2">
                      <Upload size={28}/>
                      <span className="text-[11px] font-bold uppercase tracking-widest">更換產品圖片</span>
                    </div>
                  </button>
                </div>
                
                <div className="flex-1 space-y-4">
                  <div className="p-5 bg-stone-50 rounded-[2rem] border border-gold/5 shadow-inner">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-stone-400 uppercase tracking-widest">System Identifier (SKU)</span>
                      {editingProduct && (
                        <span className="text-[9px] font-bold px-3 py-1 bg-primary/10 text-primary rounded-full animate-pulse">編輯模式</span>
                      )}
                    </div>
                    <div className="text-3xl font-mono font-bold text-primary tracking-widest">{generatedSKU}</div>
                  </div>
                  <p className="text-xs text-stone-400 leading-relaxed italic">提示：更換圖片後，請按下方的儲存按鈕，系統會將圖片資料同步回您的 Firebase 資料庫。</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <LabelInput label="產品代碼" icon={<Hash size={12}/>}>
                  <input type="text" placeholder="EQ" value={form.code} onChange={e => setForm({...form, code: e.target.value.toUpperCase()})} className="input" />
                </LabelInput>
                <LabelInput label="分類標記" icon={<Layers size={12}/>}>
                  <input type="text" placeholder="NC" value={form.category} onChange={e => setForm({...form, category: e.target.value.toUpperCase()})} className="input" />
                </LabelInput>
                <LabelInput label="流水編號" icon={<Calculator size={12}/>}>
                  <input type="text" placeholder="001" value={form.number} onChange={e => setForm({...form, number: e.target.value})} className="input" />
                </LabelInput>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <LabelInput label="產品完整名稱" icon={<Tag size={12}/>}>
                  <input type="text" placeholder="輸入產品全稱..." value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="input" />
                </LabelInput>
                <LabelInput label="S/N 設備序號" icon={<Info size={12}/>}>
                  <input type="text" placeholder="如有序號請填寫..." value={form.sn} onChange={e => setForm({...form, sn: e.target.value})} className="input" />
                </LabelInput>
              </div>

              <div className="flex gap-4 pt-4">
                <button 
                  disabled={isSaving}
                  onClick={submitForm} 
                  className={`flex-1 bg-primary text-white py-5 rounded-[1.5rem] font-bold shadow-xl shadow-primary/20 flex items-center justify-center gap-3 transition-all ${isSaving ? 'opacity-50' : 'hover:bg-gold-dark hover:scale-[1.01]'}`}
                >
                  {isSaving ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                  {isSaving ? '正在同步至雲端...' : '確認修改並同步雲端'}
                </button>
                {editingProduct && (
                  <button onClick={() => { clearEditing(); setForm({...form, code:'', category:'', number:'', name:'', imagePreview:''}); }} className="px-8 py-5 rounded-[1.5rem] font-bold text-stone-400 hover:bg-stone-100 transition-all border border-stone-200">取消</button>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass border border-gold/10 p-8 rounded-[2.5rem] shadow-xl shadow-stone-200/10 h-full">
              <h3 className="text-xs font-bold text-stone-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                <ListPlus size={14} className="text-primary"/> 配件/標籤明細
              </h3>
              <div className="space-y-4">
                <div className="space-y-3">
                  <input type="text" placeholder="配件名稱..." value={form.accName} onChange={e => setForm({...form, accName: e.target.value})} className="input bg-white/80" />
                  <div className="flex gap-2">
                    <input type="number" min="1" value={form.accQty} onChange={e => setForm({...form, accQty: parseInt(e.target.value) || 1})} className="input w-24 bg-white/80" />
                    <button onClick={addAccessory} className="flex-1 bg-stone-800 text-white rounded-xl text-xs font-bold hover:bg-stone-700 transition-colors">加入標籤</button>
                  </div>
                </div>
                <div className="pt-4 flex flex-wrap gap-2">
                  {accessories.map((acc, i) => (
                    <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }} key={i} className="bg-white pl-3 pr-2 py-2 rounded-xl flex items-center gap-3 border border-gold/10 text-xs font-bold shadow-sm">
                      <span className="text-stone-700">{acc.name}</span>
                      <span className="text-primary px-1.5 py-0.5 bg-gold/5 rounded-md">x{acc.qty}</span>
                      <button onClick={() => removeAccessory(i)} className="text-stone-300 hover:text-rose-500"><X size={14} /></button>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-6">
           <div className="glass p-8 rounded-[2.5rem] border border-gold/10 shadow-xl">
              <h3 className="text-xl font-serif font-bold text-stone-800 mb-6">點擊產品名稱以載入編輯</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                 {productsList.map(p => (
                   <button key={p.SKU} onClick={() => { setEditingProduct(p); setSubPage('add'); }} className="flex items-center gap-4 p-4 rounded-2xl bg-white hover:bg-stone-50 border border-gold/5 transition-all text-left group">
                      <div className="w-14 h-14 rounded-2xl overflow-hidden shrink-0 border border-stone-100 shadow-inner">
                        <img src={resolveImageUrl(p.ImageFile)} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1">
                         <div className="font-bold text-stone-800 group-hover:text-primary transition-colors">{p.Name}</div>
                         <div className="text-[10px] font-mono text-stone-400 mt-1">{p.SKU}</div>
                      </div>
                      <Edit size={16} className="text-stone-200 group-hover:text-primary transition-colors"/>
                   </button>
                 ))}
              </div>
           </div>
        </div>
      )}
    </div>
  );
}

// --- APP CORE ---
const App: React.FC = () => {
    const [page, setPage] = useState<Page>('overview');
    const [products, setProducts] = useState<Product[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);

    const fetchCloudData = useCallback(async () => {
      setIsSyncing(true);
      try {
        const [prodRes, logRes] = await Promise.all([
          fetch(`${SYSTEM_CONFIG.FIREBASE_URL}/products.json`),
          fetch(`${SYSTEM_CONFIG.FIREBASE_URL}/logs.json`)
        ]);
        
        const prodData = await prodRes.json();
        const logData = await logRes.json();
        
        if (prodData) {
          const list = Object.values(prodData) as Product[];
          setProducts(list);
        } else {
          setProducts([]);
        }

        if (logData) {
          const list = Object.values(logData) as LogEntry[];
          setLogs(list.reverse()); // Newest first
        }
      } catch (err) {
        console.error("Firebase Sync Error:", err);
      } finally {
        setIsSyncing(false);
      }
    }, []);

    useEffect(() => {
      fetchCloudData();
    }, [fetchCloudData]);

    const saveToCloud = async (p: Product) => {
      setIsSaving(true);
      try {
        const sanitizedSKU = p.SKU.replace(/\//g, '_').replace(/\./g, '_');
        
        await fetch(`${SYSTEM_CONFIG.FIREBASE_URL}/products/${sanitizedSKU}.json`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(p)
        });
        
        const log: LogEntry = {
          Time: getCurrentTimestamp(),
          User: 'Admin',
          Type: editingProduct ? '修改' : '新增',
          SKU: p.SKU,
          Name: p.Name,
          Quantity: p.Stock,
          Note: editingProduct ? '更換產品資訊/圖片' : '雲端建檔'
        };
        await fetch(`${SYSTEM_CONFIG.FIREBASE_URL}/logs.json`, {
          method: 'POST',
          body: JSON.stringify(log)
        });

        await fetchCloudData();
        setPage('overview');
      } catch (err) {
        console.error("Cloud Save Error:", err);
        alert("資料同步失敗，請確認 Firebase 規則權限。");
      } finally {
        setIsSaving(false);
      }
    };

    return (
        <div className="h-screen w-screen flex bg-background font-sans relative overflow-hidden">
            <div className="absolute inset-0 z-0 opacity-[0.04]"><HeroScene /></div>
            <Sidebar currentPage={page} setPage={setPage} isSyncing={isSyncing} />
            <main className="flex-1 overflow-y-auto relative z-10 p-8 md:p-12">
                <AnimatePresence mode='wait'>
                    <motion.div key={page} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.3 }}>
                        {page === 'overview' && (
                          <OverviewPage 
                            products={products} 
                            onEdit={(p) => { setEditingProduct(p); setPage('maintenance'); }} 
                            isSyncing={isSyncing}
                          />
                        )}
                        {page === 'maintenance' && (
                          <MaintenancePage 
                            onSave={saveToCloud} 
                            editingProduct={editingProduct} 
                            clearEditing={() => setEditingProduct(null)}
                            setEditingProduct={setEditingProduct}
                            productsList={products}
                            isSaving={isSaving}
                          />
                        )}
                        {page === 'logs' && <LogsPage logs={logs} />}
                    </motion.div>
                </AnimatePresence>
            </main>
            <AIChat products={products} />
        </div>
    );
};

const OverviewPage: React.FC<{ products: Product[], onEdit: (p: Product) => void, isSyncing: boolean }> = ({ products, onEdit, isSyncing }) => (
    <div className="space-y-10 max-w-6xl mx-auto">
        <header className="flex justify-between items-end">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-1 h-1 rounded-full bg-primary"></div>
                <span className="text-[10px] font-bold text-primary uppercase tracking-[0.3em]">Cloud Live Monitoring</span>
              </div>
              <h2 className="text-4xl font-serif font-bold text-stone-800">庫存總覽</h2>
              <p className="text-sm text-stone-400 mt-1">同步自 Firebase 之即時數據</p>
            </div>
            {isSyncing && <div className="text-[10px] font-bold text-stone-400 flex items-center gap-2 animate-pulse"><Loader2 size={12} className="animate-spin" /> 同步中...</div>}
        </header>
        
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {products.length > 0 ? products.map(p => (
                <motion.div whileHover={{ y: -5 }} key={p.SKU} className="relative glass p-5 rounded-[2.5rem] border border-gold/10 flex items-center gap-6 shadow-sm hover:shadow-xl hover:shadow-stone-200/40 transition-all group">
                    <button 
                      onClick={(e) => { e.stopPropagation(); onEdit(p); }}
                      className="absolute top-4 right-4 p-2.5 bg-white/90 rounded-full border border-gold/10 text-stone-400 hover:text-primary hover:bg-white shadow-sm opacity-0 group-hover:opacity-100 transition-all scale-90 hover:scale-110"
                      title="更換資訊/圖片"
                    >
                      <Edit size={16} />
                    </button>

                    <div className="w-24 h-24 rounded-3xl bg-stone-100 overflow-hidden border border-gold/5 shrink-0 group-hover:scale-105 transition-transform shadow-inner">
                        <img src={resolveImageUrl(p.ImageFile)} className="w-full h-full object-cover" onError={(e) => (e.currentTarget.src = 'https://via.placeholder.com/300?text=No+Photo')} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                           <span className="px-2.5 py-1 rounded-lg bg-stone-100 text-stone-500 text-[10px] font-bold uppercase tracking-wider">{p.Location}</span>
                        </div>
                        <h4 className="font-bold text-stone-800 truncate text-lg tracking-tight">{p.Name}</h4>
                        <p className="text-[11px] text-stone-400 font-mono tracking-widest mt-1">{p.SKU}</p>
                    </div>
                    <div className="text-right pl-3 border-l border-gold/5">
                        <span className="text-3xl font-bold text-primary tabular-nums block">{p.Stock}</span>
                        <p className="text-[9px] text-stone-400 uppercase font-bold tracking-[0.2em] mt-1">Qty</p>
                    </div>
                </motion.div>
            )) : isSyncing ? (
              <div className="col-span-full py-32 flex flex-col items-center justify-center gap-4 text-stone-300">
                  <Loader2 className="animate-spin text-primary" size={32} />
                  <span className="font-serif italic">正在連接雲端資料庫...</span>
              </div>
            ) : (
              <div className="col-span-full py-32 text-center glass rounded-[3rem] border-dashed border-2 border-stone-200">
                  <Package className="mx-auto text-stone-200 mb-4" size={48} />
                  <div className="text-stone-400 font-serif italic mb-2">雲端目前無產品紀錄</div>
                  <button onClick={() => window.location.reload()} className="text-xs font-bold text-primary hover:underline flex items-center gap-2 mx-auto justify-center"><RefreshCw size={12}/> 重新同步</button>
              </div>
            )}
        </div>
    </div>
);

const LogsPage: React.FC<{ logs: LogEntry[] }> = ({ logs }) => (
    <div className="max-w-6xl mx-auto space-y-10">
        <header>
            <h2 className="text-4xl font-serif font-bold text-stone-800">操作日誌</h2>
            <p className="text-sm text-stone-400 mt-1">Firebase 回傳之歷史異動清單</p>
        </header>
        <div className="glass rounded-[2.5rem] border border-gold/10 overflow-hidden shadow-2xl">
            <table className="w-full text-sm text-left">
                <thead className="bg-stone-50/80 border-b border-gold/10 text-stone-400 font-bold uppercase tracking-[0.15em] text-[10px]">
                    <tr>
                      <th className="px-8 py-5">時間點</th>
                      <th className="px-8 py-5">產品詳情</th>
                      <th className="px-8 py-5">操作類型</th>
                      <th className="px-8 py-5">備註說明</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-stone-100/50">
                    {logs.map((log, i) => (
                        <tr key={i} className="hover:bg-white/60 transition-colors">
                            <td className="px-8 py-5 font-mono text-stone-400 text-xs">{log.Time}</td>
                            <td className="px-8 py-5">
                               <div className="font-bold text-stone-800">{log.Name}</div>
                               <div className="text-[10px] text-stone-400 font-mono mt-0.5">{log.SKU}</div>
                            </td>
                            <td className="px-8 py-5">
                               <span className={`px-3 py-1 rounded-full text-[10px] font-bold tracking-wider ${
                                 log.Type === '入庫' ? 'bg-emerald-50 text-emerald-600' : 
                                 log.Type === '出庫' ? 'bg-rose-50 text-rose-600' :
                                 'bg-amber-50 text-amber-600'
                               }`}>{log.Type}</span>
                            </td>
                            <td className="px-8 py-5 text-stone-500 text-xs italic">{log.Note}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

export default App;
