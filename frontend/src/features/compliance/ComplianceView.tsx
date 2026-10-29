"use client";

import React, { useState, useEffect } from "react";
import { ComplianceResultItem } from "@/lib/types";
import { apiRequest } from "@/lib/api";
import {
  Scale,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  BookOpen,
  Info,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

interface ComplianceViewProps {
  applicationId: number;
}

export const ComplianceView: React.FC<ComplianceViewProps> = ({ applicationId }) => {
  const [results, setResults] = useState<ComplianceResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [reEvaluating, setReEvaluating] = useState(false);

  const fetchCompliance = async (force: boolean = false) => {
    try {
      if (force) setReEvaluating(true);
      else setLoading(true);

      const data = await apiRequest<ComplianceResultItem[]>(
        `/applications/${applicationId}/compliance${force ? "?re_evaluate=true" : ""}`
      );
      setResults(data);
    } catch (err) {
      console.error("Failed to fetch compliance evaluation", err);
    } finally {
      setLoading(false);
      setReEvaluating(false);
    }
  };

  useEffect(() => {
    fetchCompliance();
  }, [applicationId]);

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case "compliant":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Compliant
          </span>
        );
      case "non_compliant":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
            Non-Compliant
          </span>
        );
      case "needs_update":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">
            <Clock className="w-3.5 h-3.5 text-[#0A4D2E]" />
            Needs Update
          </span>
        );
      case "needs_review":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Info className="w-3.5 h-3.5 text-amber-600" />
            Needs Review
          </span>
        );
    }
  };

  const compliantCount = results.filter((r) => r.outcome === "compliant").length;
  const nonCompliantCount = results.filter((r) => r.outcome === "non_compliant").length;
  const reviewCount = results.filter((r) => r.outcome === "needs_review").length;

  return (
    <div className="space-y-6">
      {/* Top Header & Summary Stats */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Scale className="w-5 h-5 text-[#0A4D2E]" />
              AICTE Regulatory Compliance Matrix
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated deterministic verification against versioned Council standards and Approval Process Handbook clauses.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchCompliance(true)}
              disabled={reEvaluating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${reEvaluating ? "animate-spin" : ""}`} />
              Re-Evaluate Rules
            </button>
          </div>
        </div>

        {/* Aggregate KPI counters */}
        <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-100">
          <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg p-3 text-center">
            <span className="text-xs text-emerald-700 font-medium">Compliant Clauses</span>
            <p className="text-xl font-bold text-emerald-800 mt-0.5">{compliantCount}</p>
          </div>
          <div className="bg-rose-50/60 border border-rose-100 rounded-lg p-3 text-center">
            <span className="text-xs text-rose-700 font-medium">Deficiencies / Non-Compliant</span>
            <p className="text-xl font-bold text-rose-800 mt-0.5">{nonCompliantCount}</p>
          </div>
          <div className="bg-amber-50/60 border border-amber-100 rounded-lg p-3 text-center">
            <span className="text-xs text-amber-700 font-medium">Missing / Needs Review</span>
            <p className="text-xl font-bold text-amber-800 mt-0.5">{reviewCount}</p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center">
          <RefreshCw className="w-8 h-8 animate-spin text-slate-400 mb-3" />
          <p className="text-sm">Evaluating active regulatory clauses against institutional records...</p>
        </div>
      ) : results.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <BookOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <h3 className="text-sm font-semibold text-slate-700">No Compliance Rules Evaluated</h3>
          <p className="text-xs text-slate-500 mt-1">
            Click &quot;Re-Evaluate Rules&quot; above to run the compliance engine on declared institutional details.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {results.map((res) => {
            const rule = res.rule;
            return (
              <div
                key={res.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-slate-300 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h4 className="text-sm font-bold text-slate-900">
                        {rule?.name || `Rule #${res.rule_id}`}
                      </h4>
                      {rule && !rule.verified_against_handbook && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          Unverified placeholder threshold
                        </span>
                      )}
                      <span className="text-[11px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        v{res.rule_version}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                      <span>{rule?.clause || "Clause Reference"}</span>
                      <span>&bull;</span>
                      <span className="italic">{rule?.source || "AICTE APH"}</span>
                    </p>
                  </div>
                  <div>{getOutcomeBadge(res.outcome)}</div>
                </div>

                {/* Values comparison block */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 rounded-lg p-3 border border-slate-100 text-xs mb-3">
                  <div>
                    <span className="text-slate-400 block text-[11px] mb-0.5">Statutory Requirement:</span>
                    <span className="font-semibold text-slate-800">{res.required_value}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px] mb-0.5">Provided / Extracted Value:</span>
                    <span className="font-semibold text-slate-800">
                      {res.provided_value || "None detected"}
                    </span>
                  </div>
                </div>

                {/* Detailed Explanation */}
                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50/50 p-2.5 rounded-lg border border-slate-100">
                  {res.explanation}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
