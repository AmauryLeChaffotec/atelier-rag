# Certificats publics RDS

`rds.pem` est le bundle public d’autorités de certification AWS RDS, téléchargé le 8 septembre 2026 depuis [AWS Trust Store](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem). Il ne contient aucune clé privée.

FastAPI l’utilise avec `sslmode=verify-full` pour vérifier le certificat et le nom DNS de RDS. En cas de renouvellement des autorités annoncé par AWS, remplacez ce fichier par le bundle officiel, reconstruisez l’image serveur et déployez un nouveau tag :

```powershell
# Depuis la racine du dépôt.
Invoke-WebRequest https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -OutFile serveur/certificats/rds.pem
```

La durée du certificat du serveur RDS et celle des autorités sont différentes. Ne désactivez pas la vérification TLS pour contourner un problème de certificat. [Documentation RDS PostgreSQL SSL/TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).
