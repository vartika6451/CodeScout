"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Loader2,
  Sparkles,
  Bot,
  User,
  FileCode,
  Layers,
  ChevronRight,
  RotateCcw,
  Compass,
  AlertCircle,
  ExternalLink,
  Percent,
} from "lucide-react";
import { ChatMessage, SourceCitation, Repository } from "../types";
import MarkdownView from "./MarkdownView";
import CitationViewer from "./CitationViewer";

interface ChatWorkspaceProps {
  apiBaseUrl: string;
  selectedRepo: string;
  repositories: Repository[];
  onOpenAnalyzer: () => void;
}

export default function ChatWorkspace({
  apiBaseUrl,
  selectedRepo,
  repositories,
  onOpenAnalyzer,
}: ChatWorkspaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const sampleQuestions = [
    "Where is authentication and route protection implemented?",
    "Explain the overall project architecture and key components.",
    "What third-party APIs or payment integrations are used?",
    "How does the state management or data flow work?",
  ];

  const currentRepoObj = repositories.find((r) => r.repository === selectedRepo);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isLoading) return;

    if (!selectedRepo) {
      alert("Please select or index a repository first!");
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!queryText) setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository: selectedRepo,
          question: userMessage.content,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `API error (${response.status})`
        );
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer || "No answer generated.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        sources: data.sources || [],
        refined_question: data.refined_question,
        attempt_count: data.attempt_count,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${err.message || "Failed to retrieve an answer from the agent."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    if (messages.length > 0 && confirm("Clear current conversation history?")) {
      setMessages([]);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-[calc(100vh-4rem)] max-w-6xl w-full mx-auto px-2 sm:px-6 py-4">
      {/* Active Repo Subheader */}
      <div className="glass-panel rounded-xl px-4 py-3 mb-3 flex items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-2.5 truncate">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
            <Layers className="w-4 h-4" />
          </div>
          <div className="truncate">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Target Repo:</span>
              <span className="font-mono text-xs font-bold text-slate-100 truncate">
                {selectedRepo || "None Selected"}
              </span>
            </div>
          </div>
          {currentRepoObj && (
            <span className="hidden sm:inline-flex px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-300">
              {currentRepoObj.total_chunks} chunks ({currentRepoObj.total_files} files)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="Clear conversation"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Reset</span>
            </button>
          )}
          {!selectedRepo && (
            <button
              onClick={onOpenAnalyzer}
              className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
            >
              Select / Index Repo
            </button>
          )}
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto px-1 sm:px-2 space-y-6 pb-4">
        {messages.length === 0 ? (
          <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-center px-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4 shadow-xl shadow-indigo-500/10">
              <Compass className="w-7 h-7 animate-spin-slow text-cyan-400" />
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-100">
              Autonomous Codebase Exploration
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md mt-1 mb-8">
              Ask any architectural, logic, or file-level question. CodeScout uses a multi-step LangGraph agent with semantic retrieval, evaluation, and query refinement.
            </p>

            {/* Prompt suggestions */}
            <div className="w-full max-w-2xl text-left space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 px-1">
                Suggested Questions for {selectedRepo || "this repository"}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {sampleQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    disabled={!selectedRepo || isLoading}
                    className="p-3 text-left rounded-xl glass-panel glass-panel-hover border border-slate-800 text-xs text-slate-300 hover:text-white transition-all flex items-start justify-between gap-2 group cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="leading-snug">{q}</span>
                    <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 shrink-0 mt-0.5 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 sm:gap-4 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              } animate-in fade-in duration-200`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-indigo-500/20">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-4 sm:p-5 shadow-lg ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-sm"
                    : msg.isError
                    ? "glass-panel border-rose-500/40 bg-rose-950/20 text-rose-200 rounded-tl-sm"
                    : "glass-panel border-slate-700/70 text-slate-200 rounded-tl-sm"
                }`}
              >
                {/* Agent reasoning telemetry if present */}
                {msg.role === "assistant" && (msg.refined_question || (msg.attempt_count && msg.attempt_count > 1)) && (
                  <div className="mb-3 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-300 flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-cyan-300">LangGraph Agent Refined Query: </span>
                      <span>&ldquo;{msg.refined_question}&rdquo;</span>
                      <span className="ml-2 text-slate-400">({msg.attempt_count} retrieval attempts)</span>
                    </div>
                  </div>
                )}

                {/* Message body */}
                {msg.role === "user" ? (
                  <div className="text-sm sm:text-base leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                  </div>
                ) : (
                  <div className="text-sm sm:text-base leading-relaxed">
                    <MarkdownView content={msg.content} />
                  </div>
                )}

                {/* Source Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 mb-2">
                      <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Retrieved Source Citations ({msg.sources.length})</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((src, sIdx) => {
                        const simPercent = Math.round(src.similarity * 100);
                        return (
                          <button
                            key={sIdx}
                            onClick={() => setSelectedCitation(src)}
                            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 hover:border-cyan-500/40 text-xs font-mono text-slate-300 transition-all cursor-pointer group"
                            title="Click to view code chunk"
                          >
                            <span className="truncate max-w-[170px] sm:max-w-[240px] text-cyan-300 group-hover:text-cyan-200">
                              {src.file_path}
                            </span>
                            <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-400 font-semibold flex items-center gap-0.5">
                              {simPercent}%
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                <div className="mt-2 text-[10px] text-slate-400 text-right">
                  {msg.timestamp}
                </div>
              </div>

              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-3 sm:gap-4 items-start animate-in fade-in">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-indigo-500/20">
              <Bot className="w-4 h-4" />
            </div>
            <div className="glass-panel rounded-2xl rounded-tl-sm p-4 border-slate-700/70 space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium text-cyan-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Agent executing multi-step RAG workflow...</span>
              </div>
              <div className="text-xs text-slate-400 space-y-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  <span>Retrieving top vector embeddings from pgvector</span>
                </div>
                <div className="flex items-center gap-1.5 opacity-70">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                  <span>Evaluating relevance with Gemini 3.5 Flash</span>
                </div>
                <div className="flex items-center gap-1.5 opacity-50">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                  <span>Synthesizing concise architectural response</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="pt-2">
        <div className="relative glass-panel rounded-2xl border border-slate-700/80 shadow-2xl p-2 sm:p-2.5">
          <textarea
            ref={textareaRef}
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedRepo
                ? `Ask about ${selectedRepo} (e.g., "Where is authentication handled?")...`
                : "Select or index a repository above to start chatting..."
            }
            disabled={isLoading || !selectedRepo}
            className="w-full bg-transparent px-3 py-2 text-slate-100 placeholder-slate-500 text-sm focus:outline-none resize-none disabled:opacity-50"
          />

          <div className="flex items-center justify-between px-2 pt-1 border-t border-slate-800/60 text-xs text-slate-400">
            <span className="hidden sm:inline text-[11px] text-slate-500">
              Press <kbd className="px-1 py-0.5 rounded bg-slate-800 font-mono text-[10px]">Enter</kbd> to submit, <kbd className="px-1 py-0.5 rounded bg-slate-800 font-mono text-[10px]">Shift+Enter</kbd> for newline
            </span>
            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => handleSend()}
                disabled={isLoading || !input.trim() || !selectedRepo}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-40 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <>
                    <span>Send</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Citation Detail Modal */}
      {selectedCitation && (
        <CitationViewer
          citation={selectedCitation}
          repository={selectedRepo}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </div>
  );
}
