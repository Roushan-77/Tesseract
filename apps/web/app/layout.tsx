import "./globals.css";
import type { Metadata } from "next";
import { AppProvider } from "@/components/app-provider";
export const metadata: Metadata = { title: "Tesseract | Criminal Network Intelligence", description: "Investigator intelligence platform" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AppProvider>{children}</AppProvider></body></html>; }
