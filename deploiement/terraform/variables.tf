variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "nom" {
  type    = string
  default = "atelier-rag"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.nom))
    error_message = "Utilisez 3 à 20 caractères : lettres minuscules, chiffres et tirets."
  }
}

variable "domaine" {
  type        = string
  description = "Sous-domaine dont vous pouvez modifier le DNS, par exemple rag.mondomaine.fr."
  validation {
    condition     = can(regex("^[a-z0-9.-]+\\.[a-z]{2,}$", var.domaine))
    error_message = "Indiquez un nom DNS, sans https:// ni chemin."
  }
}

variable "email_alertes" {
  type        = string
  description = "Email pour les alarmes et le budget AWS."
}

variable "budget_mensuel" {
  type    = number
  default = 100
}

variable "etape" {
  type        = string
  default     = "socle"
  description = "socle : ressources ; preparation : images et tâche de migration ; application : service ECS public HTTPS."
  validation {
    condition     = contains(["socle", "preparation", "application"], var.etape)
    error_message = "Étapes possibles : socle, preparation, application."
  }
}

variable "version_image" {
  type    = string
  default = "a-publier"
}

variable "version_preparation" {
  type        = string
  default     = null
  description = "Image des migrations. Permet de migrer avant de mettre à jour le service existant."
}

variable "nombre_taches" {
  type    = number
  default = 1
  validation {
    condition     = var.nombre_taches >= 0 && var.nombre_taches <= 2 && floor(var.nombre_taches) == var.nombre_taches
    error_message = "Pour ce projet, utilisez 0, 1 ou 2 tâches."
  }
}

variable "classe_rds" {
  type    = string
  default = "db.t4g.micro"
}

variable "stockage_rds_go" {
  type    = number
  default = 20
  validation {
    condition     = var.stockage_rds_go >= 20 && var.stockage_rds_go <= 40
    error_message = "Choisissez entre 20 et 40 Go, la limite de stockage automatique de cette configuration."
  }
}

variable "proteger_donnees" {
  type    = bool
  default = true
}

variable "jours_journaux" {
  type    = number
  default = 7
}

variable "openai_generation" {
  type    = string
  default = "gpt-4o-mini"
}

variable "openai_embedding" {
  type    = string
  default = "text-embedding-3-small"
}

variable "mistral_ocr" {
  type    = string
  default = "mistral-ocr-latest"
}
