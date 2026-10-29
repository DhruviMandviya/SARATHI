"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { DashboardSummary, ApplicationItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import {
  Building2,
  FilePlus,
  Files,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
  Check,
  ChevronRight,
  Upload,
} from "lucide-react";

export function ApplicantDashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadApplicantData() {
      try {
        setLoading(true);
        setError(null);
        const [sumData, appsData] = await Promise.all([
          apiRequest<DashboardSummary>("/dashboard/summary"),
          apiRequest<ApplicationItem[]>("/applications"),
        ]);
        setSummary(sumData);
        setApplications(appsData);
      } catch (err: any) {
        console.error("Failed to load applicant dashboard data", err);
        setError(err.message || "Failed to load institutional dashboard data.");
      } finally {
        setLoading(false);
      }
    }
    loadApplicantData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-72 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading institutional dashboard data...
      </div>
    );
  }

  const totalApps = summary?.total_applications ?? applications.length;
  const draftApps = summary?.draft ?? applications.filter((a) => a.status === "draft").length;
  const underReviewApps =
    (summary?.under_verification ?? 0) +
    (summary?.needs_review ?? 0) +
    (summary?.submitted ?? 0);
  const infoRequestedApps =
    summary?.info_requested ?? applications.filter((a) => a.status === "info_requested").length;
  const decidedApps =
    (summary?.approved ?? 0) + (summary?.rejected ?? 0);

  const pendingNotices = applications.filter((a) => a.status === "info_requested");

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="bg-[#073F2A] border border-[#0A4D2E]/40 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-white/10 text-emerald-100 border border-white/20">
              Institution Portal
            </span>
            <span className="text-xs text-emerald-200/75 font-mono">
              Academic Year 2026–2027
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white p-1 flex items-center justify-center shrink-0 shadow-xs">
              <img
                src="/assets/aicte_logo.png"
                alt="AICTE Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <span>{user?.full_name || "Applicant Technical Institution"}</span>
          </h1>
          <p className="text-xs text-emerald-100/80">
            Welcome to SARATHI — AICTE Document Verification and Regulatory Governance Portal. Track your submissions and statutory compliance below.
          </p>
        </div>

        <Link
          href="/applications/new"
          className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-[#0A4D2E] hover:bg-[#083D24] text-white text-xs font-bold shadow-md transition-all shrink-0 border border-emerald-600/40"
        >
          <FilePlus className="w-4 h-4" />
          <span>Start New Application</span>
        </Link>
      </div>

      {/* 2. Urgent Deficiency Alert (if information is requested) */}
      {infoRequestedApps > 0 && (
        <div className="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl shadow-sm text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-amber-950 text-xs">
                ACTION REQUIRED: Information Requested by Scrutiny Committee
              </h4>
              <p className="text-[11px] text-amber-800 mt-0.5">
                You have {infoRequestedApps} application(s) requiring document clarification or re-upload. Please respond promptly to avoid formal processing delays.
              </p>
            </div>
          </div>
          <Link
            href="/information-requests?status=action_required"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs transition-colors shrink-0 shadow-xs"
          >
            <span>Review Notices</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* 3. Real Institution Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total Applications */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Total Applications</span>
            <Files className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{totalApps}</div>
          <p className="text-[10px] text-slate-400 mt-1">Council docket records</p>
        </div>

        {/* Drafts */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Draft Applications</span>
            <Clock className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-700">{draftApps}</div>
          <p className="text-[10px] text-slate-400 mt-1">Pending submission</p>
        </div>

        {/* Under Review */}
        <div className="bg-[#F0FDF4] p-4 rounded-xl border border-[#0A4D2E]/25 shadow-xs">
          <div className="flex items-center justify-between text-[#0A4D2E] mb-2">
            <span className="text-xs font-semibold">Under Scrutiny</span>
            <Clock className="w-4 h-4 text-[#0A4D2E]" />
          </div>
          <div className="text-2xl font-bold text-[#073F2A]">{underReviewApps}</div>
          <p className="text-[10px] text-[#0A4D2E]/80 mt-1">Official review active</p>
        </div>

        {/* Info Requested */}
        <Link
          href="/information-requests?status=action_required"
          className={`p-4 rounded-xl border shadow-xs block transition-all hover:scale-[1.02] ${
            infoRequestedApps > 0
              ? "bg-amber-50 border-amber-300 text-amber-900 cursor-pointer"
              : "bg-white border-slate-200"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold">Action Required</span>
            <ShieldAlert className={`w-4 h-4 ${infoRequestedApps > 0 ? "text-amber-600" : "text-slate-400"}`} />
          </div>
          <div className={`text-2xl font-bold ${infoRequestedApps > 0 ? "text-amber-800" : "text-slate-700"}`}>
            {infoRequestedApps}
          </div>
          <p className={`text-[10px] mt-1 ${infoRequestedApps > 0 ? "text-amber-700 font-semibold" : "text-slate-400"}`}>
            {infoRequestedApps > 0 ? "Deficiency notice issued &bull; Click to respond" : "No pending cure items"}
          </p>
        </Link>

        {/* Decisions Issued */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold">Decisions Issued</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{decidedApps}</div>
          <p className="text-[10px] text-slate-400 mt-1">
            {summary?.approved ?? 0} Approved • {summary?.rejected ?? 0} Rejected
          </p>
        </div>
      </div>

      {/* 4. My Applications Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">My Institutional Applications</h3>
            <p className="text-xs text-slate-400">Applications submitted or in progress under this accredited institution</p>
          </div>
          <Link
            href="/applications"
            className="text-xs text-[#0A4D2E] hover:text-[#083D24] font-semibold flex items-center gap-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {applications.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Files className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-xs text-slate-500">No applications recorded yet for this institution.</p>
            <Link
              href="/applications/new"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded-lg text-xs font-semibold"
            >
              <FilePlus className="w-3.5 h-3.5" />
              <span>Create First Application</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
                  <th className="p-3.5">Application No</th>
                  <th className="p-3.5">Program / Type</th>
                  <th className="p-3.5">Academic Year</th>
                  <th className="p-3.5">Created Date</th>
                  <th className="p-3.5">Current Status</th>
                  <th className="p-3.5 text-right">Permitted Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.slice(0, 6).map((app) => {
                  const isDraft = app.status === "draft";
                  const isActionReq = app.status === "info_requested";

                  return (
                    <tr key={app.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3.5 font-bold font-mono text-slate-900">
                        <Link
                          href={`/applications/${app.id}`}
                          className="hover:text-[#0A4D2E] hover:underline"
                        >
                          {app.application_no}
                        </Link>
                      </td>
                      <td className="p-3.5 text-slate-700 font-medium">
                        {app.type}
                      </td>
                      <td className="p-3.5 text-slate-500 font-mono">
                        {app.academic_year}
                      </td>
                      <td className="p-3.5 text-slate-500">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="p-3.5">
                        <StatusChip status={app.status} size="sm" />
                      </td>
                      <td className="p-3.5 text-right">
                        <Link
                          href={`/applications/${app.id}`}
                          className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                            isActionReq
                              ? "bg-amber-600 hover:bg-amber-700 text-white shadow-xs"
                              : isDraft
                              ? "bg-[#0A4D2E] hover:bg-[#083D24] text-white shadow-xs"
                              : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                          }`}
                        >
                          <span>{isActionReq ? "Respond to Notice" : isDraft ? "Continue Draft" : "View Dossier"}</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Statutory Document Guidelines */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 space-y-3">
        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <span>Statutory Document Submission Checklist (Approval Process Handbook)</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-2xs space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Registered Land Deed</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Sale deed, registered lease, or ownership document with clear survey number and plot area in acres.
            </p>
          </div>

          <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-2xs space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Sanctioned Building Plan</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Approved municipal plan with sanction reference number, built-up area (sqm), and Floor Space Index.
            </p>
          </div>

          <div className="p-3 bg-white rounded-lg border border-slate-200 shadow-2xs space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Fire Safety NOC</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Active clearance from the State Fire & Rescue Services showing valid NOC number and validity date.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
