import { Geist, Geist_Mono, JetBrains_Mono, Barlow, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// WarpSense analysis surface font — only used by components/analysis/
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-warp-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

// Marketing (V1 Instrument) — Barlow display/body, IBM Plex Mono for chrome/data
const barlow = Barlow({
  variable: "--font-barlow",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${jetbrainsMono.variable} ${barlow.variable} ${plexMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
