"use client";

import Link from "next/link";
import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { api, apiPost, base, Evidence, EntityMention, Extraction, getProcessingMethod, Integrity } from "@/lib/api";
import { TranslationKey } from "@/lib/i18n";
import { useApp } from "@/components/app-provider";
import { EmptyState, StatusBadge, AlertBanner } from "@/components/ui";
import {
  FileText,
  Table as TableIcon,
  ShieldCheck,
  Search,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Phone,
  CreditCard,
  Car,
  MapPin,
  Users,
  Building2,
  Code,
  Layers,
  ArrowRight,
  Calendar,
  DollarSign,
  Fingerprint,
  Info,
  Copy,
  Check,
  Flag
} from "lucide-react";
import { FlagModal } from "@/components/flag-modal";

const categoryOrder = [
  "CASE_ID",
  "PERSON",
  "ORGANIZATION",
  "LOCATION",
  "VEHICLE",
  "PHONE",
  "ACCOUNT",
  "DATE",
  "MONEY",
  "EVIDENCE_REFERENCE"
];

const categoryLabels: Record<string, string> = {
  CASE_ID: "Case Information",
  PERSON: "Persons & Individuals",
  ORGANIZATION: "Organizations & Companies",
  LOCATION: "Locations & Addresses",
  VEHICLE: "Vehicles & Transport",
  PHONE: "Phone Numbers",
  ACCOUNT: "Financial / Bank Accounts",
  DATE: "Dates & Timestamps",
  MONEY: "Monetary Amounts",
  EVIDENCE_REFERENCE: "Evidence References"
};

const categoryIcons: Record<string, any> = {
  CASE_ID: Fingerprint,
  PERSON: Users,
  ORGANIZATION: Building2,
  LOCATION: MapPin,
  VEHICLE: Car,
  PHONE: Phone,
  ACCOUNT: CreditCard,
  DATE: Calendar,
  MONEY: DollarSign,
  EVIDENCE_REFERENCE: FileText
};

function EntityGroup({
  type,
  entities,
  label
}: {
  type: string;
  entities: EntityMention[];
  label: string;
}) {
  if (!entities.length) return null;
  const Icon = categoryIcons[type] || Sparkles;
  return (
    <section className="border-t border-line pt-3 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5 text-accent" />
          <span>{label}</span>
        </h3>
        <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
          {entities.length}
        </span>
      </div>
      <ul className="space-y-1.5 text-xs text-slate-800">
        {entities.map((entity, idx) => (
          <li
            key={`${type}-${entity.mentionId || idx}-${entity.text}`}
            className="flex items-center justify-between gap-3 p-2 rounded bg-white hover:bg-slate-50/80 border border-slate-200/80 transition-colors shadow-xs"
          >
            <div className="flex flex-col min-w-0">
              <span className="font-semibold text-slate-900 truncate">{entity.text}</span>
              {entity.normalizedValue && entity.normalizedValue !== entity.text && (
                <span className="text-[10px] text-slate-500 truncate font-mono">
                  Normalized: <strong className="text-slate-700">{entity.normalizedValue}</strong>
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-right text-[10px] font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {Math.round((entity.confidence || 0.95) * 100)}%
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function EvidencePage() {
  const { t, token, locale } = useApp();
  const { evidenceId } = useParams<{ evidenceId: string }>();
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [rawCsvText, setRawCsvText] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [integrity, setIntegrity] = useState<Integrity | null>(null);
  const [copiedText, setCopiedText] = useState(false);
  const [flagModalOpen, setFlagModalOpen] = useState(false);

  // Structured Table state
  const [tableSearch, setTableSearch] = useState("");
  const [tablePage, setTablePage] = useState(1);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const pageSize = 15;

  useEffect(() => {
    if (!token) return;
    let active = true;
    Promise.all([
      api<Evidence>(`/evidence/${evidenceId}`, token),
      api<Extraction>(`/evidence/${evidenceId}/extraction`, token),
      api<Integrity>(`/evidence/${evidenceId}/integrity`, token)
    ])
      .then(([nextEvidence, nextExtraction, nextIntegrity]) => {
        if (active) {
          setEvidence(nextEvidence);
          setExtraction(nextExtraction);
          setIntegrity(nextIntegrity);
          if (nextExtraction?.structured?.sheets) {
            const sheetNames = Object.keys(nextExtraction.structured.sheets);
            if (sheetNames.length > 0) setSelectedSheet(sheetNames[0]);
          }
        }
      })
      .catch(() => {
        if (active) setError(t("processingError"));
      });
    return () => {
      active = false;
    };
  }, [token, evidenceId, locale, t]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    let objectUrl: string | null = null;
    fetch(`${base}/evidence/${evidenceId}/file`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.blob();
      })
      .then(async (blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) {
          setFileUrl(objectUrl);
          if (blob.type.includes("csv") || blob.type.includes("text") || evidence?.filename.endsWith(".csv")) {
            const text = await blob.text();
            setRawCsvText(text);
          }
        }
      })
      .catch(() => {
        if (active) setError(t("processingError"));
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, evidenceId, locale, t, evidence?.filename]);

  async function processEvidence() {
    if (!token) return;
    setBusy(true);
    setError("");
    setSuccessMessage("");
    try {
      const result = await apiPost<Extraction>(`/evidence/${evidenceId}/process`, token, {});
      setExtraction(result);
      setEvidence(await api<Evidence>(`/evidence/${evidenceId}`, token));
      setSuccessMessage("Evidence re-processed successfully.");
    } catch {
      setError(t("processingError"));
      try {
        setExtraction(await api<Extraction>(`/evidence/${evidenceId}/extraction`, token));
      } catch {}
    } finally {
      setBusy(false);
    }
  }

  async function verifyIntegrity() {
    if (!token) return;
    setError("");
    setSuccessMessage("");
    try {
      const res = await apiPost<Integrity>(`/evidence/${evidenceId}/verify-integrity`, token, {});
      setIntegrity(res);
      setEvidence(await api<Evidence>(`/evidence/${evidenceId}`, token));
      setSuccessMessage(
        res.verified
          ? "Evidence cryptographic hash verified against ledger."
          : "Evidence file modification detected."
      );
    } catch {
      setError("Integrity verification failed.");
    }
  }

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  // Structured table rows & columns calculation
  const structuredData = extraction?.structured;
  const tableColumns = useMemo(() => {
    if (structuredData?.sheets && selectedSheet && structuredData.sheets[selectedSheet]) {
      const cols = structuredData.sheets[selectedSheet].columns;
      if (Array.isArray(cols) && cols.length > 0) return cols;
    }
    if (structuredData?.columns && Array.isArray(structuredData.columns) && structuredData.columns.length > 0) {
      return structuredData.columns;
    }
    if (structuredData?.records && Array.isArray(structuredData.records) && structuredData.records.length > 0) {
      const first = structuredData.records[0];
      if (first && typeof first === "object") {
        if ("fields" in first && first.fields && typeof first.fields === "object") {
          return Object.keys(first.fields);
        }
        return Object.keys(first).filter((k) => k !== "row" && k !== "id");
      }
    }
    if (rawCsvText) {
      const lines = rawCsvText.trim().split(/\r?\n/);
      if (lines.length > 0) {
        return lines[0].split(",").map((c) => c.trim().replace(/^["']|["']$/g, ""));
      }
    }
    return [];
  }, [structuredData, selectedSheet, rawCsvText]);

  const rawRows: Array<{ row: number; fields: Record<string, any> }> = useMemo(() => {
    if (structuredData?.sheets && selectedSheet && structuredData.sheets[selectedSheet]) {
      const sheetRows = structuredData.sheets[selectedSheet].rows || [];
      return sheetRows.map((r: any, idx: number) => {
        if (Array.isArray(r)) {
          const fields: Record<string, any> = {};
          tableColumns.forEach((col, cIdx) => {
            fields[col] = r[cIdx] ?? "";
          });
          return { row: idx + 1, fields };
        }
        if (r && typeof r === "object") {
          const fields = "fields" in r && r.fields && typeof r.fields === "object" ? r.fields : r;
          return {
            row: r.row || idx + 1,
            fields: { ...fields }
          };
        }
        return { row: idx + 1, fields: {} };
      });
    }

    if (structuredData?.records && Array.isArray(structuredData.records) && structuredData.records.length > 0) {
      return structuredData.records.map((r: any, idx: number) => {
        if (!r || typeof r !== "object") {
          return { row: idx + 1, fields: {} };
        }
        if ("fields" in r && r.fields && typeof r.fields === "object") {
          return {
            row: typeof r.row === "number" ? r.row : idx + 1,
            fields: { ...r.fields }
          };
        }
        const { row, id, ...rest } = r;
        return {
          row: typeof row === "number" ? row : idx + 1,
          fields: rest
        };
      });
    }

    if (rawCsvText && tableColumns.length > 0) {
      const lines = rawCsvText.trim().split(/\r?\n/);
      return lines.slice(1).filter((l) => l.trim().length > 0).map((line, idx) => {
        const parts = line.split(",").map((p) => p.trim().replace(/^["']|["']$/g, ""));
        const fields: Record<string, string> = {};
        tableColumns.forEach((col, cIdx) => {
          fields[col] = parts[cIdx] ?? "";
        });
        return { row: idx + 1, fields };
      });
    }

    return [];
  }, [structuredData, selectedSheet, tableColumns, rawCsvText]);

  const filteredRows = useMemo(() => {
    if (!tableSearch.trim()) return rawRows;
    const term = tableSearch.toLowerCase();
    return rawRows.filter((r) => {
      if (!r || !r.fields || typeof r.fields !== "object") return false;
      return Object.values(r.fields).some((val) =>
        val !== null && val !== undefined && String(val).toLowerCase().includes(term)
      );
    });
  }, [rawRows, tableSearch]);

  const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
  const paginatedRows = useMemo(() => {
    const start = (tablePage - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, tablePage]);

  if (!evidence || !token) return <p className="text-sm text-slate-500">{t("fileLoading")}</p>;

  const method = getProcessingMethod(evidence);
  const isStructured = method === "Structured Parsing";
  const processed = extraction?.processing_status === "EXTRACTION_COMPLETED";
  const failed = extraction?.processing_status === "FAILED";

  // Document extraction groupings
  const categories = extraction?.categories ?? {};
  const orderedCategories = categoryOrder
    .filter((type) => categories[type] && categories[type].length > 0)
    .map((type) => [type, categories[type]] as const);

  // Remaining categories not in predefined order
  const otherCategories = Object.keys(categories)
    .filter((type) => !categoryOrder.includes(type) && categories[type].length > 0)
    .map((type) => [type, categories[type]] as const);

  const allCategoryGroups = [...orderedCategories, ...otherCategories];
  const totalEntityCount = extraction?.entities?.length ?? 0;

  return (
    <>
      <Link
        href={evidence.case_number ? `/cases/${evidence.case_number}` : "/cases"}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-ink transition-colors"
      >
        <span>&larr;</span>
        <span>{t("evidenceDocuments")} ({evidence.case_number || "Case"})</span>
      </Link>

      <header className="mt-4 border-b border-line pb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-wide text-slate-500 font-mono uppercase">
              {evidence.evidence_id} &bull; {evidence.case_number || "CASE"}
            </p>
            <h1 className="mt-1 text-2xl font-bold text-ink flex items-center gap-3">
              <span>{evidence.filename}</span>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFlagModalOpen(true)}
              className="flex items-center gap-1.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 px-3.5 py-2 text-xs font-semibold rounded transition-colors shadow-2xs cursor-pointer"
              title="Attach an investigator review flag to this evidence"
            >
              <Flag className="h-3.5 w-3.5 text-amber-700" />
              <span>Flag for Review</span>
            </button>
            <button
              onClick={processEvidence}
              disabled={busy}
              className="bg-accent hover:bg-sky-700 px-4 py-2 text-xs font-bold text-white rounded disabled:cursor-not-allowed disabled:opacity-60 transition-colors shadow-xs"
            >
              {busy ? t("processing") : processed ? t("reprocessEvidence") : t("processEvidence")}
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <StatusBadge value={evidence.processing_status} />
          <span className="text-xs font-semibold text-slate-700 border border-line px-2.5 py-1 bg-white rounded shadow-xs">
            Method: <strong>{method}</strong>
          </span>
          <span className="text-xs text-slate-600 border border-line px-2.5 py-1 bg-slate-50 rounded">
            Type: <strong>{evidence.document_type}</strong>
          </span>
          {!isStructured && (
            <span className="text-xs text-slate-600 border border-line px-2.5 py-1 bg-slate-50 rounded">
              Language: <strong>{extraction?.language?.code ?? evidence.document_language ?? "en"}</strong>
            </span>
          )}
          {totalEntityCount > 0 && (
            <span className="text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded font-semibold">
              {totalEntityCount} Entities Extracted
            </span>
          )}
        </div>
      </header>

      {error && <AlertBanner message={error} type="error" onDismiss={() => setError("")} className="mt-5" />}
      {successMessage && <AlertBanner message={successMessage} type="success" onDismiss={() => setSuccessMessage("")} className="mt-5" />}
      {failed && extraction?.error && <AlertBanner message={extraction.error} type="error" onDismiss={() => {}} className="mt-5" />}

      {/* Per-Evidence Integrity Panel */}
      <section className="panel mt-6 p-5 bg-gradient-to-r from-slate-50 to-white border border-line">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <h2 className="font-bold text-slate-900">Evidence Integrity & Cryptographic Ledger</h2>
              <StatusBadge value={integrity?.status || evidence.integrity_status || "NOT_REGISTERED"} />
            </div>
            <p className="break-all text-xs text-slate-600 font-mono">
              <span className="font-semibold text-slate-500">SHA-256:</span> {integrity?.sha256 || "Not registered"}
            </p>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 font-mono">
              <span>
                <strong className="text-slate-500">Ledger ID:</strong> {integrity?.ledger_record_id || "-"}
              </span>
              <span>
                <strong className="text-slate-500">File Size:</strong> {integrity?.file_size ? `${integrity.file_size.toLocaleString()} bytes` : "-"}
              </span>
              <span>
                <strong className="text-slate-500">Verified:</strong> {integrity?.verified_at ? new Date(integrity.verified_at).toLocaleString() : "Never"}
              </span>
            </div>
          </div>
          <button
            onClick={verifyIntegrity}
            className="border border-line bg-white hover:bg-slate-50 px-4 py-2 text-xs font-bold text-slate-800 rounded shadow-xs transition-colors"
          >
            Verify Integrity
          </button>
        </div>
      </section>

      {/* ========================================================= */}
      {/* STRUCTURED EVIDENCE LAYOUT (CSV / XLS / XLSX / JSON) */}
      {/* ========================================================= */}
      {isStructured ? (
        <div className="mt-6 space-y-6">
          <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            {/* LEFT: ORIGINAL DATA TABLE */}
            <div className="panel p-5 flex flex-col min-h-[580px]">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <TableIcon className="h-4 w-4 text-accent" />
                  <h2 className="font-bold text-slate-900">Structured Data Records</h2>
                  <span className="text-xs bg-sky-100 text-sky-800 px-2 py-0.5 rounded-full font-semibold">
                    {filteredRows.length} Records
                  </span>
                </div>
                {/* Search Bar */}
                <div className="relative w-48 sm:w-64">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    value={tableSearch}
                    onChange={(e) => {
                      setTableSearch(e.target.value);
                      setTablePage(1);
                    }}
                    placeholder="Search records..."
                    className="w-full pl-8 pr-3 py-1.5 text-xs border border-line rounded bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              </div>

              {/* Multi-Sheet Selector if available */}
              {structuredData?.sheets && Object.keys(structuredData.sheets).length > 1 && (
                <div className="flex gap-2 border-b border-line py-2 overflow-x-auto">
                  {Object.keys(structuredData.sheets).map((sheetName) => (
                    <button
                      key={sheetName}
                      onClick={() => {
                        setSelectedSheet(sheetName);
                        setTablePage(1);
                      }}
                      className={`text-xs px-3 py-1 rounded font-medium transition-colors ${
                        selectedSheet === sheetName
                          ? "bg-accent text-white font-bold"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      {sheetName}
                    </button>
                  ))}
                </div>
              )}

              {/* Data Table */}
              <div className="mt-3 flex-1 overflow-auto border border-line rounded">
                <table className="w-full text-left text-xs border-collapse min-w-[500px]">
                  <thead className="bg-slate-100 sticky top-0 border-b border-line">
                    <tr>
                      <th className="px-3 py-2 font-bold text-slate-600 w-12 text-center">#</th>
                      {tableColumns.map((col) => (
                        <th key={col} className="px-3 py-2 font-bold text-slate-700 border-l border-line whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line font-mono">
                    {paginatedRows.map((r, idx) => {
                      const rowFields = r && r.fields && typeof r.fields === "object" ? r.fields : (r && typeof r === "object" ? r : {});
                      const rowNum = r?.row || (tablePage - 1) * pageSize + idx + 1;
                      return (
                        <tr key={r?.row || idx} className="hover:bg-sky-50/40 transition-colors">
                          <td className="px-3 py-2 text-slate-400 text-center select-none bg-slate-50/50">
                            {rowNum}
                          </td>
                          {tableColumns.map((col) => {
                            const rawVal = (rowFields as any)[col];
                            const displayVal =
                              rawVal !== null && rawVal !== undefined && String(rawVal).trim() !== ""
                                ? String(rawVal)
                                : "-";
                            return (
                              <td
                                key={col}
                                className="px-3 py-2 text-slate-800 border-l border-line max-w-[240px] truncate"
                                title={displayVal !== "-" ? displayVal : ""}
                              >
                                {displayVal}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                    {!paginatedRows.length && (
                      <tr>
                        <td
                          colSpan={Math.max(tableColumns.length + 1, 1)}
                          className="px-4 py-8 text-center text-slate-400 font-sans"
                        >
                          No matching records found in structured data.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="mt-3 flex items-center justify-between text-xs text-slate-600 border-t border-line pt-2">
                  <span>
                    Showing {Math.min((tablePage - 1) * pageSize + 1, filteredRows.length)} to{" "}
                    {Math.min(tablePage * pageSize, filteredRows.length)} of {filteredRows.length}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setTablePage((p) => Math.max(1, p - 1))}
                      disabled={tablePage === 1}
                      className="p-1 border border-line rounded hover:bg-slate-100 disabled:opacity-40"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="font-semibold px-2">
                      {tablePage} / {totalPages}
                    </span>
                    <button
                      onClick={() => setTablePage((p) => Math.min(totalPages, p + 1))}
                      disabled={tablePage === totalPages}
                      className="p-1 border border-line rounded hover:bg-slate-100 disabled:opacity-40"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* RIGHT: PARSED INFORMATION */}
            <div className="panel p-5 flex flex-col max-h-[720px] overflow-y-auto space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-600" />
                    <h2 className="font-bold text-slate-900">Parsed Information & Schema</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Structured ingestion metadata, detected column entities, and document-local relationships.
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-50 text-sky-800 border border-sky-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                  Document-level extraction
                </span>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-2.5">
                <div className="p-3 bg-slate-50 rounded border border-line">
                  <p className="text-[10px] font-bold uppercase text-slate-500">Format</p>
                  <p className="text-xs font-bold text-slate-900 mt-0.5 font-mono">
                    {structuredData?.file_type || evidence.document_type || "CSV"}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-line">
                  <p className="text-[10px] font-bold uppercase text-slate-500">Total Rows</p>
                  <p className="text-xs font-bold text-slate-900 mt-0.5">
                    {structuredData?.row_count ?? rawRows.length}
                  </p>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-line">
                  <p className="text-[10px] font-bold uppercase text-slate-500">Columns</p>
                  <p className="text-xs font-bold text-slate-900 mt-0.5">{tableColumns.length}</p>
                </div>
              </div>

              {/* Column Headers */}
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Column Headers</p>
                <div className="flex flex-wrap gap-1.5">
                  {tableColumns.map((col) => (
                    <span key={col} className="bg-slate-100 text-slate-700 text-xs px-2 py-0.5 rounded font-mono border border-line">
                      {col}
                    </span>
                  ))}
                </div>
              </div>

              {/* Detected Entities from Structured Data */}
              {extraction?.entities && extraction.entities.length > 0 && (
                <div className="border-t border-line pt-4">
                  <div className="flex items-center justify-between mb-2.5">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-accent" />
                      Detected Entities & Identifiers ({extraction.entities.length})
                    </p>
                  </div>
                  <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                    {extraction.entities.map((ent, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded bg-white border border-slate-200 text-xs shadow-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="bg-slate-100 border border-line px-1.5 py-0.5 rounded text-[10px] font-bold text-slate-600 shrink-0">
                            {ent.type}
                          </span>
                          <span className="font-semibold text-slate-900 truncate">{ent.text}</span>
                        </div>
                        <span className="text-emerald-700 font-mono text-[10px] font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 shrink-0">
                          {Math.round((ent.confidence || 0.95) * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Relationships Inferred from Structured Ingestion */}
              {extraction?.relations && extraction.relations.length > 0 && (
                <div className="border-t border-line pt-4">
                  <div className="flex items-center justify-between mb-2.5">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-accent" />
                      Document-Level Linkages ({extraction.relations.length})
                    </p>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {extraction.relations.map((rel, idx) => (
                      <div key={idx} className="p-2.5 bg-slate-50 border border-line rounded text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-accent text-[11px]">{rel.type}</span>
                          {rel.sourceRow && (
                            <span className="text-[10px] font-mono bg-white px-1.5 py-0.5 rounded border border-line text-slate-500">
                              Row #{rel.sourceRow}
                            </span>
                          )}
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-slate-800 font-mono text-[11px]">
                          <span className="font-semibold truncate">{rel.source?.text || "—"}</span>
                          <ArrowRight className="h-3 w-3 text-slate-400 shrink-0" />
                          <span className="font-semibold truncate">{rel.target?.text || "—"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Events Created */}
              {extraction?.events && extraction.events.length > 0 && (
                <div className="border-t border-line pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-emerald-600" />
                    Structured Events ({extraction.events.length})
                  </p>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {extraction.events.map((ev, idx) => (
                      <div key={idx} className="p-2.5 bg-emerald-50/40 border border-emerald-200/60 rounded text-xs">
                        <div className="flex items-center justify-between font-bold text-emerald-900">
                          <span>{ev.type}</span>
                          {ev.sourceRow && (
                            <span className="text-[10px] font-mono bg-white px-1.5 py-0.5 rounded border border-line text-slate-500">
                              Row #{ev.sourceRow}
                            </span>
                          )}
                        </div>
                        {ev.date && <p className="text-[11px] text-slate-600 font-mono mt-1">Date/Time: {ev.date}</p>}
                        {ev.participants && ev.participants.length > 0 && (
                          <p className="text-[11px] text-slate-700 mt-0.5">
                            Participants: {ev.participants.map((p) => p.text).join(", ")}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Raw Records Collapsible */}
          <details className="panel p-5">
            <summary className="cursor-pointer font-bold text-sm text-slate-800 flex items-center gap-2">
              <Code className="h-4 w-4 text-slate-500" />
              <span>View Raw Structured Records (JSON / CSV)</span>
            </summary>
            <div className="mt-4">
              <pre className="p-4 bg-slate-900 text-emerald-400 font-mono text-xs rounded border border-slate-800 overflow-x-auto max-h-72">
                {JSON.stringify(extraction?.structured || { rows: rawRows }, null, 2)}
              </pre>
            </div>
          </details>
        </div>
      ) : (
        /* ========================================================= */
        /* DOCUMENT EVIDENCE LAYOUT (PDF / IMAGES / TXT / DOCX) */
        /* ========================================================= */
        <div className="mt-6 space-y-6">
          <section className="grid gap-6 lg:grid-cols-2">
            {/* LEFT: ORIGINAL DOCUMENT VIEWER */}
            <div className="panel min-h-[600px] p-4 flex flex-col">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-accent" />
                  <h2 className="font-bold text-slate-900">{t("originalDocument")}</h2>
                </div>
                <span className="text-xs text-slate-500 font-mono">
                  {evidence.document_type} &bull; {evidence.filename}
                </span>
              </div>
              <div className="mt-3 flex-1 flex items-center justify-center bg-slate-100/60 rounded border border-line overflow-hidden min-h-[520px]">
                {fileUrl ? (
                  evidence.mime_type === "application/pdf" || evidence.filename.endsWith(".pdf") ? (
                    <iframe title={evidence.filename} src={fileUrl} className="h-[560px] w-full border-0" />
                  ) : evidence.mime_type.startsWith("image/") ? (
                    <img src={fileUrl} alt={evidence.filename} className="max-h-[560px] w-full object-contain p-2" />
                  ) : (
                    <pre className="p-4 text-xs font-mono text-slate-800 max-h-[560px] overflow-auto whitespace-pre-wrap w-full bg-white">
                      {rawCsvText || extraction?.text || "Document preview available."}
                    </pre>
                  )
                ) : (
                  <p className="p-8 text-sm text-slate-500">{t("fileLoading")}</p>
                )}
              </div>
            </div>

            {/* RIGHT: EXTRACTED INFORMATION FROM DOCUMENT */}
            <section className="panel max-h-[660px] overflow-y-auto p-5 flex flex-col space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-emerald-600" />
                    <h2 className="font-bold text-slate-900">Extracted Information & Analysis</h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Normalized entities and facts extracted exclusively from this document.
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-50 text-sky-800 border border-sky-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                  Document-level extraction
                </span>
              </div>

              <div className="space-y-4 flex-1">
                {allCategoryGroups.map(([type, entities]) => (
                  <EntityGroup
                    key={type}
                    type={type}
                    entities={entities}
                    label={categoryLabels[type] || type.replaceAll("_", " ")}
                  />
                ))}
                {!allCategoryGroups.length && (
                  <EmptyState title={t("noEntities")} body={t("processingLater")} />
                )}
              </div>

              {/* Document-level Relations if present */}
              {extraction?.relations && extraction.relations.length > 0 && (
                <div className="border-t border-line pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-accent" />
                    Document-Level Relations ({extraction.relations.length})
                  </p>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {extraction.relations.map((rel, idx) => (
                      <div key={idx} className="p-2 bg-slate-50 border border-line rounded text-xs">
                        <div className="font-bold text-accent text-[11px]">{rel.type}</div>
                        <div className="mt-1 flex items-center gap-2 text-slate-800 font-mono text-[11px]">
                          <span className="font-semibold truncate">{rel.source?.text || "—"}</span>
                          <ArrowRight className="h-3 w-3 text-slate-400 shrink-0" />
                          <span className="font-semibold truncate">{rel.target?.text || "—"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Document-level Events if present */}
              {extraction?.events && extraction.events.length > 0 && (
                <div className="border-t border-line pt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-emerald-600" />
                    Events Mentioned in Document ({extraction.events.length})
                  </p>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {extraction.events.map((ev, idx) => (
                      <div key={idx} className="p-2 bg-emerald-50/40 border border-emerald-200/60 rounded text-xs">
                        <div className="font-bold text-emerald-900">{ev.type}</div>
                        {ev.date && <p className="text-[11px] text-slate-600 font-mono mt-0.5">Date: {ev.date}</p>}
                        {ev.participants && ev.participants.length > 0 && (
                          <p className="text-[11px] text-slate-700 mt-0.5">
                            Participants: {ev.participants.map((p) => p.text).join(", ")}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          </section>

          {/* NLP Analysis Table */}
          <section className="panel p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                <span>{t("nlpAnalysis")}</span>
                {extraction?.entities && extraction.entities.length > 0 && (
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">
                    {extraction.entities.length} tokens
                  </span>
                )}
              </h2>
            </div>
            {extraction?.entities && extraction.entities.length > 0 ? (
              <div className="max-h-[360px] overflow-auto border border-line rounded">
                <table className="w-full min-w-[520px] text-xs">
                  <thead className="bg-slate-100 sticky top-0 border-b border-line">
                    <tr>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Entity Text</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Type</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">{t("normalizedValue")}</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">{t("confidence")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line font-mono">
                    {extraction.entities.map((entity, idx) => (
                      <tr key={entity.mentionId || idx} className="hover:bg-slate-50/50">
                        <td className="px-3 py-2 font-semibold text-slate-900">{entity.text}</td>
                        <td className="px-3 py-2">
                          <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-line text-[10px] font-sans font-bold">
                            {entity.type}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-slate-700">{entity.normalizedValue || "—"}</td>
                        <td className="px-3 py-2 text-emerald-700 font-semibold">
                          {Math.round((entity.confidence || 0.95) * 100)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-slate-500">{t("processingLater")}</p>
            )}
          </section>

          {/* Raw OCR Text Collapsible */}
          <details className="panel p-5">
            <summary className="cursor-pointer font-bold text-sm text-slate-800 flex items-center justify-between">
              <span>{t("rawOcrText")}</span>
              {extraction?.text && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    if (extraction?.text) handleCopyText(extraction.text);
                  }}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-ink border border-line px-2 py-1 rounded bg-white"
                >
                  {copiedText ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedText ? "Copied" : "Copy Text"}</span>
                </button>
              )}
            </summary>
            <div className="mt-4">
              {extraction?.text ? (
                <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap bg-slate-900 text-emerald-400 p-4 text-xs font-mono rounded border border-slate-800">
                  {extraction.text}
                </pre>
              ) : (
                <p className="text-sm text-slate-500">{t("processingLater")}</p>
              )}
            </div>
          </details>
        </div>
      )}

      {!!extraction?.warnings.length && (
        <section className="panel mt-6 p-5 border-l-4 border-l-amber-500 bg-amber-50/30">
          <h2 className="font-bold text-sm text-amber-900">{t("warnings")}</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-800">
            {extraction.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      )}

      {flagModalOpen && evidence && token && (
        <FlagModal
          isOpen={true}
          onClose={() => setFlagModalOpen(false)}
          caseNumber={evidence.case_number || "CASE-002"}
          token={token}
          resourceType="EVIDENCE"
          resourceId={evidence.evidence_id}
          resourceLabel={`${evidence.evidence_id} (${evidence.filename})`}
          onSuccess={() => {
            setSuccessMessage(`Flag created for ${evidence.filename}`);
          }}
        />
      )}
    </>
  );
}
