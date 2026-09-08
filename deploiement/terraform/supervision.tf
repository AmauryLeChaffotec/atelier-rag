resource "aws_sns_topic" "alertes" {
  name = "${var.nom}-alertes"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alertes.arn
  protocol  = "email"
  endpoint  = var.email_alertes
}

locals {
  alarmes = {
    erreurs_http = {
      namespace = "AWS/ApplicationELB", metric = "HTTPCode_Target_5XX_Count", statistic = "Sum", threshold = 5, comparison = "GreaterThanOrEqualToThreshold", dimensions = {
        LoadBalancer = aws_lb.entree.arn_suffix
      }
    }

    cibles_indisponibles = {
      namespace = "AWS/ApplicationELB", metric = "HealthyHostCount", statistic = "Minimum", threshold = 1, comparison = "LessThanThreshold", dimensions = {
        LoadBalancer = aws_lb.entree.arn_suffix, TargetGroup = aws_lb_target_group.application.arn_suffix
      }
    }

    processeur = {
      namespace = "AWS/ECS", metric = "CPUUtilization", statistic = "Average", threshold = 80, comparison = "GreaterThanThreshold", dimensions = {
        ClusterName = aws_ecs_cluster.atelier.name, ServiceName = var.nom
      }
    }

    memoire = {
      namespace = "AWS/ECS", metric = "MemoryUtilization", statistic = "Average", threshold = 85, comparison = "GreaterThanThreshold", dimensions = {
        ClusterName = aws_ecs_cluster.atelier.name, ServiceName = var.nom
      }
    }

    stockage_rds = {
      namespace = "AWS/RDS", metric = "FreeStorageSpace", statistic = "Minimum", threshold = 2147483648, comparison = "LessThanThreshold", dimensions = {
        DBInstanceIdentifier = aws_db_instance.base.identifier
      }
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "application" {
  for_each            = local.alarmes
  alarm_name          = "${var.nom}-${each.key}"
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  statistic           = each.value.statistic
  period              = 60
  evaluation_periods  = 3
  threshold           = each.value.threshold
  comparison_operator = each.value.comparison
  dimensions          = each.value.dimensions
  treat_missing_data  = each.key == "cibles_indisponibles" ? "breaching" : "notBreaching"
  actions_enabled     = each.key != "cibles_indisponibles" || (var.etape == "application" && var.nombre_taches > 0)
  alarm_actions       = [aws_sns_topic.alertes.arn]
  ok_actions          = [aws_sns_topic.alertes.arn]
}

resource "aws_budgets_budget" "mensuel" {
  name         = var.nom
  budget_type  = "COST"
  limit_amount = tostring(var.budget_mensuel)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.email_alertes]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.email_alertes]
  }
}
