"use client";

import React from "react";
import {
  X,
  Check,
  Cpu,
  Layers,
  Database,
  Search,
  Sparkles,
  GitBranch,
  ShieldCheck,
  Zap,
} from "lucide-react";

export type ModalType = "how-it-works" | "use-cases" | "features" | "pricing" | "faq" | null;

interface ModalDetailsProps {
  type: ModalType;
  onClose: () => void;
  onStartNow: () => void;
}

export default function ModalDetails({ type, onClose, onStartNow }: ModalDetailsProps) {
  if (!type) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[85vh] overflow-y-auto bg-[#FAF8F5] text-neutral-900 rounded-[32px] p-6 sm:p-8 shadow-2xl border border-white/40">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 w-9 h-9 rounded-full bg-neutral-200/80 hover:bg-neutral-300 flex items-center justify-center text-neutral-600 hover:text-neutral-900 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Content based on type */}
        {type === "how-it-works" && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-600">
                System Architecture
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-neutral-900 mt-1">
                How CodeScout Works
              </h2>
              <p className="text-sm text-neutral-600 mt-2">
                CodeScout transforms raw GitHub repositories into an autonomous multi-step reasoning system.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm space-y-2">
                <div className="w-8 h-8 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center font-bold text-sm">
                  1
                </div>
                <h3 className="font-bold text-sm text-neutral-900">GitHub File Tree Ingestion</h3>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Fetches recursive git trees, filters lockfiles and assets, and extracts clean, analyzable source code files.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm space-y-2">
                <div className="w-8 h-8 rounded-xl bg-pink-100 text-pink-600 flex items-center justify-center font-bold text-sm">
                  2
                </div>
                <h3 className="font-bold text-sm text-neutral-900">Syntax Chunking & Embeddings</h3>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Splits code into semantic AST chunks and vectorizes them using Gemini 768-dimensional embedding vectors.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm space-y-2">
                <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-sm">
                  3
                </div>
                <h3 className="font-bold text-sm text-neutral-900">pgvector Cosine Retrieval</h3>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Indexes vectors in PostgreSQL with pgvector distance operator (`&lt;=&gt;`) for sub-10ms nearest neighbor queries.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm space-y-2">
                <div className="w-8 h-8 rounded-xl bg-orange-100 text-orange-600 flex items-center justify-center font-bold text-sm">
                  4
                </div>
                <h3 className="font-bold text-sm text-neutral-900">LangGraph Multi-Agent Loop</h3>
                <p className="text-xs text-neutral-600 leading-relaxed">
                  Evaluates retrieval relevance, reformulates queries if needed (up to 3 attempts), and synthesizes cited answers.
                </p>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => {
                  onClose();
                  onStartNow();
                }}
                className="px-6 py-3 rounded-full text-white font-semibold text-xs sm:text-sm bg-gradient-to-r from-purple-600 to-pink-500 shadow-md hover:scale-105 transition-all cursor-pointer"
              >
                Try It Live
              </button>
            </div>
          </div>
        )}

        {type === "use-cases" && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-pink-600">
                Applications
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-neutral-900 mt-1">
                Real-World Use Cases
              </h2>
              <p className="text-sm text-neutral-600 mt-2">
                Accelerate software engineering velocity with autonomous code comprehension.
              </p>
            </div>

            <div className="space-y-3">
              {[
                {
                  title: "Instant Codebase Onboarding",
                  desc: "New engineers ask natural language questions about architecture, authentication flows, or service boundaries and receive instant file-cited explanations.",
                },
                {
                  title: "Incident Root Cause Triage",
                  desc: "Quickly locate error handlers, distributed locks, retry policies, and database connection pools during production outages.",
                },
                {
                  title: "Legacy Monolith Refactoring",
                  desc: "Identify coupling between modules, dependency flow, and obsolete endpoint implementations with zero hallucination.",
                },
                {
                  title: "Security Auditing & Secret Hygiene",
                  desc: "Search for cryptographic usages, token validation paths, and unprotected API routes across thousands of files.",
                },
              ].map((item, idx) => (
                <div key={idx} className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm">
                  <h3 className="font-bold text-sm text-neutral-900">{item.title}</h3>
                  <p className="text-xs text-neutral-600 mt-1 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {type === "features" && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-orange-600">
                Core Capabilities
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-neutral-900 mt-1">
                Engineered for High-Precision RAG
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {[
                "Google Gemini 3.5 Flash Model Integration",
                "PostgreSQL 15+ & pgvector Cosine Search",
                "LangGraph Multi-Step Self-Refining Loop",
                "Line-Numbered Source Code Citations",
                "Recursive GitHub Repository Ingestion",
                "AST Code Chunking with Overlap Preservation",
                "Zero-Setup Public Repository Exploration",
                "Interactive Swagger & FastAPI Backend",
              ].map((feat, i) => (
                <div key={i} className="flex items-center gap-2.5 p-3 rounded-xl bg-white border border-neutral-200/80">
                  <Check className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span className="font-medium text-neutral-800">{feat}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {type === "pricing" && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-600">
                Transparent Pricing
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-neutral-900 mt-1">
                Simple, Predictable Plans
              </h2>
              <p className="text-sm text-neutral-600 mt-2">
                Start for free today with 50% off premium features for your first 3 months.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Free Plan */}
              <div className="p-5 rounded-2xl bg-white border border-neutral-200/80 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-base text-neutral-900">Community</h3>
                  <div className="text-2xl font-extrabold text-neutral-900 my-2">$0</div>
                  <p className="text-xs text-neutral-500 mb-4">Open source & individual exploration</p>
                  <ul className="text-xs space-y-2 text-neutral-700">
                    <li className="flex items-center gap-1.5">✓ Up to 10 Repositories</li>
                    <li className="flex items-center gap-1.5">✓ 5,000 Code Chunks</li>
                    <li className="flex items-center gap-1.5">✓ Line Citations</li>
                  </ul>
                </div>
                <button
                  onClick={onClose}
                  className="mt-6 w-full py-2.5 rounded-xl border border-neutral-300 font-semibold text-xs text-neutral-800 hover:bg-neutral-50"
                >
                  Current Plan
                </button>
              </div>

              {/* Pro Plan */}
              <div className="p-5 rounded-2xl bg-neutral-950 text-white border-2 border-purple-500 shadow-xl flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-3 right-3 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 text-white">
                  Popular
                </div>
                <div>
                  <h3 className="font-bold text-base text-white">Pro Team</h3>
                  <div className="text-2xl font-extrabold text-white my-2">
                    $29<span className="text-xs font-normal text-neutral-400">/mo</span>
                  </div>
                  <p className="text-xs text-neutral-400 mb-4">Autonomous agent reasoning for teams</p>
                  <ul className="text-xs space-y-2 text-neutral-200">
                    <li className="flex items-center gap-1.5">✓ Unlimited Repositories</li>
                    <li className="flex items-center gap-1.5">✓ 500,000 Code Chunks</li>
                    <li className="flex items-center gap-1.5">✓ Private GitHub Repos</li>
                    <li className="flex items-center gap-1.5">✓ LangGraph Self-Correction</li>
                  </ul>
                </div>
                <button
                  onClick={() => {
                    onClose();
                    onStartNow();
                  }}
                  className="mt-6 w-full py-2.5 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 font-semibold text-xs text-white shadow-md hover:scale-102 transition-all cursor-pointer"
                >
                  Start 14-Day Trial
                </button>
              </div>

              {/* Enterprise */}
              <div className="p-5 rounded-2xl bg-white border border-neutral-200/80 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-base text-neutral-900">Enterprise</h3>
                  <div className="text-2xl font-extrabold text-neutral-900 my-2">Custom</div>
                  <p className="text-xs text-neutral-500 mb-4">Dedicated VPC & on-premise vector DB</p>
                  <ul className="text-xs space-y-2 text-neutral-700">
                    <li className="flex items-center gap-1.5">✓ Self-Hosted PostgreSQL</li>
                    <li className="flex items-center gap-1.5">✓ Custom Fine-Tuned Models</li>
                    <li className="flex items-center gap-1.5">✓ SLA & Dedicated Support</li>
                  </ul>
                </div>
                <button
                  onClick={onClose}
                  className="mt-6 w-full py-2.5 rounded-xl border border-neutral-300 font-semibold text-xs text-neutral-800 hover:bg-neutral-50"
                >
                  Contact Sales
                </button>
              </div>
            </div>
          </div>
        )}

        {type === "faq" && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-600">
                Help & Answers
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-neutral-900 mt-1">
                Frequently Asked Questions
              </h2>
            </div>

            <div className="space-y-3">
              {[
                {
                  q: "How does CodeScout avoid hallucinating code?",
                  a: "CodeScout strictly injects actual file contents retrieved from pgvector into the prompt context and forces the model to cite exact file paths and line ranges. If no relevant chunks are found, the LangGraph loop initiates refinement or reports low confidence.",
                },
                {
                  q: "What programming languages are supported?",
                  a: "All common languages including Python, TypeScript, JavaScript, Go, Rust, Java, C++, Ruby, PHP, and SQL. Non-code files (images, binaries, lock files) are automatically filtered out.",
                },
                {
                  q: "Is my repository data private?",
                  a: "Yes. When running locally with your own PostgreSQL database and Gemini API key, your embeddings and code chunks remain entirely within your private instance.",
                },
                {
                  q: "How does query refinement work in LangGraph?",
                  a: "When a retrieval returns low cosine similarity or insufficient code context, an evaluation node evaluates the match. If incomplete, a refinement node rewrites technical keywords and triggers re-retrieval (up to 3 times).",
                },
              ].map((item, i) => (
                <div key={i} className="p-4 rounded-2xl bg-white border border-neutral-200/80 shadow-sm">
                  <h3 className="font-bold text-sm text-neutral-900">{item.q}</h3>
                  <p className="text-xs text-neutral-600 mt-1.5 leading-relaxed">{item.a}</p>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
