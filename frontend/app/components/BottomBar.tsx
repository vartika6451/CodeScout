"use client";

import React from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  ShellsLogo,
  SmartFinderLogo,
  ZoomerrLogo,
  KontrastrLogo,
  WavesMarathonLogo,
} from "./Icons";

interface BottomBarProps {
  onPromoClick?: () => void;
}

export default function BottomBar({ onPromoClick }: BottomBarProps) {
  return (
    <div className="w-full pt-6 pb-4 flex flex-col items-center space-y-8">
      
      {/* 1. Promo Ribbon Banner from the image */}
      <div className="w-full flex justify-center px-4">
        <div className="inline-flex flex-wrap items-center justify-center gap-2 px-5 py-2.5 rounded-full bg-white/70 hover:bg-white text-neutral-800 text-xs sm:text-sm font-medium border border-neutral-300/80 shadow-sm transition-all">
          <span className="font-semibold text-neutral-900">
            Enjoy 50% off premium features
          </span>
          <span className="text-neutral-500">
            for first 3 months — 21 days remaining
          </span>
          <button
            onClick={onPromoClick}
            className="inline-flex items-center gap-1 font-semibold text-purple-600 hover:text-purple-700 ml-1 transition-colors cursor-pointer"
          >
            <span className="w-4 h-4 rounded-full border border-purple-500 flex items-center justify-center text-[10px]">
              →
            </span>
            <span>Start 14 days trial</span>
          </button>
        </div>
      </div>

      {/* 2. Partner Brand Logos Row from the reference image */}
      <div className="w-full max-w-5xl mx-auto px-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-6 sm:gap-8 items-center justify-items-center opacity-85 hover:opacity-100 transition-opacity">
          {/* Logo 1: SHELLS */}
          <div className="text-neutral-900 hover:scale-105 transition-transform cursor-pointer">
            <ShellsLogo />
          </div>

          {/* Logo 2: SmartFinder */}
          <div className="text-neutral-900 hover:scale-105 transition-transform cursor-pointer">
            <SmartFinderLogo />
          </div>

          {/* Logo 3: Zoomerr */}
          <div className="text-neutral-900 hover:scale-105 transition-transform cursor-pointer">
            <ZoomerrLogo />
          </div>

          {/* Logo 4: kontrastr */}
          <div className="text-neutral-900 hover:scale-105 transition-transform cursor-pointer">
            <KontrastrLogo />
          </div>

          {/* Logo 5: WAVESMARATHON */}
          <div className="text-neutral-900 hover:scale-105 transition-transform cursor-pointer col-span-2 sm:col-span-1">
            <WavesMarathonLogo />
          </div>
        </div>
      </div>

      {/* 3. Subtle Technical Credit */}
      <div className="text-center pt-2 text-[11px] text-neutral-400">
        <p>
          CodeScout AI • Engineered with{" "}
          <span className="font-medium text-neutral-600">LangGraph</span>,{" "}
          <span className="font-medium text-neutral-600">Gemini 3.5 Flash</span>,{" "}
          <span className="font-medium text-neutral-600">pgvector</span> &amp;{" "}
          <span className="font-medium text-neutral-600">Next.js 16</span>
        </p>
      </div>

    </div>
  );
}
