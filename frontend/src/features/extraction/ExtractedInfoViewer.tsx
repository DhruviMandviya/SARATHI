"use client";

import React, { useState, useEffect } from "react";
import { DocumentItem, ExtractedField } from "@/lib/types";
import { apiRequest, getApiBase } from "@/lib/api";
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
  ExternalLink,
  Layers,
  FileCheck,
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
  const { isOfficial, token: authContextToken } = useAuth();
  const token =
    authContextToken ||
    (typeof window !== "undefined" ? localStorage.getItem("aicte_token") : null);

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [viewMode, setViewMode] = useState<"page" | "direct">("page");
  const [selectedField, setSelectedField] = useState<ExtractedField | null>(
    document.extracted_fields[0] || null
  );
  const [imageLoading, setImageLoading] = useState<boolean>(true);
  const [imageError, setImageError] = useState<boolean>(false);
  const [directLoadError, setDirectLoadError] = useState<boolean>(false);

  // Editing state for officials
  const [editingFieldId, setEditingFieldId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [editRemarks, setEditRemarks] = useState<string>("");
  const [savingEdit, setSavingEdit] = useState<boolean>(false);

  const totalPages = Math.max(document.page_count || 1, 1);
  const apiBase = getApiBase();
  const fileUrl = `${apiBase}/documents/${document.id}/file${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  const pageImageUrl = `${apiBase}/documents/${document.id}/page/${currentPage}/image${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  const isPdf = (document.mime_type || "").toLowerCase().includes("pdf") || document.original_filename.toLowerCase().endsWith(".pdf");

  useEffect(() => {
    setImageLoading(true);
    setImageError(false);
    setDirectLoadError(false);
  }, [document.id, currentPage, token]);

  const handleSelectField = (field: ExtractedField) => {
    setSelectedField(field);
    if (field.page && field.page <= totalPages) {
      setCurrentPage(field.page);
    }
    // Switch to page mode to show bounding box if in direct mode
    if (viewMode === "direct") {
      setViewMode("page");
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
            <span className="text-xs font-bold text-slate-800 truncate max-w-[170px]" title={document.original_filename}>
              {document.original_filename}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold uppercase">
              {document.doc_type}
            </span>

            {/* View Mode Toggle */}
            <div className="hidden sm:flex items-center bg-slate-100 rounded-lg p-0.5 text-[11px] border border-slate-200 ml-1">
              <button
                type="button"
                onClick={() => setViewMode("page")}
                className={`px-2 py-0.5 rounded font-medium transition-colors ${
                  viewMode === "page"
                    ? "bg-white text-[#0A4D2E] shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="View page render with OCR bounding box overlay"
              >
                Page {currentPage}
              </button>
              <button
                type="button"
                onClick={() => setViewMode("direct")}
                className={`px-2 py-0.5 rounded font-medium transition-colors ${
                  viewMode === "direct"
                    ? "bg-white text-[#0A4D2E] shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
                title="View original stored file directly"
              >
                Direct File
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Page navigation (active in page mode) */}
            {viewMode === "page" && (
              <div className="flex items-center gap-1 text-xs text-slate-600 font-medium">
                <button
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-[11px]">
                  {currentPage}/{totalPages}
                </span>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  className="p-1 rounded hover:bg-slate-100 disabled:opacity-30"
                  title="Next Page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Zoom Controls (active in page mode or image) */}
            {viewMode === "page" && (
              <div className="flex items-center gap-0.5 border-l border-slate-200 pl-2">
                <button
                  onClick={() => setZoom((z) => Math.max(z - 20, 60))}
                  className="p-1 rounded hover:bg-slate-100 text-slate-600"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] text-slate-500 w-7 text-center font-mono">{zoom}%</span>
                <button
                  onClick={() => setZoom((z) => Math.min(z + 20, 180))}
                  className="p-1 rounded hover:bg-slate-100 text-slate-600"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Open Original in New Window */}
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-[#0A4D2E] transition-colors"
              title="Open Original Document in New Tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>

            {onReprocessRequested && (
              <button
                onClick={onReprocessRequested}
                className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-[#0A4D2E] transition-colors"
                title="Reprocess Document OCR"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Viewer Viewport */}
        <div className="relative flex-1 min-h-[460px] max-h-[600px] overflow-auto flex items-center justify-center p-4 bg-slate-900/10">
          {imageLoading && viewMode === "page" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10 gap-2">
              <RefreshCw className="w-6 h-6 text-[#0A4D2E] animate-spin" />
              <span className="text-xs text-slate-600 font-semibold">Loading Page {currentPage}...</span>
            </div>
          )}

          {/* VIEW MODE 1: DIRECT FILE VIEWER (OR AUTOMATIC FALLBACK WHEN PAGE RENDER FAILS) */}
          {viewMode === "direct" || (imageError && !directLoadError) ? (
            <div className="w-full h-full flex flex-col min-h-[460px] bg-white rounded-lg overflow-hidden shadow-sm border border-slate-200">
              {imageError && (
                <div className="p-2.5 bg-amber-50 border-b border-amber-200 text-[11px] text-amber-800 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Page thumbnail unavailable. Displaying original document directly.</span>
                  </div>
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="underline font-semibold hover:text-amber-950 ml-2 shrink-0"
                  >
                    Open in Tab &rarr;
                  </a>
                </div>
              )}

              {isPdf ? (
                <object
                  data={fileUrl}
                  type="application/pdf"
                  className="w-full flex-1 min-h-[440px] border-none"
                  onError={() => setDirectLoadError(true)}
                >
                  <iframe
                    src={fileUrl}
                    className="w-full flex-1 min-h-[440px] border-none"
                    title="Document View"
                  >
                    <div className="p-8 text-center text-xs text-slate-500">
                      Your browser does not support inline PDF viewing.{" "}
                      <a href={fileUrl} target="_blank" rel="noreferrer" className="text-[#0A4D2E] underline font-semibold">
                        Click here to open the file directly.
                      </a>
                    </div>
                  </iframe>
                </object>
              ) : (
                <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
                  <img
                    src={fileUrl}
                    alt={document.original_filename}
                    className="max-h-[500px] w-auto object-contain shadow-sm"
                    onError={() => setDirectLoadError(true)}
                  />
                </div>
              )}
            </div>
          ) : imageError && directLoadError ? (
            /* GENUINE ERROR: FILE DOES NOT EXIST IN STORAGE */
            <div className="p-8 text-center space-y-3 bg-white rounded-xl border border-slate-200 max-w-sm shadow-sm">
              <AlertTriangle className="w-8 h-8 text-rose-500 mx-auto" />
              <p className="text-xs font-semibold text-slate-800">Document File Not Found</p>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                The stored file could not be retrieved from the storage disk. The document may have been deleted or requires re-upload.
              </p>
              {onReprocessRequested && (
                <button
                  onClick={onReprocessRequested}
                  className="px-3 py-1.5 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded-lg text-xs font-semibold"
                >
                  Trigger Reprocessing
                </button>
              )}
            </div>
          ) : (
            /* VIEW MODE 2: RENDERED PAGE IMAGE WITH BOUNDING BOX HIGHLIGHTS */
            <div
              className="relative bg-white shadow-lg transition-transform duration-150 origin-top"
              style={{ width: `${zoom}%` }}
            >
              {/* Document Rendered Page */}
              <img
                src={pageImageUrl}
                alt={`Page ${currentPage} of ${document.original_filename}`}
                className="w-full h-auto object-contain block select-none"
                onLoad={() => setImageLoading(false)}
                onError={() => {
                  setImageLoading(false);
                  setImageError(true);
                }}
              />

              {/* Interactive Bounding Box Highlight Overlay */}
              {bboxStyle && (
                <div
                  style={bboxStyle}
                  className="absolute border-2 border-[#0A4D2E] bg-[#0A4D2E]/20 rounded shadow-md pointer-events-none transition-all duration-200 animate-pulse"
                >
                  <span className="absolute -top-5 left-0 px-1 py-0.2 rounded bg-[#0A4D2E] text-white text-[9px] font-bold tracking-tight uppercase whitespace-nowrap shadow">
                    {selectedField?.key}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Caveat Footer */}
        <div className="p-2 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 text-center flex items-center justify-between px-4">
          <span>Click any extracted field on the right to focus its position on the document.</span>
          <span className="text-slate-400 font-mono text-[10px]">
            Status: {document.processing_status}
          </span>
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

        {document.extracted_fields.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            No extracted parameters found for this document.
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[540px] overflow-y-auto pr-1">
            {document.extracted_fields.map((field) => {
              const isSelected = selectedField?.id === field.id;
              const isEditing = editingFieldId === field.id;
              const isLowConf = field.ocr_confidence < 0.7;
              const displayVal = field.edited_value !== null && field.edited_value !== undefined
                ? field.edited_value
                : field.value;

              return (
                <div
                  key={field.id}
                  onClick={() => !isEditing && handleSelectField(field)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "border-[#0A4D2E] bg-[#F0FDF4] ring-1 ring-[#0A4D2E] shadow-xs"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                        {field.key.replace(/_/g, " ")}
                      </span>
                      {field.edited_value !== null && field.edited_value !== undefined && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-100 text-purple-700 font-semibold">
                          Corrected
                        </span>
                      )}
                      {field.needs_review && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-700 font-semibold flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5" />
                          Needs Review
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {/* Confidence Pill */}
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium ${
                          isLowConf
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                        title={`Extraction Confidence: ${(field.ocr_confidence * 100).toFixed(0)}%`}
                      >
                        {(field.ocr_confidence * 100).toFixed(0)}%
                      </span>

                      {/* Official edit trigger */}
                      {isOfficial && !isEditing && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(field);
                          }}
                          className="p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors ml-1"
                          title="Correct field value"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Field Value Display or Inline Editor */}
                  {isEditing ? (
                    <div className="mt-2.5 space-y-2 pt-2 border-t border-slate-200" onClick={(e) => e.stopPropagation()}>
                      <div>
                        <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">
                          Corrected Value:
                        </label>
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="w-full text-xs p-1.5 rounded border border-[#86EFAC] focus:outline-none focus:ring-1 focus:ring-[#0A4D2E]"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">
                          Audit Remarks (Mandatory):
                        </label>
                        <input
                          type="text"
                          value={editRemarks}
                          placeholder="Reason for manual value change..."
                          onChange={(e) => setEditRemarks(e.target.value)}
                          className="w-full text-xs p-1.5 rounded border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0A4D2E]"
                        />
                      </div>
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={cancelEditing}
                          className="px-2 py-1 rounded text-[11px] font-medium text-slate-600 hover:bg-slate-200"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          disabled={savingEdit || !editRemarks.trim()}
                          onClick={() => saveCorrection(field.id)}
                          className="px-2.5 py-1 rounded text-[11px] font-bold text-white bg-[#0A4D2E] hover:bg-[#083D24] disabled:opacity-50"
                        >
                          {savingEdit ? "Saving..." : "Save Correction"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-1 flex items-baseline justify-between text-xs font-mono">
                      <span className="text-slate-900 font-semibold break-all">
                        {displayVal || <span className="text-slate-400 italic">Not extracted</span>}
                      </span>
                      {field.page && (
                        <span className="text-[10px] text-slate-400 font-sans shrink-0 ml-2">
                          Page {field.page}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
