import type { Metadata } from "next";
import { Cadre } from "@/composants/cadre";
import "./apparence.css";
export const metadata: Metadata = {
  title: "Atelier — Votre documentation, en conversation",
  description:
    "Explorez vos documents et comprenez chaque étape du RAG, avec Ollama et pgvector.",
};
export default function Disposition({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head><link rel="stylesheet" href="/polices/polices.css" /></head>
      <body>
        <Cadre>{children}</Cadre>
      </body>
    </html>
  );
}
