import React, { useState, useMemo } from 'react';
import { Search, Upload, FileText, Package, List, Tag, Layers, Database, AlertCircle, CheckCircle, X } from 'lucide-react';

// -----------------------------------------------------------------------------
// UI Components (Styled for Warm/Exquisite Theme)
// -----------------------------------------------------------------------------

const Card = ({ children, className = "" }) => (
  <div className={`bg-white rounded-xl shadow-sm border border-stone-100 ${className}`}>
    {children}
  </div>
);

const Button = ({ children, onClick, variant = 'primary', className = "", disabled = false }) => {
  const baseStyle = "px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-orange-400 hover:bg-orange-500 text-white shadow-orange-100 shadow-md",
    secondary: "bg-stone-100 hover:bg-stone-200 text-stone-600",
    outline: "border border-orange-200 text-orange-600 hover:bg-orange-50"
  };
  return (
    <button onClick={onClick} className={`${baseStyle} ${variants[variant]} ${className}`} disabled={disabled}>
      {children}
    </button>
  );
};

const Badge = ({ children }) => (
  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
    {children}
  </span>
);

// -----------------------------------------------------------------------------
// Helper Functions
// -----------------------------------------------------------------------------

// Simple CSV Parser
const parseCSV = (text) => {
  const lines = text.split('\n').filter(line => line.trim() !== '');
  if (lines.length < 2) return [];

  // Assuming first row is header, but we map by index based on user requirement
  // User columns: 產品代碼(0), 產品分類(1), 類別名稱(2), 品名(3), 規格(4) ... based on provided snippet
  // Snippet Header: 產品代碼,產品分類,類別名稱,品名,規格,條碼編號...
  
  const result = [];
  
  // Skip header row (index 0) and process data
  for (let i = 1; i < lines.length; i++) {
    // Handle CSV split (considering potential quotes, though simple split works for simple data)
    // For robustness with the snippet provided, simple split is likely enough, 
    // but regex is safer for quoted fields containing commas.
    const matches = lines[i].match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g); 
    // Fallback to simple split if regex fails or for simple csv
    const columns = matches ? matches.map(m => m.replace(/^"|"$/g, '')) : lines[i].split(',');

    if (columns.length < 5) continue;

    const code = columns[0]?.trim() || '';
    
    // FILTER LOGIC: Filter out "ZZ" or "待" at the start of Product Code
    if (code.toUpperCase().startsWith('ZZ') || code.startsWith('待')) {
      continue;
    }

    result.push({
      id: i, // unique key
      code: code,
      categoryCode: columns[1]?.trim() || '',
      categoryName: columns[2]?.trim() || '',
      name: columns[3]?.trim() || '',
      spec: columns[4]?.trim() || '',
      udi: '' // Placeholder as requested
    });
  }
  return result;
};

// -----------------------------------------------------------------------------
// Main Application
// -----------------------------------------------------------------------------

export default function ProductSystem() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' or 'admin'
  const [data, setData] = useState([
    // Pre-loaded sample data based on user snippet (filtered "待" ones)
    { id: 1, code: '0137NE', categoryCode: '4-04', categoryName: 'Syringes', name: 'Perouse Perouse Syringes 150ml', spec: '', udi: '' },
    { id: 2, code: '0163NA', categoryCode: '4-03', categoryName: 'High Pressure Tubing', name: 'Perouse HighPressure Line 50cm', spec: '1.8mm', udi: '' },
    { id: 3, code: '0163ND', categoryCode: '4-03', categoryName: 'High Pressure Tubing', name: 'Perouse HighPressure Line120cm', spec: '', udi: '' },
    { id: 4, code: '0185NA', categoryCode: '4-02', categoryName: 'Inflation Device', name: 'Perouse Inflation Device 30atm', spec: '', udi: '' },
  ]);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [uploadText, setUploadText] = useState('');
  const [notification, setNotification] = useState(null);

  // Search Logic
  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    const lowerTerm = searchTerm.toLowerCase();
    return data.filter(item => 
      item.code.toLowerCase().includes(lowerTerm) ||
      item.name.toLowerCase().includes(lowerTerm) ||
      item.categoryName.toLowerCase().includes(lowerTerm) ||
      item.spec.toLowerCase().includes(lowerTerm)
    );
  }, [data, searchTerm]);

  // Handle File Upload (Parsing text)
  const handleImport = () => {
    try {
      if (!uploadText) {
        showNotification('請輸入或貼上 CSV 內容', 'error');
        return;
      }
      const parsed = parseCSV(uploadText);
      if (parsed.length === 0) {
        showNotification('無有效資料或格式錯誤 (所有資料可能已被過濾條件排除)', 'error');
        return;
      }
      setData(parsed);
      showNotification(`成功匯入 ${parsed.length} 筆資料`, 'success');
      setUploadText('');
      setActiveTab('search');
    } catch (e) {
      showNotification('解析錯誤，請檢查格式', 'error');
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadText(event.target.result);
    };
    reader.readAsText(file);
  };

  const showNotification = (msg, type) => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 3000);
  };

  // ---------------------------------------------------------------------------
  // Views
  // ---------------------------------------------------------------------------

  const SearchView = () => (
    <div className="space-y-6 animate-fade-in">
      {/* Search Header */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-end md:items-center">
        <div>
          <h2 className="text-2xl font-serif text-stone-800 font-bold mb-1">產品查詢</h2>
          <p className="text-stone-500 text-sm">輸入代碼、品名或規格進行搜尋</p>
        </div>
        <div className="relative w-full md:w-96 group">
          <input
            type="text"
            placeholder="搜尋關鍵字..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-white border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-400 transition-all shadow-sm"
          />
          <Search className="w-5 h-5 text-stone-400 absolute left-3 top-3.5 group-focus-within:text-orange-500 transition-colors" />
        </div>
      </div>

      {/* Data Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-orange-50 border-b border-orange-100">
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm w-32">產品代碼</th>
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm w-32">產品分類</th>
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm w-48">類別名稱</th>
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm">品名</th>
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm w-40">規格</th>
                <th className="py-4 px-6 font-semibold text-stone-700 text-sm w-32">UDI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredData.length > 0 ? (
                filteredData.map((item) => (
                  <tr key={item.id} className="hover:bg-orange-50/50 transition-colors group">
                    <td className="py-4 px-6 text-stone-800 font-medium font-mono">{item.code}</td>
                    <td className="py-4 px-6 text-stone-600">{item.categoryCode}</td>
                    <td className="py-4 px-6">
                      <Badge>{item.categoryName}</Badge>
                    </td>
                    <td className="py-4 px-6 text-stone-800 font-medium">{item.name}</td>
                    <td className="py-4 px-6 text-stone-600 text-sm">{item.spec || '-'}</td>
                    <td className="py-4 px-6 text-stone-400 text-xs italic">
                      {item.udi || '未建立'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="py-12 text-center text-stone-400">
                    <div className="flex flex-col items-center gap-2">
                      <Package className="w-12 h-12 opacity-20" />
                      <p>沒有找到符合的產品資料</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-stone-50 px-6 py-3 border-t border-stone-100 text-xs text-stone-500 flex justify-between items-center">
          <span>共顯示 {filteredData.length} 筆資料</span>
          <span>資料來源：系統匯入</span>
        </div>
      </Card>
    </div>
  );

  const AdminView = () => (
    <div className="max-w-3xl mx-auto space-y-8 animate-fade-in">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-serif text-stone-800 font-bold mb-2">資料管理後台</h2>
        <p className="text-stone-500">上傳 CSV 檔案以更新產品資料庫</p>
      </div>

      <div className="grid gap-6">
        <Card className="p-6 md:p-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-orange-100 rounded-lg text-orange-600">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-stone-800">匯入資料</h3>
          </div>
          
          <div className="space-y-4">
            <div className="border-2 border-dashed border-stone-200 rounded-xl p-8 text-center hover:border-orange-300 hover:bg-orange-50 transition-all cursor-pointer relative">
              <input 
                type="file" 
                accept=".csv,.txt"
                onChange={handleFileUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <FileText className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <p className="text-stone-600 font-medium">點擊選擇檔案 或 拖曳至此</p>
              <p className="text-xs text-stone-400 mt-1">支援格式：CSV, TXT</p>
            </div>

            <div className="relative">
              <div className="absolute top-0 left-0 -mt-2 ml-3 bg-white px-1 text-xs text-stone-400 font-medium">
                或直接貼上 CSV 內容
              </div>
              <textarea
                value={uploadText}
                onChange={(e) => setUploadText(e.target.value)}
                placeholder="產品代碼,產品分類,類別名稱,品名,規格..."
                className="w-full h-48 p-4 border border-stone-200 rounded-xl focus:ring-2 focus:ring-orange-200 focus:border-orange-400 focus:outline-none font-mono text-sm bg-stone-50"
              />
            </div>

            <div className="bg-orange-50 rounded-lg p-4 text-sm text-stone-600 space-y-2">
              <p className="font-semibold text-orange-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                匯入規則說明：
              </p>
              <ul className="list-disc list-inside space-y-1 ml-1 text-stone-600">
                <li>系統將只讀取前 5 欄資料。</li>
                <li>欄位順序須為：產品代碼、產品分類、類別名稱、品名、規格。</li>
                <li>產品代碼若為 <strong>"ZZ"</strong> 或 <strong>"待"</strong> 開頭，將自動過濾不匯入。</li>
              </ul>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={handleImport}>
                確認更新資料庫
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-stone-800 font-sans selection:bg-orange-200">
      {/* Navbar */}
      <nav className="bg-white border-b border-stone-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="bg-orange-500 p-2 rounded-lg text-white shadow-md shadow-orange-200">
                <Database className="w-6 h-6" />
              </div>
              <span className="text-xl font-serif font-bold text-stone-800 tracking-tight">
                產品資料系統
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveTab('search')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === 'search' 
                    ? 'bg-orange-50 text-orange-700' 
                    : 'text-stone-500 hover:bg-stone-50'
                }`}
              >
                <Search className="w-4 h-4" />
                查詢
              </button>
              <button
                onClick={() => setActiveTab('admin')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === 'admin' 
                    ? 'bg-orange-50 text-orange-700' 
                    : 'text-stone-500 hover:bg-stone-50'
                }`}
              >
                <Layers className="w-4 h-4" />
                後台管理
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'search' ? <SearchView /> : <AdminView />}
      </main>

      {/* Notification Toast */}
      {notification && (
        <div className={`fixed bottom-6 right-6 px-6 py-3 rounded-xl shadow-lg flex items-center gap-3 animate-slide-up z-50 ${
          notification.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-500 text-white'
        }`}>
          {notification.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <X className="w-5 h-5" />}
          <span className="font-medium">{notification.msg}</span>
        </div>
      )}

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 py-6 text-center text-stone-400 text-sm">
        &copy; 2025 Product Data System. Designed for Efficiency.
      </footer>
      
      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.4s ease-out forwards;
        }
        @keyframes slide-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
