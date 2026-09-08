export async function verifier(reponse: Response) {
  if (reponse.status === 401)
    window.dispatchEvent(new Event("connexion-requise"));
  if (!reponse.ok) {
    const donnees = await reponse.json().catch(() => ({}));
    const detail = donnees.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((e: { msg: string }) => e.msg).join(" · ")
          : "Une erreur est survenue.",
    );
  }
  return reponse;
}
export async function api<T>(
  chemin: string,
  options?: RequestInit,
): Promise<T> {
  const reponse = await verifier(
    await fetch(`/api${chemin}`, { cache: "no-store", ...options }),
  );
  return reponse.status === 204 ? (undefined as T) : reponse.json();
}
export const corps = (donnees: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(donnees),
});
export function erreurTexte(erreur: unknown) {
  return erreur instanceof Error ? erreur.message : "Une erreur est survenue.";
}

export async function flux(
  demande: unknown,
  recevoir: (type: string, donnees: unknown) => void,
  signal: AbortSignal,
) {
  const reponse = await verifier(
    await fetch("/api/chat", { ...corps(demande), signal }),
  );
  const lecteur = reponse.body?.getReader();
  if (!lecteur) throw new Error("Streaming indisponible.");
  const decodeur = new TextDecoder();
  let tampon = "";
  let termine = false;
  try {
    while (true) {
      const { done, value } = await lecteur.read();
      tampon += decodeur
        .decode(value, { stream: !done })
        .replace(/\r\n/g, "\n");
      let position;
      while ((position = tampon.indexOf("\n\n")) !== -1) {
        const evenement = tampon.slice(0, position);
        tampon = tampon.slice(position + 2);
        const type =
          evenement
            .split("\n")
            .find((l) => l.startsWith("event: "))
            ?.slice(7) || "message";
        const texte = evenement
          .split("\n")
          .filter((l) => l.startsWith("data: "))
          .map((l) => l.slice(6))
          .join("\n");
        if (texte) recevoir(type, JSON.parse(texte));
        if (type === "fin" || type === "erreur") termine = true;
      }
      if (done) break;
    }
    if (!termine)
      throw new Error(
        "La connexion a été interrompue avant la fin de la réponse.",
      );
  } finally {
    lecteur.releaseLock();
  }
}
