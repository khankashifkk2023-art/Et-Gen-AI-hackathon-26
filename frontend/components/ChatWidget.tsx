"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Bot, User, Sparkles, AlertCircle } from "lucide-react";
import axios from "axios";
import { API_BASE } from "../lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatWidgetProps {
  articleText?: string;
  userName?: string;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({ articleText, userName = "Investor" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: `Hello ${userName}! I'm the Nexus Assistant. I can help you understand this article or answer general questions about the platform and markets. How can I help today?`,
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session_${Math.random().toString(36).substring(7)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    
    // Add user message to UI
    const newMessage: Message = {
      role: "user",
      content: userMessage,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        session_id: sessionId,
        user_message: userMessage,
        article_text: articleText,
        user_profile: { name: userName }
      });

      const assistantMessage: Message = {
        role: "assistant",
        content: response.data.ai_reply,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error("Chat Error:", error);
      const detail = error.response?.data?.detail || error.message || "Connection failed";
      const errorMessage: Message = {
        role: "assistant",
        content: `Sorry, I encountered an error connecting to the Nexus Intelligence Unit: ${detail}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="mb-4 w-96 max-w-[calc(100vw-3rem)] h-[500px] bg-zinc-950/80 backdrop-blur-xl border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="p-4 bg-gradient-to-r from-red-600/20 to-zinc-900 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center">
                  <Bot size={18} className="text-white" />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-sm">Nexus Assistant</h3>
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-[10px] text-zinc-400">Intelligence Unit Online</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-400 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            {/* Context Notice (if article active) */}
            {articleText && (
              <div className="px-4 py-2 bg-zinc-900/50 border-b border-zinc-800 flex items-center gap-2">
                <Sparkles size={12} className="text-red-500" />
                <span className="text-[10px] text-zinc-500 font-medium">Analyzing current article context...</span>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div 
                    className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                      msg.role === "user" 
                        ? "bg-red-600 text-white rounded-tr-none" 
                        : "bg-zinc-900 text-zinc-200 border border-zinc-800 rounded-tl-none"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-2xl rounded-tl-none w-2/3 space-y-2">
                    <div className="h-3 bg-zinc-800 rounded-full animate-pulse w-full"></div>
                    <div className="h-3 bg-zinc-800 rounded-full animate-pulse w-[60%]"></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Footer */}
            <div className="p-4 bg-zinc-950 border-t border-zinc-800">
              <div className="relative flex items-center">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                  placeholder="Ask a question..."
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-xl py-3 pl-4 pr-12 text-sm text-zinc-200 focus:outline-none focus:border-red-600 transition-colors"
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={isLoading}
                  className="absolute right-2 p-2 bg-red-600 hover:bg-red-500 disabled:bg-zinc-800 transition-colors rounded-lg text-white"
                >
                  <Send size={16} />
                </button>
              </div>
              <p className="mt-2 text-[10px] text-center text-zinc-600">
                Nexus Assistant can make mistakes. Verify critical financial info.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle Button (The Orb) */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 ${
          isOpen ? "bg-zinc-900 border border-zinc-800" : "bg-red-600 hover:bg-red-500"
        }`}
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
            >
              <X size={24} className="text-white" />
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              className="relative"
            >
              <MessageCircle size={24} className="text-white" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-white rounded-full border-2 border-red-600 animate-pulse"></div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
};
