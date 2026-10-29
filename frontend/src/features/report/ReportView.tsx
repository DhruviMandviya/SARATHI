"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ApplicationItem } from "@/lib/types";
import { apiRequest, getApiBase } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  FileText,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Send,
  Save,
  Copy,
  Check,
  ShieldCheck,
  Info,
  Scale,
  RefreshCw,
  Clock,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import { NoticeBuilderView } from "./NoticeBuilderView";

interface ReportViewProps {
  application: ApplicationItem;
  onApplicationUpdated: () => void;
  stage?: "stage8" | "stage9" | "all";
  onNavigateToStage9?: () => void;
  onNavigateToStage8?: () => void;
}

export const ReportView: React.FC<ReportViewProps> = ({
  application,
  onApplicationUpdated,
  stage = "all",
  onNavigateToStage9,
  onNavigateToStage8,
}) => {
  const { user, isOfficial } = useAuth();

  // Report & Deficiency Letter state
  const [reportData, setReportData] = useState<any>(null);
  const [deficiencyLetter, setDeficiencyLetter] = useState<any>(null);
  const [editedLetter, setEditedLetter] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingLetter, setSavingLetter] = useState<boolean>(false);
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);

  // Official Decision state
  const [decisionOutcome, setDecisionOutcome] = useState<"approved" | "rejected" | "info_requested" | null>(null);
  const [decisionRemarks, setDecisionRemarks] = useState<string>("");
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [existingDecision, setExistingDecision] = useState<any>(null);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

  const fetchReportAndLetter = async () => {
    try {
      setLoading(true);
      const [rep, letter, dec] = await Promise.all([
        apiRequest<any>(`/applications/${application.id}/report`),
        apiRequest<any>(`/applications/${application.id}/deficiency-letter`).catch(() => null),
        apiRequest<any>(`/applications/${application.id}/decision`).catch(() => null),
      ]);
      setReportData(rep);
      if (letter) {
        setDeficiencyLetter(letter);
        setEditedLetter(letter.letter_text || "");
      }
      if (dec) {
        setExistingDecision(dec);
        // Persisted decision is shown separately; do not pre-populate unsaved decisionOutcome or remarks
      }
    } catch (err) {
      console.error("Failed to fetch report data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReportAndLetter();
  }, [application.id]);

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true);
      const token = localStorage.getItem("aicte_token");
      const res = await fetch(`${getApiBase()}/applications/${application.id}/report.pdf`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to download PDF dossier");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `AICTE_Scrutiny_Dossier_${application.application_no}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error", err);
      alert("Unable to download PDF dossier. Please ensure the backend server is running.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleSaveDeficiencyLetter = async () => {
    try {
      setSavingLetter(true);
      await apiRequest(`/applications/${application.id}/deficiency-letter`, {
        method: "POST",
        body: JSON.stringify({ letter_text: editedLetter }),
      });
      alert("Deficiency letter updated and recorded in append-only audit log.");
    } catch (err) {
      console.error("Failed to save letter", err);
      alert("Error saving deficiency letter changes.");
    } finally {
      setSavingLetter(false);
    }
  };

  const handleCopyLetter = () => {
    navigator.clipboard.writeText(editedLetter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleInitiateDecision = () => {
    if (!decisionOutcome) {
      setDecisionError("Please select an official scrutiny determination (Approve, Request More Information, or Reject).");
      return;
    }
    if (!decisionRemarks.trim() || decisionRemarks.trim().length < 5) {
      setDecisionError("Mandatory official remarks are required (minimum 5 characters).");
      return;
    }
    setDecisionError(null);
    setShowConfirmModal(true);
  };

  const handleConfirmDecision = async () => {
    if (!decisionOutcome) return;
    try {
      setSubmittingDecision(true);
      setDecisionError(null);
      const res = await apiRequest(`/applications/${application.id}/decision`, {
        method: "POST",
        body: JSON.stringify({
          outcome: decisionOutcome,
          remarks: decisionRemarks.trim(),
        }),
      });
      setExistingDecision(res);
      setDecisionSuccess(`Application determination successfully recorded as '${decisionOutcome.toUpperCase()}'.`);
      setShowConfirmModal(false);
      onApplicationUpdated();
    } catch (err: any) {
      setDecisionError(err.message || "Failed to record official scrutiny decision.");
    } finally {
      setSubmittingDecision(false);
    }
  };

  const score = reportData?.risk_score ?? application.risk_score ?? 0;
  const band = reportData?.risk_band ?? application.risk_band ?? "Low";
  const breakdown = reportData?.risk_breakdown ?? application.risk_breakdown ?? {};
  const topFactors = breakdown?.top_contributing_factors ?? [];

  const getBandBadge = (b: string) => {
    switch (b) {
      case "High":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">High Scrutiny Priority</span>;
      case "Medium":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">Medium Scrutiny Priority</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">Low Scrutiny Priority</span>;
    }
  };

  if (!isOfficial) {
    // APPLICANT VIEW: Clean, Official communications and released documents only
    const hasIssuedNotice = !!(deficiencyLetter && deficiencyLetter.is_issued);

    return (
      <div className="space-y-6">
        {/* 1. Official Decision Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" />
                <span>Official Scrutiny Determination</span>
              </h3>
              <p className="text-xs text-slate-400">
                Application #{application.application_no} &bull; {application.declared_details?.institution_name || user?.full_name || "Applicant Institution"}
              </p>
            </div>
            {existingDecision && (
              <span className="text-[11px] font-mono text-slate-500 bg-slate-50 px-2.5 py-1 rounded border border-slate-200">
                Ref: {existingDecision.reference_no || `DEC/${application.academic_year}/${application.application_no}`}
              </span>
            )}
          </div>

          {existingDecision ? (
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border bg-slate-50">
                <div className="flex items-center gap-3">
                  {existingDecision.outcome === "approved" ? (
                    <div className="p-2.5 rounded-xl bg-emerald-100 text-emerald-700">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                  ) : existingDecision.outcome === "rejected" ? (
                    <div className="p-2.5 rounded-xl bg-rose-100 text-rose-700">
                      <XCircle className="w-6 h-6" />
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-xl bg-amber-100 text-amber-700">
                      <Clock className="w-6 h-6" />
                    </div>
                  )}
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Decision Status</span>
                    <span
                      className={`text-base font-extrabold capitalize ${
                        existingDecision.outcome === "approved"
                          ? "text-emerald-700"
                          : existingDecision.outcome === "rejected"
                          ? "text-rose-700"
                          : "text-amber-700"
                      }`}
                    >
                      {existingDecision.outcome.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                <div className="text-left sm:text-right text-xs text-slate-500">
                  <span className="block font-medium">
                    Date: {new Date(existingDecision.decided_at).toLocaleDateString()}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    Authority: {existingDecision.issuing_authority || "AICTE Regional Scrutiny Cell"}
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800 space-y-1">
                <span className="font-bold text-slate-700 block text-[11px] uppercase tracking-wider">
                  Official Decision Remarks:
                </span>
                <p className="leading-relaxed whitespace-pre-wrap">{existingDecision.remarks}</p>
              </div>

              <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-xs text-blue-900 space-y-1">
                <span className="font-bold block text-[11px] uppercase tracking-wider text-blue-950">
                  Next Step for Institution:
                </span>
                <p className="leading-relaxed">
                  {existingDecision.outcome === "approved"
                    ? "Your Letter of Approval (LoA) has been granted. Proceed to download the formal order below and initiate university affiliation clearance."
                    : existingDecision.outcome === "rejected"
                    ? "Your application was not approved under statutory norms. An appeal petition may be submitted within 30 days under the AICTE Approval Process Handbook."
                    : "Information or document cure has been formally requested. Please submit your responses via the Information Requests workflow."}
                </p>
              </div>
            </div>
          ) : (
            <div className="py-10 text-center text-xs text-slate-500 space-y-2">
              <Clock className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="font-semibold text-slate-700 text-sm">No official decision has been issued yet.</p>
              <p className="text-slate-400 max-w-md mx-auto">
                Your application is currently undergoing statutory scrutiny. When an official determination is recorded by authorized council officers, it will be published here.
              </p>
            </div>
          )}
        </div>

        {/* 2. Official Notices Card (Only if a formal notice has been issued) */}
        {hasIssuedNotice && (
          <div className="bg-white border-2 border-amber-300 rounded-xl p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-amber-100 gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold uppercase tracking-wider">
                  Formal Deficiency Notice
                </span>
                <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  {deficiencyLetter.reference_no}
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200 uppercase">
                  {deficiencyLetter.status?.replace(/_/g, " ") || "Action Required"}
                </span>
              </div>

              <div className="text-left sm:text-right text-xs">
                <span className="text-slate-400 block text-[11px]">Response Deadline</span>
                <span className="font-bold text-amber-900">
                  {deficiencyLetter.cure_deadline}
                </span>
              </div>
            </div>

            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-700 block uppercase tracking-wider text-[11px]">
                Notice Preview:
              </span>
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                {deficiencyLetter.letter_text}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 flex-wrap gap-2">
              <button
                onClick={() => {
                  const blob = new Blob([deficiencyLetter.letter_text || ""], { type: "text/plain;charset=utf-8" });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `Deficiency_Notice_${application.application_no}.txt`;
                  document.body.appendChild(a);
                  a.click();
                  window.URL.revokeObjectURL(url);
                }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200 transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>Download Notice</span>
              </button>

              <Link
                href={`/information-requests/${deficiencyLetter.id || deficiencyLetter.request_id || 1}`}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-xs transition-colors"
              >
                <span>Respond to Notice</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {/* 3. Released Reports & Documents Section */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
          <div className="pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-700" />
              <span>Released Reports &amp; Official Communications</span>
            </h3>
            <p className="text-xs text-slate-400">
              Only formal orders and notices released to this institution are downloadable below.
            </p>
          </div>

          <div className="space-y-3">
            {/* Approved LoA Document */}
            {existingDecision && existingDecision.outcome === "approved" && (
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 text-xs">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <p className="font-bold text-emerald-950">Official Letter of Approval (LoA)</p>
                    <p className="text-[11px] text-emerald-700">Council Granted Technical Institution Sanction Order</p>
                  </div>
                </div>
                <button
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download LoA</span>
                </button>
              </div>
            )}

            {/* Official Decision Order */}
            {existingDecision && (
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-blue-600 shrink-0" />
                  <div>
                    <p className="font-bold text-slate-800">Council Scrutiny Decision Order</p>
                    <p className="text-[11px] text-slate-500">
                      Recorded on {new Date(existingDecision.decided_at).toLocaleDateString()} &bull; AICTE Regional Scrutiny Cell
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Order</span>
                </button>
              </div>
            )}

            {/* Issued Deficiency Notice Document */}
            {hasIssuedNotice && (
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-amber-200 bg-amber-50/50 text-xs">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  <div>
                    <p className="font-bold text-amber-950">Issued Deficiency Notice ({deficiencyLetter.reference_no})</p>
                    <p className="text-[11px] text-amber-700">Formal cure instruction issued on {deficiencyLetter.generated_date}</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    const blob = new Blob([deficiencyLetter.letter_text || ""], { type: "text/plain;charset=utf-8" });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `Deficiency_Notice_${application.application_no}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Notice</span>
                </button>
              </div>
            )}

            {!existingDecision && !hasIssuedNotice && (
              <div className="p-8 text-center text-xs text-slate-400 space-y-1">
                <FileText className="w-6 h-6 text-slate-300 mx-auto" />
                <p className="font-semibold text-slate-600">No official reports or released documents are available yet.</p>
                <p className="text-[11px]">When official approval orders or deficiency notices are formally released, they will appear here.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  const showDossier = stage === "stage8" || stage === "all";
  const showDecision = stage === "stage9" || stage === "all";

  // OFFICIAL VIEW: Full Scrutiny Dossier, Scoring Factors, Stage 9 Decision, and Deficiency Editor
  return (
    <div className="space-y-6">
      {/* 1. Decision Support Notice Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-amber-800 leading-relaxed">
          <p className="font-bold text-amber-900 mb-0.5">
            Core Regulatory Principle: The AI Recommends; The Authorised Official Decides
          </p>
          The Review-Priority Score and contributing factor weights are decision-support indicators calculated to prioritize committee inspection workload. Under AICTE regulations, an automated model never declares fraud or automatically issues approval or denial.
        </div>
      </div>

      {/* STAGE 8: Scrutiny Committee Assessment & Dossier */}
      {showDossier && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-100">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Stage 8: Scrutiny Committee Dossier &amp; Assessment
              </span>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-3xl font-extrabold text-slate-900 font-mono">
                  {score}
                  <span className="text-lg text-slate-400 font-normal"> / 100</span>
                </span>
                {getBandBadge(band)}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Aggregated across {breakdown.critical_flags_count || 0} critical flags, {breakdown.warning_flags_count || 0} warnings, and {breakdown.compliance_deficits_count || 0} regulatory deficits.
              </p>
            </div>

            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 shadow-sm transition-colors"
            >
              <Download className={`w-4 h-4 ${downloadingPdf ? "animate-spin" : ""}`} />
              {downloadingPdf ? "Generating PDF..." : "Download Official PDF Dossier"}
            </button>
          </div>

          {/* Priority Factors Explainability Breakdown */}
          {topFactors.length > 0 && (
            <div className="mt-5">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
                Top Priority Contributing Factors (Explainable Attribution):
              </h4>
              <div className="space-y-2">
                {topFactors.map((tf: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-start justify-between gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100 text-xs"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">{tf.title}</span>
                        <span className="text-[10px] text-slate-400 font-mono">({tf.source})</span>
                      </div>
                      <p className="text-slate-600 leading-normal">{tf.detail}</p>
                    </div>
                    <span className="font-mono font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-100 flex-shrink-0">
                      +{tf.points} pts
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation link to Stage 9 if in Stage 8 view */}
          {stage === "stage8" && onNavigateToStage9 && (
            <div className="pt-4 border-t border-slate-100 flex items-center justify-between flex-wrap gap-3">
              <div className="text-xs text-slate-500">
                Evidence assessment complete. Proceed to Stage 9 to record an official determination.
              </div>
              <button
                type="button"
                onClick={onNavigateToStage9}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg shadow-sm transition-colors"
              >
                <span>Proceed to Stage 9: Official Decision</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* STAGE 9: Official Decision and Notice Management */}
      {showDecision && (
        <>
          {stage === "stage9" && onNavigateToStage8 && (
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <button
                type="button"
                onClick={onNavigateToStage8}
                className="text-xs font-bold text-slate-600 hover:text-blue-600 flex items-center gap-1.5 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Stage 8: Scrutiny Dossier</span>
              </button>
              <div className="text-xs text-slate-500 font-mono">
                App #{application.application_no} &bull; Advisory Score: {score}/100 ({band} Priority)
              </div>
            </div>
          )}

          <div className="bg-white border-2 border-slate-900 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-blue-600" />
                  <span>Stage 9: Competent Official Scrutiny Decision</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Only authorized AICTE Scrutiny Officers can record a binding application determination or issue deficiency cure notices.
                </p>
              </div>
            </div>

            {/* Prominent Persisted Scrutiny Determination Box */}
            {existingDecision ? (
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/80 space-y-2 text-xs">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">
                      Persisted Scrutiny Determination:
                    </span>
                    <span
                      className={`px-3 py-0.5 rounded-full text-xs font-extrabold uppercase ${
                        existingDecision.outcome === "approved"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : existingDecision.outcome === "rejected"
                          ? "bg-rose-100 text-rose-800 border border-rose-300"
                          : "bg-amber-100 text-amber-800 border border-amber-300"
                      }`}
                    >
                      {existingDecision.outcome.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    Recorded on {new Date(existingDecision.decided_at).toLocaleString()}
                  </span>
                </div>
                {existingDecision.remarks && (
                  <div className="bg-white p-3 rounded-lg border border-slate-200 text-slate-800 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                      Official Decision Remarks:
                    </span>
                    <p className="whitespace-pre-wrap leading-relaxed">{existingDecision.remarks}</p>
                  </div>
                )}
                <p className="text-[11px] text-slate-400">
                  Note: The actions below allow an authorized official to record a new binding determination or issue a structured deficiency cure notice. Selecting an action will not overwrite this persisted determination until confirmed.
                </p>
              </div>
            ) : (
              <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-lg text-xs text-blue-800 flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <span>No official determination has been recorded yet for this application. Review the scrutiny evidence and select an action below.</span>
              </div>
            )}

            {decisionSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{decisionSuccess}</span>
              </div>
            )}

            {decisionError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{decisionError}</span>
              </div>
            )}

            {/* Official Decision Action Selection */}
            <div className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-2">
                  Select Official Workflow Action:
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setDecisionOutcome("approved");
                      setDecisionError(null);
                    }}
                    className={`p-3 rounded-xl border text-left flex items-center gap-3 transition-all ${
                      decisionOutcome === "approved"
                        ? "border-emerald-600 bg-emerald-50/70 text-emerald-900 ring-2 ring-emerald-600/20 shadow-sm"
                        : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    <div>
                      <span className="text-xs font-bold block">Approve Application</span>
                      <span className="text-[11px] text-slate-500">All mandatory requirements met</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setDecisionOutcome("info_requested");
                      setDecisionError(null);
                    }}
                    className={`p-3 rounded-xl border text-left flex items-center gap-3 transition-all ${
                      decisionOutcome === "info_requested"
                        ? "border-amber-600 bg-amber-50/70 text-amber-900 ring-2 ring-amber-600/20 shadow-sm"
                        : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <Clock className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <div>
                      <span className="text-xs font-bold block">Request More Information</span>
                      <span className="text-[11px] text-slate-500">Open Notice Builder workflow</span>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setDecisionOutcome("rejected");
                      setDecisionError(null);
                    }}
                    className={`p-3 rounded-xl border text-left flex items-center gap-3 transition-all ${
                      decisionOutcome === "rejected"
                        ? "border-rose-600 bg-rose-50/70 text-rose-900 ring-2 ring-rose-600/20 shadow-sm"
                        : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                    <div>
                      <span className="text-xs font-bold block">Reject Application</span>
                      <span className="text-[11px] text-slate-500">Critical defects or deficits</span>
                    </div>
                  </button>
                </div>
              </div>

              {/* If Approve or Reject is selected, show official remarks textarea and commit button */}
              {(decisionOutcome === "approved" || decisionOutcome === "rejected") && (
                <div className="space-y-3 p-4 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Authorised Official Scrutiny Remarks <span className="text-rose-500">*</span>:
                    </label>
                    <textarea
                      rows={3}
                      value={decisionRemarks}
                      onChange={(e) => setDecisionRemarks(e.target.value)}
                      placeholder={
                        decisionOutcome === "approved"
                          ? "State the official approval rationale confirming all essential accreditation requirements and site conditions are satisfied..."
                          : "Detail the specific regulatory grounds, failed checks, and evidence warranting rejection under the Approval Process Handbook..."
                      }
                      className="w-full text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 bg-white"
                    />
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-slate-500">
                      Binding decision will be recorded with actor, timestamp, and audit event.
                    </span>

                    <button
                      type="button"
                      disabled={submittingDecision || decisionRemarks.trim().length < 5}
                      onClick={handleInitiateDecision}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition-colors shadow-sm"
                    >
                      <Send className={`w-3.5 h-3.5 ${submittingDecision ? "animate-spin" : ""}`} />
                      <span>Review &amp; Commit Determination</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* If Request More Information is selected, render the Official Notice Builder */}
          {decisionOutcome === "info_requested" && (
            <NoticeBuilderView
              applicationId={application.id}
              applicationNo={application.application_no}
              institutionName={application.declared_details?.institution_name || "Applicant Institution"}
              onNoticeIssued={() => {
                fetchReportAndLetter();
                onApplicationUpdated();
              }}
            />
          )}
        </>
      )}

      {/* Confirmation Modal for Official Binding Decision */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-700">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Confirm Official Scrutiny Determination
                </h3>
                <p className="text-xs text-slate-500">
                  You are about to record a binding determination on this application.
                </p>
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Application ID:</span>
                <span className="font-mono font-bold text-slate-800">{application.application_no}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Institution:</span>
                <span className="font-bold text-slate-800">{application.declared_details?.institution_name || "Applicant Institution"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Selected Outcome:</span>
                <span className={`px-2.5 py-0.5 rounded-full font-bold text-[11px] ${
                  decisionOutcome === "approved"
                    ? "bg-emerald-100 text-emerald-800"
                    : decisionOutcome === "info_requested"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-rose-100 text-rose-800"
                }`}>
                  {decisionOutcome ? decisionOutcome.toUpperCase() : "NONE"}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200">
                <span className="text-slate-500 font-medium block mb-1">Official Remarks:</span>
                <p className="text-slate-800 font-mono text-[11px] whitespace-pre-wrap bg-white p-2.5 rounded border border-slate-200 leading-relaxed">
                  {decisionRemarks}
                </p>
              </div>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-[11px] text-amber-800">
              <strong>Notice:</strong> This action commits directly to the AICTE ledger and dispatches official notifications to the applicant institution.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={submittingDecision}
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Back to Review
              </button>
              <button
                type="button"
                disabled={submittingDecision}
                onClick={handleConfirmDecision}
                className="px-5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-bold text-white transition-colors shadow-sm flex items-center gap-1.5"
              >
                <Send className={`w-3.5 h-3.5 ${submittingDecision ? "animate-spin" : ""}`} />
                <span>{submittingDecision ? "Recording..." : "Confirm Official Decision"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

