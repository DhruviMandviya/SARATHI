"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { FlagItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { useAuth } from "@/lib/auth";
import {
  FileCheck2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldAlert,
  HelpCircle,
  Eye,
  Check,
  RefreshCw,
} from "lucide-react";

interface ValidationItem {
  doc_type: string;
  description: string;
  mandatory: boolean;
  is_uploaded: boolean;
  document_id: number | null;
  original_filename: string | null;
  validation_status: string;
  processing_status: string | null;
  official_verification_status?: string | null;
  official_verification_remarks?: string | null;
  official_verified_by?: number | null;
  official_verified_at?: string | null;
}

interface ValidationViewProps {
  applicationId: number;
  onSelectDocumentForViewer?: (docId: number) => void;
}

export function ValidationView({
  applicationId,
  onSelectDocumentForViewer,
}: ValidationViewProps) {
  const { isOfficial } = useAuth();
  const [items, setItems] = useState<ValidationItem[]>([]);
  const [flags, setFlags] = useState<FlagItem[]>([]);
  const [expandedDocType, setExpandedDocType] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Official Document Verification Modal State
  const [reviewModalDoc, setReviewModalDoc] = useState<ValidationItem | null>(null);
  const [reviewOutcome, setReviewOutcome] = useState<"verified" | "rejected" | "requires_correction" | "unable_to_verify">("verified");
  const [reviewFieldName, setReviewFieldName] = useState<string>("");
  const [reviewRemarks, setReviewRemarks] = useState<string>("");
  const [reviewModalError, setReviewModalError] = useState<string | null>(null);
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);
  const [revalidatingDocId, setRevalidatingDocId] = useState<number | null>(null);

  // Dismissing modal state
  const [dismissingFlagId, setDismissingFlagId] = useState<number | null>(null);
  const [dismissReason, setDismissReason] = useState<string>("");

  const fetchData = async () => {
    try {
      setLoading(true);
      const valRes = await apiRequest<any>(`/applications/${applicationId}/validation`);
      setItems(valRes.items || []);

      const flagsRes = await apiRequest<FlagItem[]>(`/applications/${applicationId}/findings`);
      setFlags(flagsRes || []);
    } catch (err: any) {
      console.error("Failed to load validation:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [applicationId]);

  const handleAcknowledge = async (flagId: number, newStatus: "acknowledged" | "dismissed", reason?: string) => {
    try {
      await apiRequest(`/findings/${flagId}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus, reason: reason || "Reviewed by official" }),
      });
      setDismissingFlagId(null);
      setDismissReason("");
      fetchData();
    } catch (err: any) {
      alert(err.message || "Action failed");
    }
  };

  const openReviewModal = (item: ValidationItem) => {
    setReviewModalDoc(item);
    const existing = (item.official_verification_status || "").toLowerCase();
    if (existing === "verified") {
      setReviewOutcome("verified");
    } else if (existing === "rejected" || existing === "mismatch_confirmed") {
      setReviewOutcome("rejected");
    } else if (existing === "requires_correction" || existing === "more_information_required") {
      setReviewOutcome("requires_correction");
    } else if (existing === "unable_to_verify") {
      setReviewOutcome("unable_to_verify");
    } else {
      setReviewOutcome("verified");
    }

    setReviewRemarks(item.official_verification_remarks || "");
    setReviewFieldName("");
    setReviewModalError(null);
  };

  const handleOfficialReviewSubmit = async () => {
    if (!reviewModalDoc || !reviewModalDoc.document_id) return;
    if (reviewOutcome !== "verified" && (!reviewRemarks.trim() || reviewRemarks.trim().length < 5)) {
      setReviewModalError("Substantive official remarks (min 5 characters) are mandatory when rejecting, requesting correction, or marking unable to verify.");
      return;
    }
    try {
      setSubmittingReview(true);
      setReviewModalError(null);
      const updatedDoc = await apiRequest<any>(`/documents/${reviewModalDoc.document_id}/official-review`, {
        method: "POST",
        body: JSON.stringify({
          outcome: reviewOutcome,
          remarks: reviewRemarks.trim() || undefined,
          field_name: reviewFieldName.trim() || undefined,
        }),
      });

      // Update local item state immediately with returned record
      setItems((prev) =>
        prev.map((it) =>
          it.document_id === reviewModalDoc.document_id
            ? {
                ...it,
                official_verification_status: updatedDoc.official_verification_status,
                official_verification_remarks: updatedDoc.official_verification_remarks,
                official_verified_by: updatedDoc.official_verified_by,
                official_verified_at: updatedDoc.official_verified_at,
                validation_status: updatedDoc.validation_status || it.validation_status,
              }
            : it
        )
      );

      setReviewModalDoc(null);
      setReviewRemarks("");
      setReviewFieldName("");
      await fetchData();
    } catch (err: any) {
      setReviewModalError(err.message || "Failed to record official determination");
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleRevalidateDocument = async (docId: number) => {
    try {
      setRevalidatingDocId(docId);
      await apiRequest(`/documents/${docId}/re-validate`, {
        method: "POST",
      });
      await fetchData();
    } catch (err: any) {
      alert(err.message || "Failed to re-validate document");
    } finally {
      setRevalidatingDocId(null);
    }
  };

  const toggleExpand = (docType: string) => {
    setExpandedDocType(expandedDocType === docType ? null : docType);
  };

  if (loading) {
    return (
      <div className="bg-white p-12 text-center rounded-xl border border-slate-200 text-xs text-slate-500 animate-pulse">
        Evaluating document completeness and regulatory validity rules...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="w-4 h-4 text-emerald-600" />
            <span>Document Validation & Completeness Matrix</span>
          </h3>
          <p className="text-xs text-slate-500">
            Automated statutory checklist verification, expiry validation, and authorised official scrutiny determination.
          </p>
        </div>

        <button
          onClick={() => {
            setRefreshing(true);
            fetchData();
          }}
          disabled={refreshing}
          className="text-xs font-semibold px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          <span>Re-evaluate Matrix</span>
        </button>
      </div>

      {/* Validation Matrix Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden text-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <th className="px-5 py-3.5">Checklist Document</th>
              <th className="px-5 py-3.5">Uploaded File</th>
              <th className="px-5 py-3.5">Automated Check</th>
              <th className="px-5 py-3.5">Official Verification</th>
              <th className="px-5 py-3.5">Findings</th>
              <th className="px-5 py-3.5 text-right">Actions / Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-slate-700">
            {items.map((item) => {
              const docFlags = flags.filter(
                (f) =>
                  f.document_id === item.document_id ||
                  (f.evidence && f.evidence.doc_type === item.doc_type) ||
                  (f.rule_ref && f.rule_ref.includes(item.doc_type))
              );
              const isExpanded = expandedDocType === item.doc_type;
              const hasCritical = docFlags.some((f) => f.severity === "critical" && f.status === "open");

              return (
                <React.Fragment key={item.doc_type}>
                  <tr
                    onClick={() => toggleExpand(item.doc_type)}
                    className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <div className="font-bold text-slate-900">{item.description}</div>
                      <div className="text-[11px] text-slate-400 capitalize">
                        {item.doc_type.replace(/_/g, " ")} &bull; {item.mandatory ? "Mandatory" : "Optional"}
                      </div>
                    </td>

                    <td className="px-5 py-3.5">
                      {item.original_filename ? (
                        <span className="font-medium text-slate-800">{item.original_filename}</span>
                      ) : (
                        <span className="text-slate-400 italic">Not Uploaded</span>
                      )}
                    </td>

                    <td className="px-5 py-3.5">
                      <StatusChip status={item.validation_status} type="document" size="sm" />
                    </td>

                    <td className="px-5 py-3.5">
                      {item.official_verification_status === "verified" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Verified
                        </span>
                      ) : (item.official_verification_status === "rejected" || item.official_verification_status === "mismatch_confirmed") ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-100 text-red-800 border border-red-300">
                          <XCircle className="w-3 h-3 text-red-600" />
                          Rejected
                        </span>
                      ) : (item.official_verification_status === "requires_correction" || item.official_verification_status === "more_information_required") ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                          <AlertTriangle className="w-3 h-3 text-amber-600" />
                          Requires Correction
                        </span>
                      ) : item.official_verification_status === "unable_to_verify" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-300">
                          <AlertTriangle className="w-3 h-3 text-slate-500" />
                          Unable to Verify
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                          <Clock className="w-3 h-3 text-slate-400" />
                          Pending Review
                        </span>
                      )}
                    </td>

                    <td className="px-5 py-3.5">
                      {docFlags.length > 0 ? (
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                              hasCritical
                                ? "bg-red-100 text-red-800 border border-red-200"
                                : "bg-amber-100 text-amber-800 border border-amber-200"
                            }`}
                          >
                            {docFlags.length} Flag(s)
                          </span>
                        </div>
                      ) : (
                        <span className="text-emerald-700 font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Clear</span>
                        </span>
                      )}
                    </td>

                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                        {isOfficial && item.document_id && (
                          <>
                            <button
                              onClick={() => openReviewModal(item)}
                              className="px-2.5 py-1 bg-[#F0FDF4] hover:bg-emerald-100 text-[#0A4D2E] font-semibold rounded text-[11px] border border-[#86EFAC] transition-colors"
                              title="Record Official Scrutiny Verification"
                            >
                              {item.official_verification_status ? "Update Review" : "Official Review"}
                            </button>
                            <button
                              onClick={() => handleRevalidateDocument(item.document_id!)}
                              disabled={revalidatingDocId === item.document_id}
                              className="p-1 hover:bg-slate-100 text-slate-600 rounded border border-slate-200 transition-colors disabled:opacity-50"
                              title="Re-run automated validation"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${revalidatingDocId === item.document_id ? "animate-spin text-[#0A4D2E]" : ""}`} />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => toggleExpand(item.doc_type)}
                          className="p-1 hover:bg-slate-100 text-slate-500 rounded"
                          title="Toggle Details"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Accordion Drawer */}
                  {isExpanded && (
                    <tr className="bg-slate-50/60">
                      <td colSpan={6} className="px-6 py-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                            <span className="font-bold text-slate-700 text-xs">
                              Detailed Verification Signals & Evidence Trace
                            </span>
                            {item.document_id && onSelectDocumentForViewer && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSelectDocumentForViewer(item.document_id!);
                                }}
                                className="inline-flex items-center gap-1 text-[#0A4D2E] font-semibold hover:underline"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Inspect in Document Viewer</span>
                              </button>
                            )}
                          </div>

                          {/* Official Review Status Badge & Remarks */}
                          {item.official_verification_status && (
                            <div className="p-3 rounded-lg bg-[#F0FDF4] border border-[#86EFAC]/70 text-xs">
                              <div className="font-semibold text-[#073F2A] flex items-center justify-between">
                                <span>Official Scrutiny Determination: {item.official_verification_status.replace(/_/g, " ").toUpperCase()}</span>
                                {item.official_verified_at && (
                                  <span className="text-[10px] text-[#0A4D2E] font-mono">
                                    Recorded: {new Date(item.official_verified_at).toLocaleString()}
                                  </span>
                                )}
                              </div>
                              {item.official_verification_remarks && (
                                <p className="text-[#0A4D2E] mt-1 italic">&ldquo;{item.official_verification_remarks}&rdquo;</p>
                              )}
                            </div>
                          )}

                          {docFlags.length === 0 ? (
                            <p className="text-slate-500 italic">No flags or issues registered for this document.</p>
                          ) : (
                            <div className="space-y-2">
                              {docFlags.map((flag) => (
                                <div
                                  key={flag.id}
                                  className={`p-3 rounded-lg border text-xs ${
                                    flag.severity === "critical"
                                      ? "bg-red-50/60 border-red-200"
                                      : "bg-amber-50/60 border-amber-200"
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center gap-2">
                                      <StatusChip status={flag.severity} type="severity" size="sm" />
                                      <span className="font-bold text-slate-800">{flag.title}</span>
                                    </div>

                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] text-slate-500 font-medium capitalize">
                                        Status: {flag.status}
                                      </span>
                                      {isOfficial && flag.status === "open" && (
                                        <div className="flex items-center gap-1">
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              handleAcknowledge(flag.id, "acknowledged");
                                            }}
                                            className="px-2 py-0.5 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-medium"
                                          >
                                            Acknowledge
                                          </button>
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              setDismissingFlagId(flag.id);
                                            }}
                                            className="px-2 py-0.5 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-medium"
                                          >
                                            Dismiss...
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  </div>

                                  <p className="text-slate-700 mt-1">{flag.explanation}</p>

                                  {flag.rule_ref && (
                                    <p className="text-[10px] text-slate-500 mt-1 font-mono">
                                      Rule Reference: {flag.rule_ref} &bull; Confidence: {flag.confidence_meaning} ({flag.confidence})
                                    </p>
                                  )}

                                  {/* Dismissal Reason Form */}
                                  {dismissingFlagId === flag.id && (
                                    <div
                                      onClick={(e) => e.stopPropagation()}
                                      className="mt-2.5 p-2.5 bg-white border border-slate-300 rounded-lg space-y-2"
                                    >
                                      <label className="block text-[11px] font-bold text-slate-700">
                                        Mandatory Official Dismissal Justification:
                                      </label>
                                      <input
                                        type="text"
                                        value={dismissReason}
                                        onChange={(e) => setDismissReason(e.target.value)}
                                        placeholder="e.g. Scrutiny committee verified supplementary gazette notice"
                                        className="w-full px-2.5 py-1 text-xs border border-slate-300 rounded"
                                      />
                                      <div className="flex justify-end gap-1.5">
                                        <button
                                          onClick={() => setDismissingFlagId(null)}
                                          className="px-2 py-1 text-[11px] text-slate-600"
                                        >
                                          Cancel
                                        </button>
                                        <button
                                          onClick={() => handleAcknowledge(flag.id, "dismissed", dismissReason)}
                                          disabled={!dismissReason.trim()}
                                          className="px-3 py-1 bg-[#0A4D2E] hover:bg-[#083D24] text-white font-semibold rounded text-[11px] disabled:opacity-50"
                                        >
                                          Confirm Dismissal
                                        </button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Official Scrutiny Review Modal */}
      {reviewModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden text-xs">
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Record Official Document Scrutiny</h4>
                <p className="text-[11px] text-slate-500">
                  {reviewModalDoc.description} &bull; <span className="font-mono">{reviewModalDoc.original_filename}</span>
                </p>
              </div>
              <button
                onClick={() => setReviewModalDoc(null)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
              {/* Error banner */}
              {reviewModalError && (
                <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{reviewModalError}</span>
                </div>
              )}

              {/* Status and Secure Preview Bar */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-500 font-semibold">Automated Check:</span>
                  <StatusChip status={reviewModalDoc.validation_status} type="document" size="sm" />
                </div>
                {reviewModalDoc.document_id && (
                  <div className="flex items-center gap-2">
                    {onSelectDocumentForViewer && (
                      <button
                        type="button"
                        onClick={() => {
                          onSelectDocumentForViewer(reviewModalDoc.document_id!);
                        }}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#0A4D2E] hover:underline"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect Viewer</span>
                      </button>
                    )}
                    <a
                      href={`/api/v1/documents/${reviewModalDoc.document_id}/file`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 hover:text-[#0A4D2E] hover:underline"
                    >
                      <span>Preview File</span>
                    </a>
                  </div>
                )}
              </div>

              {/* Associated compliance findings/flags if any */}
              {(() => {
                const docFlags = flags.filter(f => f.document_id === reviewModalDoc.document_id);
                if (docFlags.length === 0) return null;
                return (
                  <div className="p-3 rounded-lg bg-amber-50/60 border border-amber-200 space-y-1.5">
                    <span className="font-bold text-amber-900 text-[11px] block">
                      Active Regulatory Findings ({docFlags.length}):
                    </span>
                    <ul className="list-disc pl-4 space-y-1 text-[11px] text-amber-800">
                      {docFlags.map(f => (
                        <li key={f.id}>
                          <strong>{f.title}:</strong> {f.explanation}
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })()}

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Verification Determination <span className="text-red-500">*</span>
                </label>
                <select
                  value={reviewOutcome}
                  onChange={(e: any) => setReviewOutcome(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
                >
                  <option value="verified">Mark Verified — Statutory criteria satisfied & authentic</option>
                  <option value="rejected">Reject / Mark Invalid — Non-compliant, invalid, or conflicting document</option>
                  <option value="requires_correction">Request Correction — Requires resubmission or applicant clarification</option>
                  <option value="unable_to_verify">Unable to Verify / Retain Pending — Inconclusive scan or inspection pending</option>
                </select>
              </div>

              {(reviewOutcome === "rejected") && (
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Conflicting Parameter / Field Name
                  </label>
                  <input
                    type="text"
                    value={reviewFieldName}
                    onChange={(e) => setReviewFieldName(e.target.value)}
                    placeholder="e.g. land_area, survey_number, validity_date, trust_name"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
                  />
                </div>
              )}

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Authorised Officer Remarks / Justification {reviewOutcome !== "verified" && <span className="text-red-500">*</span>}
                </label>
                <textarea
                  value={reviewRemarks}
                  onChange={(e) => setReviewRemarks(e.target.value)}
                  rows={3}
                  placeholder={
                    reviewOutcome === "verified"
                      ? "e.g. Scrutinised against revenue records; registration seal and survey numbers confirmed."
                      : reviewOutcome === "rejected"
                      ? "Explain the specific regulatory discrepancy or conflict observed."
                      : reviewOutcome === "requires_correction"
                      ? "Detail the specific correction, schedule pages, or re-attestation required from applicant."
                      : "Explain why verification could not be completed and what clarification is needed."
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
                />
              </div>

              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-[11px] text-amber-800">
                <strong>Administrative Rule:</strong> Recording a document-level determination updates document scrutiny status and appends an immutable audit event. It does not approve or reject the entire application.
              </div>
            </div>

            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <button
                onClick={() => setReviewModalDoc(null)}
                disabled={submittingReview}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleOfficialReviewSubmit}
                disabled={submittingReview}
                className="px-4 py-1.5 rounded-lg bg-[#0A4D2E] hover:bg-[#083D24] text-white font-semibold flex items-center gap-1.5 disabled:opacity-50"
              >
                {submittingReview ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                <span>Record Scrutiny Determination</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
