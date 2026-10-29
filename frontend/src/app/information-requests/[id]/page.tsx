"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest, getApiBase } from "@/lib/api";
import {
  InformationRequestItem,
  InformationResponseItem,
  ResponseItem,
  DeficiencyRequirement,
} from "@/lib/types";
import {
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Upload,
  Download,
  FileText,
  Send,
  Save,
  Check,
  AlertCircle,
  Building,
  RefreshCw,
  Receipt,
  Eye,
  X,
  History,
} from "lucide-react";

export default function InformationRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reqId = params.id as string;
  const { user, isOfficial, token, isLoading: authLoading } = useAuth();

  const [request, setRequest] = useState<InformationRequestItem | null>(null);
  const [response, setResponse] = useState<InformationResponseItem | null>(null);
  const [responseHistory, setResponseHistory] = useState<InformationResponseItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Per deficiency item response state
  const [responseItems, setResponseItems] = useState<Record<string, ResponseItem>>({});
  const [uploadingSlot, setUploadingSlot] = useState<string | null>(null);
  const [savingDraft, setSavingDraft] = useState<boolean>(false);
  const [submittingResponse, setSubmittingResponse] = useState<boolean>(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);
  const [submissionReceipt, setSubmissionReceipt] = useState<{
    receipt_no: string;
    submitted_at: string;
    items_count: number;
  } | null>(null);

  // Official review state
  const [reviewOutcome, setReviewOutcome] = useState<"resolved" | "further_info_required">("resolved");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<{
        request: InformationRequestItem;
        application_no?: string;
        institution_name?: string;
        latest_response?: InformationResponseItem | null;
        response?: InformationResponseItem | null;
        response_history?: InformationResponseItem[];
        has_released_notice_doc?: boolean;
      }>(`/information-requests/${reqId}`);

      const reqObj = { ...data.request };
      if (data.application_no) reqObj.application_no = data.application_no;
      if (data.institution_name) reqObj.institution_name = data.institution_name;
      setRequest(reqObj);

      const activeResp = data.latest_response || data.response || null;
      setResponse(activeResp);
      setResponseHistory(data.response_history || []);

      // Initialize response items mapping from existing response or deficiencies
      const initialMap: Record<string, ResponseItem> = {};
      const existingItems = activeResp?.items || [];

      reqObj.deficiencies.forEach((def) => {
        const found = existingItems.find((it: any) => it.deficiency_id === def.id);
        if (found) {
          initialMap[def.id] = { ...found };
        } else {
          initialMap[def.id] = {
            deficiency_id: def.id,
            explanation: "",
            document_id: null,
            original_filename: null,
            status: "not_started",
          };
        }
      });
      setResponseItems(initialMap);

      const receiptNo = activeResp?.receipt_no || (activeResp as any)?.submission_receipt;
      if (receiptNo && activeResp?.submitted_at) {
        setSubmissionReceipt({
          receipt_no: receiptNo,
          submitted_at: activeResp.submitted_at,
          items_count: activeResp.items?.length || 0,
        });
      }
    } catch (err: any) {
      setError(err.message || "Failed to load information request details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && reqId) {
      fetchDetail();
    }
  }, [user, reqId]);

  // Upload deficiency-linked document
  const handleDeficiencyDocUpload = async (def: DeficiencyRequirement, file: File) => {
    if (!file) return;

    try {
      setUploadingSlot(def.id);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("deficiency_id", def.id);
      formData.append("doc_type", def.doc_type || "general_compliance");

      const res = await apiRequest<{
        document_id: number;
        original_filename: string;
        message: string;
      }>(`/information-requests/${reqId}/upload-deficiency-doc`, {
        method: "POST",
        body: formData,
      });

      // Update response item state
      setResponseItems((prev) => ({
        ...prev,
        [def.id]: {
          ...prev[def.id],
          document_id: res.document_id,
          original_filename: res.original_filename,
          status: "completed",
        },
      }));
      setSuccessMsg(`Uploaded attachment for requirement "${def.requirement}"`);
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err: any) {
      setError(err.message || "Failed to upload document for this deficiency");
    } finally {
      setUploadingSlot(null);
    }
  };

  const handleExplanationChange = (defId: string, value: string) => {
    setResponseItems((prev) => {
      const hasDoc = !!prev[defId]?.document_id;
      const isCompleted = value.trim().length > 0 || hasDoc;
      return {
        ...prev,
        [defId]: {
          ...prev[defId],
          explanation: value,
          status: isCompleted ? "completed" : "not_started",
        },
      };
    });
  };

  // Save Draft Response
  const handleSaveDraft = async () => {
    try {
      setSavingDraft(true);
      setError(null);

      const itemsArray = Object.values(responseItems);
      const res = await apiRequest<InformationResponseItem>(
        `/information-requests/${reqId}/response/draft`,
        {
          method: "POST",
          body: JSON.stringify({ items: itemsArray }),
        }
      );
      setResponse(res);
      setSuccessMsg("Draft response saved successfully. You can return anytime before the deadline.");
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to save draft response");
    } finally {
      setSavingDraft(false);
    }
  };

  // Validate before submission
  const validateBeforeSubmit = (): string[] => {
    const errs: string[] = [];
    if (!request) return errs;

    request.deficiencies.forEach((def, idx) => {
      const item = responseItems[def.id];
      const hasDoc = !!item?.document_id;
      const hasExpl = !!item?.explanation?.trim();

      if (def.mandatory && !hasDoc && !hasExpl) {
        errs.push(`Item #${idx + 1} (${def.requirement}): Requires a substantive explanation and/or a cured certified document attachment.`);
      }
    });

    return errs;
  };

  const handleOpenReviewModal = () => {
    const errs = validateBeforeSubmit();
    setValidationErrors(errs);
    setIsReviewModalOpen(true);
  };

  // Submit Response
  const handleSubmitResponse = async () => {
    const errs = validateBeforeSubmit();
    if (errs.length > 0) {
      setValidationErrors(errs);
      setError("Please complete all required response items before submitting.");
      setIsReviewModalOpen(false);
      return;
    }

    try {
      setSubmittingResponse(true);
      setError(null);
      setValidationErrors([]);

      const itemsArray = Object.values(responseItems);
      const res = await apiRequest<{
        status: string;
        receipt_no: string;
        submission_receipt?: string;
        submitted_at: string;
        message?: string;
      }>(`/information-requests/${reqId}/response/submit`, {
        method: "POST",
        body: JSON.stringify({ items: itemsArray }),
      });

      const receipt = res.receipt_no || res.submission_receipt || "RCP-2026";
      setSubmissionReceipt({
        receipt_no: receipt,
        submitted_at: res.submitted_at,
        items_count: itemsArray.length,
      });

      setIsReviewModalOpen(false);
      setSuccessMsg(`Response successfully submitted. Council Docket Receipt: #${receipt}`);
      await fetchDetail();
    } catch (err: any) {
      setError(err.message || "Failed to submit response");
    } finally {
      setSubmittingResponse(false);
    }
  };

  // Official review handler
  const handleOfficialReview = async () => {
    if (!reviewNotes.trim()) {
      setError("Please provide official review notes for this resolution.");
      return;
    }

    try {
      setSubmittingReview(true);
      setError(null);

      await apiRequest(`/information-requests/${reqId}/review`, {
        method: "POST",
        body: JSON.stringify({
          outcome: reviewOutcome,
          notes: reviewNotes.trim(),
        }),
      });

      setSuccessMsg(`Information Request determination recorded as '${reviewOutcome.toUpperCase()}'.`);
      setReviewNotes("");
      await fetchDetail();
    } catch (err: any) {
      setError(err.message || "Failed to submit official review");
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleDownloadNotice = () => {
    const url = `${getApiBase()}/information-requests/${reqId}/notice-doc${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    window.open(url, "_blank");
  };

  if (authLoading || (loading && !request)) {
    return (
      <div className="flex h-72 items-center justify-center text-xs text-slate-500 animate-pulse space-y-2">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
        <p>Loading statutory deficiency notice and response workspace...</p>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="p-12 text-center text-xs text-slate-500 space-y-3 bg-white border border-slate-200 rounded-xl max-w-xl mx-auto my-12">
        <ShieldAlert className="w-8 h-8 text-slate-400 mx-auto" />
        <p className="font-bold text-slate-800 text-sm">Notice Record Not Found</p>
        <p className="text-slate-500">The requested notice does not exist or belongs to another accredited institution.</p>
        <Link href="/information-requests" className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg text-xs">
          Return to Notices List
        </Link>
      </div>
    );
  }

  const isResponseLocked =
    !isOfficial &&
    (response?.status === "submitted" ||
      request.status === "submitted" ||
      request.status === "under_review" ||
      request.status === "resolved");

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href="/information-requests"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Information Requests</span>
        </Link>

        <span className="text-xs font-mono text-slate-400">
          Request ID: #{request.id} &bull; Notice: {request.reference_no}
        </span>
      </div>

      {/* Global Alerts */}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 shadow-xs">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-2 shadow-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold">Error Notice:</span>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Submission Receipt Banner */}
      {submissionReceipt && (
        <div className="bg-emerald-50 border-2 border-emerald-400 rounded-2xl p-6 shadow-sm space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-100 rounded-xl text-emerald-700">
                <Receipt className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-bold uppercase tracking-wide text-emerald-900">
                  Official Response Submission Receipt
                </span>
                <h3 className="text-base font-extrabold text-emerald-950 font-mono">
                  Receipt #{submissionReceipt.receipt_no}
                </h3>
              </div>
            </div>

            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-200 text-emerald-900">
              Response Committed &amp; Queued
            </span>
          </div>
          <p className="text-xs text-emerald-800 leading-relaxed">
            Your formal cure explanation and certified attachments were recorded on{" "}
            <strong>{new Date(submissionReceipt.submitted_at).toLocaleString()}</strong>.
            This timestamp is permanently logged in the immutable AICTE Council audit trail. Scrutiny Committee officers have been notified to review your submission.
          </p>
        </div>
      )}

      {/* 1. Official Notice Preview (Read-Only) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 font-bold uppercase tracking-wider">
                Official Deficiency Notice
              </span>
              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {request.reference_no}
              </span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-1">{request.title}</h2>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleDownloadNotice}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold border border-slate-200 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Download Official Notice</span>
            </button>
          </div>
        </div>

        {/* Notice Meta Information */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 bg-slate-50 rounded-xl text-xs text-slate-600">
          <div>
            <span className="text-[11px] text-slate-400 block font-medium">Application</span>
            <span className="font-bold text-slate-800 font-mono">
              #{request.application_no || request.application_id}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-400 block font-medium">Institution</span>
            <span className="font-bold text-slate-800 truncate block">
              {request.institution_name || "Applicant Technical Institution"}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-400 block font-medium">Issued Date</span>
            <span className="font-bold text-slate-800">
              {request.issued_at ? new Date(request.issued_at).toLocaleDateString() : "—"}
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-400 block font-medium">Actual Response Deadline</span>
            <span className="font-bold text-amber-800">
              {request.deadline ? new Date(request.deadline).toLocaleDateString() : "—"}
            </span>
          </div>
        </div>

        {/* Notice Grounds / Reason */}
        <div className="space-y-1 text-xs">
          <span className="font-bold text-slate-700 block uppercase tracking-wider text-[11px]">
            Official Scrutiny Grounds &amp; Instructions:
          </span>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
            {request.notice_text || request.reason}
          </div>
        </div>
      </div>

      {/* 2. Response Form (Per Deficiency Item) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-6">
        <div className="pb-3 border-b border-slate-100 flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span>Institutional Response &amp; Supporting Document Cure</span>
            </h3>
            <p className="text-xs text-slate-400">
              Each listed deficiency requires an explanation and/or a cured statutory document attachment.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              {request.deficiencies.length} Deficiency Items
            </span>
            {isResponseLocked && (
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
                Response Locked (Under Scrutiny)
              </span>
            )}
          </div>
        </div>

        {/* Incomplete Validation Errors Alert */}
        {validationErrors.length > 0 && (
          <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 space-y-1">
            <div className="flex items-center gap-1.5 font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Incomplete Items Requiring Action:</span>
            </div>
            <ul className="list-disc pl-5 space-y-0.5 pt-1">
              {validationErrors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Deficiency Response Items List */}
        <div className="space-y-6 divide-y divide-slate-100">
          {request.deficiencies.map((def, idx) => {
            const currentItem = responseItems[def.id] || {
              deficiency_id: def.id,
              explanation: "",
              document_id: null,
              original_filename: null,
              status: "not_started",
            };

            const isSlotUploading = uploadingSlot === def.id;
            const hasDocument = !!currentItem.document_id;
            const hasExplanation = !!currentItem.explanation?.trim();
            const isCompleted = hasDocument || hasExplanation;

            return (
              <div key={def.id} className="pt-6 first:pt-0 space-y-4">
                {/* Deficiency Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-slate-900 text-white font-bold text-xs flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <h4 className="text-xs font-bold text-slate-900">{def.requirement}</h4>
                    {def.mandatory && (
                      <span className="text-[10px] text-rose-600 font-semibold uppercase bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                        Required
                      </span>
                    )}
                  </div>

                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      isCompleted
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {isCompleted ? "Response Prepared" : "Not Started"}
                  </span>
                </div>

                {/* Explanation text from official notice */}
                {def.explanation && (
                  <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200/80 leading-relaxed">
                    <strong className="text-slate-800">Scrutiny Detail:</strong> {def.explanation}
                  </p>
                )}

                {/* Applicant Response Controls */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  {/* Text Explanation Field */}
                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-slate-700">
                      Institutional Explanation:
                    </label>
                    <textarea
                      rows={4}
                      disabled={isResponseLocked}
                      value={currentItem.explanation || ""}
                      onChange={(e) => handleExplanationChange(def.id, e.target.value)}
                      placeholder="Provide detailed statutory clarification regarding this item..."
                      className="w-full text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 disabled:bg-slate-50 disabled:text-slate-600"
                    />
                  </div>

                  {/* Document Attachment Field */}
                  <div className="space-y-1">
                    <label className="block text-xs font-semibold text-slate-700">
                      Supporting Document Attachment:
                    </label>

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white rounded-lg border border-slate-200 min-h-[92px]">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-blue-600 shrink-0" />
                        {currentItem.original_filename ? (
                          <div className="truncate">
                            <span className="font-mono font-bold text-slate-800 truncate block text-xs">
                              {currentItem.original_filename}
                            </span>
                            <span className="text-[10px] text-emerald-700 font-semibold">
                              Attached for Deficiency Verification
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic text-xs">No replacement file attached yet</span>
                        )}
                      </div>

                      {!isResponseLocked && (
                        <div className="flex items-center gap-2 shrink-0">
                          <input
                            type="file"
                            id={`def-file-${def.id}`}
                            accept=".pdf,.png,.jpg,.jpeg"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                handleDeficiencyDocUpload(def, file);
                              }
                              e.target.value = "";
                            }}
                          />
                          <button
                            type="button"
                            disabled={isSlotUploading}
                            onClick={() => {
                              const el = document.getElementById(`def-file-${def.id}`);
                              if (el) el.click();
                            }}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                              currentItem.document_id
                                ? "bg-amber-50 text-amber-800 border border-amber-300 hover:bg-amber-100"
                                : "bg-blue-600 text-white hover:bg-blue-700 shadow-xs"
                            }`}
                          >
                            {isSlotUploading ? (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Upload className="w-3.5 h-3.5" />
                            )}
                            <span>
                              {isSlotUploading
                                ? "Uploading..."
                                : currentItem.document_id
                                ? "Replace Document"
                                : "Upload Document"}
                            </span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Response Action Bar (for applicants) */}
        {!isOfficial && !isResponseLocked && (
          <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span className="text-[11px] text-slate-500">
              Deadline: {request.deadline ? new Date(request.deadline).toLocaleDateString() : "—"}. All responses and attachments will be timestamped in the audit log.
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={savingDraft || submittingResponse}
                onClick={handleSaveDraft}
                className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs flex items-center gap-1.5 transition-colors"
              >
                <Save className="w-4 h-4 text-slate-500" />
                <span>{savingDraft ? "Saving Draft..." : "Save Draft"}</span>
              </button>

              <button
                type="button"
                disabled={savingDraft || submittingResponse}
                onClick={handleOpenReviewModal}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-xs"
              >
                <Eye className="w-4 h-4 text-slate-300" />
                <span>Review Response</span>
              </button>

              <button
                type="button"
                disabled={submittingResponse || savingDraft}
                onClick={handleSubmitResponse}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>{submittingResponse ? "Submitting..." : "Submit Response"}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Review Response Modal */}
      {isReviewModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 shrink-0">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Eye className="w-4 h-4 text-blue-600" />
                  <span>Review Response Summary Before Final Submission</span>
                </h3>
                <p className="text-xs text-slate-500">
                  Notice #{request.reference_no} &bull; Application #{request.application_no || request.application_id}
                </p>
              </div>
              <button
                onClick={() => setIsReviewModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 pr-1 text-xs divide-y divide-slate-100 flex-1">
              {request.deficiencies.map((def, idx) => {
                const item = responseItems[def.id];
                const hasDoc = !!item?.document_id;
                const hasExpl = !!item?.explanation?.trim();
                const isItemValid = hasDoc || hasExpl;

                return (
                  <div key={def.id} className="pt-3 first:pt-0 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">
                        Item #{idx + 1}: {def.requirement}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isItemValid
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {isItemValid ? "Ready" : "Incomplete"}
                      </span>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 space-y-1">
                      <p className="text-slate-700">
                        <strong>Explanation:</strong>{" "}
                        {item?.explanation?.trim() || <span className="italic text-slate-400">None provided</span>}
                      </p>
                      <p className="text-slate-700 font-mono">
                        <strong>Attached File:</strong>{" "}
                        {item?.original_filename || <span className="italic text-slate-400">No file attached</span>}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between shrink-0">
              <button
                type="button"
                onClick={() => setIsReviewModalOpen(false)}
                className="px-4 py-2 border border-slate-300 text-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-50 transition-colors"
              >
                Back to Edit
              </button>

              <button
                type="button"
                disabled={submittingResponse}
                onClick={handleSubmitResponse}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs shadow-sm flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>{submittingResponse ? "Submitting..." : "Confirm & Submit Response"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Submitted Responses History (if any) */}
      {responseHistory.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
            <History className="w-4 h-4 text-slate-600" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Submitted Response History &amp; Immutable Receipts
            </h4>
          </div>

          <div className="space-y-2">
            {responseHistory.map((hist) => (
              <div
                key={hist.id}
                className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-mono font-bold text-slate-800">
                    Receipt #{hist.receipt_no || (hist as any).submission_receipt || "RCP-2026"}
                  </span>
                  <span className="text-slate-400 text-[11px] block">
                    Version {hist.version || 1} &bull; Committed on{" "}
                    {hist.submitted_at ? new Date(hist.submitted_at).toLocaleString() : "—"}
                  </span>
                </div>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800">
                  {hist.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Official Review Panel (Only visible to Authorised AICTE Officials) */}
      {isOfficial && (
        <div className="bg-white border-2 border-slate-900 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-blue-600" />
              <span>Official Scrutiny Committee Review &amp; Resolution</span>
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 font-bold uppercase">
              Official Controls
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-2">Review Outcome:</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setReviewOutcome("resolved")}
                  className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                    reviewOutcome === "resolved"
                      ? "border-emerald-600 bg-emerald-50/70 text-emerald-950 ring-2 ring-emerald-600/20"
                      : "border-slate-200 hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <span className="font-bold block">Accept &amp; Resolve Request</span>
                    <span className="text-[11px] text-slate-500">Cured deficiencies meet norms</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setReviewOutcome("further_info_required")}
                  className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all ${
                    reviewOutcome === "further_info_required"
                      ? "border-amber-600 bg-amber-50/70 text-amber-950 ring-2 ring-amber-600/20"
                      : "border-slate-200 hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  <div>
                    <span className="font-bold block">Request Further Information</span>
                    <span className="text-[11px] text-slate-500">Submissions remain deficient</span>
                  </div>
                </button>
              </div>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Scrutiny Resolution Remarks <span className="text-rose-500">*</span>:
              </label>
              <textarea
                rows={3}
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Record the official evaluation of applicant responses and cured documents..."
                className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                disabled={submittingReview || !reviewNotes.trim()}
                onClick={handleOfficialReview}
                className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg text-xs shadow-sm flex items-center gap-2 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
                <span>{submittingReview ? "Recording..." : "Record Official Determination"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
