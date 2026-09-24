"use client";

import { useState } from "react";
import Link from "next/link";
import { Flag, CheckCircle2, Trash2, X, AlertTriangle, User, Clock, FileText, Sparkles, MapPin, Building2, HelpCircle } from "lucide-react";
import { apiPost, apiDelete, InvestigationFlag, User as UserType } from "@/lib/api";
import { StatusBadge, EmptyState } from "@/components/ui";

interface FlagModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseNumber: string;
  token: string;
  resourceType: string;
  resourceId: string;
  resourceLabel: string;
  onSuccess: (flag: InvestigationFlag) => void;
}

export function FlagModal({
  isOpen,
  onClose,
  caseNumber,
  token,
  resourceType,
  resourceId,
  resourceLabel,
  onSuccess,
}: FlagModalProps) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Please provide a reason or note for flagging this item.");
      return;
    }
    setSubmitting(true);
    setError("");

    try {
      const created = await apiPost<InvestigationFlag>(`/cases/${caseNumber}/flags`, token, {
        resource_type: resourceType,
        resource_id: resourceId,
        resource_label: resourceLabel,
        reason: reason.trim(),
      });
      setReason("");
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to flag item.");
    } finally {
      setSubmitting(false);
    }
  }

  const typeLabels: Record<string, { label: string; color: string }> = {
    EVIDENCE: { label: "Evidence Document", color: "bg-slate-100 text-slate-800 border-slate-300" },
    ENTITY: { label: "Entity / Subject", color: "bg-sky-50 text-sky-800 border-sky-300" },
    EVENT: { label: "Timeline Event", color: "bg-indigo-50 text-indigo-800 border-indigo-300" },
    INTELLIGENCE: { label: "Intelligence Finding", color: "bg-purple-50 text-purple-800 border-purple-300" },
  };

  const badgeInfo = typeLabels[resourceType.toUpperCase()] || {
    label: resourceType,
    color: "bg-slate-100 text-slate-800 border-slate-300",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between border-b border-line pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-amber-800">
              <Flag className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">Flag for Investigator Review</h3>
              <p className="text-xs text-slate-500">Attach an investigative review marker to this record</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="rounded border border-slate-200 bg-slate-50/80 p-3 text-xs space-y-1.5">
            <div className="flex items-center gap-2">
              <span className={`inline-block px-2 py-0.5 rounded font-bold uppercase text-[10px] border ${badgeInfo.color}`}>
                {badgeInfo.label}
              </span>
              <span className="font-mono text-slate-500">{resourceId}</span>
            </div>
            <p className="font-semibold text-slate-900 text-sm truncate">{resourceLabel}</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Investigator Reason / Review Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Describe the discrepancy, pattern, verification need, or reason for review (e.g. Cross-reference vehicle timestamps with surveillance log near Warehouse 14)..."
              rows={4}
              required
              disabled={submitting}
              className="w-full rounded border border-line p-3 text-xs text-slate-800 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="rounded border border-amber-200/80 bg-amber-50/50 p-2.5 text-[11px] text-amber-900 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
            <span>
              <strong>Note:</strong> A flag is an internal investigator review marker and does not constitute a legal finding or assertion of criminal liability.
            </span>
          </div>

          {error && (
            <p className="text-xs font-medium text-red-600 bg-red-50 p-2 rounded border border-red-200">
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 text-xs font-semibold rounded shadow-xs transition-colors disabled:opacity-60"
            >
              <Flag className="h-3.5 w-3.5" />
              <span>{submitting ? "Saving Flag..." : "Flag Item"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface ResolveModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseNumber: string;
  token: string;
  flag: InvestigationFlag | null;
  onSuccess: (updated: InvestigationFlag) => void;
}

export function ResolveFlagModal({
  isOpen,
  onClose,
  caseNumber,
  token,
  flag,
  onSuccess,
}: ResolveModalProps) {
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen || !flag) return null;

  async function handleResolve(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const updated = await apiPost<InvestigationFlag>(
        `/cases/${caseNumber}/flags/${flag?.id}/resolve`,
        token,
        {
          status: "RESOLVED",
          resolution_notes: resolutionNotes.trim() || "Investigator review completed and resolved.",
        }
      );
      setResolutionNotes("");
      onSuccess(updated);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to resolve flag.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between border-b border-line pb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">Resolve Investigation Flag</h3>
              <p className="text-xs text-slate-500">Mark this review item as verified/resolved</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleResolve} className="mt-4 space-y-4">
          <div className="rounded border border-slate-200 bg-slate-50/80 p-3 text-xs space-y-1.5">
            <p className="font-semibold text-slate-900 text-sm">{flag.resource_label}</p>
            <div className="text-slate-600">
              <span className="font-medium text-slate-700">Flag Reason:</span> {flag.reason}
            </div>
            <div className="text-[11px] text-slate-400">
              Flagged by {flag.flagged_by?.name || "Investigator"} on {new Date(flag.created_at).toLocaleDateString()}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Resolution Notes & Outcome
            </label>
            <textarea
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="e.g. Cross-referenced with primary ledger, bank statements confirmed, or duplicate record reconciled..."
              rows={3}
              disabled={submitting}
              className="w-full rounded border border-line p-3 text-xs text-slate-800 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {error && (
            <p className="text-xs font-medium text-red-600 bg-red-50 p-2 rounded border border-red-200">
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2 text-xs font-semibold rounded shadow-xs transition-colors disabled:opacity-60"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>{submitting ? "Resolving..." : "Mark Resolved"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function FlaggedItemsList({
  flags,
  caseNumber,
  token,
  onRefresh,
  onOpenFlagModal,
}: {
  flags: InvestigationFlag[];
  caseNumber: string;
  token: string;
  onRefresh: () => void;
  onOpenFlagModal?: () => void;
}) {
  const [filter, setFilter] = useState<"ALL" | "ACTIVE" | "RESOLVED">("ALL");
  const [resolvingFlag, setResolvingFlag] = useState<InvestigationFlag | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState("");

  const filtered = flags.filter((f) => {
    if (filter === "ALL") return true;
    return f.status.toUpperCase() === filter;
  });

  async function handleDelete(flag: InvestigationFlag) {
    if (!confirm(`Are you sure you want to remove this flag on "${flag.resource_label}"?`)) {
      return;
    }
    setBusyId(flag.id);
    try {
      await apiDelete(`/cases/${caseNumber}/flags/${flag.id}`, token);
      setActionMessage("Flag removed successfully.");
      onRefresh();
    } catch (err: any) {
      alert(err.message || "Failed to remove flag.");
    } finally {
      setBusyId(null);
    }
  }

  const typeStyles: Record<string, { label: string; icon: any; color: string }> = {
    EVIDENCE: { label: "Evidence", icon: FileText, color: "bg-slate-100 text-slate-800 border-slate-200" },
    ENTITY: { label: "Entity", icon: User, color: "bg-sky-50 text-sky-800 border-sky-200" },
    EVENT: { label: "Timeline Event", icon: Clock, color: "bg-indigo-50 text-indigo-800 border-indigo-200" },
    INTELLIGENCE: { label: "Finding", icon: Sparkles, color: "bg-purple-50 text-purple-800 border-purple-200" },
  };

  const activeCount = flags.filter((f) => f.status.toUpperCase() === "ACTIVE").length;
  const resolvedCount = flags.filter((f) => f.status.toUpperCase() === "RESOLVED").length;

  return (
    <section className="mt-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
            <Flag className="h-5 w-5 text-amber-600" />
            <span>Investigator Review Flags</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Internal review markers and investigation checkpoints attached to case records
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded border border-line bg-slate-100 p-0.5 text-xs font-semibold">
            <button
              onClick={() => setFilter("ALL")}
              className={`px-3 py-1 rounded transition-colors ${
                filter === "ALL" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              All ({flags.length})
            </button>
            <button
              onClick={() => setFilter("ACTIVE")}
              className={`px-3 py-1 rounded transition-colors ${
                filter === "ACTIVE" ? "bg-amber-100 text-amber-900 font-bold shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Active ({activeCount})
            </button>
            <button
              onClick={() => setFilter("RESOLVED")}
              className={`px-3 py-1 rounded transition-colors ${
                filter === "RESOLVED" ? "bg-emerald-100 text-emerald-900 font-bold shadow-xs" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Resolved ({resolvedCount})
            </button>
          </div>
        </div>
      </div>

      {!filtered.length ? (
        <EmptyState
          title="No flagged items"
          body={
            filter === "ALL"
              ? "No items have been flagged for review in this case yet. You can flag Evidence, Entities, Timeline Events, or Intelligence Findings using the 'Flag for Review' action."
              : `No items found with status '${filter}'.`
          }
        />
      ) : (
        <div className="grid gap-4">
          {filtered.map((flag) => {
            const style = typeStyles[flag.resource_type.toUpperCase()] || {
              label: flag.resource_type,
              icon: Flag,
              color: "bg-slate-100 text-slate-800 border-slate-200",
            };
            const Icon = style.icon;
            const isActive = flag.status.toUpperCase() === "ACTIVE";

            return (
              <article
                key={flag.id}
                className={`panel p-5 transition-all border ${
                  isActive
                    ? "border-amber-200 bg-white hover:shadow-md"
                    : "border-slate-200 bg-slate-50/40 opacity-80 hover:opacity-100"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1.5 flex-1 min-w-[260px]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center gap-1 border px-2 py-0.5 text-xs font-bold uppercase rounded ${style.color}`}>
                        <Icon className="h-3 w-3" />
                        <span>{style.label}</span>
                      </span>
                      <span className="font-mono text-xs text-slate-500">{flag.resource_id}</span>
                      <StatusBadge value={flag.status} />
                    </div>

                    <h3 className="text-base font-semibold text-slate-900">
                      {flag.resource_type.toUpperCase() === "EVIDENCE" ? (
                        <Link
                          href={`/evidence/${flag.resource_id}`}
                          className="hover:text-accent hover:underline inline-flex items-center gap-1"
                        >
                          <span>{flag.resource_label}</span>
                          <span className="text-xs text-accent">↗</span>
                        </Link>
                      ) : (
                        flag.resource_label
                      )}
                    </h3>

                    <div className="mt-2 rounded bg-slate-50 border border-slate-200 p-3 text-xs text-slate-800">
                      <p className="font-semibold text-slate-700 mb-0.5">Review Note / Reason:</p>
                      <p className="leading-relaxed">{flag.reason}</p>
                    </div>

                    {flag.resolved_at && (
                      <div className="mt-2 rounded bg-emerald-50/60 border border-emerald-200 p-2.5 text-xs text-emerald-900">
                        <div className="flex items-center gap-1.5 font-bold mb-0.5">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
                          <span>Resolved by {flag.resolved_by?.name || "Investigator"}</span>
                          <span className="text-[11px] font-normal text-emerald-700 font-mono">
                            ({new Date(flag.resolved_at).toLocaleString()})
                          </span>
                        </div>
                        {flag.resolution_notes && (
                          <p className="text-[11px] text-emerald-800 leading-snug">
                            {flag.resolution_notes}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col items-end gap-3 text-right">
                    <div className="text-[11px] text-slate-500 font-mono space-y-0.5">
                      <div>
                        Flagged by: <strong>{flag.flagged_by?.name || "Investigator"}</strong>
                      </div>
                      <div>{new Date(flag.created_at).toLocaleString()}</div>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      {isActive && (
                        <button
                          onClick={() => setResolvingFlag(flag)}
                          disabled={busyId === flag.id}
                          className="flex items-center gap-1 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition-colors shadow-2xs"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Resolve</span>
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(flag)}
                        disabled={busyId === flag.id}
                        className="flex items-center gap-1 text-slate-500 hover:text-red-700 hover:bg-red-50 text-xs font-medium px-2.5 py-1.5 rounded transition-colors border border-transparent hover:border-red-200"
                        title="Remove flag"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        <span>Remove</span>
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {resolvingFlag && (
        <ResolveFlagModal
          isOpen={true}
          onClose={() => setResolvingFlag(null)}
          caseNumber={caseNumber}
          token={token}
          flag={resolvingFlag}
          onSuccess={() => {
            onRefresh();
          }}
        />
      )}
    </section>
  );
}
