"use client";

import React, { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import RepositoryAnalyzer from "./components/RepositoryAnalyzer";
import ChatWorkspace from "./components/ChatWorkspace";
import { Repository } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"chat" | "analyzer">("chat");
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  // Fetch backend health
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, {
        cache: "no-store",
      });
      if (res.ok) {
        setIsBackendHealthy(true);
      } else {
        setIsBackendHealthy(false);
      }
    } catch {
      setIsBackendHealthy(false);
    }
  }, []);

  // Fetch indexed repositories from backend
  const fetchRepositories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/repositories`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        const repos: Repository[] = data.repositories || [];
        setRepositories(repos);

        // If no repo is currently selected and we have repos, default to the first one
        setSelectedRepo((curr) => {
          if (curr && repos.some((r) => r.repository === curr)) {
            return curr;
          }
          return repos.length > 0 ? repos[0].repository : "";
        });
      }
    } catch (err) {
      console.warn("Could not fetch repositories:", err);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    fetchRepositories();

    const interval = setInterval(() => {
      checkHealth();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealth, fetchRepositories]);

  const handleSelectRepo = (repoName: string) => {
    setSelectedRepo(repoName);
    setActiveTab("chat");
  };

  const handleAnalysisSuccess = (repoName: string) => {
    setSelectedRepo(repoName);
    fetchRepositories();
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100">
      {/* Header */}
      <Header
        repositories={repositories}
        selectedRepo={selectedRepo}
        onSelectRepo={handleSelectRepo}
        isBackendHealthy={isBackendHealthy}
        onOpenAnalyzer={() => setActiveTab("analyzer")}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {activeTab === "chat" ? (
          <ChatWorkspace
            apiBaseUrl={API_BASE_URL}
            selectedRepo={selectedRepo}
            repositories={repositories}
            onOpenAnalyzer={() => setActiveTab("analyzer")}
          />
        ) : (
          <RepositoryAnalyzer
            apiBaseUrl={API_BASE_URL}
            repositories={repositories}
            onAnalysisSuccess={handleAnalysisSuccess}
            onSelectRepo={handleSelectRepo}
            onRefreshRepositories={fetchRepositories}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="py-3 px-6 border-t border-slate-800/80 text-center text-xs text-slate-500 glass-panel">
        <p>
          CodeScout AI • Autonomous Code Exploration powered by{" "}
          <span className="text-slate-400">LangGraph</span>,{" "}
          <span className="text-cyan-400">Gemini</span>,{" "}
          <span className="text-indigo-400">pgvector</span> &amp;{" "}
          <span className="text-slate-300">FastAPI</span>
        </p>
      </footer>
    </div>
  );
}
