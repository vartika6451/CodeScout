"use client";

import React, { useState } from "react";
import {
  Search,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Star,
  FileCode2,
  Database,
  Cpu,
  ArrowRight,
  Sparkles,
  Trash2,
  Layers,
} from "lucide-react";
import { GithubIcon } from "./Icons";
import { AnalyzeResult, Repository } from "../types";

interface RepositoryAnalyzerProps {
  apiBaseUrl: string;
  repositories: Repository[];
  onAnalysisSuccess: (repoName: string) => void;
  onSelectRepo: (repoName: string) => void;
  onRefreshRepositories: () => void;
}

export default function RepositoryAnalyzer({
  apiBaseUrl,
  repositories,
  onAnalysisSuccess,
  onSelectRepo,
  onRefreshRepositories,
}: RepositoryAnalyzerProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [deletingRepo, setDeletingRepo] = useState<string | null>(null);

  const steps = [
    { title: "Querying GitHub API", desc: "Fetching file tree and metadata" },
    { title: "Filtering & Chunking", desc: "Extracting analyzable code blocks" },
    { title: "Generating Embeddings", desc: "Vectorizing code via Gemini API" },
    { title: "Indexing Vector DB", desc: "Upserting into PostgreSQL pgvector" },
  ];

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!repoUrl.trim()) return;

    setError(null);
    setResult(null);
    setIsAnalyzing(true);
    setCurrentStep(0);

    // Simulate multi-step progress feedback while backend completes
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev < 3 ? prev + 1 : prev));
    }, 4500);

    try {
      const response = await fetch(`${apiBaseUrl}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
      });

      clearInterval(interval);

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `Server responded with status ${response.status}`
        );
      }

      const data: AnalyzeResult = await response.json();
      setCurrentStep(3);
      setResult(data);
      onAnalysisSuccess(`${data.owner}/${data.repository}`);
      onRefreshRepositories();
    } catch (err: any) {
      clearInterval(interval);
      setError(err.message || "Failed to analyze repository.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDelete = async (repoString: string) => {
    if (!confirm(`Are you sure you want to delete indexed chunks for "${repoString}"?`)) {
      return;
    }
    const [owner, repo] = repoString.split("/");
    if (!owner || !repo) return;

    setDeletingRepo(repoString);
    try {
      const res = await fetch(`${apiBaseUrl}/repositories/${owner}/${repo}`, {
        method: "DELETE",
      });
      if (res.ok) {
        onRefreshRepositories();
        if (result?.repository === repo) {
          setResult(null);
        }
      }
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeletingRepo(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8 animate-in fade-in duration-300">
      {/* Hero Section */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Vector Ingestion Engine</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
          Index Any GitHub Repository
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto">
          Scan code structures, parse AST chunks, and generate dense Gemini vector embeddings
          ready for autonomous multi-agent exploration.
        </p>
      </div>

      {/* Input Box */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <GithubIcon className="w-5 h-5 text-indigo-400" />
            </div>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              disabled={isAnalyzing}
              className="w-full pl-12 pr-32 py-4 rounded-xl bg-slate-900/90 border border-slate-700/80 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-100 placeholder-slate-500 text-sm font-mono transition-all"
            />
            <button
              type="submit"
              disabled={isAnalyzing || !repoUrl.trim()}
              className="absolute right-2 top-2 bottom-2 px-5 rounded-lg bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-50 text-white font-medium text-xs sm:text-sm flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all cursor-pointer disabled:cursor-not-allowed"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Indexing...</span>
                </>
              ) : (
                <>
                  <span>Analyze</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs text-slate-500">Quick Test:</span>
            <button
              type="button"
              onClick={() => setRepoUrl("https://github.com/vartika6451/Yumzo")}
              className="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-xs font-mono text-slate-300 transition-colors cursor-pointer"
            >
              vartika6451/Yumzo
            </button>
          </div>
        </form>

        {/* Progress Tracker */}
        {isAnalyzing && (
          <div className="mt-8 pt-6 border-t border-slate-800 space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold text-slate-200">
                Agent Processing Pipeline
              </span>
              <span>Step {currentStep + 1} of 4</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              {steps.map((step, idx) => {
                const isActive = idx === currentStep;
                const isDone = idx < currentStep;
                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border transition-all ${
                      isActive
                        ? "border-indigo-500/60 bg-indigo-950/30 ring-1 ring-indigo-500/20"
                        : isDone
                        ? "border-emerald-500/40 bg-emerald-950/20"
                        : "border-slate-800 bg-slate-900/40 opacity-50"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : isActive ? (
                        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-600 text-[10px] flex items-center justify-center text-slate-500 shrink-0">
                          {idx + 1}
                        </div>
                      )}
                      <span
                        className={`text-xs font-semibold ${
                          isActive
                            ? "text-cyan-300"
                            : isDone
                            ? "text-emerald-300"
                            : "text-slate-400"
                        }`}
                      >
                        {step.title}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{step.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mt-6 p-4 rounded-xl border border-rose-500/30 bg-rose-950/30 text-rose-300 text-xs sm:text-sm flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-rose-200">Analysis Failed</span>
              <p className="text-rose-300/90">{error}</p>
            </div>
          </div>
        )}

        {/* Success Card */}
        {result && (
          <div className="mt-8 pt-6 border-t border-slate-800 space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <CheckCircle2 className="w-5 h-5" />
                <span>Repository Vectorized Successfully</span>
              </div>
              <button
                onClick={() => onSelectRepo(`${result.owner}/${result.repository}`)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
              >
                <span>Launch AI Chat</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[11px] text-slate-400">Repository</div>
                <div className="text-sm font-bold text-slate-100 truncate font-mono mt-0.5">
                  {result.owner}/{result.repository}
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[11px] text-slate-400">Primary Language</div>
                <div className="text-sm font-bold text-cyan-400 mt-0.5">
                  {result.language || "Multi-language"}
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[11px] text-slate-400">Files Analyzed</div>
                <div className="text-sm font-bold text-indigo-400 mt-0.5 font-mono">
                  {result.total_files} files
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="text-[11px] text-slate-400">Vector Embeddings</div>
                <div className="text-sm font-bold text-emerald-400 mt-0.5 font-mono">
                  {result.embeddings_created} chunks
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Indexed Repositories List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h2 className="text-base font-bold text-slate-200">
              Indexed Repositories in Vector Store ({repositories.length})
            </h2>
          </div>
          <button
            onClick={onRefreshRepositories}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Refresh List
          </button>
        </div>

        {repositories.length === 0 ? (
          <div className="p-8 rounded-2xl glass-panel text-center text-slate-400 text-sm">
            No repositories have been indexed yet. Paste a GitHub repository URL above to get started!
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {repositories.map((repo) => (
              <div
                key={repo.repository}
                className="p-5 rounded-2xl glass-panel glass-panel-hover flex flex-col justify-between gap-4 relative group"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 truncate">
                      <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
                        <GithubIcon className="w-4 h-4" />
                      </div>
                      <span className="font-mono text-sm font-semibold text-slate-100 truncate">
                        {repo.repository}
                      </span>
                    </div>

                    <button
                      onClick={() => handleDelete(repo.repository)}
                      disabled={deletingRepo === repo.repository}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-all"
                      title="Delete indexed embeddings"
                    >
                      {deletingRepo === repo.repository ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  <div className="flex items-center gap-3 mt-4 text-xs text-slate-400">
                    <div className="flex items-center gap-1 font-mono">
                      <FileCode2 className="w-3.5 h-3.5 text-slate-500" />
                      <span>{repo.total_files} files</span>
                    </div>
                    <span>•</span>
                    <div className="flex items-center gap-1 font-mono">
                      <Database className="w-3.5 h-3.5 text-cyan-500" />
                      <span className="text-slate-300 font-medium">{repo.total_chunks} chunks</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-end">
                  <button
                    onClick={() => onSelectRepo(repo.repository)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/30 hover:bg-indigo-600 text-indigo-200 hover:text-white border border-indigo-500/40 transition-all cursor-pointer"
                  >
                    <span>Explore Code</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
