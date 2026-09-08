import type { Metadata } from "next";
import { EB_Garamond, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";

import { AppShell } from "@/components/shell/app-shell";
import { InspectorProvider } from "@/components/shell/inspector-provider";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

/**
 * IBM Plex over the design-system search's Fira suggestion: it reads as
 * civic-tech infrastructure rather than a startup dashboard, ships real
 * tabular figures, and IBM Plex Sans Devanagari exists in the same family --
 * this product's subject matter is bilingual Hindi/English package labels.
 */
const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

/** Used for exactly one thing: quoted statute text (legal-quote utility
 * class), so a citation reads as a different kind of text from UI copy. */
const ebGaramond = EB_Garamond({
  variable: "--font-eb-garamond",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Legal Metrology Compliance Scanner — SIH 26034",
  description:
    "Advisory pre-screening signal for Legal Metrology (Packaged Commodities) Rules, 2011 compliance.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexMono.variable} ${ebGaramond.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <InspectorProvider>
          <TooltipProvider delayDuration={200}>
            <AppShell>{children}</AppShell>
            <Toaster position="bottom-right" />
          </TooltipProvider>
        </InspectorProvider>
      </body>
    </html>
  );
}
