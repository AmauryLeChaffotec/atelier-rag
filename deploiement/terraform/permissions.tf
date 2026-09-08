locals {
  confiance_ecs = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }, Action = "sts:AssumeRole"
      }
    ]
    }
  )
}

resource "aws_iam_role" "execution" {
  name               = "${var.nom}-execution"
  assume_role_policy = local.confiance_ecs
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = [aws_secretsmanager_secret.application.arn]
      }
    ]
    }
  )
}

resource "aws_iam_role" "application" {
  name               = "${var.nom}-application"
  assume_role_policy = local.confiance_ecs
}

# Le secret administrateur RDS est réservé à la tâche ponctuelle de migration.
resource "aws_iam_role" "preparation" {
  name               = "${var.nom}-preparation"
  assume_role_policy = local.confiance_ecs
}

resource "aws_iam_role_policy_attachment" "preparation" {
  role       = aws_iam_role.preparation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "preparation" {
  role = aws_iam_role.preparation.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.application.arn, aws_db_instance.base.master_user_secret[0].secret_arn]
    }]
  })
}

resource "aws_iam_role_policy" "fichiers" {
  role = aws_iam_role.application.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = ["${aws_s3_bucket.documents.arn}/*"]
      }
    ]
    }
  )
}
