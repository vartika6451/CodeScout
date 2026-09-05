"use client";

import React, { useState } from "react";
import { Check, Copy, Terminal } from "lucide-react";

interface MarkdownViewProps {
  content: string;
}

export default function MarkdownView({ content }: MarkdownViewProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (codeText: string, index: number) => {
    navigator.clipboard.writeText(codeText);
    setCopiedIndex(index);
    setTimeout(() => {
      setCopiedIndex(null);
    }, 2000);
  };

  // Parse markdown into blocks (code blocks, headers, bullet points, paragraphs)
  const renderFormattedContent = () => {
    // Split by code blocks ```lang ... ```
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let blockCounter = 0;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Text before code block
      if (match.index > lastIndex) {
        const textBefore = content.substring(lastIndex, match.index);
        parts.push(
          <div key={`text-${lastIndex}`} className="space-y-2">
            {renderTextSection(textBefore)}
          </div>
        );
      }

      const lang = match[1] || "code";
      const code = match[2].trim();
      const currentIndex = blockCounter++;

      // Code block element
      parts.push(
        <div
          key={`code-${match.index}`}
          className="my-3 rounded-xl border border-slate-700/60 bg-[#070b13] overflow-hidden shadow-lg"
        >
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900/70 text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1.5 font-medium text-cyan-400">
              <Terminal className="w-3.5 h-3.5" />
              {lang}
            </span>
            <button
              onClick={() => handleCopy(code, currentIndex)}
              className="flex items-center gap-1 px-2 py-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="Copy code"
            >
              {copiedIndex === currentIndex ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <pre className="p-4 overflow-x-auto text-xs sm:text-sm font-mono text-slate-200 leading-relaxed">
            <code>{code}</code>
          </pre>
        </div>
      );

      lastIndex = match.index + match[0].length;
    }

    // Remaining text
    if (lastIndex < content.length) {
      const remainingText = content.substring(lastIndex);
      parts.push(
        <div key={`text-end`} className="space-y-2">
          {renderTextSection(remainingText)}
        </div>
      );
    }

    return parts;
  };

  const renderTextSection = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} className="h-2" />;
      }

      // Headers
      if (trimmed.startsWith("### ")) {
        return (
          <h4
            key={idx}
            className="text-base font-semibold text-cyan-300 mt-3 mb-1"
          >
            {renderInlineMarkdown(trimmed.replace(/^###\s+/, ""))}
          </h4>
        );
      }
      if (trimmed.startsWith("## ")) {
        return (
          <h3
            key={idx}
            className="text-lg font-bold text-slate-100 mt-4 mb-2 flex items-center gap-2"
          >
            {renderInlineMarkdown(trimmed.replace(/^##\s+/, ""))}
          </h3>
        );
      }
      if (trimmed.startsWith("# ")) {
        return (
          <h2
            key={idx}
            className="text-xl font-extrabold text-white mt-4 mb-2"
          >
            {renderInlineMarkdown(trimmed.replace(/^#\s+/, ""))}
          </h2>
        );
      }

      // Bullet items
      if (/^[-*]\s+/.test(trimmed)) {
        return (
          <div key={idx} className="flex items-start gap-2.5 my-1 text-slate-300 pl-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-2 shrink-0" />
            <div className="leading-relaxed">
              {renderInlineMarkdown(trimmed.replace(/^[-*]\s+/, ""))}
            </div>
          </div>
        );
      }

      // Numbered items
      if (/^\d+\.\s+/.test(trimmed)) {
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
        return (
          <div key={idx} className="flex items-start gap-2 my-1 text-slate-300 pl-2">
            <span className="font-mono text-xs text-indigo-400 font-semibold mt-0.5 shrink-0">
              {numMatch ? numMatch[1] : ""}.
            </span>
            <div className="leading-relaxed">
              {renderInlineMarkdown(numMatch ? numMatch[2] : trimmed)}
            </div>
          </div>
        );
      }

      // Paragraph
      return (
        <p key={idx} className="text-slate-300 leading-relaxed">
          {renderInlineMarkdown(trimmed)}
        </p>
      );
    });
  };

  const renderInlineMarkdown = (line: string): React.ReactNode => {
    // Regex for bold **text**, inline code `code`, and links [text](url)
    const regex = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    const segments = line.split(regex);

    return segments.map((seg, i) => {
      if (seg.startsWith("**") && seg.endsWith("**")) {
        return (
          <strong key={i} className="font-semibold text-slate-100">
            {seg.slice(2, -2)}
          </strong>
        );
      }
      if (seg.startsWith("`") && seg.endsWith("`")) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-800 border border-slate-700/60 font-mono text-xs text-cyan-300"
          >
            {seg.slice(1, -1)}
          </code>
        );
      }
      const linkMatch = seg.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        return (
          <a
            key={i}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
          >
            {linkMatch[1]}
          </a>
        );
      }
      return seg;
    });
  };

  return <div className="space-y-1 text-sm">{renderFormattedContent()}</div>;
}
