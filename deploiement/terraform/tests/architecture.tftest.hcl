# Toutes les réponses AWS sont simulées. Ce test ne crée aucune ressource.
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["eu-west-3a", "eu-west-3b"] }
  }
  mock_resource "aws_db_instance" {
    defaults = {
      address            = "atelier.example.rds.amazonaws.com"
      master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:eu-west-3:123456789012:secret:rds-test", secret_status = "active", kms_key_id = "test" }]
    }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/test" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::test" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:eu-west-3:123456789012:test" }
  }
  mock_resource "aws_secretsmanager_secret" {
    defaults = { arn = "arn:aws:secretsmanager:eu-west-3:123456789012:secret:application-test" }
  }
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-3:123456789012:loadbalancer/app/test/1234567890123456" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-3:123456789012:targetgroup/test/1234567890123456" }
  }
  mock_resource "aws_acm_certificate" {
    defaults = { arn = "arn:aws:acm:eu-west-3:123456789012:certificate/12345678-1234-1234-1234-123456789012" }
  }
  mock_resource "aws_acm_certificate_validation" {
    defaults = { certificate_arn = "arn:aws:acm:eu-west-3:123456789012:certificate/12345678-1234-1234-1234-123456789012" }
  }
}

variables {
  domaine       = "rag.example.com"
  email_alertes = "test@example.com"
  version_image = "version-test"
}

run "socle_sans_service" {
  command = plan
  assert {
    condition     = length(aws_ecs_service.application) == 0 && length(aws_ecs_task_definition.application) == 0
    error_message = "Le socle doit pouvoir être créé avant publication des images et secrets."
  }
  assert {
    condition     = !aws_db_instance.base.publicly_accessible && aws_db_instance.base.storage_encrypted && aws_db_instance.base.deletion_protection
    error_message = "RDS doit rester privé, chiffré et protégé contre la suppression."
  }
}

run "migration_avant_service" {
  command = plan
  variables {
    etape = "preparation"
  }
  assert {
    condition     = length(aws_ecs_task_definition.preparation) == 1 && length(aws_ecs_service.application) == 0
    error_message = "La base doit pouvoir être préparée avant le premier démarrage."
  }
}

run "application_et_migration_independantes" {
  command = apply
  variables {
    etape               = "application"
    version_preparation = "prochaine-version"
  }
  assert {
    condition     = aws_ecs_service.application[0].desired_count == 1 && aws_ecs_service.application[0].deployment_circuit_breaker[0].rollback
    error_message = "Une tâche avec retour automatique à la version précédente est attendue."
  }
  assert {
    condition     = endswith(jsondecode(aws_ecs_task_definition.preparation[0].container_definitions)[0].image, ":prochaine-version") && endswith(jsondecode(aws_ecs_task_definition.application[0].container_definitions)[0].image, ":version-test")
    error_message = "Migrer ne doit pas modifier l’image du service actif."
  }
  assert {
    condition     = contains(jsondecode(aws_ecs_task_definition.application[0].container_definitions)[0].environment, { name = "MIGRER_AU_DEMARRAGE", value = "false" })
    error_message = "Les migrations AWS doivent être exécutées par la tâche de préparation."
  }
  assert {
    condition     = length(jsondecode(aws_iam_role_policy.secrets.policy).Statement[0].Resource) == 1 && jsondecode(aws_iam_role_policy.secrets.policy).Statement[0].Resource[0] == aws_secretsmanager_secret.application.arn
    error_message = "Le service courant ne doit pas pouvoir charger le secret administrateur RDS."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.documents.block_public_policy && aws_s3_bucket_versioning.documents.versioning_configuration[0].status == "Enabled"
    error_message = "Les fichiers doivent rester privés et versionnés."
  }
}
