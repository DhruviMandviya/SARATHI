"use client";

import React, { useState } from "react";
import { DocumentItem, ExtractedField } from "@/lib/types";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  FileText,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Edit2,
  Check,
  X,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Eye,
  RefreshCw,
} from "lucide-react";

interface ExtractedInfoViewerProps {
  document: DocumentItem;
  onFieldUpdated?: () => void;
  onReprocessRequested?: () => void;
}

export function ExtractedInfoViewer({
  document,
  onFieldUpdated,
  onReprocessRequested,
}: ExtractedInfoViewerProps) {
  const { isOfficial } = useAuth();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [selectedField, setSelectedField] = useState<ExtractedField | null>(
    document.extracted_fields[0] || null
  );

  // Editing state for officials
  const [editingFieldId, setEditingFieldId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [editRemarks, setEditRemarks] = useState<string>("");
  const [savingEdit, setSavingEdit] = useState<boolean>(false);

  const totalPages = Math.max(document.page_count || 1, 1);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const pageImageUrl = `${apiBase}/documents/${document.id}/page/${currentPage}/image`;

  const handleSelectField = (field: ExtractedField) => {
    setSelectedField(field);
    if (field.page && field.page <= totalPages) {
      setCurrentPage(field.page);
    }
  };

  const startEditing = (field: ExtractedField) => {
    setEditingFieldId(field.id);
    setEditValue(field.edited_value || field.value || "");
    setEditRemarks("");
  };

  const cancelEditing = () => {
    setEditingFieldId(null);
    setEditValue("");
    setEditRemarks("");
  };

  const saveCorrection = async (fieldId: number) => {
    setSavingEdit(true);
    try {
      await apiRequest(`/extracted-fields/${fieldId}`, {
        method: "PATCH",
        body: JSON.stringify({
          value: editValue,
          remarks: editRemarks || "Corrected during official scrutiny review",
        }),
      });
      setEditingFieldId(null);
      if (onFieldUpdated) onFieldUpdated();
    } catch (err: any) {
      alert(err.message || "Failed to update field value");
    } finally {
      setSavingEdit(false);
    }
  };

  // Convert normalized bbox to percentage styles
  const getBboxStyle = (bbox: any) => {
    if (!bbox || typeof bbox.x !== "number") {
      return null;
    }
    return {
      left: `${bbox.x * 100}%`,
      top: `${bbox.y * 100}%`,
      width: `${Math.max(bbox.width * 100, 4)}%`,
      height: `${Math.max(bbox.height * 100, 2)}%`,
    };
  };

  const bboxStyle = selectedField?.page === currentPage ? getBboxStyle(selectedField.bbox) : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-5">
      {/* LEFT PANE: DOCUMENT VIEWER */}
      <div className="lg:col-span-7 flex flex-col border border-slate-200 rounded-xl bg-slate-100 overflow-hidden">
        {/* Viewer Toolbar */}
        <div className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-800 truncate max-w-[200px]" title={document.original_filename}>
              {document.original_filename}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold uppercase">
              {document.doc_type}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Page navigation */}
            <div className="flex items-center gap-1 text-xs text-slate-600 font-medium">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span>
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1 border-l border-slate-200 pl-3">
              <button
                onClick={() => setZoom((z) => Math.max(z - 20, 60))}
                className="p-1 rounded hover:bg-slate-100 text-slate-600"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] text-slate-500 w-8 text-center">{zoom}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(z + 20, 180))}
                className="p-1 rounded hover:bg-slate-100 text-slate-600"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>

            {onReprocessRequested && (
              <button
                onClick={onReprocessRequested}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-blue-600 transition-colors"
                title="Reprocess Document OCR"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Viewer Viewport */}
        <div className="relative flex-1 min-h-[460px] max-h-[600px] overflow-auto flex items-center justify-center p-4 bg-slate-900/10">
          <div
            className="relative bg-white shadow-lg transition-transform duration-150 origin-top"
            style={{ width: `${zoom}%` }}
          >
            {/* Document Rendered Page */}
            <img
              src={pageImageUrl}
              alt={`Page ${currentPage}`}
              className="w-full h-auto object-contain block select-none"
              onError={(e) => {
                // Handle render fallback
                (e.target as HTMLElement).style.display = "none";
              }}
            />

            {/* Interactive Bounding Box Highlight Overlay */}
            {bboxStyle && (
              <div
                style={bboxStyle}
                className="absolute border-2 border-blue-600 bg-blue-500/20 rounded shadow-md pointer-events-none transition-all duration-200 animate-pulse"
              >
                <span className="absolute -top-5 left-0 px-1 py-0.2 rounded bg-blue-600 text-white text-[9px] font-bold tracking-tight uppercase whitespace-nowrap shadow">
                  {selectedField?.key}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Caveat Footer */}
        <div className="p-2 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 text-center">
          Click any extracted field on the right to focus and inspect its bounding coordinates on the document.
        </div>
      </div>

      {/* RIGHT PANE: EXTRACTED FIELDS LIST */}
      <div className="lg:col-span-5 flex flex-col space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-200">
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Extracted Data Fields</h4>
            <p className="text-[11px] text-slate-400">Rule-based and OCR parsed values</p>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold">
            {document.extracted_fields.length} Fields
          </span>
        </div>

        {/* Fields Table / List */}
        <div className="space-y-2.5 overflow-y-auto max-h-[520px] pr-1">
          {document.extracted_fields.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 space-y-2">
              <FileText className="w-8 h-8 text-slate-300 mx-auto" />
              <p>No fields extracted for this document yet.</p>
              {document.processing_status === "queued" && <p className="text-blue-600 font-medium">Processing in progress...</p>}
            </div>
          ) : (
            document.extracted_fields.map((field) => {
              const isSelected = selectedField?.id === field.id;
              const isEditing = editingFieldId === field.id;
              const confPct = Math.round(field.ocr_confidence <= 1.0 ? field.ocr_confidence * 100 : field.ocr_confidence);
              const isLowConf = confPct < 75 || field.needs_review;

              return (
                <div
                  key={field.id}
                  onClick={() => handleSelectField(field)}
                  className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 shadow-sm"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-slate-700 capitalize flex items-center gap-1.5">
                      <span>{field.key.replace(/_/g, " ")}</span>
                      {field.edited_value && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-purple-100 text-purple-700 border border-purple-200">
                          Official Edited
                        </span>
                      )}
                    </span>

                    {/* OCR Confidence Indicator */}
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md border ${
                          isLowConf
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200"
                        }`}
                        title="OCR Character Recognition Confidence"
                      >
                        {confPct}% Conf
                      </span>
                      <span className="text-[10px] text-slate-400 font-medium">P.{field.page}</span>
                    </div>
                  </div>

                  {/* Inline Editing for Officials */}
                  {isEditing ? (
                    <div className="mt-2 space-y-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Enter corrected value"
                        className="w-full px-2.5 py-1.5 text-xs border border-blue-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        autoFocus
                      />
                      <input
                        type="text"
                        value={editRemarks}
                        onChange={(e) => setEditRemarks(e.target.value)}
                        placeholder="Mandatory official justification remarks"
                        className="w-full px-2.5 py-1 text-[11px] border border-slate-300 rounded-lg"
                      />
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={cancelEditing}
                          className="px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => saveCorrection(field.id)}
                          disabled={savingEdit || !editValue}
                          className="px-3 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded shadow-sm disabled:opacity-50"
                        >
                          {savingEdit ? "Saving..." : "Save Correction"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-slate-900 font-semibold text-xs break-all">
                        {field.edited_value || field.value || <span className="text-slate-400 italic">Not detected</span>}
                      </p>

                      {isOfficial && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(field);
                          }}
                          className="p-1 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                          title="Official Value Correction"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}

                  {isLowConf && !field.edited_value && (
                    <div className="mt-1.5 flex items-center gap-1 text-[10px] text-amber-700 font-medium">
                      <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0" />
                      <span>Low OCR confidence &bull; Review required</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
