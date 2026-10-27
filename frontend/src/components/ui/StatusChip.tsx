import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock, ShieldAlert, HelpCircle } from "lucide-react";

interface StatusChipProps {
  status: string;
  type?: "document" | "application" | "verification" | "compliance" | "severity";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function StatusChip({ status, type = "document", size = "md", className = "" }: StatusChipProps) {
  const norm = (status || "").toLowerCase().trim();

  let bg = "bg-slate-100 text-slate-700 border-slate-200";
  let label = status;
  let Icon = HelpCircle;

  switch (norm) {
    // Valid / Compliant / Approved / Verified
    case "valid":
    case "compliant":
    case "approved":
    case "verified":
      bg = "bg-emerald-50 text-emerald-700 border-emerald-200";
      Icon = CheckCircle2;
      label = norm === "valid" ? "Valid" : norm === "compliant" ? "Compliant" : norm === "approved" ? "Approved" : "Verified";
      break;

    // Warning / Needs Review / Incomplete / Needs Update / Expired / In Progress
    case "needs_review":
    case "incomplete":
    case "warning":
      bg = "bg-amber-50 text-amber-700 border-amber-200";
      Icon = AlertTriangle;
      label = norm === "needs_review" ? "Needs Review" : norm === "incomplete" ? "Incomplete" : "Warning";
      break;

    case "needs_update":
      bg = "bg-amber-50 text-amber-800 border-amber-300";
      Icon = AlertTriangle;
      label = "Needs Update";
      break;

    case "expired":
      bg = "bg-orange-50 text-orange-700 border-orange-200";
      Icon = Clock;
      label = "Expired";
      break;

    case "pending":
    case "in_progress":
      // Neutral tone for pending / in_progress - never alarming
      bg = "bg-blue-50 text-blue-700 border-blue-200";
      Icon = Clock;
      label = norm === "pending" ? "Pending Verification" : "In Progress";
      break;

    // Critical / Non-Compliant / Rejected / Mismatch / Missing / Not Verified
    case "critical":
    case "non_compliant":
    case "rejected":
    case "missing":
    case "not_verified":
      bg = "bg-red-50 text-red-700 border-red-200";
      Icon = XCircle;
      label = norm === "non_compliant" ? "Non-Compliant" : norm === "critical" ? "Critical" : norm === "rejected" ? "Rejected" : norm === "missing" ? "Missing" : "Not Verified";
      break;

    case "mismatch":
      bg = "bg-rose-50 text-rose-700 border-rose-200";
      Icon = ShieldAlert;
      label = "Mismatch";
      break;

    case "info":
      bg = "bg-sky-50 text-sky-700 border-sky-200";
      Icon = HelpCircle;
      label = "Info";
      break;

    case "under_verification":
      bg = "bg-indigo-50 text-indigo-700 border-indigo-200";
      Icon = Clock;
      label = "Under Verification";
      break;

    case "info_requested":
      bg = "bg-purple-50 text-purple-700 border-purple-200";
      Icon = AlertTriangle;
      label = "Info Requested";
      break;

    case "submitted":
      bg = "bg-teal-50 text-teal-700 border-teal-200";
      Icon = CheckCircle2;
      label = "Submitted";
      break;

    case "draft":
      bg = "bg-slate-100 text-slate-600 border-slate-200";
      Icon = Clock;
      label = "Draft";
      break;

    default:
      label = status;
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-medium gap-1",
    md: "px-2.5 py-1 text-xs font-semibold gap-1.5",
    lg: "px-3 py-1.5 text-sm font-semibold gap-2",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${bg} ${sizeClasses} ${className}`}
    >
      <Icon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      <span>{label}</span>
    </span>
  );
}

export function SimulatedBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-100 text-amber-800 border border-amber-300 ${className}`}
      title="This integration check is simulated in this environment"
    >
      SIMULATED
    </span>
  );
}

export function UnverifiedBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 ${className}`}
      title="Threshold is a placeholder not yet verified against the official AICTE Handbook"
    >
      Unverified placeholder threshold
    </span>
  );
}
