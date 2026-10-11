"use client";

import React, { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import HeroShowcase from "./components/HeroShowcase";
import RepositoryAnalyzer from "./components/RepositoryAnalyzer";
import ChatWorkspace from "./components/ChatWorkspace";
import BottomBar from "./components/BottomBar";
import ModalDetails, { ModalType } from "./components/ModalDetails";
import { Repository } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"showcase" | "chat" | "analyzer">("showcase");
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [pendingQuery, setPendingQuery] = useState<string>("");

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
  };

  const handleAnalysisSuccess = (repoName: string) => {
    setSelectedRepo(repoName);
    fetchRepositories();
    setActiveTab("chat");
  };

  const handleExploreChat = (initialQuery?: string) => {
    if (initialQuery) {
      setPendingQuery(initialQuery);
    }
    setActiveTab("chat");
  };

  return (
    <div className="outer-gradient-canvas min-h-screen w-full p-2 sm:p-4 md:p-6 lg:p-8 flex items-center justify-center">
      {/* Signature rounded porcelain frame from the reference design */}
      <div className="inner-porcelain-frame w-full max-w-[1440px] rounded-[28px] sm:rounded-[36px] md:rounded-[44px] lg:rounded-[48px] p-3 sm:p-5 md:p-7 lg:p-9 flex flex-col justify-between min-h-[92vh] border border-white/20">
        
        {/* Top Navbar */}
        <Header
          repositories={repositories}
          selectedRepo={selectedRepo}
          onSelectRepo={handleSelectRepo}
          isBackendHealthy={isBackendHealthy}
          onOpenAnalyzer={() => setActiveTab("analyzer")}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenModal={(type) => setActiveModal(type)}
        />

        {/* Dynamic Center Stage */}
        <main className="flex-1 flex flex-col justify-center py-2 sm:py-4">
          {activeTab === "showcase" && (
            <HeroShowcase
              onStartAnalysis={() => setActiveTab("analyzer")}
              onExploreChat={handleExploreChat}
              selectedRepo={selectedRepo}
              repositories={repositories}
            />
          )}

          {activeTab === "chat" && (
            <div className="w-full bg-[#0E1017] rounded-3xl p-3 sm:p-6 shadow-2xl border border-neutral-800 my-2">
              <ChatWorkspace
                apiBaseUrl={API_BASE_URL}
                selectedRepo={selectedRepo}
                repositories={repositories}
                onOpenAnalyzer={() => setActiveTab("analyzer")}
                initialQuery={pendingQuery}
              />
            </div>
          )}

          {activeTab === "analyzer" && (
            <div className="w-full bg-[#0E1017] rounded-3xl p-3 sm:p-6 shadow-2xl border border-neutral-800 my-2">
              <RepositoryAnalyzer
                apiBaseUrl={API_BASE_URL}
                repositories={repositories}
                onAnalysisSuccess={handleAnalysisSuccess}
                onSelectRepo={handleSelectRepo}
                onRefreshRepositories={fetchRepositories}
              />
            </div>
          )}
        </main>

        {/* Bottom Bar: Promo Ribbon + Monochrome Brand Logos */}
        <BottomBar
          onPromoClick={() => setActiveModal("pricing")}
        />

      </div>

      {/* Interactive Detail Modal for Navbar items */}
      <ModalDetails
        type={activeModal}
        onClose={() => setActiveModal(null)}
        onStartNow={() => {
          setActiveModal(null);
          setActiveTab("analyzer");
        }}
      />
    </div>
  );
}
