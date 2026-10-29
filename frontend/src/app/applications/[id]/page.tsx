"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { ApplicationItem, DocumentItem, FlagItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { ProcessingStatusRow } from "@/features/processing/ProcessingStatusRow";
import { ExtractedInfoViewer } from "@/features/extraction/ExtractedInfoViewer";
import { ValidationView } from "@/features/validation/ValidationView";
import { FraudSignalsView } from "@/features/fraud/FraudSignalsView";
import { VerificationView } from "@/features/verification/VerificationView";
import { ComplianceView } from "@/features/compliance/ComplianceView";
import { ReportView } from "@/features/report/ReportView";
import { ApplicantApplicationView } from "@/features/applications/ApplicantApplicationView";
import { DocumentPreviewModal, PreviewableDocument } from "@/components/ui/DocumentPreviewModal";
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
  Upload,
  FolderOpen,
  Check,
  Cpu,
  Layers,
  Sparkles,
  Gavel,
  Eye,
  Info,
} from "lucide-react";

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, isOfficial, isInstitution, isLoading: authLoading } = useAuth();
  const appId = params.id as string;

  const [application, setApplication] = useState<ApplicationItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [checklist, setChecklist] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<
    "stage1" | "stage2" | "stage3" | "stage4" | "stage5" | "stage6" | "stage7" | "stage8" | "stage9"
  >("stage1");
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [retryingDocId, setRetryingDocId] = useState<number | null>(null);

  // Document Preview Modal state
  const [modalDoc, setModalDoc] = useState<PreviewableDocument | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // Stage 1 Document Upload state
  const [uploadDocType, setUploadDocType] = useState<string>("land_document");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchApplicationDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const appData = await apiRequest<ApplicationItem>(`/applications/${appId}`);
      setApplication(appData);

      // Fetch full document objects with extracted fields
      const docsRes = await apiRequest<DocumentItem[]>(`/applications/${appId}/documents-detailed`).catch(() => []);
      setDocuments(docsRes);
      if (docsRes.length > 0 && !selectedDocId) {
        setSelectedDocId(docsRes[0].id);
      }

      // Fetch validation checklist items
      const valRes = await apiRequest<any>(`/applications/${appId}/validation`).catch(() => null);
      if (valRes && valRes.items) {
        setChecklist(valRes.items);
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

  // Polling: Poll every 3 seconds if processing
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
    }, 3000);

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

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a file to upload.");
      return;
    }

    if (uploadFile.size > 10 * 1024 * 1024) {
      setUploadError("File exceeds the maximum allowable size of 10 MB.");
      return;
    }

    try {
      setUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("doc_type", uploadDocType);

      await apiRequest(`/applications/${appId}/documents`, {
        method: "POST",
        body: formData,
      });

      setUploadSuccess(`Document '${uploadFile.name}' successfully uploaded and queued for pipeline analysis.`);
      setUploadFile(null);
      // Reset file input element
      const fileInput = document.getElementById("doc-file-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";

      await fetchApplicationDetails();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document");
    } finally {
      setUploading(false);
    }
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocId) || documents[0];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading application scrutiny details and linked document dossier...
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 space-y-2 max-w-2xl mx-auto my-12">
        <p className="font-bold flex items-center gap-1.5">
          <AlertCircle className="w-4 h-4" />
          <span>Application Error</span>
        </p>
        <p>{error || "Application not found"}</p>
        <Link href="/applications" className="inline-block mt-2 font-semibold text-[#0A4D2E] hover:underline">
          &larr; Return to Applications Queue
        </Link>
      </div>
    );
  }

  if (isInstitution && application) {
    return (
      <ApplicantApplicationView
        application={application}
        documents={documents}
        checklistItems={checklist}
        onRefresh={fetchApplicationDetails}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / Application Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2.5">
            <Link href="/applications" className="text-slate-400 hover:text-slate-600 transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>{application.application_no}</span>
              <StatusChip status={application.status} type="application" size="sm" />
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-800 flex items-center gap-1">
              <Building className="w-3.5 h-3.5 text-[#0A4D2E]" />
              <span>{application.declared_details?.institution_name || `Institution #${application.institution_id}`}</span>
            </span>
            <span>&bull;</span>
            <span>{application.type} ({application.academic_year})</span>
            <span>&bull;</span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Created {new Date(application.created_at).toLocaleDateString()}</span>
            </span>
            <span>&bull;</span>
            <span className="font-mono text-slate-600 font-semibold">{documents.length} Linked Files</span>
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
              <span className="text-xs font-bold text-slate-700">{application.risk_band} Priority</span>
            </div>
          </div>

          <button
            onClick={() => setActiveTab("stage8")}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs transition-colors flex items-center gap-1.5 shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Dossier</span>
          </button>
        </div>
      </div>

      {/* 9-Stage Horizontal Tabs Navigation */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <div className="flex border-b border-slate-200 min-w-max text-xs font-semibold">
          <button
            onClick={() => setActiveTab("stage1")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage1"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FolderOpen className="w-4 h-4 text-[#0A4D2E]" />
            <span>Stage 1: Documents &amp; Upload</span>
          </button>

          <button
            onClick={() => setActiveTab("stage2")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage2"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Clock className="w-4 h-4 text-slate-500" />
            <span>Stage 2: OCR Processing</span>
          </button>

          <button
            onClick={() => setActiveTab("stage3")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage3"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileText className="w-4 h-4 text-[#0A4D2E]" />
            <span>Stage 3: Extracted Info</span>
          </button>

          <button
            onClick={() => setActiveTab("stage4")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage4"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Stage 4: Validation</span>
          </button>

          <button
            onClick={() => setActiveTab("stage5")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage5"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>Stage 5: Forensics &amp; Fraud</span>
          </button>

          <button
            onClick={() => setActiveTab("stage6")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage6"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileCheck2 className="w-4 h-4 text-[#0A4D2E]" />
            <span>Stage 6: Authenticity</span>
          </button>

          <button
            onClick={() => setActiveTab("stage7")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage7"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Scale className="w-4 h-4 text-[#0A4D2E]" />
            <span>Stage 7: Compliance</span>
          </button>

          <button
            onClick={() => setActiveTab("stage8")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage8"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <FileBadge className="w-4 h-4 text-slate-700" />
            <span>Stage 8: Scrutiny Dossier</span>
          </button>

          <button
            onClick={() => setActiveTab("stage9")}
            className={`px-4 py-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "stage9"
                ? "border-[#0A4D2E] text-[#0A4D2E] bg-[#F0FDF4]/70 font-bold"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            <Gavel className="w-4 h-4 text-[#0A4D2E]" />
            <span>Stage 9: Official Decision</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* STAGE 1: APPLICATION CREATION, CHECKLIST & DOCUMENT UPLOAD */}
      {/* ========================================================================= */}
      {activeTab === "stage1" && (
        <div className="space-y-6">
          {/* Declared Parameters Grid */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#0A4D2E]" />
              <span>Declared Institutional Parameters</span>
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Institution Name</span>
                <span className="font-bold text-slate-800">{application.declared_details?.institution_name || "—"}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Sponsoring Trust</span>
                <span className="font-bold text-slate-800">{application.declared_details?.trust_name || "—"}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Survey / Plot No.</span>
                <span className="font-bold text-slate-800">{application.declared_details?.survey_no || "—"}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Land Area Declared</span>
                <span className="font-bold text-slate-800">
                  {application.declared_details?.land_area_acres ? `${application.declared_details.land_area_acres} Acres` : "—"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Built-Up Area</span>
                <span className="font-bold text-slate-800">
                  {application.declared_details?.built_up_area_sqm ? `${application.declared_details.built_up_area_sqm} sq.m` : "—"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Academic Program</span>
                <span className="font-bold text-slate-800">{application.declared_details?.program || "Engineering"}</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Student Capacity</span>
                <span className="font-bold text-slate-800">{application.declared_details?.student_enrollment || "240"} Seats</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-400 block font-medium">Faculty Members</span>
                <span className="font-bold text-slate-800">{application.declared_details?.faculty_count || "50"} Appointed</span>
              </div>
            </div>
          </div>

          {/* Statutory Checklist Table */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Mandatory Statutory Document Checklist</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-bold tracking-wider">
                  <tr>
                    <th className="p-3">Required Document</th>
                    <th className="p-3">Mandatory</th>
                    <th className="p-3">Upload Status</th>
                    <th className="p-3">Linked Filename</th>
                    <th className="p-3">Validation</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {checklist.length > 0 ? (
                    checklist.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                        <td className="p-3">
                          <p className="font-bold text-slate-900 capitalize">{item.doc_type.replace(/_/g, " ")}</p>
                          <p className="text-[11px] text-slate-500">{item.description}</p>
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              item.mandatory
                                ? "bg-red-50 text-red-700 border border-red-200"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {item.mandatory ? "Mandatory" : "Optional"}
                          </span>
                        </td>
                        <td className="p-3">
                          {item.is_uploaded ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Uploaded</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-amber-700 font-semibold text-[11px]">
                              <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                              <span>Missing</span>
                            </span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-slate-700 text-[11px]">
                          {item.original_filename || "—"}
                        </td>
                        <td className="p-3">
                          <StatusChip status={item.validation_status} size="sm" />
                        </td>
                        <td className="p-3 text-right">
                          {item.document_id ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                type="button"
                                onClick={() => {
                                  const doc = documents.find((d) => d.id === item.document_id);
                                  if (doc) {
                                    setModalDoc(doc);
                                    setIsModalOpen(true);
                                  }
                                }}
                                className="px-2 py-1 text-slate-700 bg-slate-100 hover:bg-slate-200 font-semibold rounded text-[11px] transition-colors inline-flex items-center gap-1"
                              >
                                <Eye className="w-3 h-3 text-slate-500" />
                                <span>Preview</span>
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedDocId(item.document_id);
                                  setActiveTab("stage3");
                                }}
                                className="px-2.5 py-1 text-[#0A4D2E] hover:text-[#083D24] hover:bg-[#F0FDF4] font-semibold rounded text-[11px] transition-colors"
                              >
                                Inspect Field Data &rarr;
                              </button>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Not available</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-slate-400">
                        Checklist records loading or not configured for this application type.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Official Scrutiny Guidance: Institutional Document Custody */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-start gap-3">
            <Info className="w-5 h-5 text-[#0A4D2E] mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-bold text-slate-800 mb-0.5">Applicant Document Custody & Integrity Policy</p>
              <p className="leading-relaxed">
                In strict accordance with AICTE regulatory guidelines, official council scrutiny officers do not upload or replace institutional documents. All statutory uploads and deficiency rectifications are submitted exclusively by the applicant institution through their authenticated Applicant Portal.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STAGE 2: OCR & PIPELINE PROCESSING */}
      {/* ========================================================================= */}
      {activeTab === "stage2" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Document Processing &amp; OCR Telemetry</h3>
              <p className="text-xs text-slate-500">
                Native text layer extraction active. Graceful OCR degradation engine active for scanned pages.
              </p>
            </div>
            <button
              onClick={fetchApplicationDetails}
              className="text-xs font-semibold text-[#0A4D2E] hover:underline flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Poll Status</span>
            </button>
          </div>

          {documents.length > 0 ? (
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
          ) : (
            <div className="bg-white p-12 text-center rounded-xl border border-slate-200 text-xs text-slate-400">
              No documents have been uploaded to this application yet.
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STAGE 3: EXTRACTED INFORMATION (VIEWER + BBOXES + OFFICIAL EDIT) */}
      {/* ========================================================================= */}
      {activeTab === "stage3" && (
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

      {/* ========================================================================= */}
      {/* STAGE 4: DOCUMENT VALIDATION MATRIX */}
      {/* ========================================================================= */}
      {activeTab === "stage4" && (
        <ValidationView
          applicationId={application.id}
          onSelectDocumentForViewer={(docId) => {
            setSelectedDocId(docId);
            setActiveTab("stage3");
          }}
        />
      )}

      {/* ========================================================================= */}
      {/* STAGE 5: FRAUD & FORENSICS SIGNALS */}
      {/* ========================================================================= */}
      {activeTab === "stage5" && (
        <FraudSignalsView
          applicationId={application.id}
          documents={documents}
        />
      )}

      {/* ========================================================================= */}
      {/* STAGE 6: AUTHENTICITY VERIFICATION */}
      {/* ========================================================================= */}
      {activeTab === "stage6" && (
        <VerificationView
          applicationId={application.id}
          documents={documents}
        />
      )}

      {/* ========================================================================= */}
      {/* STAGE 7: REGULATORY COMPLIANCE */}
      {/* ========================================================================= */}
      {activeTab === "stage7" && (
        <ComplianceView
          applicationId={application.id}
        />
      )}

      {/* ========================================================================= */}
      {/* STAGE 8: SCRUTINY COMMITTEE DOSSIER */}
      {/* ========================================================================= */}
      {activeTab === "stage8" && (
        <ReportView
          application={application}
          onApplicationUpdated={fetchApplicationDetails}
          stage="stage8"
          onNavigateToStage9={() => setActiveTab("stage9")}
        />
      )}

      {/* ========================================================================= */}
      {/* STAGE 9: OFFICIAL DECISION & STATUTORY NOTICE ISSUANCE */}
      {/* ========================================================================= */}
      {activeTab === "stage9" && (
        <ReportView
          application={application}
          onApplicationUpdated={fetchApplicationDetails}
          stage="stage9"
          onNavigateToStage8={() => setActiveTab("stage8")}
        />
      )}

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        document={modalDoc}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
