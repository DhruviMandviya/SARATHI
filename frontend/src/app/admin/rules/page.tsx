"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ComplianceRuleItem } from "@/lib/types";
import {
  Settings,
  Scale,
  Plus,
  Edit2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  BookOpen,
  Info,
  Save,
  X,
} from "lucide-react";

export default function AdminRulesPage() {
  const { user } = useAuth();
  const [rules, setRules] = useState<ComplianceRuleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRule, setEditingRule] = useState<ComplianceRuleItem | null>(null);
  const [editParamValue, setEditParamValue] = useState<string>("");
  const [editVerified, setEditVerified] = useState<boolean>(false);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchRules = async () => {
    try {
      setLoading(true);
      const data = await apiRequest<ComplianceRuleItem[]>("/admin/rules?active_only=false");
      setRules(data);
    } catch (err) {
      console.error("Failed to load rules", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const startEdit = (rule: ComplianceRuleItem) => {
    setEditingRule(rule);
    const paramVal = rule.parameters?.min_value ?? rule.parameters?.max_ratio ?? "";
    setEditParamValue(String(paramVal));
    setEditVerified(rule.verified_against_handbook);
  };

  const handleSaveRule = async () => {
    if (!editingRule) return;

    try {
      setSaving(true);
      setSuccessMsg(null);
      const updatedParams = { ...editingRule.parameters };
      if ("min_value" in updatedParams) {
        updatedParams.min_value = parseFloat(editParamValue) || editParamValue;
      } else if ("max_ratio" in updatedParams) {
        updatedParams.max_ratio = parseFloat(editParamValue) || editParamValue;
      }

      await apiRequest(`/admin/rules/${editingRule.id}`, {
        method: "PUT",
        body: JSON.stringify({
          parameters: updatedParams,
          active: true,
          verified_against_handbook: editVerified,
        }),
      });

      setSuccessMsg(`Rule '${editingRule.name}' version incremented and updated non-mutatingly.`);
      setEditingRule(null);
      await fetchRules();
    } catch (err) {
      console.error("Failed to update rule", err);
      alert("Error updating compliance rule.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <Settings className="w-6 h-6 text-[#0A4D2E]" />
            AICTE Regulatory Rule Management (Admin)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure versioned Approval Process Handbook thresholds. Updates are strictly non-mutating with version increments.
          </p>
        </div>
        <button
          onClick={fetchRules}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Rules
        </button>
      </div>

      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Rules Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Configured Regulatory Standards</h3>
          <span className="text-xs text-slate-400 font-mono">{rules.length} total versions</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center">
            <RefreshCw className="w-8 h-8 animate-spin text-slate-400 mb-3" />
            <p className="text-sm">Loading compliance rules...</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {rules.map((rule) => (
              <div key={rule.id} className="p-4 hover:bg-slate-50/70 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{rule.name}</span>
                    <span className="font-mono text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      v{rule.version}
                    </span>
                    {rule.active ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500">
                        Deprecated
                      </span>
                    )}
                    {!rule.verified_against_handbook && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        Unverified placeholder threshold
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 flex items-center gap-2">
                    <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                    <span>{rule.clause}</span>
                    <span>&bull;</span>
                    <span className="italic">{rule.source}</span>
                  </p>
                  <p className="text-xs font-mono text-slate-700">
                    Threshold: {JSON.stringify(rule.parameters)}
                  </p>
                </div>

                {rule.active && (
                  <button
                    onClick={() => startEdit(rule)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors self-end sm:self-center"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    Edit Version
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Edit Rule Modal / Card */}
      {editingRule && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                Update Rule Standard (Creates v{editingRule.version + 1})
              </h3>
              <button
                onClick={() => setEditingRule(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Standard Name:</label>
                <input
                  type="text"
                  disabled
                  value={editingRule.name}
                  className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-100 text-slate-600"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Required Threshold Value ({editingRule.parameters?.unit || "units"}):
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={editParamValue}
                  onChange={(e) => setEditParamValue(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E] font-mono"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="verified_check"
                  checked={editVerified}
                  onChange={(e) => setEditVerified(e.target.checked)}
                  className="w-4 h-4 rounded text-[#0A4D2E] focus:ring-[#0A4D2E]"
                />
                <label htmlFor="verified_check" className="font-semibold text-slate-700 cursor-pointer">
                  Mark Verified against AICTE Approval Process Handbook (Official Gazette)
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setEditingRule(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={saving || !editParamValue}
                onClick={handleSaveRule}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold text-white bg-[#0A4D2E] hover:bg-[#083D24] disabled:opacity-50 transition-colors shadow-sm"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Versioning..." : "Save New Version"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
