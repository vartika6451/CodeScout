"use client";

import React, { useState } from "react";
import { X, FileCode, Check, Copy, ExternalLink, Percent } from "lucide-react";
import { SourceCitation } from "../types";

interface CitationViewerProps {
  citation: SourceCitation | null;
  repository: string;
  onClose: () => void;
}

export default function CitationViewer({
  citation,
  repository,
  onClose,
}: CitationViewerProps) {
  const [copied, setCopied] = useState(false);

  if (!citation) return null;

  const handleCopy = () => {
    if (citation.content) {
      navigator.clipboard.writeText(citation.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lines = (citation.content || "").split("\n");
  const similarityPercent = Math.round(citation.similarity * 100);
  const githubFileUrl = `https://github.com/${repository}/blob/main/${citation.file_path}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl glass-panel border border-slate-700/80 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-slate-900/60">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
              <FileCode className="w-5 h-5" />
            </div>
            <div className="truncate">
              <h3 className="text-sm font-semibold text-slate-100 truncate font-mono">
                {citation.file_path}
              </h3>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
                <span>Chunk #{citation.chunk_index}</span>
                <span>•</span>
                <span className="flex items-center gap-1 text-cyan-400 font-medium">
                  <Percent className="w-3 h-3" />
                  {similarityPercent}% match
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={githubFileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="Open file on GitHub"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Code</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Code Content */}
        <div className="flex-1 overflow-auto p-4 bg-[#070b13] font-mono text-xs sm:text-sm text-slate-300">
          {citation.content ? (
            <div className="table w-full border-collapse">
              {lines.map((line, idx) => (
                <div key={idx} className="table-row hover:bg-slate-800/30">
                  <span className="table-cell pr-4 text-right select-none text-slate-600 w-10 text-xs">
                    {idx + 1}
                  </span>
                  <span className="table-cell whitespace-pre font-mono text-slate-200">
                    {line}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-500 italic p-6 text-center">
              Snippet content preview is not available for this chunk.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-slate-900/40 flex items-center justify-between text-xs text-slate-400">
          <span>
            Repository: <span className="text-slate-300 font-mono">{repository}</span>
          </span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
