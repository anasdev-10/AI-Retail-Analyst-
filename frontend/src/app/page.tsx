"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Download, Copy, Code, Table as TableIcon, Check } from "lucide-react";
import ChartComponent from "./ChartComponent";

type Message = {
  role: "user" | "assistant";
  content: string;
  payload?: any;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const DEMO_QUESTIONS = [
    "What is the total net sales by category for 2025?",
    "Which store has the highest average order value in Punjab?",
    "Which subcategory has the highest return rate?",
    "Delete low-profit products from the database.",
    "Show the monthly trend for Total Sales for the entire year of 2025 and recommend a chart."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleCopySql = (sql: string, index: number) => {
    navigator.clipboard.writeText(sql);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleDownloadCsv = (data: any[], filename = "data_export.csv") => {
    if (!data || data.length === 0) return;
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(","),
      ...data.map(row => headers.map(header => `"${(row[header] ?? "").toString().replace(/"/g, '""')}"`).join(","))
    ].join("\n");
    
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sendQuery = async (queryText: string) => {
    if (!queryText.trim()) return;

    const userMessage: Message = { role: "user", content: queryText };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Create conversation history from previous messages
      const history = messages.map(m => ({
        role: m.role,
        content: m.content
      }));

      const response = await fetch("http://localhost:8002/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: queryText,
          conversation_history: history
        })
      });

      const data = await response.json();
      
      let assistantContent = data.explanation || data.error || "Query processed.";
      if (data.clarification_needed) {
        assistantContent = `❓ Clarification needed: ${data.clarification_needed}`;
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: assistantContent,
        payload: data
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error connecting to the server: ${error.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuery(input);
    }
  };

  return (
    <div className="layout-container">
      <aside className="sidebar">
        <div className="brand-container">
          <div className="brand-icon">⬡</div>
          <div className="brand-text">
            <h2>RETAIL<br/><span style={{ color: "var(--accent-emerald)" }}>ANALYST</span></h2>
            <p>ENTERPRISE BI ENGINE</p>
          </div>
        </div>

        <div className="demo-questions">
          <h4>🚀 Demo Questions</h4>
          {DEMO_QUESTIONS.map((q, i) => (
            <button key={i} className="demo-btn" onClick={() => sendQuery(q)}>
              Q{i + 1}: {q.substring(0, 40)}...
            </button>
          ))}
        </div>

        <div style={{ marginTop: "auto" }}>
          <button 
            className="demo-btn" 
            style={{ textAlign: "center", borderColor: "var(--border-subtle)" }}
            onClick={() => setMessages([])}
          >
            🗑️ Clear Conversation
          </button>
        </div>
      </aside>

      <main className="main-content">
        {messages.length === 0 && !loading ? (
          <div className="hero-section animate-fade-in-up">
            <div className="status-badge">
              <div className="status-dot"></div>
              <div className="status-text">Production Data Engine Active</div>
            </div>
            <h1 className="hero-title">
              Autonomous <span>Retail Intelligence</span>
            </h1>
            <p className="hero-subtitle">
              Query 2.5 million atomic POS transactions instantly. Backed by verified Kimball dimensional constraints and generative AI reasoning.
            </p>
          </div>
        ) : (
          <div className="chat-container">
            {messages.map((msg, i) => (
              <div key={i} className="message">
                <div className={`message-avatar ${msg.role === "user" ? "user-avatar" : "ai-avatar"}`}>
                  {msg.role === "user" ? "🧑" : "🤖"}
                </div>
                <div className={`message-content ${msg.role}`}>
                  <div className="markdown">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                  
                  {msg.payload?.error && !msg.payload?.blocked && (
                    <div className="error-banner">
                      ⚠️ {msg.payload.error}
                    </div>
                  )}

                  {msg.payload?.blocked && (
                    <div className="error-banner" style={{ borderColor: 'rgba(239, 68, 68, 0.8)', background: 'rgba(239, 68, 68, 0.2)' }}>
                      🛡️ Safety Block: {msg.payload.error}
                    </div>
                  )}

                  {msg.payload?.sql && (
                    <details className="data-expander">
                      <summary style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Code size={18} /> SQL Used (Explainability)
                        </span>
                        <button 
                          onClick={(e) => { e.preventDefault(); handleCopySql(msg.payload.sql, i); }}
                          style={{
                            background: 'transparent', border: '1px solid var(--border-subtle)',
                            color: 'var(--text-main)', borderRadius: '6px', padding: '4px 8px',
                            display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          {copiedIndex === i ? <><Check size={14} color="var(--accent-emerald)" /> Copied</> : <><Copy size={14} /> Copy</>}
                        </button>
                      </summary>
                      <div className="data-expander-content sql-code">
                        {msg.payload.sql}
                      </div>
                    </details>
                  )}

                  {msg.payload?.chart_config && msg.payload?.data && msg.payload.data.length > 0 && (
                    <ChartComponent config={msg.payload.chart_config} data={msg.payload.data} />
                  )}

                  {msg.payload?.data && msg.payload.data.length > 0 && (
                    <details className="data-expander">
                      <summary style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <TableIcon size={18} /> Raw Data ({msg.payload.data.length} rows)
                        </span>
                        <button 
                          onClick={(e) => { e.preventDefault(); handleDownloadCsv(msg.payload.data); }}
                          style={{
                            background: 'var(--accent-emerald)', border: 'none',
                            color: '#fff', borderRadius: '6px', padding: '4px 8px',
                            display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer',
                            fontSize: '12px', fontWeight: 600
                          }}
                        >
                          <Download size={14} /> Download CSV
                        </button>
                      </summary>
                      <div className="data-expander-content" style={{ padding: 0 }}>
                        <div className="table-wrapper">
                          <table>
                            <thead>
                              <tr>
                                {Object.keys(msg.payload.data[0]).map((key) => (
                                  <th key={key}>{key}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {msg.payload.data.map((row: any, rIdx: number) => (
                                <tr key={rIdx}>
                                  {Object.values(row).map((val: any, cIdx: number) => (
                                    <td key={cIdx}>{val?.toString()}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </details>
                  )}

                  {msg.payload?.elapsed_seconds && (
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "16px" }}>
                      ⏱ Response time: {msg.payload.elapsed_seconds}s
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="message">
                <div className="message-avatar ai-avatar">🤖</div>
                <div className="message-content assistant">
                  <div style={{ color: "var(--accent-cyan)", fontWeight: 600, fontSize: "14px" }}>
                    Generating SQL and analyzing data...
                  </div>
                  <div className="loader">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="input-area">
          <div className="input-box">
            <input
              type="text"
              className="chat-input"
              placeholder="Ask a retail analytics question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button 
              className="send-btn" 
              onClick={() => sendQuery(input)}
              disabled={loading || !input.trim()}
            >
              ➤
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
