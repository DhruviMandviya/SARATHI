"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { ChecklistItem, ApplicationItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import {
  FilePlus,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Building,
  ArrowRight,
  ArrowLeft,
  Trash2,
  Send,
  ShieldCheck,
  AlertCircle,
  Clock,
  Sparkles,
} from "lucide-react";

interface ChecklistStatusResponse {
  application_id: number;
  can_submit: boolean;
  missing_mandatory: string[];
  items: {
    checklist_item_id: number;
    doc_type: string;
    description: string;
    mandatory: boolean;
    validity_required: boolean;
    is_uploaded: boolean;
    document_id: number | null;
    original_filename: string | null;
    validation_status: string;
    processing_status: string | null;
    processing_stage: string | null;
  }[];
}

export default function NewApplicationPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1: Declared Details Form State
  const [formData, setFormData] = useState({
    institution_name: "Apex Institute of Technology",
    trust_name: "Apex Education Trust",
    address: "Sector 14, Plot 8, Kharghar, Navi Mumbai",
    state: "Maharashtra",
    land_area_acres: 3.25,
    built_up_area_sqm: 4500.0,
    student_intake: 300,
    faculty_count: 20,
    student_faculty_ratio: 15.0,
    labs_count: 12,
    ews_quota_percentage: 10.0,
    corpus_fund_lakhs: 150.0,
    affidavit_stamp_value_inr: 100.0,
  });

  const [application, setApplication] = useState<ApplicationItem | null>(null);
  const [checklist, setChecklist] = useState<ChecklistStatusResponse | null>(null);
  const [selectedDocType, setSelectedDocType] = useState<string>("land_document");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Step 1 Submit: Create Application draft
  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const app = await apiRequest<ApplicationItem>("/applications", {
        method: "POST",
        body: JSON.stringify({
          type: "New Technical Institution",
          academic_year: "2026-2027",
          declared_details: formData,
        }),
      });
      setApplication(app);
      await fetchChecklist(app.id);
      setStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to create application draft");
    }
  };

  // Fetch checklist status
  const fetchChecklist = async (appId: number) => {
    try {
      const data = await apiRequest<ChecklistStatusResponse>(`/applications/${appId}/checklist`);
      setChecklist(data);
    } catch (err: any) {
      console.error("Error fetching checklist:", err);
    }
  };

  // Step 2: Upload document
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!application || !selectedFile) {
      setError("Please select a file to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const data = new FormData();
      data.append("file", selectedFile);
      data.append("doc_type", selectedDocType);

      await apiRequest(`/applications/${application.id}/documents`, {
        method: "POST",
        body: data,
      });

      setSuccessMsg(`Uploaded ${selectedFile.name} successfully.`);
      setSelectedFile(null);
      await fetchChecklist(application.id);
    } catch (err: any) {
      setError(err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  };

  // Delete draft document
  const handleDeleteDoc = async (docId: number) => {
    if (!confirm("Are you sure you want to remove this document?")) return;
    try {
      await apiRequest(`/documents/${docId}`, { method: "DELETE" });
      if (application) await fetchChecklist(application.id);
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    }
  };

  // Step 3: Final Submission
  const handleSubmitApplication = async () => {
    if (!application) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest(`/applications/${application.id}/submit`, { method: "POST" });
      alert("Application submitted successfully! Your application is now queued for AICTE automated scrutiny.");
      router.push(`/applications/${application.id}`);
    } catch (err: any) {
      setError(err.message || "Submission failed. Please check mandatory checklist documents.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Stepper Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <FilePlus className="w-5 h-5 text-blue-600" />
              <span>New Institution Approval Application</span>
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Academic Year 2026-2027 &bull; Approval Process Handbook Guidelines
            </p>
          </div>
          {application && (
            <div className="text-right">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Draft No</span>
              <span className="text-sm font-bold text-blue-700">{application.application_no}</span>
            </div>
          )}
        </div>

        {/* 3-Step Indicator */}
        <div className="grid grid-cols-3 gap-3 mt-6 pt-5 border-t border-slate-100 text-xs">
          <div
            className={`flex items-center gap-2.5 p-2.5 rounded-lg border transition-all ${
              step === 1
                ? "bg-blue-50 border-blue-300 text-blue-800 font-bold"
                : step > 1
                ? "bg-slate-50 border-slate-200 text-emerald-700 font-semibold"
                : "border-slate-100 text-slate-400"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                step > 1 ? "bg-emerald-600 text-white" : step === 1 ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"
              }`}
            >
              1
            </div>
            <span>1. Declared Details</span>
          </div>

          <div
            className={`flex items-center gap-2.5 p-2.5 rounded-lg border transition-all ${
              step === 2
                ? "bg-blue-50 border-blue-300 text-blue-800 font-bold"
                : step > 2
                ? "bg-slate-50 border-slate-200 text-emerald-700 font-semibold"
                : "border-slate-100 text-slate-400"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                step > 2 ? "bg-emerald-600 text-white" : step === 2 ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"
              }`}
            >
              2
            </div>
            <span>2. Uploads & Checklist</span>
          </div>

          <div
            className={`flex items-center gap-2.5 p-2.5 rounded-lg border transition-all ${
              step === 3
                ? "bg-blue-50 border-blue-300 text-blue-800 font-bold"
                : "border-slate-100 text-slate-400"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                step === 3 ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-600"
              }`}
            >
              3
            </div>
            <span>3. Review & Submit</span>
          </div>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-xs text-red-700 shadow-sm">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Submission Notice</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* STEP 1: DECLARED DETAILS FORM */}
      {step === 1 && (
        <form onSubmit={handleCreateDraft} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-800">Institution Information & Parameter Declarations</h3>
            <p className="text-xs text-slate-500">
              Values declared here will be cross-checked against supporting certificates and AICTE compliance norms.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Institution Name</label>
              <input
                type="text"
                required
                value={formData.institution_name}
                onChange={(e) => setFormData({ ...formData, institution_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Promoting Trust / Society Name</label>
              <input
                type="text"
                required
                value={formData.trust_name}
                onChange={(e) => setFormData({ ...formData, trust_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block font-semibold text-slate-700 mb-1">Campus Address</label>
              <input
                type="text"
                required
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">State / UT</label>
              <input
                type="text"
                required
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Campus Land Area (in Acres)</label>
              <input
                type="number"
                step="0.01"
                required
                value={formData.land_area_acres}
                onChange={(e) => setFormData({ ...formData, land_area_acres: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Total Built-up Area (in Sq. Meters)</label>
              <input
                type="number"
                step="0.1"
                required
                value={formData.built_up_area_sqm}
                onChange={(e) => setFormData({ ...formData, built_up_area_sqm: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Total Approved Student Intake</label>
              <input
                type="number"
                required
                value={formData.student_intake}
                onChange={(e) => setFormData({ ...formData, student_intake: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Total Regular Faculty Count</label>
              <input
                type="number"
                required
                value={formData.faculty_count}
                onChange={(e) => {
                  const fc = parseInt(e.target.value) || 1;
                  const ratio = parseFloat((formData.student_intake / fc).toFixed(2));
                  setFormData({ ...formData, faculty_count: fc, student_faculty_ratio: ratio });
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Core Laboratories Count</label>
              <input
                type="number"
                required
                value={formData.labs_count}
                onChange={(e) => setFormData({ ...formData, labs_count: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">EWS Supernumerary Quota (%)</label>
              <input
                type="number"
                step="0.1"
                required
                value={formData.ews_quota_percentage}
                onChange={(e) => setFormData({ ...formData, ews_quota_percentage: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Joint Fixed Deposit Reserve (Lakhs INR)</label>
              <input
                type="number"
                step="0.1"
                required
                value={formData.corpus_fund_lakhs}
                onChange={(e) => setFormData({ ...formData, corpus_fund_lakhs: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Affidavit Stamp Paper Value (INR)</label>
              <input
                type="number"
                required
                value={formData.affidavit_stamp_value_inr}
                onChange={(e) => setFormData({ ...formData, affidavit_stamp_value_inr: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button
              type="submit"
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs shadow-sm flex items-center gap-2"
            >
              <span>Save & Proceed to Uploads</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      )}

      {/* STEP 2: UPLOADS & CHECKLIST */}
      {step === 2 && (
        <div className="space-y-6">
          {/* Upload Dropzone Form */}
          <form onSubmit={handleUpload} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800">Upload Supporting Document</h3>
                <p className="text-xs text-slate-500">Formats: PDF, JPG, PNG &bull; Max size: 10MB per file</p>
              </div>
              <span className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 font-semibold rounded-md border border-blue-200">
                Magic byte inspection active
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Checklist Category</label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="land_document">Land Ownership / Title Deed</option>
                  <option value="building_plan">Sanctioned Building Plan</option>
                  <option value="fire_noc">Fire Safety Certificate (NOC)</option>
                  <option value="society_registration">Society / Trust Registration</option>
                  <option value="affidavit">AICTE Prescribed Affidavit</option>
                  <option value="env_clearance">Environmental Clearance (Optional)</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select File</label>
                <div className="flex items-center gap-3">
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                  />
                  <button
                    type="submit"
                    disabled={uploading || !selectedFile}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs shadow-sm transition-colors disabled:opacity-50 flex items-center gap-1.5 shrink-0"
                  >
                    <UploadCloud className="w-4 h-4" />
                    <span>{uploading ? "Verifying & Uploading..." : "Upload Document"}</span>
                  </button>
                </div>
              </div>
            </div>

            {successMsg && (
              <p className="text-xs font-semibold text-emerald-700 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                {successMsg}
              </p>
            )}
          </form>

          {/* Checklist Status Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Required Document Checklist</h4>
                <p className="text-[11px] text-slate-500">Green = Uploaded &bull; Red = Mandatory Missing &bull; Amber = Optional/Incomplete</p>
              </div>
              <span
                className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                  checklist?.can_submit
                    ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                    : "bg-red-50 text-red-700 border-red-300"
                }`}
              >
                {checklist?.can_submit ? "Mandatory Checklist Complete" : `${checklist?.missing_mandatory.length || 0} Mandatory Item(s) Pending`}
              </span>
            </div>

            <div className="divide-y divide-slate-100 text-xs">
              {checklist?.items.map((item) => (
                <div key={item.doc_type} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {item.is_uploaded ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : item.mandatory ? (
                        <XCircle className="w-5 h-5 text-red-500" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                      )}
                    </div>
                    <div>
                      <div className="font-bold text-slate-800 flex items-center gap-2">
                        <span>{item.description}</span>
                        {item.mandatory ? (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">Mandatory</span>
                        ) : (
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">Optional</span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        {item.is_uploaded ? (
                          <span className="text-emerald-700 font-medium">Uploaded: {item.original_filename}</span>
                        ) : (
                          <span>Document not yet uploaded</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusChip status={item.validation_status} type="document" size="sm" />
                    {item.is_uploaded && item.document_id && (
                      <button
                        onClick={() => handleDeleteDoc(item.document_id!)}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Remove file"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stepper Navigation */}
          <div className="flex justify-between items-center pt-2">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Details</span>
            </button>

            <button
              onClick={() => setStep(3)}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg text-xs shadow-sm flex items-center gap-2"
            >
              <span>Proceed to Pre-Check</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: PRE-CHECK & FINAL SUBMISSION */}
      {step === 3 && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-800">Pre-Submission Verification Summary</h3>
            <p className="text-xs text-slate-500">
              Verify your declared metrics and uploaded documents before committing the submission.
            </p>
          </div>

          {/* Summary Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div>
              <span className="text-[11px] text-slate-400 block font-medium">Campus Land Area</span>
              <span className="font-bold text-slate-800 text-sm">{formData.land_area_acres} Acres</span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block font-medium">Built-Up Area</span>
              <span className="font-bold text-slate-800 text-sm">{formData.built_up_area_sqm} sq.m</span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block font-medium">Student-Faculty Ratio</span>
              <span className="font-bold text-slate-800 text-sm">1:{formData.student_faculty_ratio}</span>
            </div>
            <div>
              <span className="text-[11px] text-slate-400 block font-medium">Corpus Fund Reserve</span>
              <span className="font-bold text-slate-800 text-sm">₹{formData.corpus_fund_lakhs} Lakhs</span>
            </div>
          </div>

          {/* Submission Readiness Box */}
          <div
            className={`p-4 rounded-xl border flex items-start gap-3 text-xs ${
              checklist?.can_submit
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : "bg-amber-50 border-amber-200 text-amber-800"
            }`}
          >
            {checklist?.can_submit ? (
              <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            )}
            <div>
              <p className="font-bold">
                {checklist?.can_submit
                  ? "Application Ready for Official Submission"
                  : "Submission Blocked: Mandatory Documents Incomplete"}
              </p>
              <p className="mt-0.5">
                {checklist?.can_submit
                  ? "All mandatory statutory documents have been uploaded and passed integrity verification. Submitting will launch the 9-stage automated AICTE scrutiny pipeline."
                  : `Please upload the remaining mandatory documents: ${checklist?.missing_mandatory.join(", ")}`}
              </p>
            </div>
          </div>

          <div className="flex justify-between items-center pt-4 border-t border-slate-100">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Uploads</span>
            </button>

            <button
              onClick={handleSubmitApplication}
              disabled={submitting || !checklist?.can_submit}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs shadow-md transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
              <span>{submitting ? "Submitting Application..." : "Submit Application for Scrutiny"}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
