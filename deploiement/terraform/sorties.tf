output "configuration" {
  description = "Configuration publique pour les scripts de déploiement ; aucun secret."
  value = {
    region  = var.region, nom = var.nom, compte = data.aws_caller_identity.compte.account_id,
    cluster = aws_ecs_cluster.atelier.name, service = var.nom,
    repositories = {
      for nom, depot in aws_ecr_repository.images : nom => depot.repository_url
    },
    secret_application  = aws_secretsmanager_secret.application.arn,
    base                = aws_db_instance.base.identifier, bucket = aws_s3_bucket.documents.id,
    subnet_group_base   = aws_db_subnet_group.base.name,
    security_group_base = aws_security_group.base.id,
    parametres_base     = aws_db_parameter_group.base.name,
    tache_preparation   = try(aws_ecs_task_definition.preparation[0].arn, null),
    subnets             = aws_subnet.publics[*].id, security_group = aws_security_group.application.id,
    journaux            = aws_cloudwatch_log_group.application.name,
    url                 = "https://${var.domaine}", cible_dns = aws_lb.entree.dns_name,
    validation_dns = [for option in aws_acm_certificate.site.domain_validation_options : {
      nom = option.resource_record_name, type = option.resource_record_type, valeur = option.resource_record_value
      }
    ]
  }
}
