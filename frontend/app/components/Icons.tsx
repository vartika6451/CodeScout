import React from "react";

export function GithubIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

// Brand squircle logo from the reference design
export function BrandSquircleIcon({ className = "w-5 h-5 text-white" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="10" fill="currentColor" />
      <path
        d="M10 16C10 12.6863 12.6863 10 16 10C19.3137 10 22 12.6863 22 16C22 19.3137 19.3137 22 16 22H11C10.4477 22 10 21.5523 10 21V16Z"
        fill="white"
      />
      <circle cx="16" cy="16" r="3" fill="black" />
    </svg>
  );
}

// Partner Brand: SHELLS
export function ShellsLogo({ className = "h-5 text-neutral-800" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 font-bold tracking-wider text-sm ${className}`}>
      <svg className="w-6 h-6 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" strokeDasharray="3 3" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="3" />
      </svg>
      <span className="font-extrabold uppercase tracking-widest text-xs sm:text-sm">SHELLS</span>
    </div>
  );
}

// Partner Brand: SmartFinder
export function SmartFinderLogo({ className = "h-5 text-neutral-800" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 font-bold text-sm ${className}`}>
      <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
      </svg>
      <span className="font-extrabold tracking-tight text-xs sm:text-sm">SmartFinder</span>
    </div>
  );
}

// Partner Brand: Zoomerr
export function ZoomerrLogo({ className = "h-5 text-neutral-800" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 font-bold text-sm ${className}`}>
      <div className="w-5 h-5 rounded-full bg-current flex items-center justify-center text-white shrink-0">
        <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
          <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" fill="white" />
        </svg>
      </div>
      <span className="font-extrabold tracking-tight text-xs sm:text-sm">Zoomerr</span>
    </div>
  );
}

// Partner Brand: kontrastr
export function KontrastrLogo({ className = "h-5 text-neutral-800" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 font-bold text-sm ${className}`}>
      <div className="w-4 h-4 rounded border-2 border-current flex items-center justify-center shrink-0">
        <div className="w-2 h-3 bg-current ml-auto" />
      </div>
      <span className="font-bold lowercase tracking-tight text-xs sm:text-sm">kontrastr</span>
    </div>
  );
}

// Partner Brand: WAVESMARATHON
export function WavesMarathonLogo({ className = "h-5 text-neutral-800" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2 font-bold text-sm ${className}`}>
      <div className="flex items-center gap-0.5 shrink-0">
        <span className="w-0.5 h-2 bg-current rounded-full" />
        <span className="w-0.5 h-3.5 bg-current rounded-full" />
        <span className="w-0.5 h-5 bg-current rounded-full" />
        <span className="w-0.5 h-3 bg-current rounded-full" />
        <span className="w-0.5 h-4.5 bg-current rounded-full" />
        <span className="w-0.5 h-2 bg-current rounded-full" />
      </div>
      <span className="font-extrabold uppercase tracking-wider text-[11px] sm:text-xs">WAVESMARATHON</span>
    </div>
  );
}

