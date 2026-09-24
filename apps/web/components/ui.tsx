import { ReactNode } from "react";
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from "lucide-react";

export function AlertBanner({
  message,
  type = "info",
  onDismiss,
  className = "",
}: {
  message: string;
  type?: "info" | "success" | "error" | "warning";
  onDismiss?: () => void;
  className?: string;
}) {
  if (!message) return null;

  const styles = {
    info: "border-sky-200 bg-sky-50 text-sky-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    error: "border-red-200 bg-red-50 text-red-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
  }[type] || "border-sky-200 bg-sky-50 text-sky-900";

  const Icon = {
    info: Info,
    success: CheckCircle2,
    error: AlertCircle,
    warning: AlertTriangle,
  }[type] || Info;

  return (
    <div
      role="alert"
      className={`mt-4 flex items-center justify-between gap-3 border p-3.5 text-sm rounded shadow-sm transition-all ${styles} ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <Icon className="h-4 w-4 shrink-0 opacity-80" />
        <span className="font-medium">{message}</span>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded p-1 text-current opacity-60 hover:opacity-100 hover:bg-black/5 focus:outline-none transition-all cursor-pointer"
          aria-label="Dismiss notification"
          title="Dismiss notification"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function StatusBadge({ value }:{value:string}) {
  const upper = (value || "").toUpperCase();
  const label = (upper === "EXTRACTION_COMPLETED" || upper === "COMPLETED" || upper === "PROCESSED") ? "Processed"
              : (upper === "UPLOADED" || upper === "NOT_STARTED" || upper === "PENDING") ? "Pending"
              : upper === "PROCESSING" ? "Processing"
              : upper === "FAILED" ? "Failed"
              : upper.replaceAll("_", " ");
  const tone = (upper === "ACTIVE" || upper === "HIGH" || upper === "COMPLETED" || upper === "EXTRACTION_COMPLETED" || upper === "PROCESSED" || upper === "VERIFIED" || upper === "SUCCESS")
    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
    : (upper === "MEDIUM" || upper === "PROCESSING" || upper === "REGISTERED" || upper === "SUGGESTED")
    ? "bg-amber-50 text-amber-800 border-amber-200"
    : (upper === "FAILED" || upper === "MODIFIED" || upper === "REJECTED" || upper === "DENIED")
    ? "bg-red-50 text-red-800 border-red-200"
    : "bg-slate-100 text-slate-700 border-slate-200";
  return <span className={`inline-flex border px-2 py-0.5 text-xs font-semibold tracking-wide ${tone}`}>{label}</span>;
}
export function MetricCard({ label, value, detail }:{label:string;value:string|number;detail:string}) { return <div className="panel p-5"><p className="text-sm text-slate-600">{label}</p><p className="mt-2 text-3xl font-semibold text-ink">{value}</p><p className="mt-2 text-xs text-slate-500">{detail}</p></div>; }
export function EmptyState({ title, body }:{title:string;body:string}) { return <div className="border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center"><p className="font-medium text-slate-800">{title}</p><p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{body}</p></div>; }
export function DataTable({ children }:{children:ReactNode}) { return <div className="panel overflow-x-auto"><table className="w-full min-w-[650px] text-sm">{children}</table></div>; }
export function DocumentDrawer(){ return null; }
export function EntityDrawer(){ return null; }
