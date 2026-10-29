"use client";

import React, { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  History,
  ShieldCheck,
  Search,
  Filter,
  RefreshCw,
  Lock,
  Calendar,
  User,
  Activity,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface AuditLogItem {
  id: number;
  actor_id?: number | null;
  actor_name: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id?: number | null;
  before_state?: Record<string, any> | null;
  after_state?: Record<string, any> | null;
  timestamp: string;
}

export default function AuditTrailPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  // Filters
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [selectedRole, setSelectedRole] = useState<string>("");

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (selectedEntity) params.append("entity_type", selectedEntity);
      if (selectedRole) params.append("actor_role", selectedRole);

      const queryStr = params.toString() ? `?${params.toString()}` : "";
      const data = await apiRequest<AuditLogItem[]>(`/audit${queryStr}`);
      setLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [selectedEntity, selectedRole]);

  const toggleExpand = (id: number) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "official":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#F0FDF4] text-[#0A4D2E] border border-[#86EFAC]">Official</span>;
      case "admin":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">Admin</span>;
      case "auditor":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Auditor</span>;
      case "institution":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Institution</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">System</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2.5">
            <History className="w-6 h-6 text-[#0A4D2E]" />
            Statutory Council Audit Trail (Append-Only Ledger)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable log of all scrutiny decisions, document uploads, verifications, and regulatory rule revisions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-800">
            <Lock className="w-3.5 h-3.5 text-slate-600" />
            Immutable Append-Only
          </span>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-sm transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Controls Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="font-semibold text-slate-700">Filter By:</span>
        </div>

        <div>
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="p-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
          >
            <option value="">All Entity Types</option>
            <option value="application">Application</option>
            <option value="document">Document</option>
            <option value="compliance_rule">Compliance Rule</option>
            <option value="extracted_field">Extracted Field</option>
          </select>
        </div>

        <div>
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="p-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0A4D2E]"
          >
            <option value="">All Actor Roles</option>
            <option value="official">Official</option>
            <option value="admin">Admin</option>
            <option value="auditor">Auditor</option>
            <option value="institution">Institution</option>
            <option value="system">System Background Job</option>
          </select>
        </div>

        <span className="ml-auto text-slate-400 font-mono">
          Showing {logs.length} recorded events
        </span>
      </div>

      {/* Log Entries Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center justify-center">
            <RefreshCw className="w-8 h-8 animate-spin text-slate-400 mb-3" />
            <p className="text-sm">Querying immutable audit log entries...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No audit records found matching the selected filter criteria.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {logs.map((log) => {
              const isExpanded = expandedLogId === log.id;
              const hasState = Boolean(log.before_state || log.after_state);
              return (
                <div key={log.id} className="p-4 hover:bg-slate-50/70 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 p-2 rounded-lg bg-slate-100 border border-slate-200 text-slate-600">
                        <Activity className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                            {log.action}
                          </span>
                          {getRoleBadge(log.actor_role)}
                          <span className="text-xs text-slate-600 font-medium">
                            {log.actor_name}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 flex items-center gap-2">
                          <span>Target: <strong className="text-slate-700 capitalize">{log.entity_type}</strong> #{log.entity_id || "N/A"}</span>
                          <span>&bull;</span>
                          <span className="font-mono">{new Date(log.timestamp).toLocaleString()}</span>
                        </p>
                      </div>
                    </div>

                    {hasState && (
                      <button
                        onClick={() => toggleExpand(log.id)}
                        className="inline-flex items-center gap-1 text-xs text-[#0A4D2E] hover:text-[#083D24] font-semibold self-end sm:self-center"
                      >
                        <span>{isExpanded ? "Hide Details" : "Inspect State"}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>

                  {/* Expanded JSON State Drawer */}
                  {isExpanded && hasState && (
                    <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                      {log.before_state && (
                        <div className="bg-slate-900 text-slate-200 p-3 rounded-lg overflow-x-auto">
                          <span className="text-slate-400 block mb-1 font-bold text-[11px]">Before State:</span>
                          <pre>{JSON.stringify(log.before_state, null, 2)}</pre>
                        </div>
                      )}
                      {log.after_state && (
                        <div className="bg-slate-900 text-emerald-300 p-3 rounded-lg overflow-x-auto">
                          <span className="text-slate-400 block mb-1 font-bold text-[11px]">After State:</span>
                          <pre>{JSON.stringify(log.after_state, null, 2)}</pre>
                        </div>
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
