import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Growly — маркетинговая система для бизнеса",
    template: "%s | Growly",
  },
  description:
    "Анализ рынка, конкурентные отчёты, контент-планы и черновики в одном рабочем пространстве.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
