import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Your notes",
  description: "A place for your thoughts.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
