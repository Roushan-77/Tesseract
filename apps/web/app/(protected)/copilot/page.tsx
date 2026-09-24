"use client";
import { useApp } from "@/components/app-provider";
import { EmptyState } from "@/components/ui";
export default function Copilot(){const {t}=useApp();return <><p className="text-sm text-slate-500">Investigation assistance</p><h1 className="mt-1 text-2xl font-semibold text-ink">{t("copilot")}</h1><div className="mt-7"><EmptyState title={t("copilot")} body="Evidence-linked investigation assistance will appear here."/></div></>}
