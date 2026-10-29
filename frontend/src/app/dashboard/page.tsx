"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";
import { ApplicantDashboard } from "@/features/dashboard/ApplicantDashboard";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";
import {
  LayoutDashboard,
  Files,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  ShieldAlert,
  ArrowUpRight,
  RefreshCw,
  Cpu,
  BarChart3,
  AlertCircle,
  Building2,
  Calendar,
  Layers,
  FileCheck2,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  "Under Verification": "#3b82f6",
  under_verification: "#3b82f6",
  "Needs Review": "#f59e0b",
  needs_review: "#f59e0b",
  "Approved": "#10b981",
  approved: "#10b981",
  "Rejected": "#ef4444",
  rejected: "#ef4444",
  "Information Requested": "#8b5cf6",
  info_requested: "#8b5cf6",
  "Submitted": "#06b6d4",
  submitted: "#06b6d4",
  "Draft": "#94a3b8",
  draft: "#94a3b8",
};

function formatStatus(status: string): string {
  const map: Record<string, string> = {
    under_verification: "Under Verification",
    needs_review: "Needs Review",
    approved: "Approved",
    rejected: "Rejected",
    info_requested: "Information Requested",
    submitted: "Submitted",
    draft: "Draft",
  };
  return map[status] || status;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isOfficial, isInstitution, isLoading: authLoading } = useAuth();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alertFilter, setAlertFilter] = useState<string>("all");

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<DashboardSummary>("/dashboard/summary");
      setSummary(data);
    } catch (err: any) {
      console.error("Failed to load dashboard summary", err);
      setError(err.message || "Failed to load live scrutiny metrics from backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && !isInstitution) {
      fetchSummary();
    }
  }, [user, isInstitution]);

  if (authLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Verifying council session and credentials...
      </div>
    );
  }

  // If logged-in user is an applicant/institution, serve the Applicant Dashboard
  if (isInstitution) {
    return <ApplicantDashboard />;
  }

  // Status Distribution Calculation
  const totalStatusCount = summary?.status_distribution
    ? summary.status_distribution.reduce((acc, curr) => acc + curr.count, 0)
    : 0;

  const chartData = summary?.status_distribution
    ? summary.status_distribution
        .filter((s) => s.count > 0)
        .map((s) => {
          const formatted = formatStatus(s.status);
          const pct = s.percentage !== undefined
            ? s.percentage
            : totalStatusCount > 0
            ? (s.count / totalStatusCount) * 100
            : 0;
          return {
            name: formatted,
            statusKey: s.status,
            value: s.count,
            percentage: pct,
            color: STATUS_COLORS[s.status] || STATUS_COLORS[formatted] || "#64748b",
          };
        })
    : [];

  // Filter alerts by finding group
  const filteredAlerts = (summary?.recent_alerts || []).filter((alert) => {
    if (alertFilter === "all") return true;
    if (alertFilter === "deficiencies") return alert.finding_group === "deficiency" || alert.category === "missing";
    if (alertFilter === "mismatches") return alert.finding_group === "mismatch" || alert.category === "mismatch";
    if (alertFilter === "duplicates") return alert.finding_group === "duplicate" || alert.category === "duplicate";
    if (alertFilter === "forensics") return alert.finding_group === "forensic" || alert.category === "tampering";
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-white border border-slate-200 p-0.5 flex items-center justify-center shrink-0 shadow-2xs">
              <img
                src="/assets/aicte_logo.png"
                alt="AICTE Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <span>SARATHI Official Scrutiny Dashboard</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            AICTE Regulatory Governance — Real-time scrutiny status, explainable risk metrics, and institutional application queues.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[#0A4D2E]" : "text-slate-500"}`} />
            <span>Refresh Data</span>
          </button>
        </div>
      </div>

      {/* Error Alert Banner */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchSummary}
            className="px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded font-semibold text-xs transition-colors shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* KPI Cards Grid (Clickable to open filtered queue) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Card 1: Total Applications */}
        <div
          onClick={() => router.push("/applications")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-[#0A4D2E] hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-400 group-hover:text-[#0A4D2E]">
            <span className="text-[11px] font-bold uppercase tracking-wider">Total</span>
            <Files className="w-4 h-4 text-slate-500 group-hover:text-[#0A4D2E]" />
          </div>
          <p className="text-2xl font-black text-slate-900 mt-2 font-mono">
            {summary?.total_applications ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">All Applications</span>
        </div>

        {/* Card 2: Needs Review */}
        <div
          onClick={() => router.push("/applications?status=needs_review")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-amber-400 hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-amber-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-amber-700">Needs Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-black text-amber-700 mt-2 font-mono">
            {summary?.needs_review ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Manual Scrutiny</span>
        </div>

        {/* Card 3: Under Verification */}
        <div
          onClick={() => router.push("/applications?status=under_verification")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-blue-400 hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-blue-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-blue-700">Under Verification</span>
            <Clock className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-black text-blue-700 mt-2 font-mono">
            {summary?.under_verification ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">In Processing</span>
        </div>

        {/* Card 4: Approved */}
        <div
          onClick={() => router.push("/applications?status=approved")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-emerald-400 hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-emerald-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-emerald-700">Approved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-black text-emerald-700 mt-2 font-mono">
            {summary?.approved ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Authorized Decided</span>
        </div>

        {/* Card 5: Rejected */}
        <div
          onClick={() => router.push("/applications?status=rejected")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-rose-400 hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-rose-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-rose-700">Rejected</span>
            <XCircle className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-2xl font-black text-rose-700 mt-2 font-mono">
            {summary?.rejected ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Non-Compliant</span>
        </div>

        {/* Card 6: Information Requested */}
        <div
          onClick={() => router.push("/applications?status=info_requested")}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-purple-400 hover:shadow-md cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-purple-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-purple-700">Info Requested</span>
            <FileText className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-black text-purple-700 mt-2 font-mono">
            {summary?.info_requested ?? 0}
          </p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Cure Window</span>
        </div>
      </div>

      {/* Main Charts & Pipeline Stats Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Donut: Status Distribution */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Application Scrutiny Distribution</h3>
              <p className="text-xs text-slate-500">
                Reconciled statuses across all institutional applications ({totalStatusCount} total recorded)
              </p>
            </div>
            <BarChart3 className="w-4 h-4 text-slate-400" />
          </div>

          <div className="h-64 flex flex-col md:flex-row items-center justify-around">
            <div className="w-full h-56 md:w-1/2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData.length > 0 ? chartData : [{ name: "No data", value: 1, color: "#cbd5e1", percentage: 0 }]}
                    innerRadius={60}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    onClick={(entry) => {
                      if (entry?.statusKey) {
                        router.push(`/applications?status=${entry.statusKey}`);
                      }
                    }}
                    cursor="pointer"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Clickable Legend list with Counts and Percentages */}
            <div className="w-full md:w-1/2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {summary?.status_distribution.map((item) => {
                const formatted = formatStatus(item.status);
                const color = STATUS_COLORS[item.status] || STATUS_COLORS[formatted] || "#94a3b8";
                const pct = item.percentage !== undefined
                  ? item.percentage
                  : totalStatusCount > 0
                  ? (item.count / totalStatusCount) * 100
                  : 0;

                return (
                  <div
                    key={item.status}
                    onClick={() => router.push(`/applications?status=${item.status}`)}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100 hover:border-slate-300 hover:bg-slate-100/70 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span className="truncate text-slate-700 font-medium">{formatted}</span>
                    </div>
                    <div className="text-right pl-2 flex-shrink-0">
                      <span className="font-bold text-slate-900 font-mono">{item.count}</span>
                      <span className="text-[10px] text-slate-400 ml-1">({pct.toFixed(1)}%)</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Processing Performance Metrics (Live measurements, OCR vs Native PDF segregated) */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-slate-900">Pipeline Performance</h3>
              <Cpu className="w-4 h-4 text-[#0A4D2E]" />
            </div>
            <p className="text-[11px] text-slate-500 mb-4">
              Real processing measurements. Native PDF text extraction separated from OCR.
            </p>

            <div className="space-y-3 text-xs">
              {/* Avg Ingestion Latency */}
              <div className="p-3 rounded-lg bg-[#F0FDF4] border border-[#86EFAC]/70">
                <span className="text-[11px] text-[#0A4D2E] font-semibold block">Avg Processing Latency</span>
                <p className="text-xl font-bold text-[#073F2A] mt-0.5 font-mono">
                  {summary?.processing_stats?.avg_processing_time_sec !== undefined
                    ? `${summary.processing_stats.avg_processing_time_sec.toFixed(2)}s`
                    : "0.00s"}
                  <span className="text-xs font-normal text-[#0A4D2E] ml-1">/ document</span>
                </p>
              </div>

              {/* Native PDF vs OCR counts */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-slate-500 font-medium block">Native PDF Extractions</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {summary?.processing_stats?.native_pdf_count ?? 0}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 font-medium block">OCR Tesseract Jobs</span>
                  <p className="text-base font-bold text-slate-900 font-mono">
                    {summary?.processing_stats?.ocr_count ?? 0}
                  </p>
                </div>
              </div>

              {/* Pending vs Failed Jobs */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-slate-500 font-medium block">Pending Jobs</span>
                  <p className="text-base font-bold text-slate-700 font-mono">
                    {summary?.processing_stats?.pending_jobs ?? 0}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 font-medium block">Failed Jobs</span>
                  <p className={`text-base font-bold font-mono ${(summary?.processing_stats?.failed_jobs ?? 0) > 0 ? "text-rose-600" : "text-slate-400"}`}>
                    {summary?.processing_stats?.failed_jobs ?? 0}
                  </p>
                </div>
              </div>

              {/* Total Documents Parsed */}
              <div className="flex items-center justify-between text-slate-600 px-1 text-[11px]">
                <span>Total Documents Processed:</span>
                <span className="font-bold text-slate-900 font-mono">
                  {summary?.processing_stats?.total_processed_documents ?? 0}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[10px] text-slate-400 flex items-center justify-between">
            <span>Period: {summary?.processing_stats?.reporting_period || "Active Session"}</span>
            <span>Refreshed: {summary?.processing_stats?.last_refresh_time ? new Date(summary.processing_stats.last_refresh_time).toLocaleTimeString() : "Live"}</span>
          </div>
        </div>
      </div>

      {/* Two Columns: Recent Alerts (Segregated) & High-Scrutiny Priority Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Discrepancy & Fraud Alerts */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-slate-900">Recent Discrepancy &amp; Fraud Alerts</h3>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              {filteredAlerts.length} unresolved alerts
            </span>
          </div>

          {/* Finding Categories Filter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            {[
              { id: "all", label: "All Alerts" },
              { id: "deficiencies", label: "Deficiencies" },
              { id: "mismatches", label: "Mismatches" },
              { id: "duplicates", label: "Duplicates" },
              { id: "forensics", label: "Forensics" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setAlertFilter(tab.id)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-colors ${
                  alertFilter === tab.id
                    ? "bg-[#0A4D2E] text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {filteredAlerts.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">
              No open alerts recorded under this category.
            </p>
          ) : (
            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => router.push(`/applications/${alert.application_id}`)}
                  className="flex items-start justify-between gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100 hover:border-slate-300 hover:bg-slate-100/60 cursor-pointer transition-colors"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                          alert.severity === "critical"
                            ? "bg-rose-100 text-rose-800"
                            : alert.severity === "warning"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-blue-100 text-blue-800"
                        }`}
                      >
                        {alert.severity}
                      </span>
                      <span className="font-semibold text-xs text-slate-900 truncate">{alert.title}</span>
                    </div>

                    <p className="text-[11px] text-slate-600 truncate">
                      {alert.institution_name} &bull; <span className="font-mono">{alert.application_no}</span>
                    </p>

                    <div className="flex items-center gap-3 text-[10px] text-slate-400">
                      <span>Doc: <strong className="text-slate-600">{alert.affected_document || "Statutory Upload"}</strong></span>
                      <span>Detected: {new Date(alert.created_at).toLocaleDateString()}</span>
                      <span className="capitalize font-medium text-amber-700">Status: {alert.review_status || "open"}</span>
                    </div>
                  </div>

                  <Link
                    href={`/applications/${alert.application_id}`}
                    className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-white rounded-lg transition-colors shrink-0"
                    title="Inspect Finding"
                  >
                    <ArrowUpRight className="w-4 h-4" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* High Scrutiny Priority Queue */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-bold text-slate-900">High Scrutiny Priority Queue</h3>
            </div>
            <Link
              href="/applications"
              className="text-xs font-semibold text-[#0A4D2E] hover:underline flex items-center gap-1"
            >
              <span>View Full Queue</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <p className="text-[11px] text-slate-500">
            Submitted applications prioritized by unique risk score. Drafts and resolved/decided applications are excluded.
          </p>

          {!summary?.high_risk_applications || summary.high_risk_applications.length === 0 ? (
            <p className="text-xs text-slate-400 py-8 text-center">
              No pending high-priority scrutiny applications.
            </p>
          ) : (
            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {summary.high_risk_applications.map((app) => (
                <div
                  key={app.id}
                  className="flex items-start justify-between gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100 hover:border-slate-300 transition-colors"
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold text-slate-800">{app.application_no}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          app.risk_band === "High"
                            ? "bg-rose-100 text-rose-800"
                            : app.risk_band === "Medium"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {app.risk_band} Priority
                      </span>
                      {app.submission_date && (
                        <span className="text-[10px] text-slate-400">
                          Submitted: {new Date(app.submission_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-slate-700 font-medium truncate">
                      {app.institution_name} ({app.state})
                    </p>

                    {app.reasons && app.reasons.length > 0 && (
                      <p className="text-[11px] text-slate-500 line-clamp-1 italic">
                        Factors: {app.reasons.join("; ")}
                      </p>
                    )}

                    <div className="text-[10px] text-slate-400">
                      Unresolved Flags: <strong className="text-rose-600 font-bold">{app.unresolved_flags_count ?? app.critical_flags_count}</strong>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <span className="font-mono text-base font-extrabold text-slate-900">
                        {app.risk_score}
                      </span>
                      <span className="text-[10px] text-slate-400 block font-normal">score / 100</span>
                    </div>
                    <Link
                      href={`/applications/${app.id}`}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-[#0A4D2E] hover:bg-[#083D24] transition-colors"
                    >
                      Inspect
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
