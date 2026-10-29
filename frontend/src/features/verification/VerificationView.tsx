"use client";

import React, { useState, useEffect } from "react";
import { VerificationResultItem, DocumentItem } from "@/lib/types";
import { apiRequest } from "@/lib/api";
import { SimulatedBadge } from "@/components/ui/StatusChip";
import {
  ShieldCheck,
  Building2,
  Flame,
  FileCheck2,
  Clock,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
  Info
} from "lucide-react";

interface VerificationViewProps {
  applicationId: number;
  documents: DocumentItem[];
}

export const VerificationView: React.FC<VerificationViewProps> = ({
  applicationId,
  documents,
}) => {
  const [results, setResults] = useState<VerificationResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRefDocId, setEditingRefDocId] = useState<number | null>(null);
  const [customRefInput, setCustomRefInput] = useState<string>("");
  const [reverifyingId, setReverifyingId] = useState<number | null>(null);
  const [manualVerifyDocId, setManualVerifyDocId] = useState<number | null>(null);
  const [manualOutcome, setManualOutcome] = useState<string>("verified");
  const [manualRemarks, setManualRemarks] = useState<string>("");
  const [manualEvidence, setManualEvidence] = useState<string>("");
  const [submittingManual, setSubmittingManual] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [manualModalError, setManualModalError] = useState<string | null>(null);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const data = await apiRequest<VerificationResultItem[]>(`/applications/${applicationId}/verification`);
      const deduped: VerificationResultItem[] = [];
      const seenDocIds = new Set<number>();
      for (const r of (data || [])) {
        if (!seenDocIds.has(r.document_id)) {
          seenDocIds.add(r.document_id);
          deduped.push(r);
        }
      }
      setResults(deduped);
    } catch (err: any) {
      console.error("Failed to fetch verification results", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [applicationId]);

  const handleManualReverify = async (docId: number, overrideRef?: string) => {
    try {
      setActionError(null);
      setReverifyingId(docId);
      const payload: any = {};
      if (overrideRef && overrideRef.trim()) {
        payload.reference_no = overrideRef.trim();
      }
      await apiRequest(`/applications/${applicationId}/documents/${docId}/verify`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setEditingRefDocId(null);
      setCustomRefInput("");
      await fetchResults();
    } catch (err: any) {
      setActionError(err.message || "Manual re-verification failed");
    } finally {
      setReverifyingId(null);
    }
  };

  const handleRecordManualVerification = async () => {
    if (!manualVerifyDocId) return;
    if (!manualRemarks.trim() || manualRemarks.trim().length < 5) {
      setManualModalError("Please provide substantive scrutiny remarks (min 5 characters).");
      return;
    }
    try {
      setSubmittingManual(true);
      setManualModalError(null);
      await apiRequest(`/applications/${applicationId}/documents/${manualVerifyDocId}/manual-verify`, {
        method: "POST",
        body: JSON.stringify({
          outcome: manualOutcome,
          remarks: manualRemarks.trim(),
          evidence_reviewed: manualEvidence.trim() || "Physical Certificate / Certified Extract Scrutiny"
        }),
      });
      setManualVerifyDocId(null);
      setManualRemarks("");
      setManualEvidence("");
      await fetchResults();
    } catch (err: any) {
      setManualModalError(err.message || "Failed to record manual verification");
    } finally {
      setSubmittingManual(false);
    }
  };

  const getAuthorityIcon = (authority: string) => {
    if (authority.toLowerCase().includes("fire")) return <Flame className="w-5 h-5 text-amber-600" />;
    if (authority.toLowerCase().includes("municipal") || authority.toLowerCase().includes("planning"))
      return <Building2 className="w-5 h-5 text-indigo-600" />;
    return <FileCheck2 className="w-5 h-5 text-[#0A4D2E]" />;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "verified":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Match Found / Authentic
          </span>
        );
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">
            <RefreshCw className="w-3.5 h-3.5 text-[#0A4D2E] animate-spin" />
            Under Official Scrutiny
          </span>
        );
      case "not_verified":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
            Record Not Found / Disputed
          </span>
        );
      case "unable_to_verify":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
            <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
            Unable to Verify
          </span>
        );
      case "pending":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            Pending Verification
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Simulation Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-slate-500 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-slate-600 leading-relaxed">
          <p className="font-semibold text-slate-800 mb-1">
            Pluggable Simulated External Gateways &amp; Authorised Manual Verification
          </p>
          In accordance with AICTE regulatory guidelines, external authority verification connects to pluggable mock adapters that simulate state land records, municipal sanction registries, and state fire directorate responses. Every automated mock response is explicitly tagged with a{" "}
          <span className="font-mono bg-purple-100 text-purple-800 px-1 py-0.5 rounded text-[11px] font-semibold">
            SIMULATED
          </span>{" "}
          badge. Officers can also record controlled manual verification for self-attested affidavits or physical municipal registers.
        </div>
      </div>

      {actionError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center">
          <RefreshCw className="w-8 h-8 animate-spin text-slate-400 mb-3" />
          <p className="text-sm">Querying external authority verification adapters...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <ShieldCheck className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-700">No Verifiable Documents Found</h3>
          <p className="text-xs text-slate-500 mt-1">
            Upload institutional sanction orders, Fire NOC, or registration certificates to trigger authority checks.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((res: any) => {
            const doc = documents.find((d) => d.id === res.document_id);
            const isManual = res.verification_mode === "MANUAL" || !res.is_simulated;

            return (
              <div
                key={res.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-slate-100 border border-slate-200">
                        {getAuthorityIcon(res.authority)}
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-slate-900 leading-snug">
                          {res.authority}
                        </h4>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {doc ? doc.original_filename : `Document #${res.document_id}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isManual ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                          MANUAL SCRUTINY
                        </span>
                      ) : (
                        <SimulatedBadge />
                      )}
                      {getStatusBadge(res.status)}
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 mb-3 space-y-1.5 text-xs">
                    <div className="flex justify-between items-center text-slate-600">
                      <span className="text-slate-400">Checked Reference:</span>
                      <div className="flex items-center gap-1.5">
                        {res.manual_reference_no || res.reference_no || res.ocr_reference_no ? (
                          <span className="font-mono font-medium text-slate-800">
                            {res.manual_reference_no || res.reference_no || res.ocr_reference_no}
                          </span>
                        ) : (
                          <span className="font-mono text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-medium border border-amber-200">
                            Reference Not Detected
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            setEditingRefDocId(res.document_id);
                            setCustomRefInput(res.manual_reference_no || res.reference_no || "");
                          }}
                          className="text-[10px] text-[#0A4D2E] hover:underline font-semibold"
                        >
                          Edit
                        </button>
                      </div>
                    </div>

                    {editingRefDocId === res.document_id && (
                      <div className="pt-2 border-t border-slate-200 space-y-1.5">
                        <label className="text-[10px] font-bold text-slate-700 block">
                          Enter / Correct Reference Number:
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={customRefInput}
                            onChange={(e) => setCustomRefInput(e.target.value)}
                            placeholder="e.g. NOC-2026-FIRE-8874"
                            className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded bg-white"
                          />
                          <button
                            type="button"
                            onClick={() => handleManualReverify(res.document_id, customRefInput)}
                            disabled={reverifyingId === res.document_id || !customRefInput.trim()}
                            className="px-2.5 py-1 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded text-xs font-semibold disabled:opacity-50"
                          >
                            Verify
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingRefDocId(null)}
                            className="px-2 py-1 text-xs text-slate-500 hover:text-slate-800"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    <div className="flex justify-between text-slate-600">
                      <span className="text-slate-400">Adapter / Mode:</span>
                      <span className="font-mono text-[11px] text-slate-700">
                        {res.adapter_name} ({res.verification_mode || (isManual ? "MANUAL" : "SIMULATED")})
                      </span>
                    </div>

                    <div className="flex justify-between text-slate-600">
                      <span className="text-slate-400">Checked At:</span>
                      <span className="text-slate-700">
                        {new Date(res.checked_at).toLocaleString()}
                      </span>
                    </div>

                    {res.manual_remarks && (
                      <div className="pt-1 border-t border-slate-200 text-slate-600">
                        <span className="text-slate-400 block text-[10px]">Officer Scrutiny Remarks:</span>
                        <span className="font-semibold text-slate-800">{res.manual_remarks}</span>
                      </div>
                    )}
                  </div>

                  <p className="text-xs text-[#073F2A] leading-relaxed bg-[#F0FDF4] border border-[#86EFAC]/70 rounded-lg p-2.5">
                    {res.message || "Authority check completed without supplementary remarks."}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setManualVerifyDocId(res.document_id);
                      setManualOutcome(res.status === "verified" ? "verified" : "verified");
                      setManualRemarks(res.manual_remarks || "");
                      setManualEvidence("");
                      setManualModalError(null);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 transition-colors"
                  >
                    <span>Record Manual Verification</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleManualReverify(res.document_id)}
                    disabled={reverifyingId === res.document_id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-[#0A4D2E] hover:bg-[#083D24] disabled:opacity-50 transition-colors shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${reverifyingId === res.document_id ? "animate-spin" : ""}`} />
                    <span>{reverifyingId === res.document_id ? "Verifying..." : "Re-Verify"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Verification Modal */}
      {manualVerifyDocId && (() => {
        const selectedDoc = documents.find((d) => d.id === manualVerifyDocId);
        const selectedRes = results.find((r) => r.document_id === manualVerifyDocId);

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full border border-slate-200 p-6 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Record Manual Authority Verification
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Authorised human determination for affidavits, offline certificates, or municipal physical files.
                  </p>
                </div>
              </div>

              {selectedDoc && (
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Document:</span>
                    <span className="font-semibold text-slate-800">{selectedDoc.original_filename}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Authority:</span>
                    <span className="font-semibold text-slate-800">{selectedRes?.authority || selectedDoc.doc_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-medium">Extracted Ref:</span>
                    <span className="font-mono text-slate-700">
                      {selectedRes?.manual_reference_no || selectedRes?.reference_no || selectedRes?.ocr_reference_no || "Reference Not Detected"}
                    </span>
                  </div>
                </div>
              )}

              {manualModalError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>{manualModalError}</span>
                </div>
              )}

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Determination Outcome <span className="text-rose-500">*</span>:
                  </label>
                  <select
                    value={manualOutcome}
                    onChange={(e) => setManualOutcome(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-lg border border-slate-300 bg-white text-slate-800"
                  >
                    <option value="verified">Match Confirmed (Authentic / Legally Valid)</option>
                    <option value="not_verified">Mismatch Confirmed (Unverified / Disputed Record)</option>
                    <option value="unable_to_verify">Unable to Verify (Inconclusive / Pending Authority File)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Evidence / Certified Source Reviewed:
                  </label>
                  <input
                    type="text"
                    value={manualEvidence}
                    onChange={(e) => setManualEvidence(e.target.value)}
                    placeholder="e.g. Sub-Registrar Certified Index II / Municipal Town Planning Register"
                    className="w-full text-xs p-2.5 rounded-lg border border-slate-300 bg-white text-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Substantive Officer Remarks <span className="text-rose-500">*</span>:
                  </label>
                  <textarea
                    rows={3}
                    value={manualRemarks}
                    onChange={(e) => setManualRemarks(e.target.value)}
                    placeholder="Detail the verified particulars, official register reference, or reason for unable to verify (minimum 5 characters)..."
                    className="w-full text-xs p-2.5 rounded-lg border border-slate-300 bg-white text-slate-800"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setManualVerifyDocId(null);
                    setManualModalError(null);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleRecordManualVerification}
                  disabled={submittingManual || manualRemarks.trim().length < 5}
                  className="px-4 py-2 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded-lg text-xs font-bold disabled:opacity-50 transition-colors shadow-sm"
                >
                  {submittingManual ? "Recording..." : "Save Determination"}
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

