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
              // The gateway owns the session: it clears it on this same-origin POST.
              <form action="/__floo/logout" method="post" className="ml-auto flex min-w-0 items-center gap-4 text-sm text-muted">
                <span className="hidden truncate sm:block">{caller.email}</span>
                <button type="submit" className="shrink-0 cursor-pointer hover:text-ink">Sign out</button>
              </form>
            )}
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
