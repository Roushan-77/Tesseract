import type { Config } from "tailwindcss";
export default { content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"], theme: { extend: { colors: { ink: "#111827", navy: "#172235", line: "#dbe1e8", surface: "#f6f8fa", accent: "#315b8a" } } }, plugins: [] } satisfies Config;
