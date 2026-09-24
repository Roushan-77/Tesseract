"use client";
import { useState } from "react";
import { apiPost } from "@/lib/api";
export function Copilot({ token, caseNumber }: { token: string; caseNumber: string }) {
  const [question, setQuestion] = useState(""); const [answer, setAnswer] = useState<{answer:string;sources:string[]}|null>(null); const [busy, setBusy] = useState(false);
  async function ask() { if (!question.trim()) return; setBusy(true); try { setAnswer(await apiPost(`/cases/${caseNumber}/copilot`, token, { question })); } finally { setBusy(false); } }
  return <section className="panel mt-6 p-5"><h2 className="font-semibold">Investigator Copilot</h2><p className="mt-1 text-sm text-slate-500">Answers use only accessible case data.</p><textarea value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ask about this case" className="mt-4 min-h-24 w-full border border-line p-3 text-sm"/><button onClick={ask} disabled={busy} className="mt-3 bg-ink px-4 py-2 text-sm text-white disabled:opacity-60">{busy ? "Searching..." : "Ask Copilot"}</button>{answer && <div className="mt-5 border-t border-line pt-4"><p className="text-sm text-slate-800">{answer.answer}</p><p className="mt-3 text-xs text-slate-500">Sources: {answer.sources.join(", ") || "None"}</p></div>}</section>;
}
