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
            Automated statutory checklist verification, expiry validation, and missing parameter detection.
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
              <th className="px-5 py-3.5">Validation Status</th>
              <th className="px-5 py-3.5">Findings</th>
              <th className="px-5 py-3.5 text-right">Details</th>
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
                      <div className="inline-flex items-center gap-1 text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Accordion Drawer */}
                  {isExpanded && (
                    <tr className="bg-slate-50/60">
                      <td colSpan={5} className="px-6 py-4">
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
                                className="inline-flex items-center gap-1 text-blue-600 font-semibold hover:underline"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Inspect in Document Viewer</span>
                              </button>
                            )}
                          </div>

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
                                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded text-[11px] disabled:opacity-50"
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
    </div>
  );
}
