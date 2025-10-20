import React, { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import ChatWidget from "./ChatWidget";
import { MessageCircle } from "lucide-react";

const AX_CHATBOT_STORAGE_KEY = "AX_CHATBOT_VISITOR_ID";
const AX_CHATBOT_OPENED = "AX_CHATBOT_OPENED";

export default function Chatbot() {
    const [isOpen, setIsOpen] = useState(false);
    const [visitorId, setVisitorId] = useState(null);

    useEffect(() => {
        let existing = localStorage.getItem(AX_CHATBOT_STORAGE_KEY);
        if (!existing) {
            existing = uuidv4();
            localStorage.setItem(AX_CHATBOT_STORAGE_KEY, existing);
        }
        setVisitorId(existing);

        // Auto-open the chat on first visit
        const hasVisited = localStorage.getItem(AX_CHATBOT_OPENED);
        if (!hasVisited) {
            setIsOpen(true);
            localStorage.setItem(AX_CHATBOT_OPENED, "true");
        }
    }, []);

    if (!visitorId) return null;

    return (
        <>
            {/* Floating button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-6 right-6 w-16 h-16 bg-blue-600 hover:bg-blue-700 rounded-full flex items-center justify-center shadow-lg text-white transition"
            >
                <MessageCircle size={30} />
            </button>

            {/* Chat widget container */}
            <div
                className={`fixed bottom-24 right-6 transition-all duration-300 ${isOpen ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
                    }`}
            >
                <ChatWidget visitorId={visitorId} />
            </div>
        </>
    );
}
