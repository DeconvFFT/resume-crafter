import type { Metadata } from "next";
import { Playfair_Display, Source_Serif_4, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "sonner";

// Editorial typography - Display font for headings
const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

// Editorial typography - Body font
const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-body",
  display: "swap",
});

// Editorial typography - Monospace for technical elements
const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Resume Crafter",
  description: "Craft the perfect resume for any job",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${sourceSerif.variable} ${ibmPlexMono.variable}`}
    >
      <body className="font-body antialiased">
        <Providers>
          {children}
          <Toaster
            position="top-right"
            richColors
            toastOptions={{
              style: {
                fontFamily: "var(--font-body)",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
