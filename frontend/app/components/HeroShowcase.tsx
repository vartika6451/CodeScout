"use client";

import React, { useState } from "react";
import Image from "next/image";
import {
  ArrowRight,
  Sparkles,
  Play,
  Pause,
  MoreHorizontal,
  Mic,
  Video,
  Star,
  CheckCircle2,
  Terminal,
  Database,
  Search,
} from "lucide-react";
import { Repository } from "../types";

interface HeroShowcaseProps {
  onStartAnalysis: () => void;
  onExploreChat: (initialQuery?: string) => void;
  selectedRepo: string;
  repositories: Repository[];
}

export default function HeroShowcase({
  onStartAnalysis,
  onExploreChat,
  selectedRepo,
  repositories,
}: HeroShowcaseProps) {
  const [isPlaying, setIsPlaying] = useState(true);
  const [activeMode, setActiveMode] = useState<"meeting" | "codescout">("codescout");
  const [quickQuery, setQuickQuery] = useState("");

  const handleQuickSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickQuery.trim()) {
      onExploreChat(quickQuery.trim());
    }
  };

  return (
    <div className="w-full relative">
      {/* Hero 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-8 items-center pt-2 sm:pt-4 pb-12 sm:pb-16">
        
        {/* Left Column: Headline, Copy, Action Buttons & Micro Badges */}
        <div className="lg:col-span-5 flex flex-col justify-center text-left space-y-6 sm:space-y-7 z-10">
          
          {/* Main Headline */}
          <div className="space-y-1 sm:space-y-2">
            <h1 className="text-4xl sm:text-5xl lg:text-[62px] font-extrabold tracking-tight text-neutral-900 leading-[1.06]">
              <span className="bg-gradient-to-r from-purple-600 via-pink-500 to-orange-500 bg-clip-text text-transparent">
                AI analysis
              </span>
              <br />
              <span className="text-neutral-950">
                {activeMode === "meeting" ? "for real-time discussions" : "for complex codebases"}
              </span>
            </h1>
          </div>

          {/* Subtitle Body */}
          <p className="text-neutral-600 text-sm sm:text-base leading-relaxed max-w-lg font-normal">
            {activeMode === "meeting"
              ? "Livo AI records your meetings, recognizes who's speaking, and provides real-time insights and live recommendations — all without taking manual notes."
              : "CodeScout scans public GitHub repositories, indexes syntax chunks in pgvector, and orchestrates LangGraph multi-agent loops with transparent line citations."}
          </p>

          {/* Mode toggle badge (Meeting AI vs CodeScout Mode) */}
          <div className="inline-flex items-center gap-1.5 p-1 bg-neutral-200/60 rounded-full w-fit text-xs text-neutral-700">
            <button
              onClick={() => setActiveMode("codescout")}
              className={`px-3 py-1 rounded-full font-medium transition-all ${
                activeMode === "codescout"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              CodeScout Intelligence
            </button>
            <button
              onClick={() => setActiveMode("meeting")}
              className={`px-3 py-1 rounded-full font-medium transition-all ${
                activeMode === "meeting"
                  ? "bg-white text-neutral-900 shadow-sm"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              Live Meeting Mode
            </button>
          </div>

          {/* Primary Action Buttons */}
          <div className="flex flex-wrap items-center gap-3.5 pt-1">
            {/* Start for free / Analyze Repo Pill Button */}
            <button
              onClick={onStartAnalysis}
              className="group relative inline-flex items-center gap-3 px-6 py-3.5 rounded-full text-white font-semibold text-sm bg-gradient-to-r from-purple-600 via-pink-500 to-orange-500 shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer"
            >
              <span className="w-7 h-7 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center shrink-0 group-hover:translate-x-0.5 transition-transform">
                <ArrowRight className="w-3.5 h-3.5 text-white" />
              </span>
              <span>Start for free</span>
            </button>

            {/* Secondary Button */}
            <button
              onClick={() => onExploreChat()}
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full text-neutral-800 font-semibold text-sm bg-white border border-neutral-300 hover:bg-neutral-50 hover:border-neutral-400 shadow-sm hover:scale-[1.01] active:scale-[0.98] transition-all cursor-pointer"
            >
              <span>{activeMode === "codescout" ? "Explore AI Chat" : "Contact us"}</span>
            </button>
          </div>

          {/* Trust micro-bullets matching the reference image */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-neutral-500 font-medium pt-1">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>
              31-day free trial
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>
              No credit card required
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>
              Cancel anytime
            </span>
          </div>

          {/* Quick interactive test query box */}
          <form
            onSubmit={handleQuickSubmit}
            className="pt-2 flex items-center gap-2 max-w-md w-full bg-white rounded-2xl p-1.5 border border-neutral-300/80 shadow-sm focus-within:ring-2 focus-within:ring-purple-500/30 transition-all"
          >
            <div className="pl-3 text-neutral-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder={
                selectedRepo
                  ? `Ask about ${selectedRepo}...`
                  : "Ask anything about project architecture..."
              }
              value={quickQuery}
              onChange={(e) => setQuickQuery(e.target.value)}
              className="flex-1 bg-transparent text-xs sm:text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-xs font-semibold hover:bg-black transition-colors"
            >
              Ask
            </button>
          </form>

        </div>

        {/* Right Column: Interactive Centerpiece & Surrounding Video Avatars */}
        <div className="lg:col-span-7 relative flex items-center justify-center min-h-[520px] sm:min-h-[580px] py-4">

          {/* Connecting SVG curves between tiles and center card */}
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none z-0 hidden sm:block"
            viewBox="0 0 600 500"
            fill="none"
          >
            {/* Top-left to Center curve */}
            <path
              d="M 120 120 C 180 180, 200 200, 260 220"
              stroke="#D8B4FE"
              strokeWidth="2"
              strokeDasharray="4 4"
            />
            {/* Bottom-left to Center curve */}
            <path
              d="M 120 380 C 180 340, 200 300, 260 280"
              stroke="#FBCFE8"
              strokeWidth="2"
              strokeDasharray="4 4"
            />
          </svg>

          {/* Glowing central node pin matching the reference image's star pin */}
          <div className="absolute left-[18%] sm:left-[22%] top-[48%] -translate-y-1/2 z-20 hidden sm:flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-tr from-purple-600 via-pink-500 to-orange-400 shadow-lg glow-pin">
            <Sparkles className="w-3.5 h-3.5 text-white animate-spin-slow" />
          </div>

          {/* Top-Left Floating Avatar (Alex) */}
          <div className="absolute top-2 sm:top-4 left-0 sm:left-4 z-20 float-slow">
            <div className="relative group w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden border-2 border-white shadow-xl bg-neutral-900 transition-transform hover:scale-105">
              <Image
                src="/avatars/avatar1.jpg"
                alt="Alex video call"
                fill
                sizes="112px"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-1.5 left-2 right-2 flex items-center justify-between text-white text-[10px]">
                <span className="font-medium truncate">Alex</span>
                <div className="flex items-center gap-1">
                  <Mic className="w-3 h-3 text-emerald-400" />
                  <Video className="w-3 h-3 text-white/80" />
                </div>
              </div>
            </div>
          </div>

          {/* Top-Right Floating Avatar (Sarah) */}
          <div className="absolute top-4 sm:top-6 right-0 sm:right-6 z-20 float-delayed">
            <div className="relative group w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden border-2 border-white shadow-xl bg-neutral-900 transition-transform hover:scale-105">
              <Image
                src="/avatars/avatar2.jpg"
                alt="Sarah video call"
                fill
                sizes="112px"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-1.5 left-2 right-2 flex items-center justify-between text-white text-[10px]">
                <span className="font-medium truncate">Sarah</span>
                <div className="flex items-center gap-1">
                  <Mic className="w-3 h-3 text-emerald-400" />
                  <Video className="w-3 h-3 text-white/80" />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom-Left Floating Avatar (Maya) */}
          <div className="absolute bottom-4 sm:bottom-6 left-2 sm:left-6 z-20 float-delayed">
            <div className="relative group w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden border-2 border-white shadow-xl bg-neutral-900 transition-transform hover:scale-105">
              <Image
                src="/avatars/avatar3.jpg"
                alt="Maya video call"
                fill
                sizes="112px"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-1.5 left-2 right-2 flex items-center justify-between text-white text-[10px]">
                <span className="font-medium truncate">Maya</span>
                <div className="flex items-center gap-1">
                  <Mic className="w-3 h-3 text-emerald-400" />
                  <Video className="w-3 h-3 text-white/80" />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom-Right Floating Avatar (Elena) */}
          <div className="absolute bottom-2 sm:bottom-4 right-2 sm:right-8 z-20 float-slow">
            <div className="relative group w-24 h-24 sm:w-28 sm:h-28 rounded-2xl overflow-hidden border-2 border-white shadow-xl bg-neutral-900 transition-transform hover:scale-105">
              <Image
                src="/avatars/avatar4.jpg"
                alt="Elena video call"
                fill
                sizes="112px"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-1.5 left-2 right-2 flex items-center justify-between text-white text-[10px]">
                <span className="font-medium truncate">Elena</span>
                <div className="flex items-center gap-1">
                  <Mic className="w-3 h-3 text-emerald-400" />
                  <Video className="w-3 h-3 text-white/80" />
                </div>
              </div>
            </div>
          </div>

          {/* Central Mockup Device Container */}
          <div className="relative z-10 w-full max-w-[320px] sm:max-w-[350px] mx-auto bg-[#0F1117] text-white rounded-[32px] p-4 sm:p-5 shadow-2xl border border-neutral-800/80">

            {/* Floating G2 Rating Pill on Top-Right */}
            <div className="absolute -top-4 -right-4 sm:-right-6 bg-white text-neutral-900 px-3 py-1.5 rounded-2xl shadow-xl border border-neutral-100 flex items-center gap-2 z-30">
              <div className="w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center">
                G
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-0.5">
                  <span className="text-[11px] font-bold">5.0 / 5.0</span>
                  <div className="flex text-amber-400">
                    <Star className="w-2.5 h-2.5 fill-amber-400" />
                    <Star className="w-2.5 h-2.5 fill-amber-400" />
                    <Star className="w-2.5 h-2.5 fill-amber-400" />
                    <Star className="w-2.5 h-2.5 fill-amber-400" />
                    <Star className="w-2.5 h-2.5 fill-amber-400" />
                  </div>
                </div>
                <span className="text-[8px] text-neutral-400 font-medium">#1 Rated • 8,000+ Reviews</span>
              </div>
            </div>

            {/* Header: Title + Soundwave */}
            <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
              <div>
                <h3 className="text-sm font-semibold text-white tracking-tight">
                  {activeMode === "meeting" ? "End-of-Sprint Meeting" : "CodeScout Investigation"}
                </h3>
                <span className="text-[10px] text-neutral-400">
                  {selectedRepo ? selectedRepo : "LangGraph Multi-Agent RAG"}
                </span>
              </div>
              <button
                className="w-7 h-7 rounded-full bg-neutral-800/60 flex items-center justify-center text-neutral-400 hover:text-white"
                title="Options"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>
            </div>

            {/* Active Soundwave Visualization */}
            <div className="py-3 flex items-center justify-center gap-1.5 h-12 bg-neutral-900/60 rounded-xl my-2 border border-neutral-800/50">
              <span className={`w-1 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full ${isPlaying ? "wave-bar-1" : "h-2"}`} />
              <span className={`w-1 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full ${isPlaying ? "wave-bar-2" : "h-3"}`} />
              <span className={`w-1 bg-gradient-to-t from-pink-500 to-orange-400 rounded-full ${isPlaying ? "wave-bar-3" : "h-5"}`} />
              <span className={`w-1 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full ${isPlaying ? "wave-bar-4" : "h-2"}`} />
              <span className={`w-1 bg-gradient-to-t from-pink-500 to-orange-400 rounded-full ${isPlaying ? "wave-bar-5" : "h-4"}`} />
              <span className={`w-1 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full ${isPlaying ? "wave-bar-6" : "h-2"}`} />
              <span className={`w-1 bg-gradient-to-t from-pink-500 to-orange-400 rounded-full ${isPlaying ? "wave-bar-7" : "h-5"}`} />
              <span className={`w-1 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full ${isPlaying ? "wave-bar-8" : "h-2"}`} />
            </div>

            {/* Time Indicator & Live Analysis Pill */}
            <div className="flex items-center justify-between text-xs py-1">
              <span className="font-mono text-neutral-400 text-[11px] flex items-center gap-1">
                ⏱️ 00:05:39
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-pink-500/10 text-pink-400 border border-pink-500/20">
                <Sparkles className="w-2.5 h-2.5" />
                <span>Analysing...</span>
              </span>
            </div>

            {/* Floating Insight Popout Card (Conrad) matching the image */}
            <div className="relative -mx-2 my-2 p-3 bg-white text-neutral-900 rounded-2xl shadow-2xl border border-neutral-100 z-20">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold">
                    C
                  </div>
                  <span className="text-xs font-bold text-neutral-800">Conrad</span>
                </div>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-purple-100 text-purple-700 text-[9px] font-bold">
                  <Mic className="w-2.5 h-2.5" /> 05:46
                </span>
              </div>
              <p className="text-xs text-neutral-700 leading-snug font-medium">
                {activeMode === "meeting"
                  ? "The only thing left is to get the final illustration, and..."
                  : "pgvector cosine distance query executed. 8 semantic code chunks retrieved."}
              </p>
            </div>

            {/* Meeting Transcript Stream */}
            <div className="space-y-2 py-1 text-xs text-neutral-300">
              {/* Message 1 */}
              <div className="p-2 rounded-xl bg-neutral-900/90 border border-neutral-800/80">
                <div className="flex items-center justify-between text-[10px] text-neutral-400 mb-0.5">
                  <span className="font-semibold text-neutral-300">Sofia</span>
                  <span>04:34</span>
                </div>
                <p className="text-[11px] leading-tight text-neutral-300">
                  Perfect. Any blockers on your side, Liam?
                </p>
              </div>

              {/* Message 2 */}
              <div className="p-2 rounded-xl bg-neutral-900/90 border border-neutral-800/80">
                <div className="flex items-center justify-between text-[10px] text-neutral-400 mb-0.5">
                  <span className="font-semibold text-neutral-300">Liam</span>
                  <span>05:01</span>
                </div>
                <p className="text-[11px] leading-tight text-neutral-300">
                  Go with the slim variant. The thick one is only for the web dashboard; mobile uses the lighter style.
                </p>
              </div>
            </div>

            {/* Central Floating Audio Pause / Play Action Button */}
            <div className="pt-2 flex justify-center">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="w-10 h-10 rounded-full bg-neutral-900 border border-neutral-700 flex items-center justify-center text-white shadow-xl hover:scale-110 active:scale-95 transition-all cursor-pointer"
                title={isPlaying ? "Pause audio waveform" : "Play audio waveform"}
              >
                {isPlaying ? (
                  <Pause className="w-4 h-4 fill-white" />
                ) : (
                  <Play className="w-4 h-4 fill-white ml-0.5" />
                )}
              </button>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
