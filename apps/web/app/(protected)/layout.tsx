"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { useApp } from "@/components/app-provider";
export default function ProtectedLayout({children}:{children:React.ReactNode}){const {token,hydrated}=useApp();const router=useRouter();useEffect(()=>{if(hydrated && token===null)router.replace("/")},[token,hydrated,router]);if(!hydrated)return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">Loading…</div>;if(!token)return null;return <AppShell>{children}</AppShell>}
