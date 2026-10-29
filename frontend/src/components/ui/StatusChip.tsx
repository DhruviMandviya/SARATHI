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
    // Complete / Valid / Compliant / Approved / Verified
    case "complete":
    case "valid":
    case "compliant":
    case "approved":
    case "verified":
      bg = "bg-emerald-50 text-emerald-700 border-emerald-200";
      Icon = CheckCircle2;
      label = norm === "complete" ? "Complete" : norm === "valid" ? "Complete" : norm === "compliant" ? "Compliant" : norm === "approved" ? "Approved" : "Verified";
      break;

    // Warning / Needs Review / Incomplete / Needs Update / Expired / In Progress / Requires Correction
    case "needs_review":
    case "incomplete":
    case "warning":
    case "requires_correction":
    case "more_information_required":
      bg = "bg-amber-50 text-amber-700 border-amber-200";
      Icon = AlertTriangle;
      label = (norm === "requires_correction" || norm === "more_information_required")
        ? "Requires Correction"
        : norm === "needs_review"
        ? "Needs Review"
        : norm === "incomplete"
        ? "Incomplete"
        : "Warning";
      break;

    case "unable_to_verify":
      bg = "bg-slate-100 text-slate-700 border-slate-300";
      Icon = AlertTriangle;
      label = "Unable to Verify";
      break;

    case "pending_processing":
      bg = "bg-slate-100 text-slate-700 border-slate-200";
      Icon = Clock;
      label = "Pending Processing";
      break;

    case "pending_review":
      bg = "bg-slate-100 text-slate-600 border-slate-200";
      Icon = Clock;
      label = "Pending Review";
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
      // Restrained tone for pending / in_progress
      bg = "bg-slate-100 text-slate-700 border-slate-200";
      Icon = Clock;
      label = norm === "pending" ? "Pending Verification" : "In Progress";
      break;

    // Critical / Non-Compliant / Rejected / Mismatch / Missing / Not Verified / Invalid
    case "critical":
    case "non_compliant":
    case "rejected":
    case "mismatch_confirmed":
    case "missing":
    case "not_verified":
    case "invalid":
      bg = "bg-red-50 text-red-700 border-red-200";
      Icon = XCircle;
      label = norm === "invalid" ? "Invalid" : norm === "non_compliant" ? "Non-Compliant" : norm === "critical" ? "Critical" : (norm === "rejected" || norm === "mismatch_confirmed") ? "Rejected" : norm === "missing" ? "Missing" : "Not Verified";
      break;

    case "mismatch":
      bg = "bg-rose-50 text-rose-700 border-rose-200";
      Icon = ShieldAlert;
      label = "Mismatch";
      break;

    case "info":
      bg = "bg-slate-100 text-slate-700 border-slate-200";
      Icon = HelpCircle;
      label = "Info";
      break;

    case "under_verification":
      bg = "bg-[#F0FDF4] text-[#0A4D2E] border-[#86EFAC]";
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
