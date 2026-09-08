import Link from "next/link";
export default function PageIntrouvable() {
  return <div className="page"><h1>Cette page n’existe pas.</h1><p>Retrouvez votre documentation dans l’atelier.</p><Link className="bouton primaire" href="/">Revenir à la conversation</Link></div>;
}
