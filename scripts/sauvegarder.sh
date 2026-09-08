#!/usr/bin/env bash
# À lancer sur le serveur Ubuntu. Les écritures doivent être suspendues pendant cette courte sauvegarde.
set -euo pipefail
cd "$(dirname "$0")/.."
commande=(docker compose -f compose.yaml -f deploiement/compose.aws.yaml)
instant=$(date -u +%Y%m%dT%H%M%SZ)
destination="sauvegardes/$instant"
mkdir -p "$destination"
chmod 700 sauvegardes "$destination"
# Arrêter les applications assure la cohérence entre originaux, chunks et dump SQL.
"${commande[@]}" stop interface serveur
trap '"${commande[@]}" start serveur interface' EXIT
"${commande[@]}" exec -T base pg_dump -U atelier -d atelier -Fc > "$destination/base.dump"
"${commande[@]}" run --rm --no-deps -T --user root serveur tar -C /donnees -czf - . > "$destination/fichiers.tar.gz"
chmod 600 "$destination/"*
echo "Sauvegarde créée : $destination. Copiez-la hors de cette machine."
