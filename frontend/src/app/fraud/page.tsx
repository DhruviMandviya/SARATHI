"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { ApplicationItem, DocumentItem } from "@/lib/types";
import { StatusChip } from "@/components/ui/StatusChip";
import { FraudSignalsView } from "@/features/fraud/FraudSignalsView";
import {
  ShieldAlert,
  Building2,
  Search,
  ExternalLink,
  RefreshCw,
  ArrowRight,
} from "lucide-react";

function FraudContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isOfficial, isInstitution, isLoading: authLoading } = useAuth();

  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<ApplicationItem | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingApps, setLoadingApps] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchApplications = async () => {
    try {
      setLoadingApps(true);
      const data = await apiRequest<ApplicationItem[]>("/applications");
      setApplications(data);

      const urlAppId = searchParams.get("appId");
      if (urlAppId && data.some((a) => a.id === Number(urlAppId))) {
        setSelectedAppId(Number(urlAppId));
      } else if (data.length > 0 && !selectedAppId) {
        const priorityApp = data.find((a) => a.risk_band === "High") || data[0];
        setSelectedAppId(priorityApp.id);
      }
    } catch (err) {
      console.error("Failed to load applications", err);
    } finally {
      setLoadingApps(false);
    }
  };

  useEffect(() => {
    if (user && !isInstitution) {
      fetchApplications();
    }
  }, [user, isInstitution]);

  const fetchSelectedAppDetails = async (appId: number) => {
    try {
      const appData = await apiRequest<ApplicationItem>(`/applications/${appId}`);
      setSelectedApplication(appData);

      const docsData = await apiRequest<DocumentItem[]>(`/applications/${appId}/documents-detailed`).catch(() => []);
      setDocuments(docsData);
    } catch (err) {
      console.error("Failed to load application details", err);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      fetchSelectedAppDetails(selectedAppId);
    }
  }, [selectedAppId]);

  const handleSelectApplication = (appId: number) => {
    setSelectedAppId(appId);
    const url = new URL(window.location.href);
    url.searchParams.set("appId", String(appId));
    window.history.replaceState({}, "", url.toString());
  };

  const filteredApps = applications.filter((app) => {
    return (
      !search ||
      app.application_no.toLowerCase().includes(search.toLowerCase()) ||
      (app.declared_details?.institution_name || "").toLowerCase().includes(search.toLowerCase())
    );
  });

  if (authLoading || (loadingApps && applications.length === 0)) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
        Loading Fraud &amp; Forensics Portal...
      </div>
    );
  }

  if (isInstitution) {
    return (
      <div className="p-8 bg-white border border-slate-200 rounded-xl text-center space-y-3">
        <ShieldAlert className="w-10 h-10 text-amber-500 mx-auto" />
        <h3 className="text-base font-bold text-slate-900">Official Access Only</h3>
        <p className="text-xs text-slate-600 max-w-md mx-auto">
          Forensics and digital anomaly inspection are restricted to authorized scrutiny officers.
        </p>
        <Link
          href="/applications"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0A4D2E] hover:bg-[#083D24] text-white rounded-lg text-xs font-semibold"
        >
          <span>Return to Applications</span>
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
            <ShieldAlert className="w-6 h-6 text-amber-600" />
            <span>Fraud &amp; Forensics Analysis Portal</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Error Level Analysis (ELA), copy-move feature clustering, and cross-institution document reuse signals.
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

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Application Queue (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <span>Applications</span>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px]">
                  {filteredApps.length}
                </span>
              </h3>
              <button onClick={fetchApplications} className="text-slate-400 hover:text-slate-600 p-1">
                <RefreshCw className={`w-3.5 h-3.5 ${loadingApps ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search application..."
                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
              />
            </div>

            <div className="space-y-2 max-h-[540px] overflow-y-auto pr-1">
              {filteredApps.map((app) => {
                const isSelected = app.id === selectedAppId;
                return (
                  <div
                    key={app.id}
                    onClick={() => handleSelectApplication(app.id)}
                    className={`p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? "bg-amber-50/80 border-amber-500 shadow-sm"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono font-bold text-slate-900">{app.application_no}</span>
                      <StatusChip status={app.status} type="application" size="sm" />
                    </div>
                    <div className="text-[11px] font-semibold text-slate-700 mt-1 line-clamp-1">
                      {app.declared_details?.institution_name || `Institution #${app.institution_id}`}
                    </div>
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                      <span>Risk: <strong className={app.risk_band === "High" ? "text-rose-600 font-bold" : "text-amber-600 font-bold"}>{app.risk_band}</strong></span>
                      <span className="font-mono">{app.risk_score.toFixed(0)}/100</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Forensics Area (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {!selectedApplication ? (
            <div className="bg-white border border-slate-200 rounded-xl p-16 text-center text-slate-400 text-xs">
              Select an application to inspect forensic signals.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 font-mono">
                    {selectedApplication.application_no}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {selectedApplication.declared_details?.institution_name} &bull; Priority Score: {selectedApplication.risk_score.toFixed(1)}/100
                  </p>
                </div>
                <StatusChip status={selectedApplication.status} type="application" size="sm" />
              </div>

              <FraudSignalsView
                applicationId={selectedApplication.id}
                documents={documents}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function FraudPage() {
  return (
    <Suspense fallback={<div className="p-8 text-xs text-slate-400">Loading Forensics...</div>}>
      <FraudContent />
    </Suspense>
  );
}
