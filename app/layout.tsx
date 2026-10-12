import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import { getCaller } from "@/lib/identity";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

const APP_NAME = "Your notes";

export const metadata: Metadata = {
  title: APP_NAME,
  description: "A place for your thoughts.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Not-found renders through this layout for /api callers too, so a key must not throw here.
  const caller = await getCaller();

  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b bg-panel">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-8 px-6">
            <Link href="/" className="shrink-0 font-semibold tracking-tight">{APP_NAME}</Link>
            <nav className="flex shrink-0 gap-6 text-sm text-muted">
              <Link href="/" className="hover:text-ink">Notes</Link>
              <Link href="/api-docs" className="hover:text-ink">API docs</Link>
            </nav>
            {caller.kind === "user" && (
              <span className="ml-auto hidden min-w-0 truncate text-sm text-muted sm:block">{caller.email}</span>
            )}
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
