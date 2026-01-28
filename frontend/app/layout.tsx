import type { Metadata } from "next";
import { Plus_Jakarta_Sans, DM_Sans, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "sonner";
import Loading from "./loading";

// Premium Display Font - Modern geometric for headings
const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["200", "300", "400", "500", "600", "700", "800"],
});

// Premium Body Font - Clean and readable
const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"],
});

// Monospace font for code elements
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["100", "200", "300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Resume Crafter | Professional Resume Builder",
  description: "Craft the perfect resume for any job with AI-powered precision",
  keywords: ["resume", "CV", "career", "job application", "professional"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${plusJakartaSans.variable} ${dmSans.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="font-sans antialiased bg-background text-foreground">
        <Providers>
          <Suspense fallback={<Loading />}>
            {children}
          </Suspense>
          <Toaster
            position="top-right"
            richColors
            theme="dark"
            toastOptions={{
              style: {
                fontFamily: "var(--font-sans)",
                background: "rgba(18, 18, 26, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(12px)",
              },
              classNames: {
                toast: "glass-card",
                title: "font-semibold",
                description: "text-muted-foreground",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
