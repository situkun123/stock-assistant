terraform {
  required_providers {
    koyeb = {
      source  = "koyeb/koyeb"
      version = "~> 0.1"
    }
  }
}

provider "koyeb" {
}

resource "koyeb_secret" "dockerhub" {
  name = "dockersecret"
  
  registry {
    username = var.dockerhub_username
    password = var.dockerhub_token
  }
}

resource "koyeb_app" "stock_assistant" {
  name = var.app_name
}

resource "koyeb_service" "stock_assistant" {
  app_name = koyeb_app.stock_assistant.name

  definition {
    name    = "${var.app_name}-service"
    regions = [var.region]
    docker {
      image                 = var.docker_image    # e.g., "your-dockerhub-username/stock-assistant:latest"
      image_registry_secret = koyeb_secret.dockerhub.name
    }

    env {
      key   = "OPENAI_API_KEY"
      value = var.openai_api_key
    }

    env {
      key   = "DUCK_DB_TOKEN"
      value = var.duck_db_token
    }

    env {
      key   = "CHAINLIT_AUTH_SECRET"
      value = var.chainlit_auth_secret
    }

    env {
      key   = "AUTH_USERS"
      value = var.auth_users
    }

    # Port configuration
    ports {
      port     = 8000
      protocol = "http"
    }

    routes {
      port = 8000
      path = "/"
    }

    # Health check
    health_checks {
      http {
        port = 8000
        path = "/health"
      }
    }

    scalings {
      min = 0
      max = 0
    }

    instance_types {
      type = "free" # nano, micro, small, medium, large, xlarge
    }
  }

  depends_on = [koyeb_app.stock_assistant]
}