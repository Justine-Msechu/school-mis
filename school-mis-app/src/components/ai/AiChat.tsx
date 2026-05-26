import { useState, useRef, useEffect, useCallback } from "react";
import { Bot, X, Trash2, Send, Sparkles } from "lucide-react";
import { sendChatMessage, type ChatMessage } from "@/api/ai";

const SUGGESTIONS = [
  "How many students are enrolled?",
  "Who was absent today?",
  "Which students have unpaid fees?",
  "Show low stock inventory items",
];

// ── Simple markdown renderer (bold + bullets + line breaks) ───────────────────
function FormattedText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <span>
      {lines.map((line, li) => {
        const bullet = /^[-*•]\s/.test(line);
        const content = bullet ? line.replace(/^[-*•]\s/, "") : line;
        const parts = content.split(/\*\*(.*?)\*\*/g);
        const formatted = parts.map((p, pi) =>
          pi % 2 === 1 ? <strong key={pi}>{p}</strong> : <span key={pi}>{p}</span>
        );
        return (
          <span key={li} className={bullet ? "flex gap-1.5 mt-0.5" : "block"}>
            {bullet && <span className="mt-0.5 flex-shrink-0">•</span>}
            <span>{formatted}</span>
            {!bullet && li < lines.length - 1 && line.trim() !== "" && <br />}
          </span>
        );
      })}
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function AiChat() {
  const [open, setOpen]         = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const bottomRef               = useRef<HTMLDivElement>(null);
  const textareaRef             = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (open) textareaRef.current?.focus();
  }, [open]);

  // Auto-resize textarea
  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 96) + "px";
  };

  const send = useCallback(async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || loading) return;
    setInput("");
    setError("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const next: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(next);
    setLoading(true);
    try {
      const res = await sendChatMessage(next);
      setMessages([...next, { role: "assistant", content: res.message }]);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to get a response. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [input, messages, loading]);

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {/* Floating button — hidden when panel is open */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-violet-600 hover:bg-violet-700 active:scale-95 text-white rounded-full shadow-xl flex items-center justify-center transition-all"
          title="AI Assistant"
        >
          <Sparkles size={22} />
        </button>
      )}

      {/* Panel */}
      {open && (
        <div className="fixed bottom-0 right-0 z-50 flex flex-col w-full sm:w-[390px] h-[85vh] sm:h-[620px] sm:bottom-6 sm:right-6 bg-white sm:rounded-2xl rounded-t-2xl shadow-2xl border border-gray-200 overflow-hidden">

          {/* Header */}
          <div className="flex items-center gap-2 px-4 py-3 bg-violet-600 text-white flex-shrink-0">
            <Bot size={18} className="flex-shrink-0" />
            <span className="font-semibold flex-1 text-sm">AI Assistant</span>
            <button
              onClick={() => { setMessages([]); setError(""); }}
              title="Clear conversation"
              className="p-1 rounded hover:bg-violet-500 transition-colors"
            >
              <Trash2 size={15} />
            </button>
            <button
              onClick={() => setOpen(false)}
              className="p-1 rounded hover:bg-violet-500 transition-colors ml-0.5"
            >
              <X size={17} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <Sparkles size={36} className="mx-auto mb-3 text-violet-300" />
                <p className="font-semibold text-gray-600 text-sm">Ask me anything about the school</p>
                <p className="text-xs text-gray-400 mt-1 mb-4">Attendance · Fees · Grades · Students · Inventory</p>
                <div className="space-y-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="block w-full text-left px-3 py-2 rounded-xl text-xs text-violet-700 bg-violet-50 hover:bg-violet-100 border border-violet-100 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "assistant" && (
                  <div className="w-6 h-6 rounded-full bg-violet-100 flex items-center justify-center flex-shrink-0 mt-0.5 mr-2">
                    <Bot size={13} className="text-violet-600" />
                  </div>
                )}
                <div
                  className={[
                    "max-w-[82%] px-3 py-2.5 text-sm leading-relaxed",
                    m.role === "user"
                      ? "bg-violet-600 text-white rounded-2xl rounded-br-sm"
                      : "bg-white text-gray-800 rounded-2xl rounded-bl-sm border border-gray-200 shadow-sm",
                  ].join(" ")}
                >
                  <FormattedText text={m.content} />
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 rounded-full bg-violet-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot size={13} className="text-violet-600" />
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm px-4 py-3">
                  <div className="flex gap-1.5 items-center">
                    <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "160ms" }} />
                    <span className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "320ms" }} />
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-xl border border-red-200">
                {error}
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-200 bg-white flex gap-2 items-end flex-shrink-0">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); resizeTextarea(); }}
              onKeyDown={handleKey}
              placeholder="Ask about students, fees, attendance…"
              rows={1}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 leading-snug"
              style={{ minHeight: "38px", maxHeight: "96px" }}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              className="w-9 h-9 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 text-white rounded-xl flex items-center justify-center flex-shrink-0 transition-colors"
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
