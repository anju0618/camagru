COMPOSE = docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs test overlays fclean

help: ## Show this help
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

up: ## Build and start (site: :8001, mail: :8026)
	$(COMPOSE) up --build -d

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f

test: ## Run unit tests
	python3 -m unittest discover -s tests

overlays: ## Regenerate public/overlays/*.png
	python3 tools/make_overlays.py

fclean: ## Remove containers, images and volumes (deletes data)
	$(COMPOSE) down --rmi local -v
