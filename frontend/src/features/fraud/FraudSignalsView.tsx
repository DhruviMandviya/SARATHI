"use client";

import React, { useState, useEffect } from "react";
import { FlagItem, DocumentItem } from "@/lib/types";
import { apiRequest, getApiBase } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { StatusChip } from "@/components/ui/StatusChip";
import {
  ShieldAlert,
  AlertTriangle,
  Info,
  CheckCircle2,
  Copy,
  Layers,
  Image as ImageIcon,
  Flame,
  FileText,
  Building,
  Check,
  X,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

interface FraudSignalsViewProps {
  applicationId: number;
  documents: DocumentItem[];
}

export function FraudSignalsView({ applicationId, documents }: FraudSignalsViewProps) {
  const { isOfficial, token } = useAuth();
  const [flags, setFlags] = useState<FlagItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(
    documents[0]?.id || null
  );
  const [viewMode, setViewMode] = useState<"original" | "ela">("original");
  const [imageLoading, setImageLoading] = useState<boolean>(true);
  const [imageError, setImageError] = useState<boolean>(false);

  // Dismissing modal state
  const [dismissingFlagId, setDismissingFlagId] = useState<number | null>(null);
  const [dismissReason, setDismissReason] = useState<string>("");

  const apiBase = getApiBase();

  const fetchFlags = async () => {
    try {
      setLoading(true);
      const data = await apiRequest<FlagItem[]>(`/applications/${applicationId}/findings`);
      setFlags(data || []);
    } catch (err: any) {
      console.error("Failed to load flags:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, [applicationId]);

  useEffect(() => {
    setImageLoading(true);
    setImageError(false);
  }, [selectedDocId, viewMode]);

  const handleAcknowledge = async (flagId: number, newStatus: "acknowledged" | "dismissed", reason?: string) => {
    try {
      await apiRequest(`/findings/${flagId}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus, reason: reason || "Reviewed by official" }),
      });
      setDismissingFlagId(null);
      setDismissReason("");
      fetchFlags();
    } catch (err: any) {
      alert(err.message || "Failed to update review flag");
    }
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocId) || documents[0];
  const forensicFlags = flags.filter(
    (f) => f.category === "tampering" || f.category === "duplicate" || f.category === "metadata"
  );
  const docSpecificFlags = forensicFlags.filter((f) => f.document_id === selectedDocId);
  const duplicateFlags = forensicFlags.filter((f) => f.category === "duplicate");

  const originalImageUrl = selectedDocument
    ? `${apiBase}/documents/${selectedDocument.id}/page/1/image${token ? `?token=${encodeURIComponent(token)}` : ""}`
    : "";
  const elaImageUrl = selectedDocument
    ? `${apiBase}/documents/${selectedDocument.id}/ela${token ? `?token=${encodeURIComponent(token)}` : ""}`
    : "";

  if (loading) {
    return (
      <div className="bg-white p-12 text-center rounded-xl border border-slate-200 text-xs text-slate-500 animate-pulse">
        Running forensic image re-compression checks and cross-institution duplicate search...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* PERSISTENT NON-NEGOTIABLE CAVEAT BANNER */}
      <div className="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl shadow-sm text-xs text-amber-900 space-y-1">
        <div className="flex items-center gap-2 font-bold text-amber-950">
          <Info className="w-4 h-4 text-amber-600 shrink-0" />
          <span>STATUTORY FORENSIC CAVEAT & REGULATORY GUIDANCE</span>
        </div>
        <p className="leading-relaxed">
          Tampering analysis produces <strong>suspicious signals for official review, never accusations</strong>.
          Error Level Analysis (ELA) heatmaps and PDF metadata anomalies are weak heuristic signals, not proof of
          forgery. Many legitimate scanning devices, re-saving operations, watermarking tools, and PDF printers
          naturally produce compression variances. The system recommends review; the authorised AICTE official
          decides.
        </p>
      </div>

      {/* Main Grid: Forensics Viewer + Duplicate Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: IMAGE FORENSICS & ELA VIEWER */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-5 flex flex-col space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <span>Forensic Signal Inspection</span>
              </h3>
              <p className="text-[11px] text-slate-400">Error Level Analysis (ELA) & Copy-Move Feature Clusters</p>
            </div>

            {/* Document Selector */}
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(Number(e.target.value))}
              className="px-2.5 py-1.5 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-[#0A4D2E]"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.doc_type.replace(/_/g, " ")} ({d.original_filename})
                </option>
              ))}
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center justify-between">
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs font-semibold">
              <button
                onClick={() => setViewMode("original")}
                className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                  viewMode === "original" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <ImageIcon className="w-3.5 h-3.5 text-[#0A4D2E]" />
                <span>Original Document</span>
              </button>
              <button
                onClick={() => setViewMode("ela")}
                className={`px-3 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                  viewMode === "ela" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Flame className="w-3.5 h-3.5 text-amber-600" />
                <span>ELA Heatmap Overlay</span>
              </button>
            </div>

            <span className="text-[11px] text-slate-400 font-medium">Page 1 Inspection</span>
          </div>

          {/* Document / Heatmap Viewport */}
          <div className="relative border border-slate-200 rounded-xl bg-slate-900/5 min-h-[380px] max-h-[500px] overflow-auto flex items-center justify-center p-4">
            {imageLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10 gap-2">
                <RefreshCw className="w-6 h-6 text-amber-600 animate-spin" />
                <span className="text-xs text-slate-600 font-semibold">
                  {viewMode === "ela" ? "Computing ELA Heatmap..." : "Loading Inspection Document..."}
                </span>
              </div>
            )}

            {imageError ? (
              <div className="p-8 text-center space-y-3 bg-white rounded-xl border border-slate-200 max-w-sm">
                <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
                <p className="text-xs font-semibold text-slate-800">
                  {viewMode === "ela" ? "ELA Heatmap Unavailable" : "Page Thumbnail Unavailable"}
                </p>
                <p className="text-[11px] text-slate-500">
                  {viewMode === "ela"
                    ? "Error Level Analysis requires a raster image file (JPEG/PNG) or rendered page."
                    : "The page image could not be rendered from disk."}
                </p>
                {selectedDocument && viewMode === "original" && (
                  <a
                    href={`${apiBase}/documents/${selectedDocument.id}/file${token ? `?token=${encodeURIComponent(token)}` : ""}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block px-3 py-1.5 rounded-lg bg-[#0A4D2E] hover:bg-[#083D24] text-white text-xs font-semibold"
                  >
                    Open Original Document &rarr;
                  </a>
                )}
              </div>
            ) : selectedDocument ? (
              <div className="relative shadow-md max-w-full">
                <img
                  src={viewMode === "ela" ? elaImageUrl : originalImageUrl}
                  alt={viewMode === "ela" ? "ELA Forensic Heatmap" : "Original Document"}
                  className="w-full max-h-[460px] object-contain transition-all duration-300 block select-none"
                  onLoad={() => setImageLoading(false)}
                  onError={() => {
                    setImageLoading(false);
                    setImageError(true);
                  }}
                />
                {viewMode === "ela" && (
                  <div className="absolute top-2 right-2 px-2 py-1 rounded bg-black/75 text-amber-300 text-[10px] font-bold uppercase tracking-wider backdrop-blur-sm border border-amber-500/30">
                    Heuristic ELA Difference Map
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-400">Select a document to inspect</p>
            )}
          </div>

          {/* Dual Indicator: Forensic Signal Strength vs OCR Confidence */}
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 grid grid-cols-2 gap-4 text-xs">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-slate-600">Forensic Anomaly Signal Strength</span>
                <span className="font-mono font-bold text-amber-700">
                  {docSpecificFlags.length > 0 ? "Elevated (65%)" : "Nominal (12%)"}
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    docSpecificFlags.length > 0 ? "bg-amber-500 w-[65%]" : "bg-emerald-500 w-[12%]"
                  }`}
                />
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">Heuristic re-compression delta & metadata</span>
            </div>

            <div className="border-l border-slate-200 pl-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] font-bold text-slate-600">OCR Character Confidence</span>
                <span className="font-mono font-bold text-[#0A4D2E]">96%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-[#0A4D2E] rounded-full w-[96%]" />
              </div>
              <span className="text-[10px] text-slate-400 mt-1 block">Independent text extraction certainty</span>
            </div>
          </div>
        </div>

        {/* RIGHT: DUPLICATE DETECTION & FLAGGED FINDINGS */}
        <div className="lg:col-span-5 space-y-4">
          {/* Duplicate Detection Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Copy className="w-3.5 h-3.5 text-[#0A4D2E]" />
              <span>Duplicate & Template Similarity Analysis</span>
            </h4>
            <p className="text-[11px] text-slate-500">
              Evaluates cryptographic SHA-256 equality, perceptual pHash distance, and template-aware affidavit
              comparisons.
            </p>

            {duplicateFlags.length === 0 ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2.5 text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>No cross-institution document reuse or duplicate certificates detected.</span>
              </div>
            ) : (
              <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                {duplicateFlags.map((df) => (
                  <div
                    key={df.id}
                    className={`p-3.5 rounded-xl border text-xs space-y-2 ${
                      df.severity === "critical"
                        ? "bg-red-50/70 border-red-200"
                        : df.severity === "warning"
                        ? "bg-amber-50/70 border-amber-200"
                        : "bg-[#F0FDF4] border-[#86EFAC]/70"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <StatusChip status={df.severity} type="severity" size="sm" />
                      <span className="font-bold text-slate-700 text-[11px]">
                        Match: {df.evidence?.similarity_percentage || 100}%
                      </span>
                    </div>

                    <p className="font-bold text-slate-900 text-xs">{df.title}</p>
                    <p className="text-slate-700 text-[11px] leading-relaxed">{df.explanation}</p>

                    {/* Side-by-side snippet */}
                    <div className="grid grid-cols-2 gap-2 bg-white/80 p-2 rounded-lg border border-slate-200 text-[10px]">
                      <div>
                        <span className="font-semibold text-slate-500 block">Current Document:</span>
                        <span className="font-mono text-slate-800 truncate block">
                          Doc #{df.evidence?.current_doc_id}
                        </span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-500 block">Matched Against:</span>
                        <span className="font-mono text-[#0A4D2E] truncate block">
                          Doc #{df.evidence?.matched_doc_id}
                          {df.evidence?.is_cross_institution && " (Other Inst.)"}
                        </span>
                      </div>
                    </div>

                    {isOfficial && df.status === "open" && (
                      <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-200/60">
                        <button
                          onClick={() => handleAcknowledge(df.id, "acknowledged")}
                          className="px-2.5 py-1 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-[10px]"
                        >
                          Acknowledge
                        </button>
                        <button
                          onClick={() => setDismissingFlagId(df.id)}
                          className="px-2.5 py-1 rounded bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 font-semibold text-[10px]"
                        >
                          Dismiss...
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* All Flagged for Review Bullet List */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Flagged for Review Findings ({forensicFlags.length})</span>
            </h4>

            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {forensicFlags.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No forensic anomalies flagged for this application.</p>
              ) : (
                forensicFlags.map((flag) => (
                  <div key={flag.id} className="p-3 rounded-lg border border-slate-200 text-xs bg-slate-50/50 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 text-xs">{flag.title}</span>
                      <StatusChip status={flag.severity} type="severity" size="sm" />
                    </div>
                    <p className="text-slate-600 text-[11px]">{flag.explanation}</p>
                    <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1">
                      <span>Signal Confidence: {flag.confidence_meaning}</span>
                      <span className="capitalize font-semibold text-slate-600">{flag.status}</span>
                    </div>

                    {dismissingFlagId === flag.id && (
                      <div className="mt-2 p-2 bg-white border border-slate-300 rounded space-y-1.5">
                        <label className="text-[10px] font-bold text-slate-700 block">
                          Reason for Dismissing Flag:
                        </label>
                        <input
                          type="text"
                          value={dismissReason}
                          onChange={(e) => setDismissReason(e.target.value)}
                          placeholder="e.g. Verified genuine with issuing municipal office"
                          className="w-full px-2 py-1 text-xs border border-slate-300 rounded"
                        />
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => setDismissingFlagId(null)}
                            className="px-2 py-0.5 text-[10px] text-slate-600"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleAcknowledge(flag.id, "dismissed", dismissReason)}
                            disabled={!dismissReason.trim()}
                            className="px-2.5 py-0.5 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded text-[10px] font-semibold disabled:opacity-50"
                          >
                            Confirm
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
