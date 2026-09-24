"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  api,
  apiPost,
  base,
  Case,
  Evidence,
  getProcessingMethod,
  IntelligenceEntity,
  InvestigationFlag,
  RelatedCase,
  Resolution,
} from "@/lib/api";
import { useApp } from "@/components/app-provider";
import { DataTable, EmptyState, StatusBadge, AlertBanner } from "@/components/ui";
import { IntelligenceView, KnowledgeGraph, TimelineView } from "@/components/knowledge-graph";
import { Copilot } from "@/components/copilot";
import { FlagModal, FlaggedItemsList } from "@/components/flag-modal";
import { Download, FileText, Flag, User, Clock, Sparkles } from "lucide-react";

export default function CasePage() {
  const { t, token } = useApp();
  const { caseNumber } = useParams<{ caseNumber: string }>();
  const [item, setItem] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [related, setRelated] = useState<RelatedCase[]>([]);
  const [entities, setEntities] = useState<IntelligenceEntity[]>([]);
  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [flags, setFlags] = useState<InvestigationFlag[]>([]);
  const [tab, setTab] = useState("info");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"info" | "success" | "error" | "warning">("info");
  const [uploading, setUploading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [entityTypeFilter, setEntityTypeFilter] = useState("ALL");
  const [flagModalTarget, setFlagModalTarget] = useState<{
    resourceType: string;
    resourceId: string;
    resourceLabel: string;
  } | null>(null);

  async function load() {
    if (!token) return;
    const [nextCase, nextEvidence, nextRelated, nextEntities, nextResolutions, nextFlags] = await Promise.all([
      api<Case>(`/cases/${caseNumber}`, token),
      api<Evidence[]>(`/cases/${caseNumber}/evidence`, token),
      api<RelatedCase[]>(`/cases/${caseNumber}/related`, token),
      api<IntelligenceEntity[]>(`/cases/${caseNumber}/entities`, token),
      api<Resolution[]>(`/entity-resolutions?n=${caseNumber}`, token),
      api<InvestigationFlag[]>(`/cases/${caseNumber}/flags`, token).catch(() => []),
    ]);
    setItem(nextCase);
    setEvidence(nextEvidence);
    setRelated(nextRelated);
    setEntities(nextEntities);
    setResolutions(nextResolutions);
    setFlags(nextFlags || []);
  }

  useEffect(() => {
    load().catch(() => {
      setMessage("Case data could not be loaded.");
      setMessageType("error");
    });
  }, [token, caseNumber]);

  useEffect(() => {
    setMessage("");
  }, [tab]);

  const flaggedResourceIds = useMemo(() => {
    const set = new Set<string>();
    for (const f of flags) {
      if (f.status.toUpperCase() === "ACTIVE") {
        set.add(f.resource_id);
      }
    }
    return set;
  }, [flags]);

  const activeFlagCount = useMemo(() => {
    return flags.filter((f) => f.status.toUpperCase() === "ACTIVE").length;
  }, [flags]);

  if (!item) return <p className="text-sm text-slate-500">Loading case record...</p>;

  const tabs = [
    ["info", "caseInformation"],
    ["evidence", "evidenceDocuments"],
    ["entities", "entities"],
    ["graph", "knowledgeGraph"],
    ["timeline", "timeline"],
    ["intelligence", "intelligence"],
    ["flags", "investigatorFlags"],
    ["copilot", "copilot"],
  ] as const;

  async function downloadPdfReport() {
    if (!token || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const response = await fetch(`${base}/cases/${caseNumber}/report.pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`Failed to generate PDF report (status ${response.status})`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${caseNumber}-Investigation-Report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setMessage("Investigation report PDF generated and downloaded successfully.");
      setMessageType("success");
    } catch (err: any) {
      setMessage(err.message || "Failed to download PDF report.");
      setMessageType("error");
    } finally {
      setDownloadingPdf(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || uploading) return;
    const form = event.currentTarget;
    const fileInput = form.querySelector<HTMLInputElement>('input[type="file"]');
    const files = fileInput?.files ? Array.from(fileInput.files) : [];
    if (!files.length) return;

    setUploading(true);
    setMessage(`Uploading and processing ${files.length} evidence file(s)...`);
    setMessageType("info");

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }
      const langInput = form.querySelector<HTMLInputElement>('input[name="document_language"]');
      const notesInput = form.querySelector<HTMLInputElement>('input[name="notes"]');
      if (langInput?.value) formData.append("document_language", langInput.value);
      if (notesInput?.value) formData.append("notes", notesInput.value);

      if (files.length > 1) {
        await apiPost<Evidence[]>(`/cases/${caseNumber}/evidence/batch`, token, formData);
      } else {
        await apiPost<Evidence>(`/cases/${caseNumber}/evidence`, token, formData);
      }

      setMessage(`Successfully uploaded and processed ${files.length} evidence file(s). All entities, relationships, and events generated.`);
      setMessageType("success");
      form.reset();
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Evidence upload/processing failed.");
      setMessageType("error");
    } finally {
      setUploading(false);
    }
  }

  async function requestAccess(number: string) {
    if (!token) return;
    try {
      await apiPost("/access-requests", token, { case_number: number, reason: "Access required to assess the related investigation." });
      setMessage("Access request submitted.");
      setMessageType("success");
    } catch {
      setMessage("Access request could not be submitted.");
      setMessageType("error");
    }
  }

  async function reviewResolution(id: string, decision: "confirm" | "reject") {
    if (!token) return;
    try {
      await apiPost(`/entity-resolutions/${id}/${decision}`, token, {});
      setMessage(decision === "confirm" ? "Entity match confirmed." : "Entity match rejected.");
      setMessageType(decision === "confirm" ? "success" : "info");
      await load();
    } catch {
      setMessage("Failed to update entity resolution.");
      setMessageType("error");
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/cases" className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-ink">
          <span aria-hidden="true">&larr;</span>
          <span>{t("cases")}</span>
        </Link>
        <button
          onClick={downloadPdfReport}
          disabled={downloadingPdf}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded shadow-xs transition-colors disabled:opacity-60 cursor-pointer"
          title="Export official multi-page investigation report in PDF format"
        >
          {downloadingPdf ? (
            <>
              <span className="inline-block h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              <span>Generating PDF Report...</span>
            </>
          ) : (
            <>
              <Download className="h-3.5 w-3.5 text-slate-300" />
              <span>Export PDF Report</span>
            </>
          )}
        </button>
      </div>

      <header className="mt-4 border-b border-line pb-6">
        <p className="text-sm font-semibold tracking-wide text-slate-500">{item.case_number}</p>
        <h1 className="mt-1 text-2xl font-semibold text-ink">{item.title}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge value={item.status} />
          <StatusBadge value={item.priority} />
          <span className="text-sm text-slate-600">
            {t("lead")}: <b>{item.lead_investigator?.name}</b>
          </span>
          {activeFlagCount > 0 && (
            <span
              onClick={() => setTab("flags")}
              className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 cursor-pointer hover:bg-amber-200 transition-colors"
            >
              <Flag className="h-3 w-3 text-amber-700" />
              <span>{activeFlagCount} Active Flag{activeFlagCount > 1 ? "s" : ""}</span>
            </span>
          )}
        </div>
      </header>

      <nav className="mt-5 flex overflow-x-auto border-b border-line">
        {tabs.map(([id, label]) => {
          const isActive = tab === id;
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium flex items-center gap-2 ${
                isActive ? "border-accent text-accent" : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              <span>{t(label)}</span>
              {id === "flags" && activeFlagCount > 0 && (
                <span className="rounded-full bg-amber-100 text-amber-900 border border-amber-300 px-1.5 py-0.2 text-[11px] font-bold">
                  {activeFlagCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {message && <AlertBanner message={message} type={messageType} onDismiss={() => setMessage("")} />}

      {tab === "info" && (
        <section className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_.7fr]">
          <div className="panel p-6">
            <h2 className="text-lg font-semibold">{t("caseInformation")}</h2>
            <dl className="mt-5 grid gap-5 sm:grid-cols-2">
              {[
                [t("caseId"), item.case_number],
                [t("caseTitle"), item.title],
                [t("lead"), item.lead_investigator?.name || "-"],
                [t("assigned"), item.assignments?.map((assignment) => assignment.user.name).join(", ") || "-"],
                ["Evidence count", evidence.length],
                ["Key entities", entities.length],
                ["Active review flags", activeFlagCount],
                ["Related cases", related.length],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-900">{value}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-6 border-t border-line pt-4">
              <h3 className="font-semibold">{t("caseSummary")}</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{item.summary}</p>
            </div>
          </div>
          <aside className="space-y-4">
            {related.map((relatedCase) => (
              <div key={relatedCase.case_number} className="border border-line p-5 rounded panel">
                <p className="font-semibold text-slate-900">{relatedCase.case_number} · {relatedCase.title}</p>
                <p className="mt-1 text-sm text-slate-600">{relatedCase.investigating_officer}</p>
                {relatedCase.access_level === "RESTRICTED" ? (
                  <>
                    <p className="mt-3 text-sm font-medium text-amber-800">{t("restricted")}</p>
                    <button
                      onClick={() => requestAccess(relatedCase.case_number)}
                      className="mt-3 border border-amber-300 px-3 py-2 text-sm rounded bg-amber-50 hover:bg-amber-100 font-semibold text-amber-900 transition-colors"
                    >
                      {t("requestAccess")}
                    </button>
                  </>
                ) : (
                  <Link href={`/cases/${relatedCase.case_number}`} className="mt-3 inline-block text-sm font-medium text-accent hover:underline">
                    Open case →
                  </Link>
                )}
              </div>
            ))}
          </aside>
        </section>
      )}

      {tab === "evidence" && (
        <section className="mt-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-lg font-semibold">{t("evidenceDocuments")}</h2>
            <details className="group relative">
              <summary className="cursor-pointer bg-accent hover:bg-sky-700 px-4 py-2 text-sm font-semibold text-white rounded transition-colors">
                {uploading ? "Processing Evidence..." : "+ Upload & Auto-Process Evidence"}
              </summary>
              <form onSubmit={upload} className="panel mt-2 grid gap-3 p-5 shadow-lg border border-slate-300 w-full sm:w-[480px] bg-white">
                <div className="border-b border-line pb-2">
                  <h3 className="text-sm font-bold text-slate-900">Multi-Format Evidence Ingestion</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Select multiple files (PDF, CSV, XLSX, PNG, TXT, JSON, XML). All files will be automatically ingested, parsed/OCRed, registered for integrity, and mapped to entities & relationships.
                  </p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Select Files (Hold Ctrl / Shift to pick multiple):</label>
                  <input
                    name="files"
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.txt,.doc,.docx,.csv,.xls,.xlsx,.json,.xml"
                    required
                    disabled={uploading}
                    className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-accent hover:file:bg-sky-100 cursor-pointer border border-line p-2 rounded"
                  />
                </div>
                <input
                  name="document_language"
                  placeholder="Document language (optional, e.g. en, hi)"
                  className="border border-line px-3 py-2 text-xs rounded"
                  disabled={uploading}
                />
                <input
                  name="notes"
                  placeholder="Investigation notes / chain of custody (optional)"
                  className="border border-line px-3 py-2 text-xs rounded"
                  disabled={uploading}
                />
                <button
                  type="submit"
                  disabled={uploading}
                  className="bg-ink hover:bg-slate-800 px-4 py-2.5 text-sm font-bold text-white rounded disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <>
                      <span className="inline-block h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                      <span>Processing All Evidence...</span>
                    </>
                  ) : (
                    <span>Upload & Start Ingestion</span>
                  )}
                </button>
              </form>
            </details>
          </div>
          <div className="mt-4">
            <DataTable>
              <thead>
                <tr className="table-head">
                  <th className="px-3 py-3">Evidence ID</th>
                  <th className="px-3 py-3">Document</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Processing Method</th>
                  <th className="px-3 py-3">Processing Status</th>
                  <th className="px-3 py-3">Review Flag</th>
                  <th className="px-3 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((current) => {
                  const isFlagged = flaggedResourceIds.has(current.evidence_id);
                  return (
                    <tr className="border-b border-line hover:bg-slate-50/50 transition-colors" key={current.evidence_id}>
                      <td className="px-3 py-3 font-mono text-xs font-semibold text-slate-800">{current.evidence_id}</td>
                      <td className="px-3 py-3 font-medium text-slate-900">{current.filename}</td>
                      <td className="px-3 py-3 font-mono text-xs text-slate-600">{current.document_type}</td>
                      <td className="px-3 py-3 text-xs font-semibold text-slate-700">{getProcessingMethod(current)}</td>
                      <td className="px-3 py-3">
                        <StatusBadge value={current.processing_status} />
                      </td>
                      <td className="px-3 py-3">
                        {isFlagged ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded">
                            <Flag className="h-3 w-3 text-amber-700" />
                            <span>Flagged</span>
                          </span>
                        ) : (
                          <button
                            onClick={() =>
                              setFlagModalTarget({
                                resourceType: "EVIDENCE",
                                resourceId: current.evidence_id,
                                resourceLabel: `${current.evidence_id} (${current.filename})`,
                              })
                            }
                            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-amber-800 hover:bg-amber-50 px-2 py-1 rounded transition-colors"
                            title="Flag this evidence for review"
                          >
                            <Flag className="h-3 w-3 text-slate-400" />
                            <span>Flag</span>
                          </button>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <Link href={`/evidence/${current.evidence_id}`} className="font-medium text-accent hover:underline">
                          {t("viewDocument")}
                        </Link>
                      </td>
                    </tr>
                  );
                })}
                {!evidence.length && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No evidence has been uploaded. Click "+ Upload & Auto-Process Evidence" to begin.
                    </td>
                  </tr>
                )}
              </tbody>
            </DataTable>
          </div>
        </section>
      )}

      {tab === "entities" && (
        <section className="mt-6 space-y-6">
          {resolutions.length > 0 && (
            <div className="panel border-l-4 border-l-amber-500 p-5 bg-amber-50/20">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200/60 pb-3">
                <div>
                  <h3 className="font-semibold text-sm uppercase tracking-wide text-amber-900 flex items-center gap-2">
                    <span>⚡ Entity Match Review</span>
                    <span className="bg-amber-200 text-amber-900 text-xs px-2 py-0.5 rounded-full font-bold">
                      {resolutions.length} Pending
                    </span>
                  </h3>
                  <p className="text-xs text-amber-800/80 mt-0.5">
                    Suggested entity resolutions requiring investigator confirmation.
                  </p>
                </div>
              </div>
              <div className="mt-4 max-h-[320px] overflow-y-auto space-y-3 pr-1">
                {resolutions.map((resolution) => (
                  <article
                    key={resolution.id}
                    className="panel p-4 bg-white border border-amber-200 shadow-sm flex flex-wrap items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-medium text-sm text-slate-900">
                        <span className="bg-slate-100 border border-line px-2 py-0.5 rounded text-xs font-semibold">
                          {resolution.source.entity_type}
                        </span>
                        <span>{resolution.source.text}</span>
                        <span className="text-amber-600 font-bold">↔</span>
                        <span>{resolution.target.text}</span>
                      </div>
                      <p className="text-xs text-slate-500">
                        Confidence: <strong className="text-slate-800">{Math.round(resolution.confidence * 100)}%</strong>
                        {resolution.reasons.length > 0 && <span> · {resolution.reasons.join(", ")}</span>}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => reviewResolution(resolution.id, "confirm")}
                        className="bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold px-3 py-1.5 rounded transition-colors"
                      >
                        Confirm Match
                      </button>
                      <button
                        onClick={() => reviewResolution(resolution.id, "reject")}
                        className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded transition-colors"
                      >
                        Reject Match
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Entity Summary & Categories</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              <button
                onClick={() => setEntityTypeFilter("ALL")}
                className={`panel p-3 text-left transition-all ${
                  entityTypeFilter === "ALL" ? "ring-2 ring-accent border-transparent bg-sky-50/50" : "hover:border-slate-400"
                }`}
              >
                <p className="text-xs font-semibold uppercase text-slate-500">Total Entities</p>
                <p className="text-2xl font-bold text-slate-900 mt-1">{entities.length}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">All types</p>
              </button>
              {Object.entries(
                entities.reduce((acc, ent) => {
                  const type = ent.entity_type;
                  acc[type] = (acc[type] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>)
              ).map(([type, count]) => (
                <button
                  key={type}
                  onClick={() => setEntityTypeFilter(entityTypeFilter === type ? "ALL" : type)}
                  className={`panel p-3 text-left transition-all ${
                    entityTypeFilter === type ? "ring-2 ring-accent border-transparent bg-sky-50/50" : "hover:border-slate-400"
                  }`}
                >
                  <p className="text-xs font-semibold uppercase text-slate-500">{type}</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{count}</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Canonical items</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-700">
                Extracted Canonical Entities {entityTypeFilter !== "ALL" && `(${entityTypeFilter})`}
              </h3>
              <span className="text-xs text-slate-500">
                Showing {entities.filter((e) => entityTypeFilter === "ALL" || e.entity_type === entityTypeFilter).length} entities
              </span>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {entities
                .filter((entity) => entityTypeFilter === "ALL" || entity.entity_type === entityTypeFilter)
                .map((entity) => {
                  const isFlagged = flaggedResourceIds.has(entity.id) || flaggedResourceIds.has(entity.canonical_name);
                  return (
                    <article className={`panel p-5 relative hover:shadow-sm transition-shadow ${isFlagged ? "border-amber-300 bg-amber-50/15" : ""}`} key={entity.id}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <span className="inline-flex border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-bold uppercase text-slate-700">
                            {entity.entity_type}
                          </span>
                          <h4 className="mt-2 text-base font-semibold text-slate-900">{entity.canonical_name}</h4>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              setFlagModalTarget({
                                resourceType: "ENTITY",
                                resourceId: entity.id,
                                resourceLabel: `${entity.canonical_name} (${entity.entity_type})`,
                              })
                            }
                            className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors ${
                              isFlagged
                                ? "bg-amber-100 text-amber-900 border border-amber-300 font-bold"
                                : "text-slate-500 hover:text-amber-800 hover:bg-amber-50 border border-line"
                            }`}
                            title={isFlagged ? "Entity is flagged for review" : "Flag entity for review"}
                          >
                            <Flag className="h-3 w-3 text-amber-600" />
                            <span>{isFlagged ? "Flagged" : "Flag"}</span>
                          </button>
                          <span className="text-xs font-medium text-slate-500 bg-slate-50 border border-line px-2 py-1 rounded">
                            Evidence: <strong className="text-slate-800">{entity.evidence_count}</strong>
                          </span>
                        </div>
                      </div>
                      <div className="mt-4 border-t border-line pt-3">
                        <p className="text-xs font-semibold uppercase text-slate-500 mb-1.5">Mentions & Provenance:</p>
                        <div className="flex flex-wrap gap-1.5">
                          {entity.mentions.map((mention) => (
                            <span key={mention.id} className="inline-flex items-center gap-1.5 bg-slate-50 border border-line px-2 py-1 text-xs text-slate-800 rounded">
                              <span>{mention.text}</span>
                              <span className="text-[10px] text-slate-400">({Math.round(mention.confidence * 100)}%)</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    </article>
                  );
                })}
            </div>

            {!entities.filter((e) => entityTypeFilter === "ALL" || e.entity_type === entityTypeFilter).length && (
              <EmptyState title="No entities found" body="No extracted entities match the selected type filter." />
            )}
          </div>
        </section>
      )}

      {tab === "graph" && token && (
        <KnowledgeGraph
          token={token}
          caseNumber={caseNumber}
          onFlag={(target) => setFlagModalTarget(target)}
          flaggedIds={flaggedResourceIds}
        />
      )}

      {tab === "timeline" && token && (
        <TimelineView
          token={token}
          caseNumber={caseNumber}
          onFlag={(ev) =>
            setFlagModalTarget({
              resourceType: "EVENT",
              resourceId: String(ev.id || ev.event_key || `EVENT-${ev.date || '0'}`),
              resourceLabel: String(ev.sourceText || ev.type || "Timeline Event"),
            })
          }
          flaggedIds={flaggedResourceIds}
        />
      )}

      {tab === "intelligence" && token && (
        <IntelligenceView
          token={token}
          caseNumber={caseNumber}
          onFlag={(finding) =>
            setFlagModalTarget({
              resourceType: "INTELLIGENCE",
              resourceId: finding.id || `FINDING-${finding.title.replace(/\s+/g, "_")}`,
              resourceLabel: finding.title,
            })
          }
          flaggedIds={flaggedResourceIds}
        />
      )}

      {tab === "flags" && token && (
        <FlaggedItemsList
          flags={flags}
          caseNumber={caseNumber}
          token={token}
          onRefresh={load}
          onOpenFlagModal={() =>
            setFlagModalTarget({
              resourceType: "EVIDENCE",
              resourceId: evidence[0]?.evidence_id || caseNumber,
              resourceLabel: evidence[0]?.filename || caseNumber,
            })
          }
        />
      )}

      {tab === "copilot" && token && <Copilot token={token} caseNumber={caseNumber} />}

      {flagModalTarget && token && (
        <FlagModal
          isOpen={true}
          onClose={() => setFlagModalTarget(null)}
          caseNumber={caseNumber}
          token={token}
          resourceType={flagModalTarget.resourceType}
          resourceId={flagModalTarget.resourceId}
          resourceLabel={flagModalTarget.resourceLabel}
          onSuccess={(flag) => {
            setMessage(`Flag created on ${flag.resource_label}`);
            setMessageType("success");
            load();
          }}
        />
      )}
    </>
  );
}
