import { NextRequest, NextResponse } from "next/server";
export async function POST(requete: NextRequest) {
  const { cle } = await requete.json();
  if (typeof cle !== "string" || cle.length > 256)
    return new Response(null, { status: 400 });
  try {
    const resultat = await fetch(
      `${process.env.API_INTERNE || "http://127.0.0.1:8000"}/api/configuration`,
      {
        headers: { "x-cle-acces": cle },
        cache: "no-store",
      },
    );
    if (!resultat.ok)
      return NextResponse.json(
        { detail: "Clé incorrecte ou serveur indisponible." },
        { status: resultat.status },
      );
    const reponse = NextResponse.json({ connecte: true });
    reponse.cookies.set("atelier-acces", cle, {
      httpOnly: true,
      sameSite: "strict",
      secure: process.env.COOKIE_SECURISE === "true",
      path: "/",
      maxAge: 86400,
    });
    return reponse;
  } catch {
    return NextResponse.json(
      { detail: "Serveur indisponible." },
      { status: 502 },
    );
  }
}
export async function DELETE() {
  const reponse = NextResponse.json({ connecte: false });
  reponse.cookies.delete("atelier-acces");
  return reponse;
}
