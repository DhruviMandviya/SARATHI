"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  Compass,
  UserCheck,
  Building2,
  ArrowRight,
  AlertCircle,
  Info,
} from "lucide-react";

/**
 * Geometric 24-spoke Ashoka Chakra motif for dignified watermark and emblem seal.
 */
function AshokaChakra({ className }: { className?: string }) {
  // Precompute 24 spokes at 15° intervals
  const spokes = Array.from({ length: 24 }, (_, i) => {
    const angle = (i * 15 * Math.PI) / 180;
    const x1 = 100 + 19 * Math.cos(angle);
    const y1 = 100 + 19 * Math.sin(angle);
    const x2 = 100 + 87 * Math.cos(angle);
    const y2 = 100 + 87 * Math.sin(angle);
    return { x1, y1, x2, y2 };
  });

  return (
    <svg
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <circle cx="100" cy="100" r="92" stroke="currentColor" strokeWidth="3" />
      <circle cx="100" cy="100" r="88" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
      <circle cx="100" cy="100" r="19" stroke="currentColor" strokeWidth="3" />
      <circle cx="100" cy="100" r="7" fill="currentColor" />
      {spokes.map((s, idx) => (
        <line
          key={idx}
          x1={s.x1}
          y1={s.y1}
          x2={s.x2}
          y2={s.y2}
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If already authenticated, redirect to dashboard
  React.useEffect(() => {
    if (user) {
      router.push("/dashboard");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // Navigation is handled reactively by useEffect on user state
    } catch (err: any) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("Demo@Password123");
    setError(null);
    setSubmitting(true);
    try {
      await login(demoEmail, "Demo@Password123");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to log in with demo account. Please verify credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBFA] flex flex-col justify-between text-slate-800 relative selection:bg-[#0A4D2E]/20 selection:text-[#0A4D2E]">
      {/* 1. Official Government Header */}
      <header className="bg-white border-b border-slate-200 px-4 sm:px-8 py-3 shrink-0 shadow-[0_1px_3px_rgba(0,0,0,0.03)]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Council & Ministry Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center p-1 shrink-0 shadow-2xs">
              <img
                src="/assets/aicte_logo.png"
                alt="AICTE Official Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <h2 className="text-xs sm:text-sm font-extrabold text-slate-900 tracking-wide uppercase leading-tight">
                ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
              </h2>
              <p className="text-[11px] text-slate-600 font-normal leading-tight mt-0.5">
                Statutory Body Under Ministry of Education, Govt. of India
              </p>
            </div>
          </div>

          {/* Operational Status & Academic Year */}
          <div className="flex items-center gap-2.5 text-xs self-start md:self-auto">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-[#0A4D2E] border border-emerald-200/90 font-semibold text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#0A4D2E] animate-pulse" />
              Production Preview
            </span>
            <span className="text-slate-300 hidden sm:inline" aria-hidden="true">|</span>
            <span className="text-slate-600 font-medium text-[11px] sm:text-xs">
              Academic Year 2026–2027
            </span>
          </div>
        </div>
      </header>

      {/* 2. Main Two-Column Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8 sm:py-12 md:py-16 flex items-center justify-center relative">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
          
          {/* Left Column — Branding and introduction */}
          <div className="lg:col-span-7 relative space-y-6 sm:space-y-8">
            {/* Subtle national-emblem-inspired background watermark */}
            <div
              className="absolute -left-6 sm:-left-12 -top-12 w-80 sm:w-96 md:w-[460px] h-80 sm:h-96 md:h-[460px] pointer-events-none opacity-[0.035] text-[#0A4D2E] select-none -z-0"
              aria-hidden="true"
            >
              <AshokaChakra className="w-full h-full" />
            </div>

            <div className="relative z-10 space-y-4 sm:space-y-5">
              {/* Small pill label */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#0A4D2E]/10 text-[#0A4D2E] text-xs font-bold tracking-wider uppercase border border-[#0A4D2E]/20">
                <Compass className="w-3.5 h-3.5 text-[#0A4D2E]" />
                <span>AICTE REGULATORY DECISION SUPPORT</span>
              </div>

              {/* Main wordmark with Official AICTE Logo */}
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-xl bg-white border border-slate-200 p-1.5 shadow-xs flex items-center justify-center shrink-0">
                  <img
                    src="/assets/aicte_logo.png"
                    alt="AICTE Official Logo"
                    className="w-full h-full object-contain"
                  />
                </div>
                <div>
                  <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black text-[#0A4D2E] tracking-tight leading-none">
                    SARATHI
                  </h1>
                </div>
              </div>

              {/* Official tagline */}
              <div>
                <p className="text-xl sm:text-2xl font-semibold text-slate-800 leading-snug tracking-tight">
                  Your Digital Charioteer for Seamless AICTE Regulatory Governance.
                </p>
              </div>

              {/* Supporting description */}
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-xl">
                An integrated digital platform for transparent document verification, regulatory compliance, and AI-assisted scrutiny of technical institutions.
              </p>
            </div>

            {/* Light-green bordered information panel at the bottom of the column */}
            <div className="relative z-10 p-4 bg-[#F0FDF4] rounded-xl border border-[#86EFAC] text-xs text-[#166534] flex items-start gap-3 shadow-2xs max-w-xl">
              <Info className="w-4 h-4 text-[#0A4D2E] shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <strong>Official Scrutiny Architecture:</strong> Designed in compliance with AICTE Approval Process Handbook (APH) norms; final determinations remain with the authorized council officials.
              </p>
            </div>
          </div>

          {/* Right Column — Vertically centered sign-in card */}
          <div className="lg:col-span-5 w-full max-w-md mx-auto">
            <div className="bg-white rounded-2xl shadow-xl border border-[#0A4D2E]/25 overflow-hidden">
              
              {/* Deep forest-green card header */}
              <div className="bg-[#0A4D2E] text-white p-6 sm:p-7 text-center relative border-b border-[#083D24]">
                <div className="w-12 h-12 rounded-xl bg-white p-1 mx-auto flex items-center justify-center mb-3 shadow-sm border border-emerald-700/50">
                  <img
                    src="/assets/aicte_logo.png"
                    alt="AICTE Official Logo"
                    className="w-full h-full object-contain"
                  />
                </div>
                <h2 className="text-xl font-bold tracking-tight text-white">
                  Sign In to SARATHI
                </h2>
                <p className="text-xs text-emerald-100/90 mt-1 font-medium">
                  AICTE Regulatory Governance &amp; Scrutiny Portal
                </p>
              </div>

              {/* White card body with sign-in form */}
              <div className="p-6 sm:p-7 bg-white">
                {error && (
                  <div
                    role="alert"
                    className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5 text-xs text-red-700"
                  >
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label
                      htmlFor="official-email"
                      className="block text-xs font-semibold text-slate-700 mb-1.5"
                    >
                      Official Email Address
                    </label>
                    <input
                      id="official-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@aicte.gov.in"
                      className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] focus:border-[#0A4D2E] transition-colors bg-white text-slate-900 placeholder:text-slate-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="account-password"
                      className="block text-xs font-semibold text-slate-700 mb-1.5"
                    >
                      Password
                    </label>
                    <input
                      id="account-password"
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] focus:border-[#0A4D2E] transition-colors bg-white text-slate-900 placeholder:text-slate-400"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full mt-2 py-2.5 px-4 bg-[#0A4D2E] hover:bg-[#083D24] text-white font-semibold rounded-lg text-sm shadow-sm hover:shadow transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {submitting ? (
                      <span>Authenticating Credentials...</span>
                    ) : (
                      <>
                        <span>Sign In to Portal</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </form>

                {/* Subtle horizontal divider & Demo Personas */}
                <div className="mt-6 pt-5 border-t border-slate-200">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center mb-3">
                    ONE-CLICK DEMO PERSONAS
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                    {/* Persona 1: AICTE Official */}
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => handleQuickLogin("official@aicte.gov.in")}
                      className="p-3 border border-[#0A4D2E]/25 bg-[#F0FDF4]/70 hover:bg-[#DCFCE7] rounded-xl text-left transition-all group disabled:opacity-50 shadow-2xs"
                    >
                      <div className="font-bold text-slate-900 group-hover:text-[#0A4D2E] flex items-center gap-1.5">
                        <UserCheck className="w-4 h-4 text-[#0A4D2E]" />
                        <span>AICTE Official</span>
                      </div>
                      <div className="text-[11px] text-slate-600 font-medium mt-0.5">
                        Scrutiny &amp; Decisions
                      </div>
                    </button>

                    {/* Persona 2: Institution Applicant */}
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={() => handleQuickLogin("inst1@aicte.gov.in")}
                      className="p-3 border border-slate-200 bg-slate-50/80 hover:bg-slate-100 rounded-xl text-left transition-all group disabled:opacity-50 shadow-2xs"
                    >
                      <div className="font-bold text-slate-900 group-hover:text-slate-900 flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-slate-600" />
                        <span>Institution Applicant</span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                        Applicant Portal
                      </div>
                    </button>
                  </div>

                  <p className="mt-3.5 text-[11px] text-center text-slate-500">
                    Demo passwords default to{" "}
                    <code className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono text-[10px] border border-slate-200">
                      Demo@Password123
                    </code>
                    .
                  </p>
                </div>

              </div>
            </div>
          </div>

        </div>
      </main>

      {/* 4. Official Portal Footer */}
      <footer className="bg-white border-t border-slate-200 py-3.5 px-4 sm:px-8 text-center text-xs text-slate-500 shrink-0">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            <strong className="text-slate-700">SARATHI</strong> — Your Digital Charioteer for Seamless AICTE Regulatory Governance.
          </div>
          <div className="text-[11px] text-slate-400">
            Decision Support System &bull; All final determinations are subject to official verification by competent AICTE authorities.
          </div>
        </div>
      </footer>
    </div>
  );
}
