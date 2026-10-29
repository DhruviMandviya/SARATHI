"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { InformationRequestItem } from "@/lib/types";
import {
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Search,
  Filter,
  FileText,
  ArrowRight,
  Calendar,
  Building,
  RefreshCw,
} from "lucide-react";

export default function InformationRequestsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  const [requests, setRequests] = useState<InformationRequestItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<InformationRequestItem[]>("/information-requests");
      setRequests(data);
    } catch (err: any) {
      console.error("Failed to load information requests", err);
      setError(err.message || "Failed to retrieve formal deficiency notices from council server.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchRequests();
    }
  }, [user]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchRequests();
  };

  // Calculate summary counts from actual database records
  const countActionRequired = requests.filter(
    (r) => r.status === "action_required" || r.status === "further_info_required"
  ).length;
  const countSubmitted = requests.filter((r) => r.status === "submitted").length;
  const countUnderReview = requests.filter((r) => r.status === "under_review").length;
  const countResolved = requests.filter((r) => r.status === "resolved").length;

  const filteredRequests = requests.filter((req) => {
    const s = search.toLowerCase();
    const matchesSearch =
      !search ||
      req.reference_no.toLowerCase().includes(s) ||
      req.title.toLowerCase().includes(s) ||
      String(req.application_id).includes(s) ||
      (req.application_no && req.application_no.toLowerCase().includes(s)) ||
      (req.institution_name && req.institution_name.toLowerCase().includes(s));

    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "action_required" && (req.status === "action_required" || req.status === "further_info_required")) ||
      req.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "action_required":
      case "further_info_required":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Action Required</span>
          </span>
        );
      case "submitted":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-blue-600" />
            <span>Response Submitted</span>
          </span>
        );
      case "under_review":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-300 flex items-center gap-1">
            <Clock className="w-3 h-3 text-purple-600" />
            <span>Under Review</span>
          </span>
        );
      case "resolved":
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>Resolved</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status.replace(/_/g, " ")}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">
              Statutory Communications
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Formal AICTE Scrutiny Notices
            </span>
          </div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-6 h-6 text-[#0A4D2E]" />
            <span>Information Requests &amp; Deficiency Notices</span>
          </h1>
          <p className="text-xs text-slate-500 max-w-2xl">
            Official cure notices issued by the AICTE Scrutiny Committee requiring document clarification, parameter verification, or certified supplementary uploads.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={loading || refreshing}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-xs shrink-0 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${refreshing ? "animate-spin" : ""}`} />
          <span>{refreshing ? "Refreshing Notices..." : "Refresh Notices"}</span>
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          onClick={() => setStatusFilter("action_required")}
          className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all ${
            statusFilter === "action_required" ? "border-amber-500 ring-2 ring-amber-100" : "border-slate-200 hover:border-amber-300"
          }`}
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">Action Required</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-black text-amber-700 mt-2 font-mono">{countActionRequired}</p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Awaiting institutional response</span>
        </div>

        <div
          onClick={() => setStatusFilter("submitted")}
          className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all ${
            statusFilter === "submitted" ? "border-[#0A4D2E] ring-2 ring-[#F0FDF4]" : "border-slate-200 hover:border-emerald-300"
          }`}
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#0A4D2E]">Response Submitted</span>
            <CheckCircle2 className="w-4 h-4 text-[#0A4D2E]" />
          </div>
          <p className="text-2xl font-black text-[#0A4D2E] mt-2 font-mono">{countSubmitted}</p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Queued for council scrutiny</span>
        </div>

        <div
          onClick={() => setStatusFilter("under_review")}
          className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all ${
            statusFilter === "under_review" ? "border-purple-500 ring-2 ring-purple-100" : "border-slate-200 hover:border-purple-300"
          }`}
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold uppercase tracking-wider text-purple-700">Under Review</span>
            <Clock className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-black text-purple-700 mt-2 font-mono">{countUnderReview}</p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Committee examining attachments</span>
        </div>

        <div
          onClick={() => setStatusFilter("resolved")}
          className={`p-4 rounded-xl border bg-white shadow-xs cursor-pointer transition-all ${
            statusFilter === "resolved" ? "border-emerald-500 ring-2 ring-emerald-100" : "border-slate-200 hover:border-emerald-300"
          }`}
        >
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">Resolved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-black text-emerald-700 mt-2 font-mono">{countResolved}</p>
          <span className="text-[11px] text-slate-400 mt-0.5 block">Cure accepted or closed</span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by notice ref, title, or application no..."
            className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="text-xs font-semibold text-slate-600 shrink-0">Status:</span>
          {["all", "action_required", "submitted", "under_review", "resolved"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                statusFilter === st
                  ? "bg-slate-900 text-white font-bold"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {st === "all" ? "All Notices" : st.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Notices List */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-xs animate-pulse space-y-3">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#0A4D2E]" />
            <p className="font-semibold text-slate-700">Loading authoritative council notices...</p>
            <p className="text-[11px] text-slate-400">Querying institutional docket and issued deficiency items.</p>
          </div>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-8 text-center text-rose-900 text-xs space-y-3">
            <AlertTriangle className="w-8 h-8 text-rose-600 mx-auto" />
            <p className="font-bold text-sm">Failed to Retrieve Information Requests</p>
            <p className="text-slate-600 max-w-md mx-auto">{error}</p>
            <button
              onClick={fetchRequests}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold transition-colors"
            >
              Retry Request
            </button>
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-400 text-xs space-y-1">
            <ShieldAlert className="w-8 h-8 text-slate-300 mx-auto mb-2 opacity-50" />
            <p className="font-semibold text-slate-600 text-sm">No official notices found</p>
            <p className="text-[11px]">
              {statusFilter !== "all"
                ? "No notices match the selected status filter."
                : "No formal Information Requests have been issued to your institution."}
            </p>
          </div>
        ) : (
          filteredRequests.map((req) => {
            const isActionReq = req.status === "action_required" || req.status === "further_info_required";

            return (
              <div
                key={req.id}
                className={`bg-white border rounded-xl p-5 shadow-xs hover:border-slate-300 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isActionReq ? "border-amber-300 bg-amber-50/15" : "border-slate-200"
                }`}
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-[#0A4D2E] bg-[#F0FDF4] px-2 py-0.5 rounded border border-[#86EFAC]">
                      {req.reference_no}
                    </span>
                    <span className="text-xs text-slate-700 font-mono font-semibold">
                      App #{req.application_no || req.application_id}
                    </span>
                    {req.institution_name && (
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Building className="w-3 h-3 text-slate-400" />
                        <span>{req.institution_name}</span>
                      </span>
                    )}
                    {getStatusBadge(req.status)}
                  </div>

                  <h3 className="text-sm font-bold text-slate-900">{req.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed line-clamp-2">
                    {req.reason}
                  </p>

                  <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1 flex-wrap">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      <span>Issued: {req.issued_at ? new Date(req.issued_at).toLocaleDateString() : "—"}</span>
                    </span>
                    <span className="flex items-center gap-1 text-amber-800 font-semibold">
                      <Clock className="w-3 h-3 text-amber-600" />
                      <span>Response Deadline: {req.deadline ? new Date(req.deadline).toLocaleDateString() : "—"}</span>
                    </span>
                    <span className="text-slate-500 font-medium">
                      Deficiencies Listed: {req.deficiencies?.length || 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/information-requests/${req.id}`}
                    className={`px-4 py-2 rounded-lg font-semibold text-xs shadow-xs transition-colors flex items-center gap-1.5 ${
                      isActionReq
                        ? "bg-amber-600 hover:bg-amber-700 text-white"
                        : "bg-[#0A4D2E] hover:bg-[#083D24] text-white"
                    }`}
                  >
                    <span>{isActionReq ? "Respond to Notice" : "Open Request Details"}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
