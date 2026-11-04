COMPOSE = docker compose

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps shell clean fclean

help: ## Show this help
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

up: ## Build and start app + mailpit
	$(COMPOSE) up --build -d

down: ## Stop and remove containers
	$(COMPOSE) down

restart: down up ## Restart everything

logs: ## Follow logs
	$(COMPOSE) logs -f

ps: ## Show containers
	$(COMPOSE) ps

shell: ## Open a shell in the app container
	$(COMPOSE) exec app sh

clean: ## Remove containers and images
	$(COMPOSE) down --rmi local

fclean: ## Also remove volumes (deletes uploads)
	$(COMPOSE) down --rmi local -v
