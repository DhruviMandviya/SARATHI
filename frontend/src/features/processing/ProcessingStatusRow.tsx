"use client";

import React from "react";
import { DocumentItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { RefreshCw, AlertCircle, CheckCircle2, Clock, FileText } from "lucide-react";

interface ProcessingStatusRowProps {
  document: DocumentItem;
  onRetry: (docId: number) => void;
  isRetrying?: boolean;
}

export function ProcessingStatusRow({ document, onRetry, isRetrying }: ProcessingStatusRowProps) {
  const stage = document.processing_stage || "Queued";
  const isFailed = document.processing_status === "failed";
  const isCompleted = document.processing_status === "completed";
  const isProcessing = document.processing_status === "processing" || document.processing_status === "queued";

  // Calculate progress percentage based on stage
  let progressPct = 10;
  if (stage === "Extracting Text") progressPct = 35;
  else if (stage === "Identifying Document Type") progressPct = 65;
  else if (stage === "Extracting Key Information") progressPct = 85;
  else if (isCompleted) progressPct = 100;
  else if (isFailed) progressPct = 100;

  return (
    <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs transition-colors hover:border-slate-300">
      {/* File info */}
      <div className="flex items-start gap-3 min-w-[220px]">
        <div className="mt-0.5 p-2 rounded-lg bg-[#F0FDF4] text-[#0A4D2E]">
          <FileText className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-slate-800 truncate max-w-[200px]" title={document.original_filename}>
            {document.original_filename}
          </div>
          <div className="text-[11px] text-slate-400 capitalize mt-0.5">
            {document.doc_type.replace(/_/g, " ")} &bull; {(document.size / 1024).toFixed(1)} KB &bull; {document.page_count} Page(s)
          </div>
        </div>
      </div>

      {/* Progress & Stage */}
      <div className="flex-1 max-w-md space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="font-semibold text-slate-700 flex items-center gap-1.5">
            {isProcessing && <Clock className="w-3.5 h-3.5 text-[#0A4D2E] animate-spin" />}
            {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
            {isFailed && <AlertCircle className="w-3.5 h-3.5 text-red-600" />}
            <span>Stage: {stage}</span>
          </span>
          <span className="text-slate-400 font-bold">{progressPct}%</span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              isFailed
                ? "bg-red-500"
                : isCompleted
                ? "bg-emerald-500"
                : "bg-[#0A4D2E]"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {isFailed && document.processing_error && (
          <p className="text-[11px] text-red-600 font-medium truncate" title={document.processing_error}>
            Error: {document.processing_error}
          </p>
        )}
      </div>

      {/* Status Chip & Retry Action */}
      <div className="flex items-center gap-3 shrink-0">
        <StatusChip
          status={isCompleted ? "valid" : isFailed ? "critical" : "in_progress"}
          size="sm"
        />

        {isFailed && (
          <button
            onClick={() => onRetry(document.id)}
            disabled={isRetrying}
            className="inline-flex items-center gap-1 px-3 py-1 bg-[#F0FDF4] hover:bg-emerald-100 text-[#0A4D2E] font-semibold rounded-lg border border-[#86EFAC] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
            <span>Retry</span>
          </button>
        )}
      </div>
    </div>
  );
}
