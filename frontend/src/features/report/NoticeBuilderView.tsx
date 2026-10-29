"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { StatusChip } from "@/components/ui/StatusChip";
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  Check,
  Send,
  Save,
  Lock,
  Unlock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Clock,
  Info,
} from "lucide-react";

export interface CandidateItem {
  id: number;
  category: string;
  severity: string;
  title: string;
  explanation: string;
  recommended_action: string;
  doc_type: string | null;
  document_id: number | null;
  document_filename: string | null;
  rule_ref: string | null;
  evidence_ref: string | null;
  is_actionable: boolean;
  actionability: string;
  status: string;
}

export interface SelectedNoticeItem {
  finding_id: number;
  title: string;
  explanation: string;
  requested_action: string;
  requires_explanation: boolean;
  requires_upload: boolean;
  doc_type: string;
}

interface NoticeBuilderViewProps {
  applicationId: number;
  applicationNo: string;
  institutionName: string;
  onNoticeIssued: () => void;
}

const CATEGORY_LABELS: Record<string, { label: string; desc: string }> = {
  mandatory_compliance: {
    label: "Mandatory Compliance Deficiencies",
    desc: "Missing required documents, expired certificates, or unsatisfied statutory norms.",
  },
  material_inconsistencies: {
    label: "Material Cross-Document Inconsistencies",
    desc: "Conflicting institution name, land area, survey numbers, or address across records.",
  },
  document_clarifications: {
    label: "Document Clarification & Replacement Candidates",
    desc: "Illegible scans, missing endorsement seals, or low OCR extraction clarity.",
  },
  internal_forensics: {
    label: "Internal Forensic Signals (Restricted)",
    desc: "ELA anomalies, metadata discrepancies, and copy-move indicators for internal official scrutiny.",
  },
  duplicate_similarity: {
    label: "Duplicate & Similarity Findings (Restricted)",
    desc: "Perceptual or exact duplicates and template layout similarities.",
  },
  authority_pending: {
    label: "Authority Verification Pending",
    desc: "External registry or manual authority checks pending completion.",
  },
};

export function NoticeBuilderView({
  applicationId,
  applicationNo,
  institutionName,
  onNoticeIssued,
}: NoticeBuilderViewProps) {
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<Record<number, SelectedNoticeItem>>({});
  const [activeCategoryTab, setActiveCategoryTab] = useState<string>("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [issuing, setIssuing] = useState<boolean>(false);
  const [savingDraft, setSavingDraft] = useState<boolean>(false);
  const [cureDays, setCureDays] = useState<number>(15);
  const [officialRemarks, setOfficialRemarks] = useState<string>(
    "Pursuant to the scrutiny conducted under the AICTE Approval Process Handbook, the applicant institution is directed to cure the specific deficiencies identified below within 15 days."
  );
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Unlocking internal-only items requires explicit reason
  const [unlockingCandidateId, setUnlockingCandidateId] = useState<number | null>(null);
  const [unlockJustification, setUnlockJustification] = useState<string>("");

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await apiRequest<any>(`/applications/${applicationId}/notice-candidates`);
      const items: CandidateItem[] = res.candidates || [];
      setCandidates(items);

      // Pre-select actionable candidates by default
      const initialSelected: Record<number, SelectedNoticeItem> = {};
      items.forEach((c) => {
        if (c.is_actionable) {
          initialSelected[c.id] = {
            finding_id: c.id,
            title: c.title,
            explanation: c.explanation,
            requested_action: c.recommended_action || "Provide clarification or cure document.",
            requires_explanation: true,
            requires_upload: c.category === "mandatory_compliance" || c.category === "document_clarifications",
            doc_type: c.doc_type || "supporting_document",
          };
        }
      });
      setSelectedItems(initialSelected);
    } catch (err: any) {
      console.error("Failed to load notice candidates", err);
      setErrorMsg(err.message || "Failed to load candidate findings.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
  }, [applicationId]);

  const toggleItemSelection = (candidate: CandidateItem) => {
    if (selectedItems[candidate.id]) {
      const next = { ...selectedItems };
      delete next[candidate.id];
      setSelectedItems(next);
    } else {
      if (!candidate.is_actionable) {
        // Require explicit justification for internal-only findings
        setUnlockingCandidateId(candidate.id);
        setUnlockJustification("");
        return;
      }
      setSelectedItems({
        ...selectedItems,
        [candidate.id]: {
          finding_id: candidate.id,
          title: candidate.title,
          explanation: candidate.explanation,
          requested_action: candidate.recommended_action || "Provide clarification.",
          requires_explanation: true,
          requires_upload: true,
          doc_type: candidate.doc_type || "supporting_document",
        },
      });
    }
  };

  const handleConfirmUnlock = (candidate: CandidateItem) => {
    if (!unlockJustification.trim()) {
      alert("Mandatory official justification is required to include an internal finding in an applicant notice.");
      return;
    }
    setSelectedItems({
      ...selectedItems,
      [candidate.id]: {
        finding_id: candidate.id,
        title: candidate.title,
        explanation: `${candidate.explanation} (Official Justification: ${unlockJustification.trim()})`,
        requested_action: candidate.recommended_action || "Provide specific institutional clarification.",
        requires_explanation: true,
        requires_upload: false,
        doc_type: candidate.doc_type || "supporting_document",
      },
    });
    setUnlockingCandidateId(null);
    setUnlockJustification("");
  };

  const updateSelectedItem = (id: number, field: keyof SelectedNoticeItem, value: any) => {
    if (!selectedItems[id]) return;
    setSelectedItems({
      ...selectedItems,
      [id]: {
        ...selectedItems[id],
        [field]: value,
      },
    });
  };

  const selectedList = Object.values(selectedItems);
  const actionableCandidates = candidates.filter((c) => c.is_actionable);
  const internalCandidates = candidates.filter((c) => !c.is_actionable);

  const filteredCandidates =
    activeCategoryTab === "all"
      ? candidates
      : activeCategoryTab === "actionable"
      ? actionableCandidates
      : activeCategoryTab === "internal"
      ? internalCandidates
      : candidates.filter((c) => c.category === activeCategoryTab);

  const handleIssueNotice = async () => {
    if (selectedList.length === 0) {
      setErrorMsg("Cannot issue notice: At least one applicant-actionable deficiency item must be selected.");
      return;
    }
    if (!officialRemarks.trim() || officialRemarks.trim().length < 5) {
      setErrorMsg("Mandatory official remarks are required (minimum 5 characters).");
      return;
    }

    try {
      setIssuing(true);
      setErrorMsg(null);
      await apiRequest(`/applications/${applicationId}/issue-notice-builder`, {
        method: "POST",
        body: JSON.stringify({
          official_remarks: officialRemarks.trim(),
          cure_period_days: cureDays,
          selected_items: selectedList,
        }),
      });
      setSuccessMsg(`Deficiency Notice formally issued with ${selectedList.length} actionable item(s).`);
      setShowConfirmModal(false);
      onNoticeIssued();
    } catch (err: any) {
      console.error("Notice issuance failed", err);
      setErrorMsg(err.message || "Failed to issue deficiency notice.");
    } finally {
      setIssuing(false);
    }
  };

  const handleSaveDraftNotice = async () => {
    try {
      setSavingDraft(true);
      setErrorMsg(null);
      // Generate formatted draft text
      let text = `AICTE FORMAL STATUTORY DEFICIENCY NOTICE (DRAFT)\n`;
      text += `Application ID: ${applicationNo}\n`;
      text += `Institution: ${institutionName}\n`;
      text += `Cure Period: ${cureDays} Days\n\n`;
      text += `Official Scrutiny Remarks:\n${officialRemarks}\n\n`;
      text += `ACTIONABLE DEFICIENCY ITEMS (${selectedList.length}):\n`;
      selectedList.forEach((item, idx) => {
        text += `${idx + 1}. [${item.doc_type}] ${item.title}\n`;
        text += `   Deficiency: ${item.explanation}\n`;
        text += `   Required Action: ${item.requested_action}\n`;
        text += `   Submission: ${item.requires_explanation ? "Written Explanation" : ""}${
          item.requires_explanation && item.requires_upload ? " + " : ""
        }${item.requires_upload ? "Document Upload" : ""}\n\n`;
      });

      await apiRequest(`/applications/${applicationId}/deficiency-letter`, {
        method: "POST",
        body: JSON.stringify({ letter_text: text }),
      });
      alert("Draft notice letter saved to dossier.");
    } catch (err: any) {
      alert(err.message || "Failed to save draft notice.");
    } finally {
      setSavingDraft(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-xs text-slate-500 animate-pulse">
        Loading candidate scrutiny findings and deficiency classification...
      </div>
    );
  }

  return (
    <div className="space-y-5 bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-amber-600" />
            <span>Official Deficiency Notice Builder</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Select and customize applicant-actionable items. Internal forensics and duplicates are restricted to official scrutiny by default.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={fetchCandidates}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
            title="Refresh Candidate Findings"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setShowPreviewModal(true)}
            disabled={selectedList.length === 0}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Preview Notice ({selectedList.length})</span>
          </button>
          <button
            type="button"
            onClick={handleSaveDraftNotice}
            disabled={savingDraft || selectedList.length === 0}
            className="px-3 py-1.5 bg-[#F0FDF4] hover:bg-emerald-100 text-[#0A4D2E] font-semibold text-xs rounded-lg border border-[#86EFAC] transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{savingDraft ? "Saving..." : "Save Draft"}</span>
          </button>
          <button
            type="button"
            onClick={() => setShowConfirmModal(true)}
            disabled={selectedList.length === 0}
            className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg shadow-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Issue Official Notice</span>
          </button>
        </div>
      </div>

      {/* Alert Messages */}
      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Scrutiny Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
          <span className="text-[11px] text-slate-500 block">Total Candidate Findings</span>
          <span className="text-lg font-extrabold text-slate-900">{candidates.length}</span>
        </div>
        <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200">
          <span className="text-[11px] text-amber-700 font-medium block">Applicant Actionable</span>
          <span className="text-lg font-extrabold text-amber-900">{actionableCandidates.length}</span>
        </div>
        <div className="p-3 rounded-lg bg-slate-100/70 border border-slate-300">
          <span className="text-[11px] text-slate-700 font-medium block">Internal Scrutiny Only</span>
          <span className="text-lg font-extrabold text-slate-900">{internalCandidates.length}</span>
        </div>
        <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200">
          <span className="text-[11px] text-emerald-700 font-medium block">Selected for Notice</span>
          <span className="text-lg font-extrabold text-emerald-900">{selectedList.length}</span>
        </div>
      </div>

      {/* Notice Settings */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-500" />
            <label className="font-bold text-slate-700">Mandatory Statutory Cure Period:</label>
            <input
              type="number"
              min={7}
              max={45}
              value={cureDays}
              onChange={(e) => setCureDays(parseInt(e.target.value) || 15)}
              className="w-16 px-2 py-1 border border-slate-300 rounded text-center font-bold text-slate-800"
            />
            <span className="text-slate-500">Days (per AICTE APH Regulations)</span>
          </div>
          <span className="text-[11px] text-slate-500 italic">
            Calculated Deadline: {new Date(Date.now() + cureDays * 86400000).toLocaleDateString()}
          </span>
        </div>

        <div>
          <label className="block font-bold text-slate-700 mb-1">
            Authorised Official Remarks / Directions <span className="text-rose-500">*</span>:
          </label>
          <textarea
            rows={2}
            value={officialRemarks}
            onChange={(e) => setOfficialRemarks(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
            placeholder="State the formal basis under the Approval Process Handbook..."
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs border-b border-slate-200">
        <button
          onClick={() => setActiveCategoryTab("all")}
          className={`px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeCategoryTab === "all" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          All Candidates ({candidates.length})
        </button>
        <button
          onClick={() => setActiveCategoryTab("actionable")}
          className={`px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeCategoryTab === "actionable" ? "bg-amber-600 text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Actionable Only ({actionableCandidates.length})
        </button>
        <button
          onClick={() => setActiveCategoryTab("internal")}
          className={`px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-colors ${
            activeCategoryTab === "internal" ? "bg-slate-700 text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Internal Only ({internalCandidates.length})
        </button>
        {Object.entries(CATEGORY_LABELS).map(([catKey, info]) => {
          const count = candidates.filter((c) => c.category === catKey).length;
          if (count === 0) return null;
          return (
            <button
              key={catKey}
              onClick={() => setActiveCategoryTab(catKey)}
              className={`px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-colors ${
                activeCategoryTab === catKey ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {info.label.split(" ")[0]} ({count})
            </button>
          );
        })}
      </div>

      {/* Candidate Findings List */}
      <div className="space-y-3">
        {filteredCandidates.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs italic bg-slate-50 rounded-xl">
            No candidate findings matching this category filter.
          </div>
        ) : (
          filteredCandidates.map((candidate) => {
            const isSelected = !!selectedItems[candidate.id];
            const selData = selectedItems[candidate.id];
            const isInternal = !candidate.is_actionable;

            return (
              <div
                key={candidate.id}
                className={`p-4 rounded-xl border text-xs transition-all ${
                  isSelected
                    ? "bg-amber-50/40 border-amber-300 ring-1 ring-amber-300"
                    : isInternal
                    ? "bg-slate-50/70 border-slate-200 opacity-90"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Inclusion Checkbox */}
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleItemSelection(candidate)}
                      className="mt-1 w-4 h-4 rounded text-amber-600 focus:ring-amber-500 cursor-pointer"
                    />

                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-slate-900 text-sm">{candidate.title}</span>
                        <StatusChip status={candidate.severity} type="severity" size="sm" />
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {CATEGORY_LABELS[candidate.category]?.label || candidate.category}
                        </span>
                        {isInternal ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-300">
                            <Lock className="w-2.5 h-2.5" />
                            Internal Scrutiny Only
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <Unlock className="w-2.5 h-2.5" />
                            Applicant Actionable
                          </span>
                        )}
                      </div>

                      <p className="text-slate-700 leading-relaxed">{candidate.explanation}</p>

                      <div className="flex items-center gap-3 text-[11px] text-slate-500 pt-1 flex-wrap">
                        {candidate.doc_type && (
                          <span>
                            Document Type: <strong className="font-mono text-slate-700">{candidate.doc_type}</strong>
                          </span>
                        )}
                        {candidate.rule_ref && (
                          <span>
                            Rule: <strong className="font-mono text-slate-700">{candidate.rule_ref}</strong>
                          </span>
                        )}
                        {candidate.document_filename && (
                          <span>
                            File: <strong className="text-slate-700">{candidate.document_filename}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <span
                      className={`text-[11px] font-semibold px-2 py-1 rounded ${
                        isSelected ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {isSelected ? "Included in Notice" : "Excluded"}
                    </span>
                  </div>
                </div>

                {/* If selected, render editable applicant-facing fields */}
                {isSelected && selData && (
                  <div className="mt-4 pt-3 border-t border-amber-200 space-y-3 bg-white p-3.5 rounded-lg border border-amber-100">
                    <div className="text-[11px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-amber-600" />
                      <span>Applicant-Facing Notice Item Configuration</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-bold text-slate-700 mb-1">
                          Applicant-Facing Title:
                        </label>
                        <input
                          type="text"
                          value={selData.title}
                          onChange={(e) => updateSelectedItem(candidate.id, "title", e.target.value)}
                          className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs text-slate-800"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-bold text-slate-700 mb-1">
                          Associated Document Category:
                        </label>
                        <input
                          type="text"
                          value={selData.doc_type}
                          onChange={(e) => updateSelectedItem(candidate.id, "doc_type", e.target.value)}
                          className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs text-slate-800 font-mono"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Specific Deficiency Explanation:
                      </label>
                      <textarea
                        rows={2}
                        value={selData.explanation}
                        onChange={(e) => updateSelectedItem(candidate.id, "explanation", e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Action Required from Institution:
                      </label>
                      <input
                        type="text"
                        value={selData.requested_action}
                        onChange={(e) => updateSelectedItem(candidate.id, "requested_action", e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs text-slate-800"
                      />
                    </div>

                    <div className="flex items-center gap-4 pt-1">
                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selData.requires_explanation}
                          onChange={(e) =>
                            updateSelectedItem(candidate.id, "requires_explanation", e.target.checked)
                          }
                          className="w-3.5 h-3.5 rounded text-amber-600 focus:ring-amber-500"
                        />
                        <span className="text-slate-700 font-medium">Written Explanation Required</span>
                      </label>

                      <label className="inline-flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selData.requires_upload}
                          onChange={(e) => updateSelectedItem(candidate.id, "requires_upload", e.target.checked)}
                          className="w-3.5 h-3.5 rounded text-amber-600 focus:ring-amber-500"
                        />
                        <span className="text-slate-700 font-medium">Document Upload Required</span>
                      </label>
                    </div>
                  </div>
                )}

                {/* Justification Dialog to Unlock Internal Findings */}
                {unlockingCandidateId === candidate.id && (
                  <div className="mt-3 p-3 bg-[#F0FDF4] border border-[#86EFAC]/70 rounded-lg space-y-2">
                    <div className="text-[11px] font-bold text-[#073F2A] flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-[#0A4D2E]" />
                      <span>Authorised Official Override: Include Internal Scrutiny Finding</span>
                    </div>
                    <p className="text-[11px] text-[#0A4D2E] leading-normal">
                      This finding is classified as internal official scrutiny. To disclose it in a formal notice to the applicant, you must provide a statutory justification.
                    </p>
                    <input
                      type="text"
                      value={unlockJustification}
                      onChange={(e) => setUnlockJustification(e.target.value)}
                      placeholder="e.g. Scrutiny Committee requires notarized clarification regarding duplicate surveyor seal"
                      className="w-full px-2.5 py-1.5 border border-[#86EFAC] rounded text-xs bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#0A4D2E]"
                    />
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => setUnlockingCandidateId(null)}
                        className="px-2.5 py-1 text-[11px] text-slate-600 hover:bg-slate-100 rounded"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleConfirmUnlock(candidate)}
                        disabled={!unlockJustification.trim()}
                        className="px-3 py-1 bg-[#0A4D2E] hover:bg-[#083D24] text-white font-semibold text-[11px] rounded disabled:opacity-50"
                      >
                        Authorize &amp; Include
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Preview Notice Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden text-xs max-h-[85vh] flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h4 className="text-base font-bold text-slate-900">Preview Formal Statutory Deficiency Notice</h4>
                <p className="text-[11px] text-slate-500">
                  Application #{applicationNo} &bull; {institutionName}
                </p>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold"
              >
                &times;
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 font-sans text-slate-800 leading-relaxed flex-1">
              <div className="text-center pb-3 border-b border-slate-200">
                <span className="font-extrabold text-sm uppercase tracking-wider block text-slate-900">
                  All India Council for Technical Education
                </span>
                <span className="text-[11px] text-slate-500">
                  Scrutiny &amp; Document Verification Cell &bull; New Delhi
                </span>
              </div>

              <div className="space-y-1 text-slate-700">
                <p><strong>To:</strong> The Head of Institution / Authorized Signatory</p>
                <p><strong>Institution:</strong> {institutionName}</p>
                <p><strong>Application Ref:</strong> {applicationNo}</p>
                <p><strong>Date of Issue:</strong> {new Date().toLocaleDateString()}</p>
                <p><strong>Statutory Cure Period:</strong> {cureDays} Calendar Days</p>
                <p><strong>Response Deadline:</strong> {new Date(Date.now() + cureDays * 86400000).toLocaleDateString()}</p>
              </div>

              <div className="pt-2">
                <p className="font-bold text-slate-900">Official Notice Remarks:</p>
                <p className="italic bg-slate-50 p-3 rounded border border-slate-200 text-slate-700 mt-1">
                  &ldquo;{officialRemarks}&rdquo;
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <p className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                  Actionable Deficiency Items ({selectedList.length}):
                </p>
                {selectedList.map((item, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
                    <div className="font-bold text-slate-900">
                      Item #{idx + 1}: {item.title}
                    </div>
                    <p className="text-slate-700">{item.explanation}</p>
                    <div className="text-[11px] text-slate-600 pt-1">
                      <strong>Required Action:</strong> {item.requested_action}
                    </div>
                    <div className="text-[10px] font-mono text-slate-500">
                      Response Requirements: {item.requires_explanation ? "Written Clarification" : ""}{" "}
                      {item.requires_explanation && item.requires_upload ? "+ " : ""}{" "}
                      {item.requires_upload ? `Upload [${item.doc_type}]` : ""}
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-3 bg-amber-50 rounded border border-amber-200 text-[11px] text-amber-900">
                <strong>Legal Notice:</strong> Failure to address each deficiency item before the specified deadline may result in rejection of the approval application under the AICTE Approval Process Handbook.
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold text-xs"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal to Issue Notice */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full border border-slate-200 p-6 space-y-4 text-xs">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-xl bg-amber-100 text-amber-800">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Confirm Official Notice Issuance
                </h3>
                <p className="text-slate-500">
                  This will dispatch a legally binding deficiency notice to the applicant institution.
                </p>
              </div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Application No:</span>
                <span className="font-mono font-bold text-slate-900">{applicationNo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Items to Issue:</span>
                <span className="font-bold text-amber-800">{selectedList.length} Actionable Deficiencies</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Cure Period:</span>
                <span className="font-bold text-slate-900">{cureDays} Calendar Days</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Response Deadline:</span>
                <span className="font-mono text-slate-900">
                  {new Date(Date.now() + cureDays * 86400000).toLocaleDateString()}
                </span>
              </div>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-amber-800 text-[11px]">
              <strong>Workflow Impact:</strong> The application status will transition to <code>info_requested</code>. The applicant institution will be notified immediately to respond item-by-item.
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                disabled={issuing}
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-lg border border-slate-300 font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={issuing}
                onClick={handleIssueNotice}
                className="px-5 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                {issuing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>{issuing ? "Issuing..." : "Confirm & Issue Notice"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
