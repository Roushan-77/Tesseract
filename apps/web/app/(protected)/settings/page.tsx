"use client";
import { useApp } from "@/components/app-provider";
export default function Settings(){const {t}=useApp();return <><p className="text-sm text-slate-500">Workspace preferences</p><h1 className="mt-1 text-2xl font-semibold text-ink">{t("settings")}</h1><div className="panel mt-7 p-6"><p className="text-sm text-slate-600">Language and account preferences are available from the persistent application controls.</p></div></>}
