import React, { useState, useRef, useEffect } from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import Button from "./ui/Button";
import api from "../api/client";

export default function ChatWidget({ lectureId }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (customText = null) => {
    const textToSend = (customText !== null ? customText : question).trim();
    if (!textToSend || loading) return;

    const userMessage = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await api.post("/chat", {
        lecture_id: lectureId,
        question: textToSend,
      });

      const assistantMessage = { role: "assistant", content: res.data.answer };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to lecture chat service. Please ensure the backend is running." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedPrompts = [
    "Summarize the core concepts",
    "Explain the key architectural trade-offs",
    "Give me 3 practice questions",
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm flex flex-col h-[600px] overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-xs shadow-2xs font-bold">
            AI
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Ask Lecture Tutor</h3>
            <p className="text-[10px] text-slate-400">Grounded in lecture transcript & slides</p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={() => setMessages([])}
            className="text-[11px] text-slate-400 hover:text-slate-600 font-medium px-2 py-1 rounded hover:bg-slate-100 transition-colors cursor-pointer"
            title="Clear conversation"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/30">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h4 className="text-xs sm:text-sm font-semibold text-slate-800">
              Ask anything about this lecture
            </h4>
            <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
              Ask about definitions, formulas, or how topics relate to each other.
            </p>

            {/* Prompt Chips */}
            <div className="mt-4 flex flex-col gap-1.5 w-full max-w-xs">
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(prompt)}
                  className="text-left text-xs text-indigo-700 bg-white hover:bg-indigo-50 border border-indigo-100 hover:border-indigo-200 px-3 py-2 rounded-xl transition-all shadow-2xs font-medium cursor-pointer"
                >
                  "{prompt}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed max-w-[88%] shadow-2xs animate-in fade-in duration-150 ${
                m.role === "user"
                  ? "bg-indigo-600 text-white ml-auto rounded-tr-xs"
                  : "bg-white text-slate-800 mr-auto border border-slate-200/80 rounded-tl-xs"
              }`}
            >
              {m.role === "user" ? (
                <div className="whitespace-pre-wrap">{m.content}</div>
              ) : (
                <MarkdownRenderer content={m.content} className="text-xs sm:text-sm" />
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-2 p-3 bg-white rounded-2xl border border-slate-200/80 text-slate-500 text-xs w-max animate-pulse">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
            <span>Thinking with lecture context...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="p-3 bg-white border-t border-slate-100 flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          rows={1}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question... (Enter to send, Shift+Enter for newline)"
          className="flex-1 max-h-28 resize-none p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all"
          disabled={loading}
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={loading || !question.trim()}
          className="shrink-0 rounded-xl h-10 px-3.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </Button>
      </form>
    </div>
  );
}
