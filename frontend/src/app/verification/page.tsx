"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { ApplicationItem, DocumentItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { VerificationView } from "@/features/verification/VerificationView";
import { ProcessingStatusRow } from "@/features/processing/ProcessingStatusRow";
import { ExtractedInfoViewer } from "@/features/extraction/ExtractedInfoViewer";
import { ValidationView } from "@/features/validation/ValidationView";
import {
  FileCheck2,
  Building2,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  Clock,
  ShieldAlert,
  AlertCircle,
  FileText,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";

function VerificationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isOfficial, isInstitution, isLoading: authLoading } = useAuth();

  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<ApplicationItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);

  // Tabs for inspection within the verification portal
  const [activeSubTab, setActiveSubTab] = useState<"authority" | "processing" | "extraction" | "validation">("authority");

  const [loadingApps, setLoadingApps] = useState<boolean>(true);
  const [loadingDetails, setLoadingDetails] = useState<boolean>(false);
  const [retryingDocId, setRetryingDocId] = useState<number | null>(null);
  const [search, setSearch] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Role check and auth redirection
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  // Fetch all applications in queue
  const fetchApplications = async () => {
    try {
      setLoadingApps(true);
      const data = await apiRequest<ApplicationItem[]>("/applications");
      setApplications(data);

      const urlAppId = searchParams.get("appId");
      if (urlAppId && data.some((a) => a.id === Number(urlAppId))) {
        setSelectedAppId(Number(urlAppId));
      } else if (data.length > 0 && !selectedAppId) {
        // Default to first application (prioritize needs_review)
        const priorityApp = data.find((a) => a.status === "needs_review") || data[0];
        setSelectedAppId(priorityApp.id);
      }
    } catch (err) {
      console.error("Failed to load applications for verification", err);
    } finally {
      setLoadingApps(false);
    }
  };

  useEffect(() => {
    if (user && !isInstitution) {
      fetchApplications();
    }
  }, [user, isInstitution]);

  // Fetch selected application details & documents
  const fetchSelectedAppDetails = async (appId: number) => {
    try {
      setLoadingDetails(true);
      const appData = await apiRequest<ApplicationItem>(`/applications/${appId}`);
      setSelectedApplication(appData);

      const docsData = await apiRequest<DocumentItem[]>(`/applications/${appId}/documents-detailed`).catch(() => []);
      setDocuments(docsData);

      if (docsData.length > 0) {
        setSelectedDocId(docsData[0].id);
      } else {
        setSelectedDocId(null);
      }
    } catch (err) {
      console.error("Failed to load application documents", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      fetchSelectedAppDetails(selectedAppId);
    }
  }, [selectedAppId]);

  const handleSelectApplication = (appId: number) => {
    setSelectedAppId(appId);
    // Update URL query param cleanly without full reload
    const url = new URL(window.location.href);
    url.searchParams.set("appId", String(appId));
    window.history.replaceState({}, "", url.toString());
  };

  const handleRetryProcessing = async (docId: number) => {
    try {
      setRetryingDocId(docId);
      await apiRequest(`/documents/${docId}/reprocess`, { method: "POST" });
      if (selectedAppId) {
        await fetchSelectedAppDetails(selectedAppId);
      }
    } catch (err: any) {
      alert(err.message || "Failed to trigger reprocessing");
    } finally {
      setRetryingDocId(null);
    }
  };

  // Filter applications for selector
  const filteredApps = applications.filter((app) => {
    const matchesSearch =
      !search ||
      app.application_no.toLowerCase().includes(search.toLowerCase()) ||
      (app.declared_details?.institution_name || "").toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || app.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const selectedDocument = documents.find((d) => d.id === selectedDocId) || documents[0];

  if (authLoading || (loadingApps && applications.length === 0)) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading Document Verification Portal...
      </div>
    );
  }

  if (isInstitution) {
    return (
      <div className="p-8 bg-white border border-slate-200 rounded-xl text-center space-y-3">
        <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">Official Verification Restricted</h3>
        <p className="text-xs text-slate-600 max-w-md mx-auto">
          The Council Verification Portal is restricted to authorized AICTE Scrutiny Officers and Administrators.
          Institutional applicants may track submission status directly in their applications dashboard.
        </p>
        <Link
          href="/applications"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded-lg text-xs font-semibold"
        >
          <span>Go to My Applications</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <FileCheck2 className="w-6 h-6 text-[#0A4D2E]" />
            <span>Document Verification &amp; Authenticity Portal</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            AI-assisted document scrutiny, simulated statutory registry verifications, and cross-document validation findings.
          </p>
        </div>

        {selectedApplication && (
          <Link
            href={`/applications/${selectedApplication.id}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0A4D2E] hover:bg-[#083D24] text-white font-semibold text-xs rounded-lg shadow-sm transition-colors shrink-0"
          >
            <span>Full Scrutiny Dossier</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>

      {/* Main Layout: Left Application Selector + Right Scrutiny Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Applications Queue Selector (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>Applications Queue</span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px]">
                  {filteredApps.length}
                </span>
              </h3>
              <button
                onClick={fetchApplications}
                title="Refresh Queue"
                className="text-slate-400 hover:text-slate-600 p-1 rounded"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingApps ? "animate-spin" : ""}`} />
              </button>
            </div>

            {/* Quick Filter Inputs */}
            <div className="space-y-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search app no or institute..."
                  className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] bg-white text-slate-700"
              >
                <option value="">All Verification Statuses</option>
                <option value="needs_review">Needs Review</option>
                <option value="under_verification">Under Verification</option>
                <option value="submitted">Submitted</option>
                <option value="draft">Draft</option>
              </select>
            </div>

            {/* Application List */}
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {filteredApps.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400">
                  No applications match filters.
                </div>
              ) : (
                filteredApps.map((app) => {
                  const isSelected = app.id === selectedAppId;
                  const instName =
                    app.declared_details?.institution_name || `Institution #${app.institution_id}`;

                  return (
                    <div
                      key={app.id}
                      onClick={() => handleSelectApplication(app.id)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-[#F0FDF4] border-[#0A4D2E] shadow-sm"
                          : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-mono font-bold text-slate-900">{app.application_no}</span>
                        <StatusChip status={app.status} type="application" size="sm" />
                      </div>

                      <div className="text-[11px] font-semibold text-slate-700 mt-1 line-clamp-1">
                        {instName}
                      </div>

                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                        <span>Risk Band: <strong className={app.risk_band === "High" ? "text-rose-600 font-bold" : app.risk_band === "Medium" ? "text-amber-600 font-bold" : "text-emerald-600 font-bold"}>{app.risk_band}</strong></span>
                        <span className="font-mono">{app.risk_score.toFixed(0)}/100</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Active Inspection Portal (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {!selectedApplication ? (
            <div className="bg-white border border-slate-200 rounded-xl p-16 text-center text-slate-400 text-xs">
              Select an application from the queue to start verification inspection.
            </div>
          ) : (
            <>
              {/* Selected Application Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-slate-900 font-mono">
                        {selectedApplication.application_no}
                      </span>
                      <StatusChip status={selectedApplication.status} type="application" size="sm" />
                    </div>
                    <div className="text-xs text-slate-600 flex items-center gap-1.5 mt-0.5">
                      <Building2 className="w-3.5 h-3.5 text-[#0A4D2E]" />
                      <span className="font-semibold">
                        {selectedApplication.declared_details?.institution_name ||
                          `Institution #${selectedApplication.institution_id}`}
                      </span>
                      <span>&bull;</span>
                      <span>{selectedApplication.type}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                      Priority Scrutiny Score
                    </span>
                    <span
                      className={`inline-block font-mono font-black text-sm px-2.5 py-0.5 rounded mt-0.5 ${
                        selectedApplication.risk_band === "High"
                          ? "bg-rose-100 text-rose-800 border border-rose-200"
                          : selectedApplication.risk_band === "Medium"
                          ? "bg-amber-100 text-amber-800 border border-amber-200"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                      }`}
                    >
                      {selectedApplication.risk_score.toFixed(1)} / 100 ({selectedApplication.risk_band})
                    </span>
                  </div>
                </div>

                {/* Sub-tabs inside Verification Portal */}
                <div className="flex border-b border-slate-200 pt-2 text-xs font-semibold overflow-x-auto gap-2">
                  <button
                    onClick={() => setActiveSubTab("authority")}
                    className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                      activeSubTab === "authority"
                        ? "border-[#0A4D2E] text-[#0A4D2E] font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    <FileCheck2 className="w-3.5 h-3.5" />
                    <span>External Authority Checks</span>
                  </button>

                  <button
                    onClick={() => setActiveSubTab("processing")}
                    className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                      activeSubTab === "processing"
                        ? "border-[#0A4D2E] text-[#0A4D2E] font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>Pipeline Stages ({documents.length})</span>
                  </button>

                  <button
                    onClick={() => setActiveSubTab("extraction")}
                    className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                      activeSubTab === "extraction"
                        ? "border-[#0A4D2E] text-[#0A4D2E] font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Extracted Parameters</span>
                  </button>

                  <button
                    onClick={() => setActiveSubTab("validation")}
                    className={`pb-2.5 px-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                      activeSubTab === "validation"
                        ? "border-[#0A4D2E] text-[#0A4D2E] font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Checklist Validation</span>
                  </button>
                </div>
              </div>

              {/* Sub-tab 1: Authority Verification Checks */}
              {activeSubTab === "authority" && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                  <VerificationView
                    applicationId={selectedApplication.id}
                    documents={documents}
                  />
                </div>
              )}

              {/* Sub-tab 2: Processing Status Pipeline */}
              {activeSubTab === "processing" && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">Uploaded Document Ingestion Pipeline</h3>
                      <p className="text-xs text-slate-500">Live OCR progress and processing state per document slot</p>
                    </div>
                    <button
                      onClick={() => fetchSelectedAppDetails(selectedApplication.id)}
                      className="text-xs font-semibold text-[#0A4D2E] hover:underline flex items-center gap-1"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Refresh Documents</span>
                    </button>
                  </div>

                  {documents.length === 0 ? (
                    <div className="py-12 text-center text-xs text-slate-400">
                      No documents uploaded for this application.
                    </div>
                  ) : (
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
                  )}
                </div>
              )}

              {/* Sub-tab 3: Extracted Information Viewer */}
              {activeSubTab === "extraction" && (
                <div className="space-y-4">
                  {/* Document Selector Pills */}
                  <div className="flex items-center gap-2 overflow-x-auto pb-1">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider pr-1">Slot:</span>
                    {documents.map((doc) => (
                      <button
                        key={doc.id}
                        onClick={() => setSelectedDocId(doc.id)}
                        className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all whitespace-nowrap flex items-center gap-1.5 ${
                          selectedDocId === doc.id
                            ? "bg-[#0A4D2E] text-white border-[#0A4D2E] shadow-sm"
                            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <span>{doc.doc_type.replace(/_/g, " ")}</span>
                        <span className="text-[10px] opacity-80">({doc.extracted_fields?.length || 0})</span>
                      </button>
                    ))}
                  </div>

                  {selectedDocument ? (
                    <ExtractedInfoViewer
                      document={selectedDocument}
                      onFieldUpdated={() => fetchSelectedAppDetails(selectedApplication.id)}
                      onReprocessRequested={() => handleRetryProcessing(selectedDocument.id)}
                    />
                  ) : (
                    <div className="bg-white p-12 text-center rounded-xl border border-slate-200 text-xs text-slate-400">
                      No documents available for field extraction inspection.
                    </div>
                  )}
                </div>
              )}

              {/* Sub-tab 4: Validation Matrix */}
              {activeSubTab === "validation" && (
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                  <ValidationView
                    applicationId={selectedApplication.id}
                    onSelectDocumentForViewer={(docId) => {
                      setSelectedDocId(docId);
                      setActiveSubTab("extraction");
                    }}
                  />
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DocumentVerificationPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
          Loading Verification Portal...
        </div>
      }
    >
      <VerificationContent />
    </Suspense>
  );
}
