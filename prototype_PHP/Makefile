COMPOSE = docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs fclean

help: ## Show this help
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

up: ## Build and start (site: :8002, mail: :8027)
	$(COMPOSE) up --build -d

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f

fclean: ## Remove containers, images and volumes (deletes data)
	$(COMPOSE) down --rmi local -v
