"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { Institution } from "@/lib/types";
import {
  User,
  Building2,
  Mail,
  Shield,
  KeyRound,
  LogOut,
  MapPin,
  Award,
  CheckCircle2,
} from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const { user, isInstitution, logout, isLoading: authLoading } = useAuth();
  const [institution, setInstitution] = useState<Institution | null>(null);
  const [loadingInst, setLoadingInst] = useState<boolean>(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    async function loadInstitution() {
      if (user?.institution_id) {
        try {
          setLoadingInst(true);
          const data = await apiRequest<Institution>(`/institutions/${user.institution_id}`);
          setInstitution(data);
        } catch (err) {
          console.error("Failed to load institution details", err);
        } finally {
          setLoadingInst(false);
        }
      }
    }
    loadInstitution();
  }, [user?.institution_id]);

  if (authLoading || !user) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading user account profile...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-white border border-slate-200 p-0.5 flex items-center justify-center shrink-0 shadow-2xs">
            <img
              src="/assets/aicte_logo.png"
              alt="AICTE Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <span>User Profile &amp; Institutional Account</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Accredited credentials and security settings for SARATHI AICTE Regulatory Governance Portal.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: User Summary Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center text-center space-y-4">
          <div className="w-20 h-20 rounded-full bg-[#0A4D2E] text-white flex items-center justify-center text-2xl font-bold shadow-md">
            {user.full_name?.charAt(0) || "U"}
          </div>

          <div>
            <h3 className="font-bold text-base text-slate-900">{user.full_name}</h3>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>

          <div className="w-full pt-2">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold capitalize bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">
              Role: {user.role}
            </span>
          </div>

          <div className="w-full pt-4 border-t border-slate-100">
            <button
              onClick={logout}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors border border-slate-200"
            >
              <LogOut className="w-4 h-4 text-rose-600" />
              <span>Sign Out of Account</span>
            </button>
          </div>
        </div>

        {/* Right Column: Account Details & Institution Details */}
        <div className="md:col-span-2 space-y-6">
          {/* User Details */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-2 border-b border-slate-100">
              <Shield className="w-4 h-4 text-[#0A4D2E]" />
              <span>Authentication &amp; Permissions</span>
            </h4>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5 font-medium">Account ID</span>
                <span className="font-mono font-bold text-slate-800">USR-{user.id.toString().padStart(4, "0")}</span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5 font-medium">Session Status</span>
                <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Authenticated</span>
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5 font-medium">Registered Email</span>
                <span className="font-mono text-slate-800">{user.email}</span>
              </div>
              <div>
                <span className="text-slate-400 block mb-0.5 font-medium">System Role</span>
                <span className="capitalize font-semibold text-slate-800">{user.role}</span>
              </div>
            </div>
          </div>

          {/* Institutional Details (if institution user) */}
          {isInstitution && (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2 pb-2 border-b border-slate-100">
                <Building2 className="w-4 h-4 text-[#0A4D2E]" />
                <span>Accredited Technical Institution</span>
              </h4>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5 font-medium">Institution Name</span>
                  <span className="font-bold text-slate-900 text-sm">
                    {institution?.name || "Apex Institute of Technology"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-slate-400 block mb-0.5 font-medium">AICTE Permanent ID</span>
                    <span className="font-mono font-bold text-[#0A4D2E]">
                      {institution?.aicte_id || `1-${user.institution_id || "10023456"}`}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block mb-0.5 font-medium">State / Region</span>
                    <span className="font-semibold text-slate-800">
                      {institution?.state || "Maharashtra"}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block mb-0.5 font-medium">Sponsoring Trust / Society</span>
                  <span className="font-medium text-slate-800">
                    {institution?.trust_name || "Apex Education & Research Foundation Trust"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 block mb-0.5 font-medium">Campus Address</span>
                  <span className="text-slate-600 leading-relaxed block">
                    {institution?.address || "Survey No. 42/1, Tech City Corridor, Pune, Maharashtra 411057"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
