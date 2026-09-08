/** Lecture bornée, même sans Content-Length : protège la mémoire du conteneur. */
export async function lireCorps(requete: Request, limite = 16 * 1024 * 1024) {
  if (Number(requete.headers.get("content-length")) > limite)
    throw new RangeError("Requête trop volumineuse.");
  const lecteur = requete.body?.getReader();
  if (!lecteur) return undefined;
  const parties: Uint8Array[] = [];
  let taille = 0;
  try {
    while (true) {
      const { done, value } = await lecteur.read();
      if (done) break;
      taille += value.byteLength;
      if (taille > limite) {
        await lecteur.cancel();
        throw new RangeError("Requête trop volumineuse.");
      }
      parties.push(value);
    }
  } finally {
    lecteur.releaseLock();
  }
  const corps = new Uint8Array(taille);
  let position = 0;
  for (const partie of parties) {
    corps.set(partie, position);
    position += partie.length;
  }
  return corps;
}
