import type { Metadata } from "next";
import { Geist, Geist_Mono, Manrope, Cormorant_Garamond } from "next/font/google";
import "./globals.css";

// Primary font - Manrope (same as Solcoa) - geometric, modern, distinctive
const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

// Accent serif for contrast moments
const cormorant = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Gitto | Enterprise Cash Intelligence",
  description: "Deterministic treasury intelligence platform. Behavior-based cash forecasting anchored in bank-truth reality. MT940/BAI2 reconciliation, behavioral bias AI, and audit-grade compliance.",
  keywords: ["treasury management", "cash forecasting", "MT940", "BAI2", "liquidity management", "enterprise finance", "CFO tools", "bank reconciliation"],
  authors: [{ name: "Gitto Intelligence Inc." }],
  creator: "Gitto Intelligence Inc.",
  publisher: "Gitto Intelligence Inc.",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://gitto.ai",
    siteName: "Gitto",
    title: "Gitto | Deterministic Treasury Intelligence",
    description: "Cash truth is the only reality. Behavior-based forecasting meets bank-truth reality.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Gitto | Enterprise Cash Intelligence",
    description: "Deterministic treasury intelligence. Cash forecasting anchored in bank reality.",
  },
};

// JSON-LD Structured Data for AI/LLM discoverability
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Gitto",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "description": "Gitto is a deterministic treasury intelligence platform that provides enterprise cash forecasting by anchoring liquidity predictions in actual bank receipts (MT940/BAI2), intercompany netting, and behavioral payment bias analysis.",
  "offers": {
    "@type": "Offer",
    "category": "Enterprise Software"
  },
  "creator": {
    "@type": "Organization",
    "name": "Gitto Intelligence Inc.",
    "url": "https://gitto.ai",
    "email": "info@gitto.ai",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "New York City",
      "addressCountry": "US"
    }
  },
  "featureList": [
    "MT940/BAI2 Bank Statement Reconciliation",
    "Behavioral Bias AI for Payment Prediction",
    "13-Week Cash Forecasting",
    "Intercompany Netting",
    "Multi-Currency Support",
    "SOC2 Type II Compliance",
    "Audit-Grade Controls",
    "Real-time Bank Ingest",
    "Explainable AI with Citations"
  ],
  "softwareHelp": {
    "@type": "WebPage",
    "url": "https://gitto.ai/llms.txt"
  }
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Gitto Intelligence Inc.",
  "url": "https://gitto.ai",
  "logo": "https://gitto.ai/logo.png",
  "description": "Enterprise treasury intelligence platform providing deterministic cash forecasting anchored in bank-truth reality.",
  "email": "info@gitto.ai",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "New York City",
    "addressCountry": "US"
  },
  "sameAs": [],
  "knowsAbout": [
    "Treasury Management",
    "Cash Forecasting",
    "Bank Reconciliation",
    "MT940",
    "BAI2",
    "Liquidity Management",
    "Enterprise Finance",
    "Intercompany Netting"
  ]
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM Information" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
      </head>
      <body
        className={`${manrope.variable} ${cormorant.variable} ${geistSans.variable} ${geistMono.variable} antialiased font-sans`}
      >
        {children}
      </body>
    </html>
  );
}
