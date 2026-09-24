"use client";
import { useEffect, useState } from "react";
import { api, AuditEvent } from "@/lib/api";
import { EmptyState, StatusBadge } from "@/components/ui";
import { useApp } from "@/components/app-provider";

function formatAction(action: string): string {
  if (!action) return "-";
  return action
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export default function EvidenceAudit() {
  const { t, token } = useApp();
  const [events, setEvents] = useState<AuditEvent[]>([]);

  useEffect(() => {
    if (token) {
      api<AuditEvent[]>("/audit-events", token)
        .then(setEvents)
        .catch(() => setEvents([]));
    }
  }, [token]);

  return (
    <>
      <p className="text-sm text-slate-500">Security and accountability</p>
      <h1 className="mt-1 text-2xl font-semibold text-ink">{t("evidenceAudit")}</h1>
      <section className="panel mt-7 p-5">
        <h2 className="font-semibold">{t("auditTrail")}</h2>
        {events.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[750px] text-sm text-left">
              <thead className="table-head border-b border-line text-xs uppercase tracking-wider text-slate-500 font-medium">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Investigator</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {events.map((event) => (
                  <tr className="hover:bg-slate-50/50 transition-colors" key={event.id}>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-600 font-mono text-xs">
                      {new Date(event.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      {event.actor ? (
                        <div>
                          <div className="font-medium text-slate-900">{event.actor.name}</div>
                          <div className="text-xs text-slate-500 font-mono">
                            {event.actor.investigator_id} · <span className="capitalize">{event.actor.role.toLowerCase()}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="italic text-slate-400 text-xs">Unknown / Legacy Record</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {formatAction(event.action)}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        {event.resource_id ? (
                          <div className="font-mono text-xs text-slate-800 font-medium">{event.resource_id}</div>
                        ) : event.case_number ? (
                          <div className="font-mono text-xs text-slate-800 font-medium">{event.case_number}</div>
                        ) : (
                          <div className="font-mono text-xs text-slate-700">{event.resource_type}</div>
                        )}
                        {(event.case_number && event.resource_id && event.resource_id !== event.case_number) ? (
                          <div className="text-xs text-slate-500 font-mono">Case: {event.case_number}</div>
                        ) : event.resource_id ? (
                          <div className="text-xs text-slate-500 capitalize">{event.resource_type.toLowerCase()}</div>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={event.result} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-4">
            <EmptyState
              title="No audit events available"
              body="Security-relevant actions will appear here as the workflow expands."
            />
          </div>
        )}
      </section>
    </>
  );
}

