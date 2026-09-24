"use client";
import { useEffect, useState } from "react";
import { api, AccessRequest } from "@/lib/api";
import { useApp } from "@/components/app-provider";
import { DataTable, StatusBadge, AlertBanner } from "@/components/ui";

export default function RequestedDocuments() {
  const { t, token } = useApp();
  const [scope, setScope] = useState("outgoing");
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"info" | "success" | "error" | "warning">("info");

  const load = () => token && api<AccessRequest[]>(`/access-requests?scope=${scope}`, token).then(setRequests);

  useEffect(() => {
    load();
    setMessage("");
  }, [token, scope]);

  async function decide(id: string, decision: string) {
    if (!token) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/access-requests/${id}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      if (!res.ok) throw new Error();
      setMessage(`Access request successfully ${decision === "GRANTED" ? "granted" : "denied"}.`);
      setMessageType(decision === "GRANTED" ? "success" : "info");
      load();
    } catch {
      setMessage("Failed to update access request.");
      setMessageType("error");
    }
  }

  return (
    <>
      <p className="text-sm text-slate-500">Access coordination</p>
      <h1 className="mt-1 text-2xl font-semibold">{t("requestedDocuments")}</h1>
      {message && <AlertBanner message={message} type={messageType} onDismiss={() => setMessage("")} />}
      <div className="mt-6 flex gap-2">
        <button
          onClick={() => setScope("outgoing")}
          className={`border px-3 py-2 text-sm font-medium transition-colors ${
            scope === "outgoing" ? "bg-accent text-white border-accent" : "bg-white text-slate-700 border-line hover:bg-slate-50"
          }`}
        >
          Outgoing
        </button>
        <button
          onClick={() => setScope("incoming")}
          className={`border px-3 py-2 text-sm font-medium transition-colors ${
            scope === "incoming" ? "bg-accent text-white border-accent" : "bg-white text-slate-700 border-line hover:bg-slate-50"
          }`}
        >
          Incoming
        </button>
      </div>
      <div className="mt-4">
        <DataTable>
          <thead>
            <tr className="table-head">
              <th className="px-3 py-3">Request ID</th>
              <th className="px-3 py-3">Target case</th>
              <th className="px-3 py-3">Reason</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">Requested at</th>
              <th className="px-3 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((r) => (
              <tr className="border-b" key={r.id}>
                <td className="px-3 py-3 font-mono text-xs">{r.id.slice(0, 8)}</td>
                <td className="px-3 py-3">{r.case_id}</td>
                <td className="px-3 py-3">{r.reason}</td>
                <td className="px-3 py-3">
                  <StatusBadge value={r.status} />
                </td>
                <td className="px-3 py-3">{new Date(r.created_at).toLocaleString()}</td>
                <td className="px-3 py-3">
                  {scope === "incoming" && r.status === "PENDING" && (
                    <>
                      <button onClick={() => decide(r.id, "GRANTED")} className="mr-3 font-semibold text-emerald-700 hover:underline">
                        Grant
                      </button>
                      <button onClick={() => decide(r.id, "DENIED")} className="font-semibold text-red-700 hover:underline">
                        Deny
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!requests.length && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                  No requests found.
                </td>
              </tr>
            )}
          </tbody>
        </DataTable>
      </div>
    </>
  );
}
