"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { ApplicationItem, DocumentItem, FlagItem, VerificationResultItem, ComplianceResultItem } from "@/lib/types";
import { StatusChip, SimulatedBadge } from "@/components/ui/StatusChip";
import { ProcessingStatusRow } from "@/features/processing/ProcessingStatusRow";
import { ExtractedInfoViewer } from "@/features/extraction/ExtractedInfoViewer";
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Scale,
  FileCheck2,
  FileBadge,
  ArrowLeft,
  Building,
  Calendar,
  RefreshCw,
  Download,
  AlertCircle,
  HelpCircle,
  Eye,
} from "lucide-react";

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, isOfficial } = useAuth();
  const appId = params.id as string;

  const [application, setApplication] = useState<ApplicationItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [activeTab, setActiveTab] = useState<
    "overview" | "processing" | "extraction" | "validation" | "fraud" | "verification" | "compliance" | "report"
  >("extraction");
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [retryingDocId, setRetryingDocId] = useState<number | null>(null);

  const fetchApplicationDetails = async () => {
    try {
      const appData = await apiRequest<ApplicationItem>(`/applications/${appId}`);
      setApplication(appData);

      const statusData = await apiRequest<any>(`/applications/${appId}/status`);
      // Fetch full document objects with extracted fields
      const docsRes = await apiRequest<DocumentItem[]>(`/applications/${appId}/documents-detailed`).catch(() => []);
      
      // Fallback: if detailed endpoint not yet created, fetch documents through status
      setDocuments(docsRes);
      if (docsRes.length > 0 && !selectedDocId) {
        setSelectedDocId(docsRes[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load application details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (appId) {
      fetchApplicationDetails();
    }
  }, [appId]);

  // Polling: Poll every 2 seconds if processing
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const statusRes = await apiRequest<any>(`/applications/${appId}/status`);
        if (statusRes.is_processing) {
          fetchApplicationDetails();
        }
      } catch {
        // Polling failure silent catch
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [appId]);

  const handleRetryProcessing = async (docId: number) => {
    setRetryingDocId(docId);
    try {
      await apiRequest(`/documents/${docId}/reprocess`, { method: "POST" });
      await fetchApplicationDetails();
    } catch (err: any) {
      alert(err.message || "Reprocessing failed");
    } finally {
      setRetryingDocId(null);
    }
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocId) || documents[0];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading application scrutiny details...
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 space-y-2">
        <p className="font-bold flex items-center gap-1.5">
          <AlertCircle className="w-4 h-4" />
          <span>Application Error</span>
        </p>
        <p>{error || "Application not found"}</p>
        <Link href="/applications" className="inline-block mt-2 font-semibold text-blue-600 hover:underline">
          &larr; Return to Applications Queue
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Application Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <Link href="/applications" className="text-slate-400 hover:text-slate-600">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>{application.application_no}</span>
              <StatusChip status={application.status} type="application" size="sm" />
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-800 flex items-center gap-1">
              <Building className="w-3.5 h-3.5 text-blue-600" />
              <span>{application.declared_details?.institution_name || `Institution #${application.institution_id}`}</span>
            </span>
            <span>&bull;</span>
            <span>{application.type} ({application.academic_year})</span>
            <span>&bull;</span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Created {new Date(application.created_at).toLocaleDateString()}</span>
            </span>
          </div>
        </div>

        {/* Risk Score Pill & Actions */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Scrutiny Risk Band</span>
            <div className="flex items-center gap-1.5 justify-end mt-0.5">
              <span
                className={`font-black px-2.5 py-0.5 rounded text-xs ${
                  application.risk_band === "High"
                    ? "bg-red-100 text-red-800 border border-red-200"
                    : application.risk_band === "Medium"
                    ? "bg-amber-100 text-amber-800 border border-amber-200"
                    : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                }`}
              >
                {application.risk_score.toFixed(1)} / 100
              </span>
              <span className="text-xs font-bold text-slate-700">{application.risk_band}</span>
            </div>
          </div>

          <Link
            href={`/reports/${application.id}`}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF Report</span>
          </Link>
        </div>
      </div>

      {/* 9-Stage Tabs Navigation */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <div className="flex border-b border-slate-200 min-w-max text-xs font-semibold">
          <button
            onClick={() => setActiveTab("extraction")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "extraction"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileText className="w-4 h-4 text-blue-600" />
            <span>Stage 3: Extracted Info</span>
          </button>

          <button
            onClick={() => setActiveTab("processing")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "processing"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Clock className="w-4 h-4 text-slate-500" />
            <span>Stage 2: OCR Processing</span>
          </button>

          <button
            onClick={() => setActiveTab("validation")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "validation"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Stage 4: Document Validation</span>
          </button>

          <button
            onClick={() => setActiveTab("fraud")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "fraud"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Stage 5: Fraud & Forensics</span>
          </button>

          <button
            onClick={() => setActiveTab("verification")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "verification"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileCheck2 className="w-4 h-4 text-indigo-600" />
            <span>Stage 6: Authenticity</span>
          </button>

          <button
            onClick={() => setActiveTab("compliance")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "compliance"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Scale className="w-4 h-4 text-purple-600" />
            <span>Stage 7: Compliance</span>
          </button>

          <button
            onClick={() => setActiveTab("report")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "report"
                ? "border-blue-600 text-blue-700 bg-blue-50/50"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileBadge className="w-4 h-4 text-slate-700" />
            <span>Stage 8 & 9: Report & Decision</span>
          </button>
        </div>
      </div>

      {/* TAB 3: EXTRACTED INFORMATION (VIEWER + BBOXES + OFFICIAL EDIT) */}
      {activeTab === "extraction" && (
        <div className="space-y-4">
          {/* Document selector buttons */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider pr-1">Document:</span>
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => setSelectedDocId(doc.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  selectedDocId === doc.id
                    ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                    : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                }`}
              >
                <span>{doc.doc_type.replace(/_/g, " ")}</span>
                <span className="text-[10px] opacity-80">({doc.extracted_fields.length})</span>
              </button>
            ))}
          </div>

          {selectedDocument ? (
            <ExtractedInfoViewer
              document={selectedDocument}
              onFieldUpdated={fetchApplicationDetails}
              onReprocessRequested={() => handleRetryProcessing(selectedDocument.id)}
            />
          ) : (
            <div className="bg-white p-12 text-center rounded-xl border border-slate-200 text-xs text-slate-400">
              No documents available for extraction inspection.
            </div>
          )}
        </div>
      )}

      {/* TAB 2: OCR & PIPELINE PROCESSING */}
      {activeTab === "processing" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800">Per-Document Processing Pipeline Status</h3>
            <button
              onClick={fetchApplicationDetails}
              className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Poll Status</span>
            </button>
          </div>

          <div className="space-y-3">
            {documents.map((doc) => (
              <ProcessingStatusRow
                key={doc.id}
                document={doc}
                onRetry={handleRetryProcessing}
                isRetrying={retryingDocId === doc.id}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
