"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { Locale, translations, TranslationKey } from "@/lib/i18n";
import { User } from "@/lib/api";
type AppState = { locale:Locale; setLocale:(locale:Locale)=>void; t:(key:TranslationKey)=>string; token:string|null; user:User|null; hydrated:boolean; login:(token:string,user:User)=>void; logout:()=>void };
const Context = createContext<AppState | null>(null);
export function AppProvider({ children }:{children:React.ReactNode}) {
  const [locale,setLocaleState]=useState<Locale>("en"); const [token,setToken]=useState<string|null>(null); const [user,setUser]=useState<User|null>(null); const [hydrated,setHydrated]=useState(false);
  useEffect(()=>{ const saved=localStorage.getItem("tesseract-locale") as Locale|null; const session=localStorage.getItem("tesseract-session"); if(saved) setLocaleState(saved); if(session) { try { const parsed=JSON.parse(session); setToken(parsed.token); setUser(parsed.user); } catch { /* corrupted session – stay logged out */ } } setHydrated(true); },[]);
  const setLocale=(next:Locale)=>{setLocaleState(next);localStorage.setItem("tesseract-locale",next);document.documentElement.lang=next;};
  const login=(nextToken:string,nextUser:User)=>{setToken(nextToken);setUser(nextUser);localStorage.setItem("tesseract-session",JSON.stringify({token:nextToken,user:nextUser}));};
  const logout=()=>{setToken(null);setUser(null);localStorage.removeItem("tesseract-session");};
  return <Context.Provider value={{locale,setLocale,t:(key)=>translations[locale][key],token,user,hydrated,login,logout}}>{children}</Context.Provider>;
}
export const useApp=()=>{const ctx=useContext(Context);if(!ctx)throw new Error("AppProvider missing");return ctx;};
