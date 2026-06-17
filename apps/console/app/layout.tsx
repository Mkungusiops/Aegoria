import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aegoria — Planetary Data Platform",
  description:
    "Aegoria is a planet-scale, market-agnostic, privacy-preserving big-data platform. One planet. Every domain. Data you can trust.",
  icons: { icon: "/favicon.svg" },
  metadataBase: new URL("https://aegoria.dev"),
  openGraph: {
    title: "Aegoria — Planetary Data Platform",
    description: "One planet. Every domain. Data you can trust.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#070A12",
};

// Render-blocking: apply the saved theme before first paint (no flash).
const themeInitScript = `(function(){try{var t=localStorage.getItem('aegoria-theme');if(t==='light'){document.documentElement.classList.add('light');}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
