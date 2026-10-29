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
  Compass,
  LogOut,
  ChevronRight,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();
  const { user, isOfficial, isInstitution, logout } = useAuth();

  if (!user || pathname === "/login") {
    return null;
  }

  const applicantNavItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      label: "New Application",
      href: "/applications/new",
      icon: FilePlus,
    },
    {
      label: "My Applications",
      href: "/applications",
      icon: Files,
    },
    {
      label: "Information Requests",
      href: "/information-requests",
      icon: ShieldAlert,
    },
    {
      label: "Reports & Decisions",
      href: "/reports",
      icon: FileText,
    },
    {
      label: "Profile / Account",
      href: "/profile",
      icon: Settings,
    },
  ];

  const officialNavItems = [
    {
      label: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
      roles: ["official", "admin", "auditor"],
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

  const visibleNav =
    user.role === "institution"
      ? applicantNavItems
      : officialNavItems.filter((item) => item.roles.includes(user.role));

  return (
    <aside className="w-64 bg-[#E8F3EC] text-[#174D35] flex flex-col shrink-0 min-h-screen border-r border-[#C8DDD0] shadow-sm select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-[#C8DDD0] bg-[#D6E9DC] flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-white border border-[#C8DDD0] flex items-center justify-center p-1 shadow-xs shrink-0">
          <img
            src="/assets/aicte_logo.png"
            alt="AICTE Logo"
            className="w-full h-full object-contain"
          />
        </div>
        <div>
          <div className="font-black text-[#174D35] text-base tracking-wide flex items-center gap-1.5">
            SARATHI{" "}
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#C4E3D0] text-[#174D35] font-bold border border-[#A8CEB8]">
              AICTE
            </span>
          </div>
          <div className="text-[10px] text-[#39785A] font-semibold tracking-tight">Regulatory Governance</div>
        </div>
      </div>

      {/* Role Pill Strip */}
      <div className="px-5 py-2.5 bg-[#DDECE2] border-b border-[#C8DDD0] flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider text-[#39785A] font-bold">Workspace</span>
        <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold capitalize bg-[#C4E3D0] text-[#174D35] border border-[#A8CEB8]">
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
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? "bg-[#C4E3D0] text-[#174D35] font-bold border-l-4 border-[#FF9933] shadow-xs"
                  : "text-[#174D35] font-medium hover:bg-[#D5E9DC] hover:text-[#0E3524]"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-[#174D35]" : "text-[#39785A]"}`} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight className="w-4 h-4 text-[#174D35]/80" />}
            </Link>
          );
        })}
      </nav>

      {/* User Footer */}
      <div className="p-4 border-t border-[#C8DDD0] bg-[#DCEBE1]">
        <div className="flex items-center justify-between">
          <div className="overflow-hidden pr-2">
            <p className="text-xs font-bold text-[#174D35] truncate">{user.full_name}</p>
            <p className="text-[11px] text-[#39785A] font-medium truncate">{user.email}</p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="p-2 text-[#39785A] hover:text-rose-700 hover:bg-[#C8DDD0]/60 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
