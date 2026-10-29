import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export const metadata: Metadata = {
  title: "SARATHI — Your Digital Charioteer for Seamless AICTE Regulatory Governance",
  description: "SARATHI: An integrated digital platform for transparent document verification, regulatory compliance, and AI-assisted scrutiny of technical institutions.",
  icons: {
    icon: "/assets/aicte_logo.png",
    apple: "/assets/aicte_logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased font-sans">
        <AuthProvider>
          <AuthGuard>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <TopBar />
                <main className="flex-1 overflow-y-auto p-6 bg-slate-50">
                  {children}
                </main>
              </div>
            </div>
          </AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
