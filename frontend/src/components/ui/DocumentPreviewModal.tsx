"use client";

import React, { useState, useEffect } from "react";
import { getApiBase } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  X,
  FileText,
  ExternalLink,
  Download,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  RefreshCw,
  Eye,
  FileImage,
} from "lucide-react";

export interface PreviewableDocument {
  id: number;
  original_filename: string;
  doc_type: string;
  mime_type: string;
  page_count?: number;
  validation_status?: string;
  processing_status?: string;
}

interface DocumentPreviewModalProps {
  document: PreviewableDocument | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DocumentPreviewModal({
  document,
  isOpen,
  onClose,
}: DocumentPreviewModalProps) {
  const { token: authContextToken } = useAuth();
  const token =
    authContextToken ||
    (typeof window !== "undefined" ? localStorage.getItem("aicte_token") : null);

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(100);
  const [viewMode, setViewMode] = useState<"direct" | "rendered">("direct");
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setCurrentPage(1);
      setZoom(100);
      setLoading(true);
      setLoadError(null);
      // Default to direct for PDF or image
      setViewMode("direct");
    }
  }, [isOpen, document?.id]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !document) return null;

  const apiBase = getApiBase();
  const isPdf =
    document.mime_type?.toLowerCase().includes("pdf") ||
    document.original_filename?.toLowerCase().endsWith(".pdf");
  const isImage =
    document.mime_type?.toLowerCase().includes("image") ||
    /\.(png|jpe?g|webp)$/i.test(document.original_filename || "");

  const totalPages = Math.max(document.page_count || 1, 1);
  const fileUrl = `${apiBase}/documents/${document.id}/file${token ? `?token=${encodeURIComponent(token)}` : ""}`;
  const pageImageUrl = `${apiBase}/documents/${document.id}/page/${currentPage}/image${token ? `?token=${encodeURIComponent(token)}` : ""}`;

  const formatDocType = (dt: string) => {
    return dt
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl h-[88vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="h-16 bg-[#073F2A] text-white px-6 flex items-center justify-between shrink-0 border-b border-[#0A4D2E]/40">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center shrink-0 text-amber-300">
              {isPdf ? (
                <FileText className="w-5 h-5 text-amber-300" />
              ) : (
                <FileImage className="w-5 h-5 text-emerald-300" />
              )}
            </div>
            <div className="truncate">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold truncate max-w-md" title={document.original_filename}>
                  {document.original_filename}
                </h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-[#0A4D2E] text-emerald-100 border border-emerald-600/40">
                  {formatDocType(document.doc_type)}
                </span>
                {totalPages > 1 && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#052E1F] text-emerald-200/80 font-mono">
                    {totalPages} Pages
                  </span>
                )}
              </div>
              <p className="text-[11px] text-emerald-200/70 font-mono">
                {document.mime_type} • Protected Preview
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Toggle for PDFs */}
            {isPdf && (
              <div className="flex items-center bg-[#052E1F] rounded-lg p-0.5 border border-[#0A4D2E]/40 text-xs">
                <button
                  onClick={() => setViewMode("direct")}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    viewMode === "direct"
                      ? "bg-[#0A4D2E] text-white shadow-sm"
                      : "text-emerald-100/70 hover:text-white"
                  }`}
                >
                  Native PDF
                </button>
                <button
                  onClick={() => setViewMode("rendered")}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    viewMode === "rendered"
                      ? "bg-[#0A4D2E] text-white shadow-sm"
                      : "text-emerald-100/70 hover:text-white"
                  }`}
                >
                  Page Render
                </button>
              </div>
            )}

            {/* Open in new window */}
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg bg-[#0A4D2E] hover:bg-[#083D24] text-white transition-colors border border-[#0A4D2E]/60"
              title="Open Original in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>

            {/* Download */}
            <a
              href={fileUrl}
              download={document.original_filename}
              className="p-2 rounded-lg bg-[#0A4D2E] hover:bg-[#083D24] text-white transition-colors border border-[#0A4D2E]/60"
              title="Download File"
            >
              <Download className="w-4 h-4" />
            </a>

            {/* Close */}
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-black/20 hover:bg-rose-600/80 text-slate-300 hover:text-white transition-colors border border-white/10 ml-2"
              title="Close Preview (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Secondary Toolbar: Pages & Zoom (active when in rendered mode or images) */}
        {(viewMode === "rendered" || isImage) && (
          <div className="h-10 bg-slate-50 border-b border-slate-200 px-6 flex items-center justify-between text-xs text-slate-600 shrink-0">
            {totalPages > 1 && viewMode === "rendered" ? (
              <div className="flex items-center gap-1 font-medium">
                <button
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span>
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <span className="text-[11px] text-slate-400 font-medium">
                {isPdf ? "Page 1 Inspection" : "Full Resolution Preview"}
              </span>
            )}

            <div className="flex items-center gap-2">
              <button
                onClick={() => setZoom((z) => Math.max(z - 20, 50))}
                className="p-1 rounded hover:bg-slate-200"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-mono w-8 text-center">{zoom}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(z + 20, 200))}
                className="p-1 rounded hover:bg-slate-200"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Viewport */}
        <div className="flex-1 bg-slate-100 relative overflow-auto flex items-center justify-center p-4">
          {loadError ? (
            <div className="p-8 text-center space-y-3 bg-white rounded-xl border border-slate-200 max-w-md shadow-sm">
              <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
              <h4 className="text-sm font-bold text-slate-900">Preview Could Not Be Loaded</h4>
              <p className="text-xs text-slate-500 leading-relaxed">{loadError}</p>
              <div className="flex items-center justify-center gap-3 pt-2">
                <a
                  href={fileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open Direct File</span>
                </a>
                <button
                  onClick={() => {
                    setLoadError(null);
                    setLoading(true);
                  }}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : viewMode === "direct" && isPdf ? (
            /* Native PDF embed via object with fallback to iframe */
            <div className="w-full h-full bg-white rounded-lg shadow-inner overflow-hidden border border-slate-200">
              <object
                data={fileUrl}
                type="application/pdf"
                className="w-full h-full min-h-[550px] border-none"
                onLoad={() => setLoading(false)}
                onError={() => {
                  // If native object embedding is blocked, switch to rendered page images
                  setViewMode("rendered");
                }}
              >
                <iframe
                  src={fileUrl}
                  className="w-full h-full min-h-[550px] border-none"
                  title="PDF Document Preview"
                >
                  <p className="p-6 text-center text-xs text-slate-500">
                    Your browser does not support inline PDF viewing. Please{" "}
                    <a href={fileUrl} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                      click here to download or open the PDF directly
                    </a>.
                  </p>
                </iframe>
              </object>
            </div>
          ) : viewMode === "rendered" || (isPdf && !isImage) ? (
            /* Rendered Page Image via PyMuPDF with Zoom */
            <div
              className="relative bg-white shadow-xl rounded-lg transition-transform duration-150 origin-top overflow-hidden border border-slate-200"
              style={{ width: `${zoom}%`, maxWidth: zoom <= 100 ? "100%" : "none" }}
            >
              <img
                src={pageImageUrl}
                alt={`Page ${currentPage} of ${document.original_filename}`}
                className="w-full h-auto object-contain block select-none mx-auto"
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setLoadError(
                    "Page render thumbnail could not be decoded. The document file may be damaged or queued for processing."
                  );
                }}
              />
            </div>
          ) : (
            /* Direct Image View for PNG, JPG, JPEG */
            <div
              className="relative bg-white shadow-xl rounded-lg transition-transform duration-150 origin-center overflow-hidden border border-slate-200 p-2"
              style={{ width: `${zoom}%`, maxWidth: zoom <= 100 ? "100%" : "none" }}
            >
              <img
                src={fileUrl}
                alt={document.original_filename}
                className="max-h-[70vh] w-auto mx-auto object-contain block select-none"
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setLoadError("Image file could not be loaded from storage.");
                }}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="h-10 bg-white border-t border-slate-200 px-6 flex items-center justify-between text-[11px] text-slate-500 shrink-0">
          <span>AICTE National Accreditation System • Read-only Audit Copy</span>
          <span>Click anywhere outside or press ESC to dismiss</span>
        </div>
      </div>
    </div>
  );
}
