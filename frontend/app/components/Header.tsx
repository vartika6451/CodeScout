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
  ArrowRight,
  User,
  Menu,
  X,
  ExternalLink,
} from "lucide-react";
import { GithubIcon, BrandSquircleIcon } from "./Icons";
import { Repository } from "../types";
import { ModalType } from "./ModalDetails";

interface HeaderProps {
  repositories: Repository[];
  selectedRepo: string;
  onSelectRepo: (repo: string) => void;
  isBackendHealthy: boolean | null;
  onOpenAnalyzer: () => void;
  activeTab: "showcase" | "chat" | "analyzer";
  onTabChange: (tab: "showcase" | "chat" | "analyzer") => void;
  onOpenModal: (type: ModalType) => void;
}

export default function Header({
  repositories,
  selectedRepo,
  onSelectRepo,
  isBackendHealthy,
  onOpenAnalyzer,
  activeTab,
  onTabChange,
  onOpenModal,
}: HeaderProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="w-full pt-2 pb-4 px-2 sm:px-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 py-2">
        
        {/* Left: Brand Squircle Icon & Name */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => onTabChange("showcase")}
            className="group flex items-center gap-2.5 transition-transform hover:scale-105 cursor-pointer text-left"
            title="Return to Showcase"
          >
            <div className="w-10 h-10 rounded-2xl bg-black text-white flex items-center justify-center shadow-md group-hover:shadow-lg transition-all">
              <BrandSquircleIcon className="w-6 h-6 text-white" />
            </div>
            <div className="hidden sm:block">
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-neutral-900 tracking-tight text-lg">
                  CodeScout
                </span>
                <span className="px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 font-bold text-[9px] uppercase tracking-wider">
                  AI 3.5
                </span>
              </div>
            </div>
          </button>
        </div>

        {/* Center: Reference Navigation Links */}
        <nav className="hidden lg:flex items-center gap-7 text-xs sm:text-sm font-medium text-neutral-600">
          <button
            onClick={() => onOpenModal("how-it-works")}
            className="hover:text-neutral-950 transition-colors cursor-pointer"
          >
            How it works
          </button>
          <button
            onClick={() => onOpenModal("use-cases")}
            className="hover:text-neutral-950 transition-colors cursor-pointer"
          >
            Use cases
          </button>
          <button
            onClick={() => onOpenModal("features")}
            className="hover:text-neutral-950 transition-colors cursor-pointer"
          >
            Features
          </button>
          <button
            onClick={() => onOpenModal("pricing")}
            className="hover:text-neutral-950 transition-colors cursor-pointer"
          >
            Pricing
          </button>
          <button
            onClick={() => onOpenModal("faq")}
            className="hover:text-neutral-950 transition-colors cursor-pointer"
          >
            FAQ
          </button>

          {/* Interactive Workspace View Switchers */}
          <div className="flex items-center p-1 rounded-full bg-neutral-200/70 border border-neutral-300/60 ml-2">
            <button
              onClick={() => onTabChange("showcase")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                activeTab === "showcase"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              Showcase
            </button>
            <button
              onClick={() => onTabChange("chat")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                activeTab === "chat"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              AI Explorer
            </button>
            <button
              onClick={() => onTabChange("analyzer")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                activeTab === "analyzer"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              Repo Ingestion
            </button>
          </div>
        </nav>

        {/* Right: Actions matching the reference design */}
        <div className="flex items-center gap-2 sm:gap-3">
          
          {/* Active Repository Picker Pill */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-neutral-300/80 hover:border-neutral-400 text-xs text-neutral-800 font-medium transition-all shadow-sm cursor-pointer"
              title="Select active repository"
            >
              <Layers className="w-3.5 h-3.5 text-purple-600 shrink-0" />
              <span className="font-mono max-w-[100px] sm:max-w-[140px] truncate text-[11px] sm:text-xs">
                {selectedRepo || "Pick Repo"}
              </span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white border border-neutral-200 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3 py-1.5 text-[10px] font-bold text-neutral-400 uppercase tracking-wider border-b border-neutral-100 flex items-center justify-between">
                  <span>Indexed Repositories</span>
                  <span className="bg-neutral-100 px-1.5 py-0.5 rounded text-neutral-600">
                    {repositories.length}
                  </span>
                </div>
                <div className="max-h-56 overflow-y-auto py-1">
                  {repositories.length === 0 ? (
                    <div className="px-3 py-4 text-xs text-neutral-400 text-center">
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
                        className={`w-full flex items-center justify-between px-3 py-2 text-left rounded-xl text-xs transition-colors cursor-pointer ${
                          selectedRepo === repo.repository
                            ? "bg-purple-50 text-purple-800 font-semibold"
                            : "text-neutral-700 hover:bg-neutral-100"
                        }`}
                      >
                        <span className="font-mono truncate mr-2">
                          {repo.repository}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-neutral-200/60 text-[10px] text-neutral-500 shrink-0 font-mono">
                          {repo.total_chunks}
                        </span>
                      </button>
                    ))
                  )}
                </div>
                <div className="pt-2 border-t border-neutral-100">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onOpenAnalyzer();
                    }}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs text-purple-600 hover:bg-purple-50 font-semibold transition-colors cursor-pointer"
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
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-white border border-neutral-300/80 text-[11px] shadow-sm"
            title={
              isBackendHealthy
                ? "Backend API connected (http://127.0.0.1:8000)"
                : "Backend API offline"
            }
          >
            {isBackendHealthy ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-emerald-700 font-semibold text-[10px]">API Online</span>
              </>
            ) : isBackendHealthy === false ? (
              <>
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-rose-600 font-semibold text-[10px]">API Offline</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span className="text-neutral-400 text-[10px]">Connecting...</span>
              </>
            )}
          </div>

          {/* Circle Action Button (arrow in circle -> from image) */}
          <button
            onClick={() => onTabChange(activeTab === "chat" ? "showcase" : "chat")}
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-neutral-300 bg-white hover:bg-neutral-50 text-neutral-800 flex items-center justify-center shadow-sm hover:scale-105 active:scale-95 transition-all cursor-pointer"
            title="Quick toggle to AI Explorer"
          >
            <ArrowRight className="w-4 h-4 text-neutral-700" />
          </button>

          {/* Profile Avatar / User button from image */}
          <button
            onClick={() => onOpenModal("pricing")}
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border border-neutral-300 bg-white hover:bg-neutral-50 text-neutral-800 flex items-center justify-center shadow-sm hover:scale-105 active:scale-95 transition-all cursor-pointer"
            title="User Account & Subscription"
          >
            <User className="w-4 h-4 text-neutral-700" />
          </button>

          {/* Mobile hamburger menu toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-xl text-neutral-700 hover:bg-neutral-100"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden mt-2 p-4 rounded-2xl bg-white border border-neutral-200 shadow-xl space-y-3 animate-in fade-in duration-150">
          <div className="grid grid-cols-3 gap-2 pb-2 border-b border-neutral-100 text-center">
            <button
              onClick={() => {
                onTabChange("showcase");
                setMobileMenuOpen(false);
              }}
              className={`py-2 rounded-xl text-xs font-bold ${
                activeTab === "showcase" ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-800"
              }`}
            >
              Showcase
            </button>
            <button
              onClick={() => {
                onTabChange("chat");
                setMobileMenuOpen(false);
              }}
              className={`py-2 rounded-xl text-xs font-bold ${
                activeTab === "chat" ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-800"
              }`}
            >
              AI Explorer
            </button>
            <button
              onClick={() => {
                onTabChange("analyzer");
                setMobileMenuOpen(false);
              }}
              className={`py-2 rounded-xl text-xs font-bold ${
                activeTab === "analyzer" ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-800"
              }`}
            >
              Repo Ingestion
            </button>
          </div>

          <div className="flex flex-col space-y-2 text-sm font-medium text-neutral-700">
            <button
              onClick={() => {
                onOpenModal("how-it-works");
                setMobileMenuOpen(false);
              }}
              className="text-left py-1 hover:text-neutral-950"
            >
              How it works
            </button>
            <button
              onClick={() => {
                onOpenModal("use-cases");
                setMobileMenuOpen(false);
              }}
              className="text-left py-1 hover:text-neutral-950"
            >
              Use cases
            </button>
            <button
              onClick={() => {
                onOpenModal("features");
                setMobileMenuOpen(false);
              }}
              className="text-left py-1 hover:text-neutral-950"
            >
              Features
            </button>
            <button
              onClick={() => {
                onOpenModal("pricing");
                setMobileMenuOpen(false);
              }}
              className="text-left py-1 hover:text-neutral-950"
            >
              Pricing
            </button>
            <button
              onClick={() => {
                onOpenModal("faq");
                setMobileMenuOpen(false);
              }}
              className="text-left py-1 hover:text-neutral-950"
            >
              FAQ
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
