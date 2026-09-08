resource "aws_ecr_repository" "images" {
  for_each             = toset(["serveur", "interface"])
  name                 = "${var.nom}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  force_delete = false
}

resource "aws_ecr_lifecycle_policy" "sans_tag" {
  for_each   = aws_ecr_repository.images
  repository = each.value.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1, description = "Nettoyer uniquement les images sans tag après 7 jours", selection = {
        tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 7
        }, action = {
        type = "expire"
      }
      }
    ]
    }
  )
}

resource "aws_s3_bucket" "documents" {
  bucket        = "${local.prefixe}-documents"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"], Condition = {
        Bool = {
          "aws:SecureTransport" = "false"
        }
      }
      }
    ]
    }
  )
}

resource "aws_s3_bucket_lifecycle_configuration" "versions" {
  bucket     = aws_s3_bucket.documents.id
  depends_on = [aws_s3_bucket_versioning.documents]
  rule {
    id     = "anciennes-versions"
    status = "Enabled"
    filter {
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_db_subnet_group" "base" {
  name       = "${var.nom}-prive"
  subnet_ids = aws_subnet.prives[*].id
}

resource "aws_db_parameter_group" "base" {
  name   = "${var.nom}-postgres17"
  family = "postgres17"
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

resource "aws_db_instance" "base" {
  depends_on = [aws_cloudwatch_log_group.base]

  identifier                      = var.nom
  engine                          = "postgres"
  engine_version                  = "17"
  engine_lifecycle_support        = "open-source-rds-extended-support-disabled"
  instance_class                  = var.classe_rds
  db_name                         = "atelier"
  username                        = "administrateur"
  manage_master_user_password     = true
  allocated_storage               = var.stockage_rds_go
  max_allocated_storage           = 40
  storage_type                    = "gp3"
  storage_encrypted               = true
  multi_az                        = false
  publicly_accessible             = false
  db_subnet_group_name            = aws_db_subnet_group.base.name
  vpc_security_group_ids          = [aws_security_group.base.id]
  parameter_group_name            = aws_db_parameter_group.base.name
  backup_retention_period         = 7
  backup_window                   = "02:00-03:00"
  maintenance_window              = "sun:03:30-sun:04:30"
  auto_minor_version_upgrade      = true
  deletion_protection             = var.proteger_donnees
  skip_final_snapshot             = false
  final_snapshot_identifier       = "${var.nom}-sauvegarde-finale"
  copy_tags_to_snapshot           = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
}

resource "aws_secretsmanager_secret" "application" {
  name                    = "${var.nom}/application"
  description             = "Clés OpenAI/Mistral, clé d’accès et mot de passe PostgreSQL applicatif. Valeurs ajoutées hors Terraform."
  recovery_window_in_days = 7
}
