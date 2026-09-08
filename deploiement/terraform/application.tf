resource "aws_cloudwatch_log_group" "application" {
  name              = "/ecs/${var.nom}"
  retention_in_days = var.jours_journaux
}

resource "aws_cloudwatch_log_group" "base" {
  name              = "/aws/rds/instance/${var.nom}/postgresql"
  retention_in_days = var.jours_journaux
}

resource "aws_ecs_cluster" "atelier" {
  name = var.nom
  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

locals {
  journaux = {
    logDriver = "awslogs", options = {
      "awslogs-group" = aws_cloudwatch_log_group.application.name, "awslogs-region" = var.region, "awslogs-stream-prefix" = "conteneurs"
    }
  }

  postgres = [
    {
      name = "POSTGRES_HOTE", value = aws_db_instance.base.address
    },
    {
      name = "POSTGRES_BASE", value = "atelier"
    },
    {
      name = "POSTGRES_SSLMODE", value = "verify-full"
    },
    {
      name = "POSTGRES_CERTIFICAT", value = "/projet/certificats/rds.pem"
    }

  ]
  secrets_application = [for nom, cle in {
    OPENAI_API_KEY = "openai_api_key", MISTRAL_API_KEY = "mistral_api_key", CLE_ACCES = "cle_acces", POSTGRES_MOT_DE_PASSE = "postgres_mot_de_passe"
    }
    : {
      name = nom, valueFrom = "${aws_secretsmanager_secret.application.arn}:${cle}::"
    }
  ]
}

resource "aws_ecs_task_definition" "preparation" {
  count                    = var.etape == "socle" ? 0 : 1
  family                   = "${var.nom}-preparation"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.preparation.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name        = "preparation", image = "${aws_ecr_repository.images["serveur"].repository_url}:${coalesce(var.version_preparation, var.version_image)}", essential = true,
    command     = [".venv/bin/python", "-m", "application.base.preparer"],
    environment = local.postgres,
    secrets = [
      {
        name = "POSTGRES_UTILISATEUR", valueFrom = "${aws_db_instance.base.master_user_secret[0].secret_arn}:username::"
      },
      {
        name = "POSTGRES_MOT_DE_PASSE", valueFrom = "${aws_db_instance.base.master_user_secret[0].secret_arn}:password::"
      },
      {
        name = "MOT_DE_PASSE_APPLICATION", valueFrom = "${aws_secretsmanager_secret.application.arn}:postgres_mot_de_passe::"
      }

    ], logConfiguration = local.journaux
    }
  ])
}

resource "aws_ecs_task_definition" "application" {
  count                    = var.etape == "socle" ? 0 : 1
  family                   = var.nom
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.application.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name = "serveur", image = "${aws_ecr_repository.images["serveur"].repository_url}:${var.version_image}", essential = true,
      cpu  = 384, memory = 1536, stopTimeout = 120,
      portMappings = [{
        containerPort = 8000, protocol = "tcp"
        }
      ],
      environment = concat(local.postgres, [
        {
          name = "ENVIRONNEMENT", value = "production"
        },
        {
          name = "POSTGRES_UTILISATEUR", value = "atelier"
        },
        {
          name = "FOURNISSEUR_IA", value = "openai"
        },
        {
          name = "OPENAI_GENERATION", value = var.openai_generation
        },
        {
          name = "OPENAI_EMBEDDING", value = var.openai_embedding
        },
        {
          name = "MISTRAL_OCR", value = var.mistral_ocr
        },
        {
          name = "STOCKAGE", value = "s3"
        },
        {
          name = "S3_BUCKET", value = aws_s3_bucket.documents.id
        },
        {
          name = "AWS_DEFAULT_REGION", value = var.region
        },
        {
          name = "MIGRER_AU_DEMARRAGE", value = "false"
        },
        {
          name = "EXECUTER_INDEXATIONS", value = "true"
        }

      ]),
      secrets = local.secrets_application,
      healthCheck = {
        command = ["CMD-SHELL", ".venv/bin/python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/sante')\""], interval = 15, timeout = 5, retries = 3, startPeriod = 60
      },
      logConfiguration = local.journaux
    },
    {
      name = "interface", image = "${aws_ecr_repository.images["interface"].repository_url}:${var.version_image}", essential = true,
      cpu  = 128, memory = 384, stopTimeout = 120,
      portMappings = [{
        containerPort = 3000, protocol = "tcp"
        }
      ],
      dependsOn = [{
        containerName = "serveur", condition = "HEALTHY"
        }
      ],
      environment = [{
        name = "API_INTERNE", value = "http://127.0.0.1:8000"
        }, {
        name = "COOKIE_SECURISE", value = "true"
        }
      ],
      healthCheck = {
        command = ["CMD-SHELL", "node -e \"fetch('http://127.0.0.1:3000/api/sante').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))\""], interval = 20, timeout = 5, retries = 3, startPeriod = 60
      },
      logConfiguration = local.journaux
    }

  ])
}

resource "aws_acm_certificate" "site" {
  domain_name       = var.domaine
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "site" {
  count                   = var.etape == "application" ? 1 : 0
  certificate_arn         = aws_acm_certificate.site.arn
  validation_record_fqdns = [for option in aws_acm_certificate.site.domain_validation_options : option.resource_record_name]
}

resource "aws_lb" "entree" {
  depends_on                 = [aws_route_table_association.publiques]
  name                       = var.nom
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.entree.id]
  subnets                    = aws_subnet.publics[*].id
  idle_timeout               = 400
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "application" {
  name                 = var.nom
  port                 = 3000
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = aws_vpc.atelier.id
  deregistration_delay = 120
  health_check {
    path                = "/api/sante"
    matcher             = "200"
    interval            = 20
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.entree.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count             = var.etape == "application" ? 1 : 0
  load_balancer_arn = aws_lb.entree.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.site[0].certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.application.arn
  }
}

resource "aws_ecs_service" "application" {
  count                              = var.etape == "application" ? 1 : 0
  name                               = var.nom
  cluster                            = aws_ecs_cluster.atelier.id
  task_definition                    = aws_ecs_task_definition.application[0].arn
  launch_type                        = "FARGATE"
  platform_version                   = "1.4.0"
  desired_count                      = var.nombre_taches
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  health_check_grace_period_seconds = 120
  wait_for_steady_state             = true
  network_configuration {
    subnets          = aws_subnet.publics[*].id
    security_groups  = [aws_security_group.application.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.application.arn
    container_name   = "interface"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.https, aws_iam_role_policy.secrets, aws_iam_role_policy.fichiers, aws_iam_role_policy_attachment.execution]
}
