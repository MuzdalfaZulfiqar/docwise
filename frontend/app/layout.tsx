import type { Metadata } from "next";
import { Instrument_Sans, Newsreader } from "next/font/google";
import { APP_NAME } from "../lib/api";
// @ts-ignore Next.js resolves global CSS imports during its build.
import "./globals.css";

const sans = Instrument_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const serif = Newsreader({ subsets: ["latin"], variable: "--font-serif", display: "swap" });

export const metadata: Metadata = {
  title: APP_NAME,
  description: "Ask your documents. Check the source.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
