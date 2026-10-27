"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Building2, Shield, Lock, AlertCircle, ArrowRight, UserCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect
  React.useEffect(() => {
    if (user) {
      if (user.role === "institution") {
        router.push("/applications");
      } else {
        router.push("/dashboard");
      }
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // navigation handled by useEffect
    } catch (err: any) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("Demo@Password123");
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-navy-900 to-slate-950 flex flex-col justify-center items-center p-4">
      {/* Container */}
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-100">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-900 to-indigo-950 p-6 text-white text-center relative">
          <div className="w-14 h-14 bg-white/10 rounded-xl mx-auto flex items-center justify-center backdrop-blur-sm border border-white/20 mb-3 shadow-inner">
            <Building2 className="w-8 h-8 text-blue-300" />
          </div>
          <h2 className="text-xl font-bold tracking-tight">AICTE Document Verification</h2>
          <p className="text-xs text-blue-200 mt-1 font-medium">National Decision-Support System for Technical Institutions</p>
          <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/20 text-blue-200 text-[11px] font-semibold border border-blue-400/30">
            <Shield className="w-3.5 h-3.5 text-blue-300" />
            <span>Human-in-the-Loop Scrutiny</span>
          </div>
        </div>

        {/* Form Body */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Official Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@aicte.gov.in"
                className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-sm shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-70"
            >
              {submitting ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In to Portal</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Switcher */}
          <div className="mt-6 pt-5 border-t border-slate-200">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 text-center mb-2.5">
              One-Click Demo Personas
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleQuickLogin("official@aicte.gov.in")}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-blue-50 hover:border-blue-300 transition-all group"
              >
                <div className="font-bold text-slate-800 group-hover:text-blue-700 flex items-center gap-1">
                  <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>AICTE Official</span>
                </div>
                <div className="text-[10px] text-slate-500">Scrutiny & Decisions</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin("inst1@aicte.gov.in")}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-blue-50 hover:border-blue-300 transition-all group"
              >
                <div className="font-bold text-slate-800 group-hover:text-blue-700 flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-blue-600" />
                  <span>Apex Tech (Inst 1)</span>
                </div>
                <div className="text-[10px] text-slate-500">Applicant Portal</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin("inst2@aicte.gov.in")}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-blue-50 hover:border-blue-300 transition-all group"
              >
                <div className="font-bold text-slate-800 group-hover:text-blue-700 flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-blue-600" />
                  <span>Zenith College (Inst 2)</span>
                </div>
                <div className="text-[10px] text-slate-500">Duplicate Check Case</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin("auditor@aicte.gov.in")}
                className="p-2 border border-slate-200 rounded-lg text-left hover:bg-blue-50 hover:border-blue-300 transition-all group"
              >
                <div className="font-bold text-slate-800 group-hover:text-blue-700 flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5 text-blue-600" />
                  <span>Council Auditor</span>
                </div>
                <div className="text-[10px] text-slate-500">Append-Only Logs</div>
              </button>
            </div>
            <p className="mt-3 text-[10px] text-center text-slate-400">
              Demo passwords default to <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-600">Demo@Password123</code>.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 text-center text-xs text-slate-400">
        Decision Support System &bull; All final approvals are subject to official verification.
      </div>
    </div>
  );
}
