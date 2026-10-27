"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  LayoutDashboard,
  FilePlus,
  Files,
  FileCheck2,
  ShieldAlert,
  Scale,
  FileText,
  History,
  Settings,
  Building2,
  LogOut,
  ChevronRight,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { user, isOfficial, isInstitution, logout } = useAuth();

  if (!user || pathname === "/login") {
    return null;
  }

  const navItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
      roles: ["official", "admin", "auditor"],
    },
    {
      label: "New Application",
      href: "/applications/new",
      icon: FilePlus,
      roles: ["institution"],
    },
    {
      label: "My Applications",
      href: "/applications",
      icon: Files,
      roles: ["institution"],
    },
    {
      label: "Applications Queue",
      href: "/applications",
      icon: Files,
      roles: ["official", "admin", "auditor"],
    },
    {
      label: "Document Verification",
      href: "/verification",
      icon: FileCheck2,
      roles: ["official", "admin"],
    },
    {
      label: "Fraud & Forensics",
      href: "/fraud",
      icon: ShieldAlert,
      roles: ["official", "admin"],
    },
    {
      label: "Compliance Engine",
      href: "/compliance",
      icon: Scale,
      roles: ["official", "admin"],
    },
    {
      label: "Reports & Letters",
      href: "/reports",
      icon: FileText,
      roles: ["official", "admin", "auditor"],
    },
    {
      label: "Audit Trail",
      href: "/audit",
      icon: History,
      roles: ["official", "admin", "auditor"],
    },
    {
      label: "Rule Management",
      href: "/admin/rules",
      icon: Settings,
      roles: ["admin"],
    },
  ];

  const visibleNav = navItems.filter((item) => item.roles.includes(user.role));

  return (
    <aside className="w-64 bg-navy-900 text-slate-200 flex flex-col shrink-0 min-h-screen border-r border-navy-800 shadow-xl">
      {/* Brand Header */}
      <div className="p-5 border-b border-navy-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-700 flex items-center justify-center shadow-md">
          <Building2 className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="font-bold text-white text-base tracking-wide flex items-center gap-1.5">
            AICTE <span className="text-xs px-1.5 py-0.5 rounded bg-blue-600/30 text-blue-400 font-semibold border border-blue-500/30">MVP</span>
          </div>
          <div className="text-[11px] text-slate-400 font-medium">Document Decision Support</div>
        </div>
      </div>

      {/* Role Pill */}
      <div className="px-5 py-3 bg-navy-850 border-b border-navy-800/60 flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Workspace</span>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium capitalize bg-blue-900/60 text-blue-300 border border-blue-700/50">
          {user.role}
        </span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {visibleNav.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-navy-800 hover:text-white"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight className="w-4 h-4 text-white/70" />}
            </Link>
          );
        })}
      </nav>

      {/* User Footer */}
      <div className="p-4 border-t border-navy-800 bg-navy-850">
        <div className="flex items-center justify-between">
          <div className="overflow-hidden pr-2">
            <p className="text-xs font-semibold text-white truncate">{user.full_name}</p>
            <p className="text-[11px] text-slate-400 truncate">{user.email}</p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-2 text-slate-400 hover:text-red-400 hover:bg-navy-800 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
