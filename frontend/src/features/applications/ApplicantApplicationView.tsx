"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ApplicationItem, DocumentItem } from "@/lib/types";
import { apiRequest, getApiBase } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { StatusChip } from "@/components/ui/StatusChip";
import { DocumentPreviewModal, PreviewableDocument } from "@/components/ui/DocumentPreviewModal";
import {
  Building2,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  Eye,
  Trash2,
  AlertTriangle,
  Download,
  ExternalLink,
  Edit2,
  Check,
  X,
  RefreshCw,
  FilePlus,
  ShieldAlert,
  ArrowRight,
  Stamp,
} from "lucide-react";

interface ApplicantApplicationViewProps {
  application: ApplicationItem;
  documents: DocumentItem[];
  checklistItems: any[];
  onRefresh: () => void;
}

export function ApplicantApplicationView({
  application,
  documents,
  checklistItems,
  onRefresh,
}: ApplicantApplicationViewProps) {
  const { token } = useAuth();

  // Preview Modal state
  const [previewDoc, setPreviewDoc] = useState<PreviewableDocument | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState<boolean>(false);

  // Per-slot upload state
  const [uploadingSlot, setUploadingSlot] = useState<string | null>(null);
  const [slotErrors, setSlotErrors] = useState<Record<string, string>>({});
  const [slotSuccess, setSlotSuccess] = useState<Record<string, string>>({});

  // Edit Declared Details state
  const [isEditingDetails, setIsEditingDetails] = useState<boolean>(false);
  const [detailsForm, setDetailsForm] = useState<Record<string, any>>({});
  const [savingDetails, setSavingDetails] = useState<boolean>(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [detailsSuccess, setDetailsSuccess] = useState<string | null>(null);

  // Submission state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Deficiency & Decision state
  const [deficiencyLetter, setDeficiencyLetter] = useState<any>(null);
  const [decision, setDecision] = useState<any>(null);
  const [loadingExtras, setLoadingExtras] = useState<boolean>(true);

  const isEditable = application.status === "draft" || application.status === "info_requested";
  const isDraft = application.status === "draft";
  const isInfoRequested = application.status === "info_requested";

  const resetDetailsForm = () => {
    if (application.declared_details) {
      setDetailsForm({
        institution_name: application.declared_details.institution_name || "",
        trust_name: application.declared_details.trust_name || "",
        address: application.declared_details.address || "",
        state: application.declared_details.state || "",
        land_area_acres: application.declared_details.land_area_acres ?? "",
        built_up_area_sqm: application.declared_details.built_up_area_sqm ?? "",
        student_intake: application.declared_details.student_intake ?? "",
        faculty_count: application.declared_details.faculty_count ?? "",
        student_faculty_ratio: application.declared_details.student_faculty_ratio ?? "",
        labs_count: application.declared_details.labs_count ?? "",
        ews_quota_percentage: application.declared_details.ews_quota_percentage ?? "",
        corpus_fund_lakhs: application.declared_details.corpus_fund_lakhs ?? "",
        affidavit_stamp_value_inr: application.declared_details.affidavit_stamp_value_inr ?? "",
      });
    }
  };

  // Re-sync details form whenever application changes
  useEffect(() => {
    resetDetailsForm();
  }, [application]);

  useEffect(() => {
    async function loadExtras() {
      try {
        setLoadingExtras(true);
        const [letterData, decisionData] = await Promise.all([
          apiRequest<any>(`/applications/${application.id}/deficiency-letter`).catch(() => null),
          apiRequest<any>(`/applications/${application.id}/decision`).catch(() => null),
        ]);
        setDeficiencyLetter(letterData);
        setDecision(decisionData);
      } catch (err) {
        console.error("Failed to load letter or decision", err);
      } finally {
        setLoadingExtras(false);
      }
    }
    loadExtras();
  }, [application.id, application.status]);

  const handleOpenPreview = (doc: PreviewableDocument) => {
    setPreviewDoc(doc);
    setIsPreviewOpen(true);
  };

  // Inline upload or replace per document slot
  const handleSlotFileUpload = async (docType: string, file: File) => {
    if (!file) return;

    try {
      setUploadingSlot(docType);
      setSlotErrors((prev) => ({ ...prev, [docType]: "" }));
      setSlotSuccess((prev) => ({ ...prev, [docType]: "" }));

      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", docType);

      await apiRequest(`/applications/${application.id}/documents`, {
        method: "POST",
        body: formData,
      });

      setSlotSuccess((prev) => ({ ...prev, [docType]: `Uploaded ${file.name} successfully.` }));
      onRefresh();

      setTimeout(() => {
        setSlotSuccess((prev) => ({ ...prev, [docType]: "" }));
      }, 4000);
    } catch (err: any) {
      setSlotErrors((prev) => ({ ...prev, [docType]: err.message || "Failed to upload document" }));
    } finally {
      setUploadingSlot(null);
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm("Are you sure you want to remove this document from the draft?")) {
      return;
    }
    try {
      await apiRequest(`/documents/${docId}`, { method: "DELETE" });
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    }
  };

  const handleSaveDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    setDetailsError(null);
    setDetailsSuccess(null);

    // Validate positive numbers
    const land = parseFloat(detailsForm.land_area_acres);
    const builtUp = parseFloat(detailsForm.built_up_area_sqm);
    const intake = parseInt(detailsForm.student_intake);
    const faculty = parseInt(detailsForm.faculty_count);

    if (isNaN(land) || land <= 0) {
      setDetailsError("Campus land area must be a valid positive number.");
      return;
    }
    if (isNaN(builtUp) || builtUp <= 0) {
      setDetailsError("Total built-up area must be a valid positive number.");
      return;
    }
    if (isNaN(intake) || intake <= 0) {
      setDetailsError("Student intake capacity must be a positive integer.");
      return;
    }
    if (isNaN(faculty) || faculty <= 0) {
      setDetailsError("Regular faculty count must be at least 1.");
      return;
    }

    try {
      setSavingDetails(true);
      const payload = {
        ...detailsForm,
        land_area_acres: land,
        built_up_area_sqm: builtUp,
        student_intake: intake,
        faculty_count: faculty,
        student_faculty_ratio: parseFloat((intake / faculty).toFixed(2)),
        labs_count: parseInt(detailsForm.labs_count) || 0,
        ews_quota_percentage: parseFloat(detailsForm.ews_quota_percentage) || 0,
        corpus_fund_lakhs: parseFloat(detailsForm.corpus_fund_lakhs) || 0,
        affidavit_stamp_value_inr: parseFloat(detailsForm.affidavit_stamp_value_inr) || 0,
      };

      await apiRequest(`/applications/${application.id}/declared-details`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      setDetailsSuccess("Institution declared parameters successfully saved and recorded in audit trail.");
      onRefresh();
      setTimeout(() => {
        setIsEditingDetails(false);
        setDetailsSuccess(null);
      }, 1500);
    } catch (err: any) {
      setDetailsError(err.message || "Failed to update declared details");
    } finally {
      setSavingDetails(false);
    }
  };

  const handleSubmitApplication = async () => {
    if (!confirm("Are you ready to submit your application for AICTE scrutiny review? Once submitted, documents cannot be altered unless information is formally requested.")) {
      return;
    }
    try {
      setSubmitting(true);
      setSubmitError(null);
      await apiRequest(`/applications/${application.id}/submit`, {
        method: "POST",
      });
      onRefresh();
    } catch (err: any) {
      setSubmitError(err.message || "Failed to submit application");
    } finally {
      setSubmitting(false);
    }
  };

  // Milestone Progress Steps
  const milestones = [
    { id: "draft", label: "Draft" },
    { id: "submitted", label: "Submitted" },
    { id: "under_verification", label: "Under Review" },
    { id: "info_requested", label: "Info Requested" },
    { id: "decided", label: "Decision Issued" },
  ];

  const getMilestoneIndex = (status: string) => {
    switch (status) {
      case "draft":
        return 0;
      case "submitted":
        return 1;
      case "processing":
      case "under_verification":
      case "needs_review":
        return 2;
      case "info_requested":
        return 3;
      case "approved":
      case "rejected":
        return 4;
      default:
        return 1;
    }
  };

  const currentMilestoneIdx = getMilestoneIndex(application.status);

  // Group active documents
  const activeDocsByType = documents.reduce((acc, d) => {
    if (!d.superseded_by) {
      acc[d.doc_type] = d;
    }
    return acc;
  }, {} as Record<string, DocumentItem>);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Application Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">
              {application.type}
            </span>
            <span className="text-xs font-mono text-slate-500">
              Academic Year: {application.academic_year}
            </span>
            <StatusChip status={application.status} size="md" />
          </div>

          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2 pt-1">
            <Building2 className="w-5 h-5 text-[#0A4D2E]" />
            <span>Application #{application.application_no}</span>
          </h1>
          <p className="text-xs text-slate-500">
            {application.declared_details?.institution_name || "Applicant Technical Campus"}
            {application.submitted_at && ` • Submitted on ${new Date(application.submitted_at).toLocaleDateString()}`}
          </p>
        </div>

        {/* Header Action Button */}
        <div className="flex items-center gap-3 shrink-0">
          {isDraft && (
            <button
              onClick={handleSubmitApplication}
              disabled={submitting}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0A4D2E] hover:bg-[#083D24] text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{submitting ? "Submitting..." : "Submit Application"}</span>
            </button>
          )}

          {isInfoRequested && (
            <button
              onClick={handleSubmitApplication}
              disabled={submitting}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
              <span>{submitting ? "Resubmitting..." : "Resubmit Response"}</span>
            </button>
          )}

          <a
            href={`${getApiBase()}/applications/${application.id}/report.pdf${token ? `?token=${encodeURIComponent(token)}` : ""}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200 transition-colors"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Download Dossier PDF</span>
          </a>
        </div>
      </div>

      {submitError && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* 2. Milestone Progress Tracker */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
          Application Lifecycle &amp; Scrutiny Milestone
        </h4>
        <div className="grid grid-cols-5 gap-2 relative">
          {milestones.map((step, idx) => {
            const isCompleted = idx < currentMilestoneIdx;
            const isCurrent = idx === currentMilestoneIdx;
            const isFuture = idx > currentMilestoneIdx;

            return (
              <div key={step.id} className="flex flex-col items-center text-center relative">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs mb-2 transition-all ${
                    isCurrent
                      ? "bg-[#0A4D2E] text-white ring-4 ring-[#F0FDF4] shadow-sm"
                      : isCompleted
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-100 text-slate-400 border border-slate-200"
                  }`}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : idx + 1}
                </div>
                <span
                  className={`text-xs font-medium ${
                    isCurrent
                      ? "text-[#0A4D2E] font-bold"
                      : isCompleted
                      ? "text-slate-800"
                      : "text-slate-400"
                  }`}
                >
                  {step.label}
                </span>
                {isCurrent && (
                  <span className="text-[10px] text-[#0A4D2E] font-semibold mt-0.5">
                    Current Stage
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Official Deficiency Notice Banner (if information requested) */}
      {isInfoRequested && deficiencyLetter && (
        <div className="bg-amber-50 border-2 border-amber-400 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-amber-200/60 rounded-xl text-amber-900 shrink-0 mt-0.5">
                <ShieldAlert className="w-6 h-6 text-amber-700" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-bold text-amber-950 uppercase tracking-wide">
                    Formal Deficiency Notice
                  </h3>
                  <span className="font-mono text-xs font-bold text-amber-900 bg-amber-200/70 px-2 py-0.5 rounded border border-amber-300">
                    {deficiencyLetter.reference_no}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 font-bold uppercase">
                    Action Required
                  </span>
                </div>
                <p className="text-xs text-amber-900 mt-1 leading-relaxed">
                  The AICTE Scrutiny Committee has reviewed your application and issued a statutory deficiency notice. You must submit your explanations and cured document attachments on or before <strong>{deficiencyLetter.cure_deadline}</strong>.
                </p>
              </div>
            </div>

            <Link
              href={`/information-requests/${deficiencyLetter.id || deficiencyLetter.request_id || 1}`}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors shrink-0"
            >
              <span>Open Response Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="bg-white p-4 rounded-xl border border-amber-200 text-xs font-mono text-slate-800 whitespace-pre-wrap max-h-60 overflow-y-auto shadow-inner leading-relaxed">
            {deficiencyLetter.letter_text || "Deficiency notice text loading..."}
          </div>
        </div>
      )}

      {/* 4. Formal Decision Notice (if decided) */}
      {decision && (
        <div className={`rounded-2xl p-6 border shadow-sm space-y-3 ${
          decision.outcome === "approved"
            ? "bg-emerald-50/70 border-emerald-300 text-emerald-950"
            : "bg-rose-50/70 border-rose-300 text-rose-950"
        }`}>
          <div className="flex items-center gap-3">
            <Stamp className={`w-7 h-7 ${decision.outcome === "approved" ? "text-emerald-700" : "text-rose-700"}`} />
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wide">
                Official AICTE Determination: {decision.outcome.toUpperCase()}
              </h3>
              <p className="text-xs opacity-80">
                Recorded on {new Date(decision.decided_at).toLocaleString()} by Council Scrutiny Committee
              </p>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 text-xs text-slate-800 space-y-1">
            <span className="font-bold text-slate-700 block text-[11px] uppercase tracking-wider">
              Committee Determination Remarks:
            </span>
            <p className="leading-relaxed">{decision.remarks}</p>
          </div>
        </div>
      )}

      {/* 5. Declared Institutional Information Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#0A4D2E]" />
              <span>Institution Declared Parameters</span>
            </h3>
            <p className="text-xs text-slate-400">Parameters declared by the institution for statutory verification</p>
          </div>
          {isEditable && (
            <button
              onClick={() => {
                if (isEditingDetails) {
                  resetDetailsForm();
                }
                setIsEditingDetails(!isEditingDetails);
                setDetailsError(null);
                setDetailsSuccess(null);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-[#0A4D2E] bg-[#F0FDF4] hover:bg-emerald-100 transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>{isEditingDetails ? "Cancel" : "Edit Details"}</span>
            </button>
          )}
        </div>

        {detailsSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{detailsSuccess}</span>
          </div>
        )}

        {detailsError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{detailsError}</span>
          </div>
        )}

        {isEditingDetails ? (
          <form onSubmit={handleSaveDetails} className="space-y-4 pt-1">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Institution Legal Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={detailsForm.institution_name || ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, institution_name: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Sponsoring Trust / Society <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={detailsForm.trust_name || ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, trust_name: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Campus Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={detailsForm.address || ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, address: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  State / UT <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={detailsForm.state || ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, state: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Declared Land Area (Acres) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={detailsForm.land_area_acres ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, land_area_acres: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Built-Up Area (sqm) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={detailsForm.built_up_area_sqm ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, built_up_area_sqm: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Approved Student Intake <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={detailsForm.student_intake ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, student_intake: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Regular Faculty Count <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={detailsForm.faculty_count ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, faculty_count: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Core Laboratories Count <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={detailsForm.labs_count ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, labs_count: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  EWS Quota Percentage (%) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={detailsForm.ews_quota_percentage ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, ews_quota_percentage: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Corpus Fund Reserve (Lakhs INR) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  value={detailsForm.corpus_fund_lakhs ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, corpus_fund_lakhs: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Affidavit Stamp Paper Value (INR) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={detailsForm.affidavit_stamp_value_inr ?? ""}
                  onChange={(e) => setDetailsForm({ ...detailsForm, affidavit_stamp_value_inr: e.target.value })}
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] text-slate-900"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  resetDetailsForm();
                  setIsEditingDetails(false);
                  setDetailsError(null);
                }}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingDetails}
                className="px-5 py-2 rounded-lg text-xs font-bold text-white bg-[#0A4D2E] hover:bg-[#083D24] disabled:opacity-50"
              >
                {savingDetails ? "Saving to Database..." : "Save Declared Details"}
              </button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Institution Legal Name</span>
              <span className="font-bold text-slate-800">{application.declared_details?.institution_name || "—"}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Sponsoring Trust</span>
              <span className="font-bold text-slate-800">{application.declared_details?.trust_name || "—"}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Campus Address</span>
              <span className="font-semibold text-slate-800 truncate block" title={application.declared_details?.address || ""}>
                {application.declared_details?.address || "—"}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">State / UT</span>
              <span className="font-semibold text-slate-800">{application.declared_details?.state || "—"}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Land Area Declared</span>
              <span className="font-mono font-bold text-slate-800">
                {application.declared_details?.land_area_acres ? `${application.declared_details.land_area_acres} Acres` : "—"}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Built-Up Area</span>
              <span className="font-mono font-bold text-slate-800">
                {application.declared_details?.built_up_area_sqm ? `${application.declared_details.built_up_area_sqm} sqm` : "—"}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Student Intake</span>
              <span className="font-mono font-bold text-slate-800">
                {application.declared_details?.student_intake ? `${application.declared_details.student_intake} Students` : "—"}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl">
              <span className="text-slate-400 block mb-0.5 font-medium">Faculty (Ratio)</span>
              <span className="font-mono font-bold text-slate-800">
                {application.declared_details?.faculty_count
                  ? `${application.declared_details.faculty_count} (1:${application.declared_details.student_faculty_ratio || "—"})`
                  : "—"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 6. Document Dossier & Checklist Table with Per-Slot Upload/Replace */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Upload className="w-4 h-4 text-[#0A4D2E]" />
              <span>Statutory Document Dossier &amp; Checklist</span>
            </h3>
            <p className="text-xs text-slate-400">
              Upload or replace each statutory document in its designated slot. Each slot operates independently.
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 font-semibold text-slate-700">
            {documents.filter((d) => !d.superseded_by).length} Documents Uploaded
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
                <th className="p-3">Category</th>
                <th className="p-3">Requirement</th>
                <th className="p-3">Upload Status</th>
                <th className="p-3">Attached File &amp; Date</th>
                <th className="p-3">Pages / Size</th>
                <th className="p-3">Validation Status</th>
                <th className="p-3 text-right">Document Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {checklistItems && checklistItems.length > 0 ? (
                checklistItems.map((item) => {
                  const doc = activeDocsByType[item.doc_type];
                  const isUploaded = !!doc;
                  const isSlotUploading = uploadingSlot === item.doc_type;
                  const slotError = slotErrors[item.doc_type];
                  const slotSucc = slotSuccess[item.doc_type];

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="p-3 font-semibold text-slate-900">
                        <div>
                          <span>{item.description || item.doc_type.replace(/_/g, " ")}</span>
                          {slotError && (
                            <p className="text-[11px] text-rose-600 font-medium mt-1">{slotError}</p>
                          )}
                          {slotSucc && (
                            <p className="text-[11px] text-emerald-600 font-medium mt-1">{slotSucc}</p>
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                            item.mandatory
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {item.mandatory ? "Mandatory" : "Optional"}
                        </span>
                      </td>
                      <td className="p-3">
                        {isUploaded ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold text-[11px]">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Uploaded</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-700 font-semibold text-[11px]">
                            <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                            <span>Pending</span>
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-slate-700 text-[11px] max-w-[200px]">
                        {doc ? (
                          <div>
                            <p className="truncate font-semibold text-slate-800" title={doc.original_filename}>
                              {doc.original_filename}
                            </p>
                            <span className="text-[10px] text-slate-400">
                              Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="p-3 text-slate-500 font-mono text-[11px]">
                        {doc ? `${doc.page_count || 1} p • ${(doc.size / 1024).toFixed(0)} KB` : "—"}
                      </td>
                      <td className="p-3">
                        {doc ? (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <StatusChip status={doc.validation_status} type="document" size="sm" />
                            {doc.processing_status && doc.processing_status !== "completed" && (
                              <span className="text-[10px] text-[#0A4D2E] animate-pulse font-mono">
                                ({doc.processing_status})
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Not uploaded</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Hidden file input for this specific document slot */}
                          <input
                            type="file"
                            id={`slot-file-${item.doc_type}`}
                            accept=".pdf,.png,.jpg,.jpeg"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                handleSlotFileUpload(item.doc_type, file);
                              }
                              e.target.value = "";
                            }}
                          />

                          {doc && (
                            <button
                              type="button"
                              onClick={() => handleOpenPreview(doc)}
                              className="px-2.5 py-1 rounded bg-[#F0FDF4] text-[#0A4D2E] hover:bg-emerald-100 font-semibold text-[11px] inline-flex items-center gap-1 transition-colors"
                            >
                              <Eye className="w-3 h-3" />
                              <span>Preview</span>
                            </button>
                          )}

                          {isEditable && (
                            <>
                              <button
                                type="button"
                                disabled={isSlotUploading}
                                onClick={() => {
                                  const el = document.getElementById(`slot-file-${item.doc_type}`);
                                  if (el) el.click();
                                }}
                                className={`px-2.5 py-1 rounded font-semibold text-[11px] inline-flex items-center gap-1 transition-colors ${
                                  doc
                                    ? "bg-amber-50 text-amber-800 hover:bg-amber-100 border border-amber-200"
                                    : "bg-[#0A4D2E] text-white hover:bg-[#083D24] shadow-sm"
                                } disabled:opacity-50`}
                              >
                                {isSlotUploading ? (
                                  <RefreshCw className="w-3 h-3 animate-spin" />
                                ) : (
                                  <Upload className="w-3 h-3" />
                                )}
                                <span>
                                  {isSlotUploading
                                    ? "Uploading..."
                                    : doc
                                    ? "Replace"
                                    : "Upload"}
                                </span>
                              </button>

                              {doc && isDraft && (
                                <button
                                  type="button"
                                  onClick={() => handleDelete(doc.id)}
                                  className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                                  title="Delete document from draft"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </>
                          )}

                          {!isEditable && !doc && (
                            <span className="text-[11px] text-slate-400 italic">Locked</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-slate-400">
                    Checklist records loading...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        document={previewDoc}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
      />
    </div>
  );
}
