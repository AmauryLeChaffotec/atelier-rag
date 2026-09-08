# Le bucket est créé une seule fois avec les commandes du guide.
# Son nom personnel se trouve dans etat.s3.hcl, ignoré par Git.
terraform {
  backend "s3" {}
}
