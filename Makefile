NAME = camagru

.DEFAULT_GOAL := help
.PHONY: help build run shell clean

help: ## Show this help
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

build: ## Build the image
	docker build -t $(NAME) .

run: build ## Build and run on localhost:8000
	docker run --rm -p 8000:8000 $(NAME)

shell: build ## Open a shell in the container
	docker run --rm -it $(NAME) sh

clean: ## Remove the image
	docker rmi $(NAME)
