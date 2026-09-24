"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Shield } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { AlertBanner } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { login, t } = useApp();
  const [investigatorId, setId] = useState("INV-017");
  const [password, setPassword] = useState(process.env.NEXT_PUBLIC_DEMO_PASSWORD || "inv123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ investigator_id: investigatorId, password }),
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      login(data.access_token, data.user);
      router.push("/dashboard");
    } catch {
      setError("Sign-in failed. Check the demo password configured for this environment.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 p-4 lg:p-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl overflow-hidden border border-line bg-white lg:grid-cols-[1.1fr_0.9fr]">
        <section className="bg-navy px-8 py-12 text-white lg:px-14 lg:py-16">
          <div className="flex items-center gap-3">
            <Shield className="text-sky-200" />
            <span className="font-semibold tracking-[0.25em]">TESSERACT</span>
          </div>
          <p className="mt-16 text-sm font-medium uppercase tracking-[0.18em] text-sky-200">Criminal Network Intelligence</p>
          <h1 className="mt-4 max-w-lg text-4xl font-semibold leading-tight">Connected intelligence for modern investigations.</h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-slate-300">
            Turn fragmented investigation data into connected, explainable intelligence.
          </p>
          <ul className="mt-12 space-y-5">
            {[
              "Evidence Intelligence",
              "Criminal Knowledge Graph",
              "Multilingual Investigation",
              "Explainable Intelligence",
              "Evidence Integrity",
            ].map((item) => (
              <li key={item} className="flex gap-3 text-sm text-slate-200">
                <Check size={18} className="text-sky-200" />
                {item}
              </li>
            ))}
          </ul>
        </section>
        <section className="flex items-center px-8 py-12 lg:px-14">
          <div className="w-full max-w-sm">
            <p className="text-sm font-medium uppercase tracking-[0.15em] text-slate-500">Secure workspace</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">{t("investigatorAccess")}</h2>
            <form className="mt-8 space-y-5" onSubmit={submit}>
              <label className="block text-sm font-medium text-slate-700">
                {t("investigatorId")}
                <input
                  value={investigatorId}
                  onChange={(e) => setId(e.target.value)}
                  className="mt-1.5 w-full border border-line px-3 py-2.5"
                  required
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                {t("password")}
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  className="mt-1.5 w-full border border-line px-3 py-2.5"
                  required
                />
              </label>
              {error && <AlertBanner message={error} type="error" onDismiss={() => setError("")} />}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#294f77] disabled:opacity-50"
              >
                {loading ? "Signing in..." : t("signIn")}
              </button>
            </form>
            <div className="mt-8 border-t border-line pt-5 text-sm">
              <p className="font-semibold text-slate-700">{t("demoCredentials")}</p>
              <p className="mt-2 text-slate-600">
                Investigator ID: <span className="font-mono">INV-017</span>
              </p>
              <p className="mt-1 text-slate-500">Use password: inv123</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
