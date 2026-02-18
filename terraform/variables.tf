variable "app_name" {
  description = "Application name on Koyeb"
  type        = string
  default     = "stock-assistant"
}

variable "docker_image" {
  description = "Docker image to deploy (e.g., dockerhub-username/stock-assistant:latest)"
  type        = string
  default     = "kunsitudocker/stock-assistant:latest"
}

variable "registry_secret" {
  description = "Koyeb registry secret name for private registries"
  type        = string
  sensitive   = true
  default     = "dockersecret"
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "duck_db_token" {
  description = "MotherDuck token"
  type        = string
  sensitive   = true
}

variable "chainlit_auth_secret" {
  description = "Chainlit authentication secret"
  type        = string
  sensitive   = true
}

variable "auth_users" {
  description = "Chainlit auth users (format: email:password)"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Koyeb deployment region"
  type        = string
  default     = "fra"
}

variable "instance_type" {
  description = "Koyeb instance type"
  type        = string
  default     = "nano"
}

variable "koyeb_org" {
  description = "Your Koyeb organization name"
  type        = string
  default     = "kunsitu"
}