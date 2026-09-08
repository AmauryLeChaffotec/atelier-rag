import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const origine = () => process.env.API_INTERNE || "http://127.0.0.1:8000";

async function transmettre(
  requete: NextRequest,
  contexte: { params: Promise<{ chemin: string[] }> },
) {
  const { chemin } = await contexte.params;
  if (chemin.some((c) => !/^[\p{L}\p{N}_. -]+$/u.test(c) || c === ".."))
    return new Response(null, { status: 400 });
  const cle = requete.cookies.get("atelier-acces")?.value || "";
  const entetes = new Headers({ "x-cle-acces": cle });
  const type = requete.headers.get("content-type");
  if (type) entetes.set("content-type", type);
  try {
    const reponse = await fetch(
      `${origine()}/api/${chemin.map(encodeURIComponent).join("/")}${requete.nextUrl.search}`,
      {
        method: requete.method,
        headers: entetes,
        cache: "no-store",
        redirect: "manual",
        signal: requete.signal,
        body: ["GET", "HEAD"].includes(requete.method)
          ? undefined
          : await requete.arrayBuffer(),
      },
    );
    const retour = new Headers();
    for (const nom of [
      "content-type",
      "content-disposition",
      "cache-control",
      "retry-after",
    ]) {
      const valeur = reponse.headers.get(nom);
      if (valeur) retour.set(nom, valeur);
    }
    retour.set("X-Accel-Buffering", "no");
    return new Response(reponse.body, {
      status: reponse.status,
      headers: retour,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Le serveur ne répond pas. Vérifiez que les conteneurs sont démarrés.",
      },
      { status: 502 },
    );
  }
}
export {
  transmettre as GET,
  transmettre as POST,
  transmettre as PUT,
  transmettre as DELETE,
};
