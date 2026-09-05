"use client";

import React, { useState } from "react";
import {
  Compass,
  Database,
  ChevronDown,
  PlusCircle,
  Activity,
  CheckCircle2,
  AlertCircle,
  Layers,
} from "lucide-react";
import { GithubIcon } from "./Icons";
import { Repository } from "../types";

interface HeaderProps {
  repositories: Repository[];
  selectedRepo: string;
  onSelectRepo: (repo: string) => void;
  isBackendHealthy: boolean | null;
  onOpenAnalyzer: () => void;
  activeTab: "chat" | "analyzer";
  onTabChange: (tab: "chat" | "analyzer") => void;
}

export default function Header({
  repositories,
  selectedRepo,
  onSelectRepo,
  isBackendHealthy,
  onOpenAnalyzer,
  activeTab,
  onTabChange,
}: HeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 glass-panel">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-cyan-500 shadow-lg shadow-indigo-500/20 text-white">
            <Compass className="w-5 h-5 animate-spin-slow" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                CodeScout
              </span>
              <span className="hidden sm:inline-flex px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                Agentic RAG
              </span>
            </div>
            <p className="hidden md:block text-[11px] text-slate-400">
              Autonomous Codebase Intelligence
            </p>
          </div>
        </div>

        {/* Center: Tabs */}
        <div className="flex items-center p-1 rounded-xl bg-slate-900/80 border border-slate-800 text-xs font-medium">
          <button
            onClick={() => onTabChange("chat")}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all ${
              activeTab === "chat"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>AI Explorer</span>
          </button>
          <button
            onClick={() => onTabChange("analyzer")}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg transition-all ${
              activeTab === "analyzer"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/25"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Analyze Repo</span>
          </button>
        </div>

        {/* Right side: Repo Selector, Backend Status, GitHub */}
        <div className="flex items-center gap-3">
          {/* Active Repository Selector */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 text-xs text-slate-200 transition-colors shadow-sm"
              title="Switch repository"
            >
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              <span className="font-mono max-w-[130px] sm:max-w-[180px] truncate font-medium">
                {selectedRepo || "Select Repository"}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl glass-panel border border-slate-700/80 shadow-2xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  Indexed Repositories ({repositories.length})
                </div>
                <div className="max-h-60 overflow-y-auto py-1">
                  {repositories.length === 0 ? (
                    <div className="px-3 py-3 text-xs text-slate-400 text-center">
                      No repositories indexed yet.
                    </div>
                  ) : (
                    repositories.map((repo) => (
                      <button
                        key={repo.repository}
                        onClick={() => {
                          onSelectRepo(repo.repository);
                          setDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-left rounded-lg text-xs transition-colors ${
                          selectedRepo === repo.repository
                            ? "bg-indigo-600/20 text-indigo-200 border border-indigo-500/30"
                            : "text-slate-300 hover:bg-slate-800/70"
                        }`}
                      >
                        <span className="font-mono truncate mr-2 font-medium">
                          {repo.repository}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 shrink-0 font-mono">
                          {repo.total_chunks} chunks
                        </span>
                      </button>
                    ))
                  )}
                </div>
                <div className="pt-1.5 border-t border-slate-800">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onOpenAnalyzer();
                    }}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-cyan-400 hover:bg-cyan-500/10 transition-colors font-medium"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    <span>Index New Repository</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Backend Status indicator */}
          <div
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-[11px]"
            title={
              isBackendHealthy
                ? "Backend API connected (http://127.0.0.1:8000)"
                : "Backend API offline"
            }
          >
            {isBackendHealthy ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-emerald-400 font-medium">API Online</span>
              </>
            ) : isBackendHealthy === false ? (
              <>
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-rose-400 font-medium">API Offline</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span className="text-slate-400">Connecting...</span>
              </>
            )}
          </div>

          {/* GitHub link */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors border border-transparent hover:border-slate-800"
            title="GitHub"
          >
            <GithubIcon className="w-4 h-4" />
          </a>
        </div>
      </div>
    </header>
  );
}
