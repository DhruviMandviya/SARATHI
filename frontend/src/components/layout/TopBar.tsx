"use client";

import React from "react";
import { useAuth } from "@/lib/auth";
import { Bell, ShieldCheck, Building, HelpCircle } from "lucide-react";

export function TopBar() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-sm shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-bold text-slate-800 tracking-tight flex items-center gap-2">
          <span>AICTE National Approval Portal</span>
          <span className="text-xs font-normal text-slate-500">| Verification & Scrutiny System</span>
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Caveat reminder */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium border border-slate-200">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
          <span>Decision Support Mode &bull; AI Recommends, Official Decides</span>
        </div>

        {/* Institution Badge if applicable */}
        {user.institution_id && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 text-xs font-medium border border-blue-100">
            <Building className="w-3.5 h-3.5" />
            <span>Institution ID: #{user.institution_id}</span>
          </div>
        )}

        {/* Alerts Bell */}
        <button
          className="relative p-2 rounded-full text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          title="Review Alerts"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 ring-2 ring-white"></span>
        </button>

        {/* User avatar pill */}
        <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-navy-800 text-white font-bold flex items-center justify-center text-xs shadow-inner">
            {user.full_name.charAt(0)}
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-bold text-slate-800 leading-tight">{user.full_name}</p>
            <p className="text-[11px] text-slate-500 capitalize">{user.role}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
