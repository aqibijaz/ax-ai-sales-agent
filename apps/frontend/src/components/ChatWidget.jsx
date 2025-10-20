import React, { useEffect, useState, useRef } from "react";
import axios from "axios";

const WS_URL = "ws://localhost:8080/ws/chat";
const API_URL = "http://localhost:8080/api/v1/chat";
const AX_CHATBOT_HISTORY = "AX_CHATBOT_HISTORY";

export default function ChatWidget({ visitorId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ✅ Add dummy welcome message on first load
  // useEffect(() => {
  //   setMessages([
  //     {
  //       sender: "assistant",
  //       text: "👋 Hi there! I’m AccellionX AI Sales Agent. How can I assist you today?",
  //       final: true,
  //       timestamp: new Date(),
  //     },
  //   ]);
  // }, []);

  // ✅ Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ✅ Open WebSocket connection
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/${visitorId}`);
    wsRef.current = ws;

    ws.onopen = () => console.log("✅ Connected to chat server");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log("Received:", msg);

      if (msg.type === "token") {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.sender === "assistant" && !last.final) {
            const updated = [...prev];
            updated[updated.length - 1] = { ...last, text: last.text + msg.data };
            return updated;
          }
          return [...prev, { sender: "assistant", text: msg.data, final: false, timestamp: new Date() }];
        });
      }

      if (msg.type === "done") {
        setMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0 && updated[updated.length - 1].sender === "assistant") {
            updated[updated.length - 1].final = true;
          }
          return updated;
        });
        setIsTyping(false);
      }

      if (msg.type === "tool") console.log("🔧 Tool call:", msg.data);
      if (msg.type === "error") console.error("❌ Error:", msg.error);
      if (msg.type === "round_complete") console.log("✅ Round complete");
    };

    ws.onerror = (err) => console.error("❌ WebSocket error:", err);
    ws.onclose = () => console.log("🔌 Disconnected");

    return () => ws.close();
  }, [visitorId]);

  // Save messages whenever they change
  useEffect(() => {
    localStorage.setItem(AX_CHATBOT_HISTORY, JSON.stringify(messages));
  }, [messages]);

  // Load messages on initial render
  useEffect(() => {
    const savedMessages = localStorage.getItem(AX_CHATBOT_HISTORY);
    if (savedMessages && JSON.parse(savedMessages).length > 0) {
      setMessages(JSON.parse(savedMessages));
    } else {
      // ✅ If no previous history, start with dummy message
      setMessages([
        {
          sender: "assistant",
          text: "👋 Hi there! I’m AccellionX AI Sales Agent. How can I assist you today?",
          timestamp: new Date(),
          final: true,
        },
      ]);
    }
  }, []);

  // ✅ Send user message
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newMessage = { sender: "user", text: input, timestamp: new Date() };
    setMessages((prev) => [...prev, newMessage]);
    setInput("");
    setIsTyping(true);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: input }));
    } else {
      try {
        const res = await axios.post(API_URL, { visitor_id: visitorId, message: input });
        setMessages((prev) => [
          ...prev,
          { sender: "assistant", text: res.data.message, final: true, timestamp: new Date() },
        ]);
      } catch (err) {
        console.error("❌ REST error:", err);
      } finally {
        setIsTyping(false);
      }
    }
  };

  return (
    <div className="flex flex-col w-[380px] h-[600px] bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 text-lg font-semibold flex items-center justify-between">
        🤖 AI Sales Assistant
        <span className="text-xs font-light">online</span>
      </div>

      {/* Chat history */}
      <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-gray-50">
        {messages.map((m, idx) => (
          <div key={idx} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex items-end gap-2 max-w-[80%] ${m.sender === "user" ? "flex-row-reverse" : ""}`}>
              <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-sm font-bold">
                {m.sender === "user" ? "👤" : "🤖"}
              </div>
              <div
                className={`px-4 py-2 rounded-2xl text-sm shadow-sm ${m.sender === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-none"
                  }`}
              >
                <p>{m.text}</p>
                <div className="text-[10px] text-gray-400 mt-1 text-right">
                  {new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-center space-x-2 text-gray-500 text-sm">
            <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">🤖</div>
            <div className="animate-pulse">Assistant is typing...</div>
          </div>
        )}
        <div ref={messagesEndRef}></div>
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-3 border-t bg-white flex gap-2">
        <input
          type="text"
          className="flex-1 px-4 py-2 border rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="submit"
          className="px-5 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition"
        >
          Send
        </button>
      </form>
    </div>
  );
}
