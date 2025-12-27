import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  
  // NEW: Modal State for SAP Data
  const [modalData, setModalData] = useState(null);

  // NEW: SAP Connection Status State
  const [sapStatus, setSapStatus] = useState({ status: "Checking...", color: "gray" });

  // NEW: Polling logic for SAP Status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await axios.get("http://localhost:8000/sap-status");
        setSapStatus(res.data);
      } catch (err) {
        setSapStatus({ status: "Offline", color: "red" });
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Poll every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const send = async () => {
    if (!input.trim()) return;
    setLoading(true);
      
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    
    try { 
      const res = await axios.post("http://localhost:8000/chat", { 
        message: input,
        history: messages 
      });

      const newHistory = [...res.data.history];
      if (newHistory.length > 0 && res.data.sap_json) {
        newHistory[newHistory.length - 1].sapData = res.data.sap_json;
      }
      setMessages(newHistory);

    } catch (err) {
      setMessages(prev => [...prev, { role: "model", content: "Error: Could not reach SAP." }]);
    }
    
    setLoading(false);
    setInput("");
  };

  // NEW: Helper to format tab-delimited text into Markdown tables
  const formatMessageContent = (content) => {
    if (!content || typeof content !== 'string') return "";
    
    // Check if the content contains tabs and multiple lines (likely a raw table)
    if (content.includes('\t') && content.split('\n').length > 1) {
      const lines = content.split('\n').filter(l => l.trim() !== "");
      const tableLines = lines.map((line, index) => {
        const cells = line.split('\t').map(c => c.trim());
        const row = `| ${cells.join(' | ')} |`;
        if (index === 0) {
          const separator = `| ${cells.map(() => '---').join(' | ')} |`;
          return `${row}\n${separator}`;
        }
        return row;
      });
      return tableLines.join('\n');
    }
    return content;
  };
 
  const renderSapTable = (data) => {
    console.log("Rendering SAP Table with data:", data);
    if (!data || !Array.isArray(data) || data.length === 0) return null;

    // 1. DATA FLATTENING LOGIC (For Cross-Join / QueryService)
    const flattenRow = (row) => {
      let flat = {};
      Object.keys(row).forEach(key => {
        if (typeof row[key] === 'object' && row[key] !== null) {
          // If the key is 'PurchaseInvoices/DocumentLines', we merge its properties
          Object.assign(flat, row[key]);
        } else {
          flat[key] = row[key];
        }
      });
      console.log("Flattened row:", flat);
      return flat;
    };

    // Process the data: If a row contains objects (QueryService style), flatten it
    const processedData = data.map(row => {
      const hasNestedEntities = Object.values(row).some(v => typeof v === 'object' && v !== null);
      return hasNestedEntities ? flattenRow(row) : row;
    });

    // 2. HEADER EXTRACTION
    const headers = Object.keys(processedData[0]).slice(0, 12);

    return (
      <div className="overflow-x-auto my-4 rounded-lg border border-gray-200 shadow-sm bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {headers.map((h) => (
                <th key={h} className="px-4 py-2 text-left font-bold text-gray-700 capitalize whitespace-nowrap">
                  {h.replace(/([A-Z])/g, ' $1').trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {processedData.map((row, i) => (
              <tr key={i} className="hover:bg-blue-50 transition-colors">
                {headers.map((h) => (
                  <td key={h} className="px-4 py-2 text-gray-600 whitespace-nowrap">
                    {typeof row[h] === 'number' 
                      ? row[h].toLocaleString(undefined, { minimumFractionDigits: 2 }) 
                      : String(row[h] || '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="h-screen w-full flex flex-col bg-gray-50 overflow-hidden">
      
      {/* SAP Status Dashboard Pill */}
      <div className="flex items-center justify-between p-4 md:px-10 md:pt-8">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-full shadow-sm border border-gray-100">
          <div className={`w-2.5 h-2.5 rounded-full animate-pulse bg-${sapStatus.color === 'green' ? 'green' : sapStatus.color === 'red' ? 'red' : 'gray'}-500`}></div>
          <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">
            SAP B1: {sapStatus.status}
          </span>
        </div>
      </div>

      {/* Chat History Area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-6 mb-4 px-4 md:px-10">
        <div className="max-w-5xl mx-auto w-full space-y-6">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`p-4 rounded-2xl shadow-sm ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white text-gray-800 border'} max-w-[90%] md:max-w-[80%]`}>
                <div 
                  className="prose prose-sm max-w-none break-words" 
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(formatMessageContent(m.content || ""))) }} 
                />
                {m.sapData && (
                  <button 
                    onClick={() => setModalData(m.sapData)}
                    className="mt-3 flex items-center gap-2 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg border border-blue-200 text-xs font-bold transition-all active:scale-95"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    VIEW SAP DATA ({Array.isArray(m.sapData) ? m.sapData.length : 1} Records)
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-gray-400 animate-pulse ml-2">
              <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
              <span className="text-sm">Gemini is thinking...</span>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 md:px-10 md:pb-8">
        <div className="max-w-5xl mx-auto flex gap-3 bg-white p-3 rounded-xl shadow-lg border border-gray-100">
          <input 
            className="flex-1 outline-none px-2 text-gray-700 bg-transparent" 
            placeholder="Ask about inventory, invoices, or business partners..."
            value={input} 
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
          />
          <button 
            className="bg-blue-600 hover:bg-blue-700 font-bold px-6 py-2 rounded-lg transition-all active:scale-95 text-white" 
            onClick={send}
          >
            Send
          </button>
        </div>
      </div>

      {/* SAP Data Modal */}
      {modalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between bg-gray-50">
              <h3 className="font-black text-gray-800 uppercase tracking-tight flex items-center gap-2">
                <div className="w-2 h-6 bg-blue-600 rounded-full"></div>
                SAP Data Explorer
              </h3>
              <button 
                onClick={() => setModalData(null)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-auto p-6">
              {renderSapTable(modalData)}
            </div>
            <div className="p-4 border-t bg-gray-50 flex justify-end">
              <button 
                onClick={() => setModalData(null)}
                className="px-6 py-2 bg-gray-800 text-white font-bold rounded-lg hover:bg-gray-900 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}